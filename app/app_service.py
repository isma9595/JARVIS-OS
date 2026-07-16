"""Safe app-facing service layer for JARVIS.

The service is a boundary for future UI code. It can inspect command metadata
and delegate execution to CommandProcessor, but it does not execute commands,
call providers, route actions, read arbitrary files, or persist prompts.
"""

from dataclasses import dataclass
from enum import Enum
import re
from threading import Lock

from app.app_contracts import (
    APP_CONTRACT_SCHEMA_NAME,
    APP_CONTRACT_VERSION,
    AppCommandCard,
    AppClarificationOption,
    AppContractManifest,
    AppContractStatus,
    AppExecutionContract,
    AppPreviewContract,
    AppStatusCard,
    AppVoiceRequestResult,
    safe_contract_text,
)
from app.intent_resolver import (
    ClarificationState,
    HybridIntentResolver,
    IntentKind,
    ResolutionStatus,
    option_matches_text,
)
from app.conversational_loop import (
    ConversationalRequest,
    ConversationalResult,
    SafeConversationalLoop,
)
from core.command_registry import (
    CommandCategory,
    CommandMetadata,
    CommandRegistry,
    DEFAULT_COMMAND_REGISTRY,
)
from core.policy_boundary import (
    PolicyCapability,
    PolicyDecisionBoundary,
    PolicyDecisionType,
    PolicyRequest,
    policy_request_from_metadata,
)
from core.execution_coordinator import ExecutionCoordinator
from core.execution_journal import ExecutionOperation, safe_journal_text
from language.language_manager import ApplicationLanguageManager
from platform_adapters.local_filesystem import WindowsLocalFileSystemAdapter
from voice.audio_lifecycle import AudioLifecycleController, AudioLifecycleStatus
from voice.russian_voice_normalizer import normalize_russian_voice_text
from ai.secure_provider_runtime import SecureProviderRuntime
from workflows.document_review import (
    LocalTextDocumentReviewWorkflow,
    DocumentReviewProposal,
    DocumentReviewRunState,
    DocumentReviewWorkflowError,
    WORKFLOW_ID as DOCUMENT_REVIEW_WORKFLOW_ID,
)
from workflows.contracts import WorkflowRunSnapshot, WorkflowStepResult, WorkflowStepStatus
from workflows.runner import WorkflowExecutableStep, WorkflowRunner


class AppCommandSource(Enum):
    CLI = "cli"
    DESKTOP_UI = "desktop_ui"
    VOICE = "voice"
    TEST = "test"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AppCommandPreview:
    input_text: str
    normalized_text: str
    registry_match_id: str | None
    title_ru: str | None
    category: str | None
    risk_level: str | None
    read_only: bool
    voice_auto_allowed: bool
    requires_confirmation: bool
    requires_network: bool
    requires_ai_key: bool
    requires_privacy_check: bool
    app_ready: bool
    known_command: bool
    safe_summary_ru: str


@dataclass(frozen=True)
class AppCommandResult:
    ok: bool
    input_text: str
    output_text: str
    source: AppCommandSource
    registry_match_id: str | None
    category: str | None
    risk_level: str | None
    executed: bool
    requires_confirmation: bool
    network_may_be_used: bool
    response_executed_as_command: bool
    error: str | None
    intent_resolution: object | None = None
    requires_clarification: bool = False
    clarification_question: str | None = None
    clarification_options: tuple[AppClarificationOption, ...] = ()
    policy_decision: object | None = None
    operation_id: str | None = None
    operation_status: str | None = None
    idempotency_key: str | None = None
    duplicate_suppressed: bool = False
    cancellable: bool = False
    workflow_id: str | None = None
    workflow_status: str | None = None
    current_step_id: str | None = None
    current_step_name: str | None = None
    completed_steps: tuple[str, ...] = ()
    total_steps: int | None = None
    progress_percent: int | None = None
    awaiting_confirmation: bool = False
    source_filename: str | None = None
    proposed_output_filename: str | None = None
    issue_count: int | None = None
    issue_summaries: tuple[dict[str, object], ...] = ()
    proposed_output_path: str | None = None
    saved: bool = False
    verified: bool = False
    user_message: str | None = None


@dataclass(frozen=True)
class PendingAppConfirmation:
    operation_id: str
    idempotency_key: str
    request_fingerprint: str
    command_text: str
    source: str
    resolution: object | None = None


@dataclass(frozen=True)
class PendingDocumentReviewConfirmation:
    operation_id: str
    idempotency_key: str
    request_fingerprint: str
    command_text: str
    source: str
    state: DocumentReviewRunState


@dataclass(frozen=True)
class AppStatusSnapshot:
    app_service_enabled: bool
    execution_source: str
    command_registry_enabled: bool
    command_count: int
    categories_count: int
    ui_ready: bool
    installer_ready: bool
    secure_key_storage_ready: bool
    secure_provider_runtime_ready: bool
    network_default: bool
    dry_run_default: bool
    privacy_boundary_active: bool
    fallback_explicit_only: bool
    consensus_explicit_only: bool
    voice_safety_active: bool


class JarvisAppService:
    """Stable boundary for app/UI code."""

    PREVIEW_PREFIX_ALIASES = (
        "app preview:",
        "предпросмотр команды:",
        "preview command:",
        "предварительная проверка команды:",
    )
    DOCUMENT_REVIEW_PREFIX = "\u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442 "

    def __init__(
        self,
        command_processor=None,
        command_registry=None,
        one_shot_voice_recognition=None,
        language_manager=None,
        local_filesystem=None,
    ):
        self.command_registry = command_registry or DEFAULT_COMMAND_REGISTRY
        if command_processor is None:
            from core.command_processor import CommandProcessor

            command_processor = CommandProcessor(command_registry=self.command_registry)
        self.command_processor = command_processor
        self.one_shot_voice_recognition = (
            one_shot_voice_recognition
            or getattr(command_processor, "one_shot_vosk_real_recognition", None)
        )
        self.language_manager = (
            language_manager
            or ApplicationLanguageManager.from_profile(
                getattr(command_processor, "user_profile", None)
            )
        )
        self._one_shot_voice_lock = Lock()
        self.audio_lifecycle_controller = self._build_audio_lifecycle_controller()
        self.conversational_loop = SafeConversationalLoop(
            app_service=self,
            command_registry=self.command_registry,
        )
        self.intent_resolver = HybridIntentResolver(self.command_registry)
        self._pending_clarification: ClarificationState | None = None
        self._pending_clarification_operation_id: str | None = None
        self._pending_confirmation: PendingAppConfirmation | None = None
        self._pending_document_review: PendingDocumentReviewConfirmation | None = None
        self._operation_results: dict[str, AppCommandResult] = {}
        self.policy_boundary = PolicyDecisionBoundary()
        self.execution_coordinator = ExecutionCoordinator()
        self._local_filesystem = local_filesystem or WindowsLocalFileSystemAdapter()
        self.document_review_workflow = LocalTextDocumentReviewWorkflow(
            filesystem=self._local_filesystem,
        )
        self.document_review_runner = self._build_document_review_runner()

    def status_snapshot(self) -> AppStatusSnapshot:
        return AppStatusSnapshot(
            app_service_enabled=True,
            execution_source="CommandProcessor remains active",
            command_registry_enabled=True,
            command_count=len(self.command_registry.commands),
            categories_count=len(self.command_registry.categories()),
            ui_ready=False,
            installer_ready=False,
            secure_key_storage_ready=True,
            secure_provider_runtime_ready=True,
            network_default=False,
            dry_run_default=True,
            privacy_boundary_active=True,
            fallback_explicit_only=True,
            consensus_explicit_only=True,
            voice_safety_active=True,
        )

    def language_settings(self) -> dict[str, str]:
        return self.language_manager.status_dict()

    def status_text_ru(self) -> str:
        snapshot = self.status_snapshot()
        return "\n".join(
            [
                "App service status:",
                "- enabled yes",
                "- mode app-facing service layer",
                f"- execution source {snapshot.execution_source}",
                "- command registry enabled yes",
                f"- command count {snapshot.command_count}",
                f"- categories count {snapshot.categories_count}",
                "- desktop ui ready: no / foundation only",
                "- installer ready: no",
                "- secure key storage foundation: available",
                "- secure provider runtime: available",
                "- provider runtime network default: no",
                "- network default: no",
                "- dry_run default: yes",
                "- privacy boundary active: yes",
                "- fallback explicit-only",
                "- consensus explicit-only",
                "- voice safety active",
                "- no secrets",
                "- no response execution",
            ]
        )

    def contract_status(self) -> AppContractStatus:
        return AppContractStatus(
            schema_name=APP_CONTRACT_SCHEMA_NAME,
            version=APP_CONTRACT_VERSION,
            stable=True,
            app_service_ready=True,
            desktop_shell_ready=True,
            secure_key_storage_ready=True,
            provider_settings_ui_ready=False,
            installer_ready=False,
            mobile_ready=False,
            admin_support_ready=False,
            network_default=False,
            secrets_included=False,
            responses_executed_as_commands=False,
            notes_ru=(
                "Contracts are metadata/status only unless execute_contract is called explicitly.",
                "Provider settings UI, installer, mobile, and admin/support surfaces are planned.",
                "Contract/list/status/card methods do not call providers or read decrypted secrets.",
            ),
        )

    def contract_status_text_ru(self) -> str:
        return self.contract_status().safe_text_ru()

    def audio_lifecycle_status(self) -> AudioLifecycleStatus:
        return self.audio_lifecycle_controller.status()

    def audio_lifecycle_status_text_ru(self) -> str:
        return self.audio_lifecycle_controller.status_text_ru()

    def audio_status_card(self) -> AppStatusCard:
        status = self.audio_lifecycle_status()
        return AppStatusCard(
            card_id="audio_lifecycle",
            title_ru="Audio lifecycle",
            value_ru=f"{status.state}/{status.capture_mode}/{status.output_mode}",
            status="safe",
            category="voice",
            safe=True,
            ui_visible=True,
            details_ru=(
                "Metadata-only lifecycle foundation is available.",
                f"microphone active: {'yes' if status.microphone_active else 'no'}",
                f"continuous listening allowed: {'yes' if status.continuous_listening_allowed else 'no'}",
                f"network used: {'yes' if status.network_used else 'no'}",
                f"audio saved: {'yes' if status.audio_saved else 'no'}",
            ),
        )

    def status_cards(self) -> tuple[AppStatusCard, ...]:
        return (
            self.audio_status_card(),
            AppStatusCard(
                card_id="conversational_loop",
                title_ru="Conversational loop",
                value_ru="foundation ready/safe",
                status="safe",
                category="conversation",
                safe=True,
                ui_visible=True,
                details_ru=(
                    "No network by default.",
                    "No command execution by default.",
                    "No providers called.",
                    "No microphone/TTS.",
                    "AI responses are not executed as commands.",
                ),
            ),
            AppStatusCard(
                card_id="app_service",
                title_ru="AppService",
                value_ru="ready",
                status="ready",
                category="app",
                safe=True,
                ui_visible=True,
                details_ru=("Stable app-facing boundary is available.",),
            ),
            AppStatusCard(
                card_id="desktop_shell",
                title_ru="Desktop shell",
                value_ru="foundation ready",
                status="ready",
                category="app",
                safe=True,
                ui_visible=True,
                details_ru=("run_desktop.py remains the simple shell entry point.",),
            ),
            AppStatusCard(
                card_id="secure_key_storage",
                title_ru="Secure key storage",
                value_ru="foundation ready",
                status="ready",
                category="secure_keys",
                safe=True,
                ui_visible=True,
                details_ru=("Contracts expose status only; no secret values.",),
            ),
            AppStatusCard(
                card_id="secure_provider_runtime",
                title_ru="Provider runtime",
                value_ru="secure credentials integrated",
                status="safe",
                category="secure_keys",
                safe=True,
                ui_visible=True,
                details_ru=(
                    "Secure store preferred.",
                    "Environment fallback available.",
                    "No secrets.",
                    "No network by default.",
                    "Explicit-only real requests.",
                ),
            ),
            AppStatusCard(
                card_id="provider_settings_ui",
                title_ru="AI provider settings UI",
                value_ru="not built",
                status="planned",
                category="ai",
                safe=True,
                ui_visible=True,
                details_ru=("Future UI will use these contracts and secure key storage.",),
            ),
            AppStatusCard(
                card_id="installer",
                title_ru="Installer",
                value_ru="not built",
                status="planned",
                category="installer",
                safe=True,
                ui_visible=True,
                details_ru=("Product mode and installer are outside this task.",),
            ),
            AppStatusCard(
                card_id="mobile",
                title_ru="Mobile companion",
                value_ru="not built",
                status="planned",
                category="mobile",
                safe=True,
                ui_visible=True,
                details_ru=("Future mobile clients should consume serialized contracts.",),
            ),
            AppStatusCard(
                card_id="admin_support",
                title_ru="Admin/support",
                value_ru="planned/no",
                status="planned",
                category="admin_support",
                safe=True,
                ui_visible=True,
                details_ru=("No admin/support backend is added by this task.",),
            ),
            AppStatusCard(
                card_id="network_default",
                title_ru="Network default",
                value_ru="no",
                status="safe",
                category="safety",
                safe=True,
                ui_visible=True,
                details_ru=("Contract methods do not make accidental network calls.",),
            ),
        )

    def command_cards(self, category: str | None = None) -> tuple[AppCommandCard, ...]:
        command_category = self._parse_category(category)
        commands = (
            self.command_registry.list_by_category(command_category)
            if command_category is not None
            else self.command_registry.commands
        )
        return tuple(self._command_card_from_metadata(command) for command in commands)

    def contract_manifest(self) -> AppContractManifest:
        categories = tuple(category.value for category in self.command_registry.categories())
        return AppContractManifest(
            schema_name=APP_CONTRACT_SCHEMA_NAME,
            version=APP_CONTRACT_VERSION,
            status=self.contract_status(),
            status_cards=self.status_cards(),
            command_cards_count=len(self.command_cards()),
            categories=categories,
        )

    def contract_manifest_text_ru(self) -> str:
        return self.contract_manifest().safe_text_ru()

    def status_cards_text_ru(self) -> str:
        lines = [
            "App status cards:",
            "- no secrets",
            "- no network",
            "- no execution",
        ]
        lines.extend(f"- {card.safe_text_ru()}" for card in self.status_cards())
        return "\n".join(lines)

    def command_cards_text_ru(self, category: str | None = None) -> str:
        cards = self.command_cards(category)
        counts: dict[str, int] = {}
        for card in cards:
            counts[card.category] = counts.get(card.category, 0) + 1
        lines = [
            "App command cards:",
            "- source: CommandRegistry metadata",
            "- no secrets",
            "- no network",
            "- no execution",
            f"- total: {len(cards)}",
            "- categories: "
            + (", ".join(f"{name}={count}" for name, count in sorted(counts.items())) or "none"),
        ]
        for card in cards:
            lines.append(f"- {card.safe_text_ru()}")
        return "\n".join(lines)

    def preview_contract(self, text: str) -> AppPreviewContract:
        preview = self.preview_command(text)
        return AppPreviewContract(
            input_text=safe_contract_text(preview.input_text),
            known_command=preview.known_command,
            command_id=preview.registry_match_id,
            title_ru=preview.title_ru,
            category=preview.category or "unknown",
            risk_level=preview.risk_level or "unknown",
            read_only=preview.read_only,
            requires_confirmation=preview.requires_confirmation,
            requires_network=preview.requires_network,
            requires_privacy_check=preview.requires_privacy_check,
            voice_auto_allowed=preview.voice_auto_allowed,
            app_ready=preview.app_ready,
            safe_summary_ru=safe_contract_text(preview.safe_summary_ru),
            secrets_included=False,
            executed=False,
        )

    def execute_contract(
        self,
        text: str,
        source: AppCommandSource = AppCommandSource.DESKTOP_UI,
        idempotency_key: str | None = None,
    ) -> AppExecutionContract:
        result = self.execute_command(text, source, idempotency_key=idempotency_key)
        return AppExecutionContract(
            ok=result.ok,
            input_text=safe_contract_text(result.input_text),
            output_text=safe_contract_text(result.output_text),
            source=result.source.value,
            command_id=result.registry_match_id,
            category=result.category,
            risk_level=result.risk_level,
            executed=result.executed,
            requires_confirmation=result.requires_confirmation,
            network_may_be_used=result.network_may_be_used,
            response_executed_as_command=False,
            secrets_included=False,
            error=safe_contract_text(result.error) if result.error else None,
            intent_resolution=(
                result.intent_resolution.to_contract()
                if hasattr(result.intent_resolution, "to_contract")
                else result.intent_resolution
            ),
            requires_clarification=result.requires_clarification,
            clarification_question=result.clarification_question,
            clarification_options=result.clarification_options,
            policy_decision=(
                result.policy_decision.to_dict()
                if hasattr(result.policy_decision, "to_dict")
                else result.policy_decision
            ),
            operation_id=result.operation_id,
            operation_status=result.operation_status,
            idempotency_key=result.idempotency_key,
            duplicate_suppressed=result.duplicate_suppressed,
            cancellable=result.cancellable,
            workflow_id=result.workflow_id,
            workflow_status=result.workflow_status,
            current_step_id=result.current_step_id,
            current_step_name=result.current_step_name,
            completed_steps=result.completed_steps,
            total_steps=result.total_steps,
            progress_percent=result.progress_percent,
            awaiting_confirmation=result.awaiting_confirmation,
            source_filename=result.source_filename,
            proposed_output_filename=result.proposed_output_filename,
            issue_count=result.issue_count,
            issue_summaries=result.issue_summaries,
            proposed_output_path=result.proposed_output_path,
            saved=result.saved,
            verified=result.verified,
            user_message=result.user_message,
        )

    def process_one_shot_voice_request(
        self,
        source: AppCommandSource = AppCommandSource.VOICE,
    ) -> AppVoiceRequestResult:
        if not isinstance(source, AppCommandSource):
            source = AppCommandSource.UNKNOWN

        if not self._one_shot_voice_lock.acquire(blocking=False):
            return self._voice_error_result(
                error_code="overlapping_one_shot_request",
                user_message="Одноразовый голосовой запрос уже выполняется.",
                result_type="voice_rejected",
            )

        recognition_result = None
        try:
            self.audio_lifecycle_controller.start_one_shot_metadata_only()
            recognizer = self._get_one_shot_voice_recognition()
            recognition_result = recognizer.run_once(explicit_one_shot_requested=True)
            recognized_text = str(
                self._get_value(recognition_result, "recognized_text", "") or ""
            ).strip()
            recognition_completed = bool(
                self._get_value(recognition_result, "completed", False)
            )
            recognition_blocked = bool(
                self._get_value(recognition_result, "blocked", False)
            )
            recognition_allowed = bool(
                self._get_value(recognition_result, "allowed", False)
            )

            if recognition_blocked or not recognition_allowed:
                return self._voice_error_result(
                    error_code=self._voice_error_code_from_reasons(
                        self._get_value(recognition_result, "reasons", ())
                    ),
                    user_message=self._voice_message_from_recognition(
                        recognition_result,
                        "Одноразовое распознавание голоса безопасно заблокировано.",
                    ),
                    result_type="voice_recognition_blocked",
                )

            if not recognition_completed:
                return self._voice_error_result(
                    error_code="recognition_incomplete",
                    user_message=self._voice_message_from_recognition(
                        recognition_result,
                        "Одноразовое распознавание голоса не завершилось.",
                    ),
                    result_type="voice_recognition_failed",
                )

            if not recognized_text:
                return self._voice_error_result(
                    error_code="empty_recognition",
                    user_message="Распознавание завершилось, но полезный текст речи не найден.",
                    result_type="voice_recognition_empty",
                    voice_capture_succeeded=True,
                )

            normalization = normalize_russian_voice_text(
                recognized_text,
                locale=self.language_manager.runtime_locale(),
            )
            command_candidate = (
                normalization.normalized_text
                if normalization.safe_to_use_as_command_candidate
                else recognized_text
            )
            normalization_applied = (
                normalization.safe_to_use_as_command_candidate
                and normalization.normalized_text != recognized_text
            )
            text_result = self.execute_contract(command_candidate, source)
            return AppVoiceRequestResult(
                ok=bool(text_result.ok),
                voice_capture_succeeded=True,
                recognition_succeeded=True,
                recognized_text=safe_contract_text(recognized_text),
                normalized_text=safe_contract_text(normalization.normalized_text),
                normalization_applied=normalization_applied,
                normalization_rules=normalization.applied_rules,
                text_processing_succeeded=bool(text_result.ok),
                result_type=(
                    "confirmation_required"
                    if text_result.requires_confirmation
                    else ("text_processed" if text_result.ok else "text_processing_failed")
                ),
                category=text_result.category,
                requires_confirmation=text_result.requires_confirmation,
                error_code=None if text_result.ok else "text_processing_failed",
                user_message=(
                    "Голосовой запрос обработан через обычный текстовый путь."
                    if text_result.ok
                    else "Распознавание голоса прошло, но обработка текста безопасно завершилась ошибкой."
                ),
                text_result=text_result,
                secrets_included=False,
                raw_audio_included=False,
                provider_objects_included=False,
                microphone_objects_included=False,
                operation_id=text_result.operation_id,
                operation_status=text_result.operation_status,
                idempotency_key=text_result.idempotency_key,
                duplicate_suppressed=text_result.duplicate_suppressed,
                cancellable=text_result.cancellable,
            )
        except Exception as exc:
            return self._voice_error_result(
                error_code="one_shot_voice_failure",
                user_message=(
                    "Голосовой запрос безопасно завершился ошибкой: "
                    + self._safe_text_preview(str(exc))
                ),
                result_type="voice_failure",
            )
        finally:
            try:
                self._cleanup_one_shot_voice_recognition()
            finally:
                self.audio_lifecycle_controller.reset_to_idle()
                self._one_shot_voice_lock.release()

    def process_one_shot_voice_request_text_ru(
        self,
        source: AppCommandSource = AppCommandSource.VOICE,
    ) -> str:
        return self.process_one_shot_voice_request(source).safe_text_ru()

    def capabilities_text_ru(self) -> str:
        return "\n".join(
            [
                "App service capabilities:",
                "- future UI can list commands",
                "- future UI can preview command risk",
                "- future UI can show categories",
                "- future UI can execute through CommandProcessor",
                "- future UI can show status snapshots",
                "- future AI settings screen planned",
                "- secure key storage foundation available",
                "- future AI Provider Settings UI will use secure key storage",
                "- installer planned",
                "- no GUI in this task",
                "- network default: no",
                "- no secrets",
                "- no response execution",
            ]
        )

    def conversational_status(self) -> dict[str, object]:
        return self.conversational_loop.status()

    def conversational_status_text_ru(self) -> str:
        return self.conversational_loop.status_text_ru()

    def conversational_preview(self, text: str) -> ConversationalResult:
        return self.conversational_loop.preview(text)

    def conversational_preview_text_ru(self, text: str) -> str:
        return self.conversational_loop.result_text_ru(
            self.conversational_preview(text)
        )

    def conversational_handle(
        self,
        text: str,
        allow_network: bool = False,
        allow_command_execution: bool = False,
    ) -> ConversationalResult:
        return self.conversational_loop.handle(
            ConversationalRequest(
                text=text,
                source="app_service",
                allow_network=allow_network,
                allow_command_execution=allow_command_execution,
                allow_risky_actions=False,
            )
        )

    def conversational_handle_text_ru(
        self,
        text: str,
        allow_network: bool = False,
        allow_command_execution: bool = False,
    ) -> str:
        return self.conversational_loop.result_text_ru(
            self.conversational_handle(
                text,
                allow_network=allow_network,
                allow_command_execution=allow_command_execution,
            )
        )

    def conversational_capabilities_text_ru(self) -> str:
        return self.conversational_loop.capabilities_text_ru()

    def provider_runtime_status(self):
        return self._provider_runtime().all_credential_statuses()

    def provider_runtime_status_text_ru(self) -> str:
        return self._provider_runtime().status_text_ru()

    def provider_runtime_credentials_text_ru(self) -> str:
        return self._provider_runtime().status_text_ru()

    def provider_runtime_provider_text_ru(self, provider: str) -> str:
        return self._provider_runtime().provider_status_text_ru(provider)

    def vertical_integration_report(self):
        from app.vertical_integration import VerticalIntegrationService

        return VerticalIntegrationService(
            app_service=self,
            command_registry=self.command_registry,
        ).run_report()

    def vertical_integration_report_text_ru(self) -> str:
        from app.vertical_integration import VerticalIntegrationService

        return VerticalIntegrationService(
            app_service=self,
            command_registry=self.command_registry,
        ).report_text_ru()

    def vertical_integration_checklist_text_ru(self) -> str:
        from app.vertical_integration import VerticalIntegrationService

        return VerticalIntegrationService(
            app_service=self,
            command_registry=self.command_registry,
        ).checklist_text_ru()

    def vertical_integration_summary_text_ru(self) -> str:
        from app.vertical_integration import VerticalIntegrationService

        return VerticalIntegrationService(
            app_service=self,
            command_registry=self.command_registry,
        ).safe_summary_text_ru()

    def list_commands(self, category: str | None = None) -> str:
        command_category = self._parse_category(category)
        return self.command_registry.list_text_ru(command_category)

    def categories_text_ru(self) -> str:
        return self.command_registry.categories_text_ru()

    def search_commands(self, query: str) -> str:
        return self.command_registry.search_text_ru(query)

    def preview_command(self, text: str) -> AppCommandPreview:
        input_text = str(text or "").strip()
        normalized_text = self.command_registry.normalize_alias(input_text)
        document_path = self._document_review_path_from_command(input_text)
        if document_path is not None:
            metadata = self._match_registry_command(input_text)
            return AppCommandPreview(
                input_text=input_text,
                normalized_text=normalized_text,
                registry_match_id=(
                    metadata.command_id if metadata is not None else "document_review.local_text"
                ),
                title_ru=(
                    metadata.title_ru
                    if metadata is not None
                    else "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 TXT-\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430"
                ),
                category=metadata.category.value if metadata is not None else "app",
                risk_level=(
                    metadata.risk_level.value if metadata is not None else "confirmation_required"
                ),
                read_only=False,
                voice_auto_allowed=False,
                requires_confirmation=True,
                requires_network=False,
                requires_ai_key=False,
                requires_privacy_check=False,
                app_ready=True,
                known_command=True,
                safe_summary_ru=(
                    "\u042d\u0442\u043e workflow \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0439 "
                    "\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 .txt: preview \u043d\u0435 "
                    "\u0447\u0438\u0442\u0430\u0435\u0442 \u0444\u0430\u0439\u043b, \u043d\u0435 "
                    "\u0441\u043e\u0437\u0434\u0430\u0435\u0442 \u043e\u043f\u0435\u0440\u0430\u0446\u0438\u044e "
                    "\u0438 \u043d\u0435 \u043f\u0438\u0448\u0435\u0442 \u0444\u0430\u0439\u043b. "
                    "\u041f\u0440\u0438 Execute \u0431\u0443\u0434\u0435\u0442 "
                    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0447\u0442\u0435\u043d\u0438\u0435, "
                    "\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u0435 "
                    "\u043d\u043e\u0432\u043e\u0439 \u043a\u043e\u043f\u0438\u0438 \u043f\u043e\u0442\u0440\u0435\u0431\u0443\u0435\u0442 "
                    "\u043e\u0442\u0434\u0435\u043b\u044c\u043d\u043e\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435."
                ),
            )
        metadata = self._match_registry_command(input_text)
        if metadata is None:
            return AppCommandPreview(
                input_text=input_text,
                normalized_text=normalized_text,
                registry_match_id=None,
                title_ru=None,
                category=None,
                risk_level=None,
                read_only=False,
                voice_auto_allowed=False,
                requires_confirmation=True,
                requires_network=False,
                requires_ai_key=False,
                requires_privacy_check=False,
                app_ready=False,
                known_command=False,
                safe_summary_ru=(
                    "Команда не найдена в CommandRegistry. AppService не выполнял "
                    "предпросмотренный текст; выполнение возможно только через "
                    "CommandProcessor."
                ),
            )

        return AppCommandPreview(
            input_text=input_text,
            normalized_text=normalized_text,
            registry_match_id=metadata.command_id,
            title_ru=metadata.title_ru,
            category=metadata.category.value,
            risk_level=metadata.risk_level.value,
            read_only=metadata.read_only,
            voice_auto_allowed=metadata.voice_auto_allowed,
            requires_confirmation=metadata.requires_confirmation,
            requires_network=metadata.requires_network,
            requires_ai_key=metadata.requires_ai_key,
            requires_privacy_check=metadata.requires_privacy_check,
            app_ready=metadata.app_ready,
            known_command=True,
            safe_summary_ru=self._summary_for_metadata(metadata),
        )

    def preview_text_ru(self, text: str) -> str:
        preview = self.preview_command(text)
        return "\n".join(
            [
                "App command preview:",
                "- does not execute command",
                f"- input preview: {self._safe_text_preview(preview.input_text)}",
                f"- known command: {'yes' if preview.known_command else 'no'}",
                f"- command id: {preview.registry_match_id or 'none'}",
                f"- category: {preview.category or 'unknown'}",
                f"- risk: {preview.risk_level or 'unknown'}",
                f"- app_ready: {'yes' if preview.app_ready else 'no'}",
                f"- requires_network: {'yes' if preview.requires_network else 'no'}",
                f"- requires_confirmation: {'yes' if preview.requires_confirmation else 'no'}",
                f"- requires_privacy_check: {'yes' if preview.requires_privacy_check else 'no'}",
                f"- voice_auto_allowed: {'yes' if preview.voice_auto_allowed else 'no'}",
                f"- safe summary: {preview.safe_summary_ru}",
                "- no secrets",
                "- no response execution",
            ]
        )

    def execute_command(
        self,
        text: str,
        source: AppCommandSource = AppCommandSource.DESKTOP_UI,
        idempotency_key: str | None = None,
    ) -> AppCommandResult:
        if not isinstance(source, AppCommandSource):
            source = AppCommandSource.UNKNOWN
        input_text = str(text or "").strip()
        resolution = self.intent_resolver.resolve(
            original_text=input_text,
            processing_text=input_text,
            source=source.value,
        )

        pending_result = self._consume_pending_control_response(input_text, source, resolution)
        if pending_result is not None:
            return pending_result

        if self._document_review_path_from_command(input_text) is not None:
            return self._execute_document_review_command(
                input_text,
                source,
                idempotency_key=idempotency_key,
                resolution=resolution,
            )

        command_text = resolution.command_text or input_text
        metadata = self._match_registry_command(command_text)
        action_id = None if metadata is not None else self._action_id_for_text(command_text)
        fingerprint = self.execution_coordinator.create_request_fingerprint(
            source=source.value,
            text=command_text,
            command_id=metadata.command_id if metadata is not None else None,
            action_id=action_id,
        )
        registration = self.execution_coordinator.register(
            source=source.value,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            command_id=metadata.command_id if metadata is not None else None,
            action_id=action_id,
            metadata={
                "input_preview": safe_journal_text(input_text),
                "intent_kind": getattr(resolution.intent_kind, "value", None),
            },
        )
        operation = registration.operation
        if registration.duplicate:
            existing = self._operation_results.get(operation.operation_id)
            if existing is not None:
                return self._with_operation(existing, operation, duplicate_suppressed=True)
            return self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Повторный запрос подавлен: операция уже зарегистрирована.",
                category="duplicate_suppressed",
                risk_level="safe_metadata_only",
            )
        if registration.conflict:
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Запрос отклонён: конфликт idempotency key. Команда не запускалась.",
                category="policy_denied",
                risk_level="safe_metadata_only",
                error="idempotency_conflict",
            )
            self._remember_operation_result(result)
            return result

        result = self._execute_command_uncoordinated(input_text, source)
        if result.requires_clarification:
            self._pending_clarification_operation_id = operation.operation_id
            operation = self.execution_coordinator.mark_awaiting_clarification(
                operation.operation_id
            )
        elif result.category == "policy_denied":
            policy_dict = (
                result.policy_decision.to_dict()
                if hasattr(result.policy_decision, "to_dict")
                else None
            )
            operation = self.execution_coordinator.mark_denied(
                operation.operation_id,
                policy_decision=policy_dict,
            )
        elif result.requires_confirmation and not result.executed:
            self._pending_confirmation = PendingAppConfirmation(
                operation_id=operation.operation_id,
                idempotency_key=operation.idempotency_key,
                request_fingerprint=operation.request_fingerprint,
                command_text=command_text,
                source=source.value,
                resolution=resolution,
            )
            operation = self.execution_coordinator.mark_awaiting_confirmation(
                operation.operation_id
            )
        elif result.executed:
            operation = self.execution_coordinator.mark_succeeded(
                operation.operation_id,
                summary=result.output_text,
            )
        else:
            operation = self.execution_coordinator.mark_succeeded(
                operation.operation_id,
                summary=result.output_text or result.category,
            )
        result = self._with_operation(result, operation)
        self._remember_operation_result(result)
        return result

    def _execute_command_uncoordinated(
        self,
        text: str,
        source: AppCommandSource = AppCommandSource.DESKTOP_UI,
    ) -> AppCommandResult:
        if not isinstance(source, AppCommandSource):
            source = AppCommandSource.UNKNOWN
        input_text = str(text or "").strip()
        clarification_result = self._consume_pending_clarification(input_text, source)
        if clarification_result is not None:
            return clarification_result

        resolution = self.intent_resolver.resolve(
            original_text=input_text,
            processing_text=input_text,
            source=source.value,
        )
        if resolution.resolution_status == ResolutionStatus.REQUIRES_CLARIFICATION:
            self._pending_clarification = ClarificationState(
                question_ru=resolution.clarification_question or "",
                options=resolution.clarification_options,
                original_text=input_text,
                source=source.value,
            )
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=self._clarification_text_ru(
                    resolution.clarification_question,
                    resolution.clarification_options,
                ),
                source=source,
                registry_match_id=None,
                category="clarification",
                risk_level="read_only",
                executed=False,
                requires_confirmation=False,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
                requires_clarification=True,
                clarification_question=resolution.clarification_question,
                clarification_options=resolution.clarification_options,
            )

        if resolution.intent_kind == IntentKind.UNSUPPORTED:
            self._pending_clarification = None
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=(
                    "Запрос не выполнен: намерение небезопасно или недостаточно точно. "
                    "Команда не запускалась."
                ),
                source=source,
                registry_match_id=None,
                category="unsupported",
                risk_level="unknown",
                executed=False,
                requires_confirmation=False,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
            )

        if resolution.intent_kind == IntentKind.ORDINARY_CONVERSATION:
            self._pending_clarification = None
            if "risky_action_question" in resolution.reason_codes:
                return AppCommandResult(
                    ok=True,
                    input_text=input_text,
                    output_text=(
                        "Это вопрос о рискованном действии. Я не запускаю удаление "
                        "и не создаю подтверждение без точной команды."
                    ),
                    source=source,
                    registry_match_id=None,
                    category="conversation",
                    risk_level="safe_metadata_only",
                    executed=False,
                    requires_confirmation=False,
                    network_may_be_used=False,
                    response_executed_as_command=False,
                    error=None,
                    intent_resolution=resolution,
                )
            conversational = self.conversational_loop.handle(
                ConversationalRequest(
                    text=input_text,
                    source=source.value,
                    allow_network=False,
                    allow_command_execution=False,
                    allow_risky_actions=False,
                )
            )
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=self.conversational_loop.result_text_ru(conversational),
                source=source,
                registry_match_id=conversational.command_id,
                category=conversational.command_category or "conversation",
                risk_level=conversational.command_risk or conversational.safety_level,
                executed=False,
                requires_confirmation=conversational.requires_confirmation,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
            )

        command_text = resolution.command_text or input_text
        return self._execute_resolved_command(command_text, source, resolution)

    def _execute_resolved_command(
        self,
        input_text: str,
        source: AppCommandSource,
        resolution=None,
        confirmation_present: bool = False,
    ) -> AppCommandResult:
        preview = self.preview_command(input_text)
        metadata = self._match_registry_command(input_text)
        policy_decision = self.policy_boundary.evaluate(
            policy_request_from_metadata(
                source=source.value,
                text=input_text,
                metadata=metadata,
                intent_kind=getattr(getattr(resolution, "intent_kind", None), "value", None),
                confirmation_present=confirmation_present,
                clarification_resolved=True,
            )
        )
        if policy_decision.decision == PolicyDecisionType.DENY:
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=policy_decision.user_message,
                source=source,
                registry_match_id=preview.registry_match_id,
                category="policy_denied",
                risk_level=preview.risk_level or "destructive_blocked",
                executed=False,
                requires_confirmation=True,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
                policy_decision=policy_decision,
            )
        if policy_decision.decision == PolicyDecisionType.REQUIRE_CONFIRMATION:
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=(
                    (preview.safe_summary_ru if preview.known_command else "Risky action.")
                    + "\n"
                    + policy_decision.user_message
                ),
                source=source,
                registry_match_id=preview.registry_match_id,
                category=preview.category,
                risk_level=preview.risk_level,
                executed=False,
                requires_confirmation=True,
                network_may_be_used=preview.requires_network,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
                policy_decision=policy_decision,
            )
        if preview.known_command and preview.requires_confirmation and not confirmation_present:
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=(
                    preview.safe_summary_ru
                    + "\nТребуется подтверждение. Команда не выполнена автоматически."
                ),
                source=source,
                registry_match_id=preview.registry_match_id,
                category=preview.category,
                risk_level=preview.risk_level,
                executed=False,
                requires_confirmation=True,
                network_may_be_used=preview.requires_network,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
                policy_decision=policy_decision,
            )
        try:
            previous_confirmation = getattr(
                self.command_processor,
                "_policy_confirmation_for_command",
                None,
            )
            if confirmation_present and hasattr(
                self.command_processor,
                "_policy_confirmation_for_command",
            ):
                self.command_processor._policy_confirmation_for_command = input_text
            processor_result = self.command_processor.process(input_text)
            if confirmation_present and hasattr(
                self.command_processor,
                "_policy_confirmation_for_command",
            ):
                self.command_processor._policy_confirmation_for_command = previous_confirmation
            output_text = str(processor_result.get("response", processor_result))
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=output_text,
                source=source,
                registry_match_id=preview.registry_match_id,
                category=preview.category,
                risk_level=preview.risk_level,
                executed=True,
                requires_confirmation=preview.requires_confirmation,
                network_may_be_used=preview.requires_network,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
                policy_decision=policy_decision,
            )
        except Exception as exc:
            if confirmation_present and hasattr(
                self.command_processor,
                "_policy_confirmation_for_command",
            ):
                self.command_processor._policy_confirmation_for_command = previous_confirmation
            return AppCommandResult(
                ok=False,
                input_text=input_text,
                output_text="",
                source=source,
                registry_match_id=preview.registry_match_id,
                category=preview.category,
                risk_level=preview.risk_level,
                executed=False,
                requires_confirmation=preview.requires_confirmation,
                network_may_be_used=preview.requires_network,
                response_executed_as_command=False,
                error=str(exc),
                intent_resolution=resolution,
                policy_decision=policy_decision,
            )

    def _consume_pending_control_response(
        self,
        input_text: str,
        source: AppCommandSource,
        resolution,
    ) -> AppCommandResult | None:
        pending_document = self._pending_document_review
        if pending_document is not None:
            if resolution.intent_kind == IntentKind.CANCELLATION_RESPONSE:
                self._pending_document_review = None
                snapshot = self.document_review_runner.cancel(
                    pending_document.operation_id,
                    reason="document_review_cancelled",
                )
                operation = self.execution_coordinator.journal.get(pending_document.operation_id)
                result = self._operation_metadata_result(
                    input_text=input_text,
                    source=source,
                    operation=operation,
                    output_text=(
                        "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 "
                        "\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430 "
                        "\u043e\u0442\u043c\u0435\u043d\u0435\u043d\u0430. "
                        "\u0412\u044b\u0445\u043e\u0434\u043d\u043e\u0439 "
                        "\u0444\u0430\u0439\u043b \u043d\u0435 \u0441\u043e\u0437\u0434\u0430\u043d."
                    ),
                    category="document_review",
                    risk_level="confirmation_required",
                )
                result = self._with_document_review_fields(
                    result,
                    pending_document.state.proposal,
                    user_message=result.output_text,
                )
                result = self._with_workflow_snapshot(result, snapshot)
                self._remember_operation_result(result)
                return result
            if resolution.intent_kind != IntentKind.CONFIRMATION_RESPONSE:
                if input_text == pending_document.command_text:
                    operation = self.execution_coordinator.journal.get(
                        pending_document.operation_id
                    )
                    existing = self._operation_results.get(pending_document.operation_id)
                    if existing is not None:
                        return self._with_operation(
                            existing,
                            operation,
                            duplicate_suppressed=True,
                        )
                self._pending_document_review = None
                return None
            return self._confirm_document_review(input_text, source, pending_document)

        if self._pending_clarification is not None:
            operation_id = self._pending_clarification_operation_id
            if (
                resolution.intent_kind == IntentKind.CANCELLATION_RESPONSE
                and operation_id is not None
            ):
                self._pending_clarification = None
                self._pending_clarification_operation_id = None
                operation = self.execution_coordinator.cancel(
                    operation_id,
                    reason="clarification_cancelled",
                )
                result = self._operation_metadata_result(
                    input_text=input_text,
                    source=source,
                    operation=operation,
                    output_text="Уточнение отменено. Команда не запускалась.",
                    category="clarification",
                    risk_level="read_only",
                )
                self._remember_operation_result(result)
                return result
            if operation_id is not None:
                return self._continue_clarification_operation(
                    input_text,
                    source,
                    operation_id,
                )

        pending = self._pending_confirmation
        if pending is None:
            return None
        if resolution.intent_kind == IntentKind.CANCELLATION_RESPONSE:
            self._pending_confirmation = None
            operation = self.execution_coordinator.cancel(
                pending.operation_id,
                reason="confirmation_cancelled",
            )
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Подтверждение отменено. Команда не запускалась.",
                category="confirmation",
                risk_level="confirmation_required",
            )
            self._remember_operation_result(result)
            return result
        if resolution.intent_kind != IntentKind.CONFIRMATION_RESPONSE:
            self._pending_confirmation = None
            return None

        self._pending_confirmation = None
        operation = self.execution_coordinator.journal.get(pending.operation_id)
        if operation is None or operation.request_fingerprint != pending.request_fingerprint:
            return self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Подтверждение устарело. Команда не запускалась.",
                category="confirmation",
                risk_level="confirmation_required",
                error="stale_confirmation",
            )
        self.execution_coordinator.mark_running(pending.operation_id)
        result = self._execute_resolved_command(
            pending.command_text,
            source,
            pending.resolution,
            confirmation_present=True,
        )
        if result.executed:
            operation = self.execution_coordinator.mark_succeeded(
                pending.operation_id,
                summary=result.output_text,
            )
        elif result.policy_decision is not None:
            policy_dict = (
                result.policy_decision.to_dict()
                if hasattr(result.policy_decision, "to_dict")
                else None
            )
            operation = self.execution_coordinator.mark_denied(
                pending.operation_id,
                policy_decision=policy_dict,
                error_code="confirmation_policy_denied",
            )
        else:
            operation = self.execution_coordinator.mark_failed(
                pending.operation_id,
                error_code=result.error or "confirmation_not_executed",
            )
        result = self._with_operation(result, operation)
        self._remember_operation_result(result)
        return result

    def _execute_document_review_command(
        self,
        input_text: str,
        source: AppCommandSource,
        *,
        idempotency_key: str | None,
        resolution,
    ) -> AppCommandResult:
        metadata = self._match_registry_command(input_text)
        fingerprint = self.execution_coordinator.create_request_fingerprint(
            source=source.value,
            text=input_text,
            command_id=metadata.command_id if metadata is not None else "document_review.local_text",
            action_id="document_review.local_text",
        )
        registration = self.execution_coordinator.register(
            source=source.value,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            command_id=metadata.command_id if metadata is not None else "document_review.local_text",
            action_id="document_review.local_text",
            metadata={
                "input_preview": safe_journal_text(input_text),
                "workflow_id": DOCUMENT_REVIEW_WORKFLOW_ID,
                "intent_kind": getattr(resolution.intent_kind, "value", None),
            },
        )
        operation = registration.operation
        if registration.duplicate:
            existing = self._operation_results.get(operation.operation_id)
            if existing is not None:
                return self._with_operation(existing, operation, duplicate_suppressed=True)
            return self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text=(
                    "\u041f\u043e\u0432\u0442\u043e\u0440\u043d\u044b\u0439 "
                    "\u0437\u0430\u043f\u0440\u043e\u0441 \u043f\u043e\u0434\u0430\u0432\u043b\u0435\u043d."
                ),
                category="duplicate_suppressed",
                risk_level="safe_metadata_only",
            )
        if registration.conflict:
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text=(
                    "\u0417\u0430\u043f\u0440\u043e\u0441 \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d: "
                    "\u043a\u043e\u043d\u0444\u043b\u0438\u043a\u0442 idempotency key. "
                    "\u0424\u0430\u0439\u043b\u044b \u043d\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u044b."
                ),
                category="policy_denied",
                risk_level="safe_metadata_only",
                error="idempotency_conflict",
            )
            self._remember_operation_result(result)
            return result

        source_path = self._document_review_path_from_command(input_text) or ""
        state = DocumentReviewRunState(source_path=source_path)
        self.document_review_runner.policy_boundary = self.policy_boundary
        snapshot = self.document_review_runner.start(
            operation=operation,
            state=state,
            token=registration.token,
            safe_metadata={"workflow_id": DOCUMENT_REVIEW_WORKFLOW_ID},
        )
        operation = self.execution_coordinator.journal.get(operation.operation_id) or operation
        if snapshot.status.value == "denied":
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Запрос отклонен политикой безопасности. Файлы не изменены.",
                category="policy_denied",
                risk_level="confirmation_required",
                error=operation.safe_error_code or "document_review_policy_denied",
            )
            result = self._with_workflow_snapshot(result, snapshot)
            self._remember_operation_result(result)
            return result
        if snapshot.status.value == "failed":
            failed = self.document_review_runner.latest_failed_result(operation.operation_id)
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text=failed.safe_message if failed else "Workflow проверки документа завершился ошибкой.",
                category="document_review",
                risk_level="confirmation_required",
                error=(failed.error_code if failed else "document_review_failed"),
            )
            result = self._with_workflow_snapshot(result, snapshot)
            self._remember_operation_result(result)
            return result
        proposal = state.proposal
        if proposal is None:
            operation = self.execution_coordinator.mark_failed(
                operation.operation_id,
                error_code="document_review_proposal_missing",
            )
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Workflow проверки документа не подготовил предложение.",
                category="document_review",
                risk_level="confirmation_required",
                error="document_review_proposal_missing",
            )
            result = self._with_workflow_snapshot(result, snapshot)
            self._remember_operation_result(result)
            return result
        write_policy = operation.policy_decision or {}
        self._pending_document_review = PendingDocumentReviewConfirmation(
            operation_id=operation.operation_id,
            idempotency_key=operation.idempotency_key,
            request_fingerprint=operation.request_fingerprint,
            command_text=input_text,
            source=source.value,
            state=state,
        )
        result = AppCommandResult(
            ok=True,
            input_text=input_text,
            output_text=self._document_review_review_text(proposal),
            source=source,
            registry_match_id=operation.command_id,
            category="document_review",
            risk_level="confirmation_required",
            executed=False,
            requires_confirmation=True,
            network_may_be_used=False,
            response_executed_as_command=False,
            error=None,
            intent_resolution=resolution,
            policy_decision=write_policy,
            workflow_id=proposal.workflow_id,
            source_filename=proposal.source_filename,
            proposed_output_filename=proposal.proposed_output_filename,
            issue_count=proposal.issue_count,
            issue_summaries=self._issue_summaries(proposal),
            proposed_output_path=proposal.output_path,
            saved=False,
            verified=False,
            user_message=(
                "\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440 "
                "\u0433\u043e\u0442\u043e\u0432. \u0414\u043b\u044f "
                "\u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f "
                "\u043d\u043e\u0432\u043e\u0439 \u043a\u043e\u043f\u0438\u0438 "
                "\u043d\u0443\u0436\u043d\u043e \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435."
            ),
        )
        result = self._with_operation(result, operation)
        result = self._with_workflow_snapshot(result, snapshot)
        self._remember_operation_result(result)
        return result

    def _confirm_document_review(
        self,
        input_text: str,
        source: AppCommandSource,
        pending: PendingDocumentReviewConfirmation,
    ) -> AppCommandResult:
        self._pending_document_review = None
        operation = self.execution_coordinator.journal.get(pending.operation_id)
        if operation is None or operation.request_fingerprint != pending.request_fingerprint:
            return self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text=(
                    "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 "
                    "\u0443\u0441\u0442\u0430\u0440\u0435\u043b\u043e. \u0424\u0430\u0439\u043b "
                    "\u043d\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d."
                ),
                category="document_review",
                risk_level="confirmation_required",
                error="stale_document_review_confirmation",
            )
        proposal = pending.state.proposal
        if proposal is None:
            operation = self.execution_coordinator.mark_failed(
                pending.operation_id,
                error_code="document_review_proposal_missing",
            )
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Workflow проверки документа не подготовил предложение.",
                category="document_review",
                risk_level="confirmation_required",
                error="document_review_proposal_missing",
            )
            self._remember_operation_result(result)
            return result
        self.document_review_runner.policy_boundary = self.policy_boundary
        snapshot = self.document_review_runner.resume(pending.operation_id)
        operation = self.execution_coordinator.journal.get(pending.operation_id) or operation
        if snapshot.status.value in {"failed", "denied"}:
            failed = self.document_review_runner.latest_failed_result(pending.operation_id)
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text=failed.safe_message if failed else "Workflow проверки документа завершился ошибкой.",
                category="policy_denied" if snapshot.status.value == "denied" else "document_review",
                risk_level="confirmation_required",
                error=failed.error_code if failed else operation.safe_error_code,
            )
            result = self._with_document_review_fields(result, proposal)
            result = self._with_workflow_snapshot(result, snapshot)
            self._remember_operation_result(result)
            return result
        saved = pending.state.save_result
        if saved is None:
            operation = self.execution_coordinator.mark_failed(
                pending.operation_id,
                error_code="document_review_save_missing",
            )
            result = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Workflow проверки документа не вернул результат сохранения.",
                category="document_review",
                risk_level="confirmation_required",
                error="document_review_save_missing",
            )
            result = self._with_document_review_fields(result, proposal)
            result = self._with_workflow_snapshot(result, snapshot)
            self._remember_operation_result(result)
            return result
        output_text = self._document_review_saved_text(proposal, saved.output_path)
        operation = self.execution_coordinator.mark_succeeded(pending.operation_id, summary=output_text)
        result = AppCommandResult(
            ok=True,
            input_text=input_text,
            output_text=output_text,
            source=source,
            registry_match_id=operation.command_id,
            category="document_review",
            risk_level="confirmation_required",
            executed=True,
            requires_confirmation=False,
            network_may_be_used=False,
            response_executed_as_command=False,
            error=None,
            policy_decision=operation.policy_decision,
            workflow_id=proposal.workflow_id,
            source_filename=proposal.source_filename,
            proposed_output_filename=proposal.proposed_output_filename,
            issue_count=proposal.issue_count,
            issue_summaries=self._issue_summaries(proposal),
            proposed_output_path=saved.output_path,
            saved=saved.saved,
            verified=saved.verified and saved.source_hash_unchanged,
            user_message=(
                "\u041d\u043e\u0432\u0430\u044f \u043a\u043e\u043f\u0438\u044f "
                "\u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430 \u0438 "
                "\u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u0430. "
                "\u0418\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0444\u0430\u0439\u043b "
                "\u043d\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d."
            ),
        )
        result = self._with_operation(result, operation)
        result = self._with_workflow_snapshot(result, snapshot)
        self._remember_operation_result(result)
        return result

    def _continue_clarification_operation(
        self,
        input_text: str,
        source: AppCommandSource,
        operation_id: str,
    ) -> AppCommandResult | None:
        result = self._consume_pending_clarification(input_text, source)
        if result is None:
            return None
        operation = self.execution_coordinator.journal.get(operation_id)
        if result.executed:
            operation = self.execution_coordinator.mark_succeeded(
                operation_id,
                summary=result.output_text,
            )
        elif result.requires_confirmation:
            self._pending_confirmation = PendingAppConfirmation(
                operation_id=operation_id,
                idempotency_key=operation.idempotency_key if operation else "",
                request_fingerprint=operation.request_fingerprint if operation else "",
                command_text=result.input_text,
                source=source.value,
                resolution=result.intent_resolution,
            )
            operation = self.execution_coordinator.mark_awaiting_confirmation(operation_id)
        elif result.category == "policy_denied":
            operation = self.execution_coordinator.mark_denied(operation_id)
        elif result.category == "clarification":
            operation = self.execution_coordinator.cancel(
                operation_id,
                reason="clarification_cancelled",
            )
        else:
            operation = self.execution_coordinator.mark_succeeded(
                operation_id,
                summary=result.output_text or result.category,
            )
        result = self._with_operation(result, operation)
        self._remember_operation_result(result)
        return result

    def _operation_metadata_result(
        self,
        *,
        input_text: str,
        source: AppCommandSource,
        operation: ExecutionOperation | None,
        output_text: str,
        category: str,
        risk_level: str,
        error: str | None = None,
    ) -> AppCommandResult:
        result = AppCommandResult(
            ok=error is None,
            input_text=input_text,
            output_text=output_text,
            source=source,
            registry_match_id=operation.command_id if operation is not None else None,
            category=category,
            risk_level=risk_level,
            executed=False,
            requires_confirmation=False,
            network_may_be_used=False,
            response_executed_as_command=False,
            error=error,
        )
        return self._with_operation(result, operation)

    def _with_operation(
        self,
        result: AppCommandResult,
        operation: ExecutionOperation | None,
        *,
        duplicate_suppressed: bool | None = None,
    ) -> AppCommandResult:
        if operation is None:
            return result
        return AppCommandResult(
            ok=result.ok,
            input_text=result.input_text,
            output_text=result.output_text,
            source=result.source,
            registry_match_id=result.registry_match_id,
            category=result.category,
            risk_level=result.risk_level,
            executed=result.executed,
            requires_confirmation=result.requires_confirmation,
            network_may_be_used=result.network_may_be_used,
            response_executed_as_command=result.response_executed_as_command,
            error=result.error,
            intent_resolution=result.intent_resolution,
            requires_clarification=result.requires_clarification,
            clarification_question=result.clarification_question,
            clarification_options=result.clarification_options,
            policy_decision=result.policy_decision,
            operation_id=operation.operation_id,
            operation_status=operation.status.value,
            idempotency_key=operation.idempotency_key,
            duplicate_suppressed=(
                operation.duplicate_suppressed
                if duplicate_suppressed is None
                else duplicate_suppressed
            ),
            cancellable=operation.cancellable,
            workflow_id=result.workflow_id,
            workflow_status=result.workflow_status,
            current_step_id=result.current_step_id,
            current_step_name=result.current_step_name,
            completed_steps=result.completed_steps,
            total_steps=result.total_steps,
            progress_percent=result.progress_percent,
            awaiting_confirmation=result.awaiting_confirmation,
            source_filename=result.source_filename,
            proposed_output_filename=result.proposed_output_filename,
            issue_count=result.issue_count,
            issue_summaries=result.issue_summaries,
            proposed_output_path=result.proposed_output_path,
            saved=result.saved,
            verified=result.verified,
            user_message=result.user_message,
        )

    def _remember_operation_result(self, result: AppCommandResult) -> None:
        if result.operation_id:
            self._operation_results[result.operation_id] = result

    def recent_execution_operations(self, limit: int | None = 20) -> tuple[dict[str, object], ...]:
        return self.execution_coordinator.journal.recent_dicts(limit)

    @staticmethod
    def _action_id_for_text(text: str) -> str | None:
        normalized = str(text or "").strip().lower()
        if "system32" in normalized:
            return "system.delete_protected_path"
        if normalized.startswith(("удали файл ", "удалить файл ", "СѓРґР°Р»Рё С„Р°Р№Р» ")):
            return "file.delete"
        return None

    def _consume_pending_clarification(
        self,
        input_text: str,
        source: AppCommandSource,
    ) -> AppCommandResult | None:
        state = self._pending_clarification
        if state is None:
            return None
        resolution = self.intent_resolver.resolve(
            original_text=input_text,
            processing_text=input_text,
            source=source.value,
        )
        if resolution.intent_kind == IntentKind.CANCELLATION_RESPONSE:
            self._pending_clarification = None
            self._pending_clarification_operation_id = None
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text="Уточнение отменено. Команда не запускалась.",
                source=source,
                registry_match_id=None,
                category="clarification",
                risk_level="read_only",
                executed=False,
                requires_confirmation=False,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
                intent_resolution=resolution,
            )
        selected = None
        for option in state.options:
            if option_matches_text(option, input_text, self.command_registry):
                selected = option
                break
        if selected is None:
            self._pending_clarification = None
            self._pending_clarification_operation_id = None
            return None
        self._pending_clarification = None
        self._pending_clarification_operation_id = None
        selected_resolution = self.intent_resolver.resolve(
            original_text=state.original_text,
            processing_text=selected.command_text,
            source=source.value,
        )
        return self._execute_resolved_command(
            selected.command_text,
            source,
            selected_resolution,
        )

    @staticmethod
    def _clarification_text_ru(
        question: str | None,
        options: tuple[AppClarificationOption, ...],
    ) -> str:
        lines = [
            "Требуется уточнение:",
            question or "Уточните вариант.",
            "",
            "Варианты:",
        ]
        lines.extend(f"- {option.label_ru}" for option in options)
        return "\n".join(lines)

    def execute_command_text_ru(
        self,
        text: str,
        source: AppCommandSource = AppCommandSource.DESKTOP_UI,
    ) -> str:
        result = self.execute_command(text, source)
        lines = [
            "App command execution:",
            f"- ok: {'yes' if result.ok else 'no'}",
            f"- source: {result.source.value}",
            f"- command id: {result.registry_match_id or 'none'}",
            f"- category: {result.category or 'unknown'}",
            f"- risk: {result.risk_level or 'unknown'}",
            f"- executed through CommandProcessor: {'yes' if result.executed else 'no'}",
            f"- network may be used: {'yes' if result.network_may_be_used else 'no'}",
            "- response executed as command: no",
            "- no secrets",
        ]
        if result.error:
            lines.append(f"- error: {self._safe_text_preview(result.error)}")
        if result.output_text:
            lines.append("Output:")
            lines.append(result.output_text)
        return "\n".join(lines)

    @staticmethod
    def _command_card_from_metadata(metadata: CommandMetadata) -> AppCommandCard:
        return AppCommandCard(
            command_id=metadata.command_id,
            title_ru=metadata.title_ru,
            description_ru=metadata.description_ru,
            category=metadata.category.value,
            aliases=metadata.aliases,
            risk_level=metadata.risk_level.value,
            read_only=metadata.read_only,
            voice_auto_allowed=metadata.voice_auto_allowed,
            requires_confirmation=metadata.requires_confirmation,
            requires_network=metadata.requires_network,
            requires_ai_key=metadata.requires_ai_key,
            requires_privacy_check=metadata.requires_privacy_check,
            app_ready=metadata.app_ready,
            ui_visible=metadata.ui_visible,
            notes_ru=metadata.notes_ru,
        )

    def _match_registry_command(self, text: str) -> CommandMetadata | None:
        exact = self.command_registry.find_by_alias(text)
        if exact is not None:
            return exact

        normalized_text = self.command_registry.normalize_alias(text)
        if self._document_review_path_from_command(text) is not None:
            return self.command_registry.find_by_id("document_review.local_text")
        for command in self.command_registry.commands:
            for alias in command.aliases:
                normalized_alias = self.command_registry.normalize_alias(alias)
                if "<text>" not in normalized_alias:
                    continue
                prefix = normalized_alias.split("<text>", 1)[0].strip()
                if prefix and normalized_text.startswith(prefix):
                    return command
        return None

    @classmethod
    def _document_review_path_from_command(cls, text: str) -> str | None:
        command = str(text or "").strip()
        if not command.startswith(cls.DOCUMENT_REVIEW_PREFIX):
            return None
        path = command[len(cls.DOCUMENT_REVIEW_PREFIX) :].strip()
        return path or None

    @staticmethod
    def _issue_summaries(proposal: DocumentReviewProposal) -> tuple[dict[str, object], ...]:
        return tuple(issue.to_dict() for issue in proposal.issues)

    def _build_document_review_runner(self) -> WorkflowRunner[DocumentReviewRunState]:
        from workflows.contracts import WorkflowStepDefinition

        def action(method_name: str):
            def _run(state: DocumentReviewRunState, token) -> WorkflowStepResult:
                token.raise_if_cancelled()
                try:
                    getattr(self.document_review_workflow, method_name)(state)
                except DocumentReviewWorkflowError as exc:
                    return WorkflowStepResult(
                        step_id=self._current_document_step_id(method_name),
                        status=WorkflowStepStatus.FAILED,
                        safe_message=exc.message_ru,
                        error_code=exc.error_code,
                    )
                return WorkflowStepResult(
                    step_id=self._current_document_step_id(method_name),
                    status=WorkflowStepStatus.SUCCEEDED,
                    safe_message="Шаг проверки документа выполнен.",
                    safe_output_metadata=state.safe_metadata(),
                )

            return _run

        steps: tuple[WorkflowExecutableStep[DocumentReviewRunState], ...] = (
            WorkflowExecutableStep(
                WorkflowStepDefinition("validate_source", "Проверка исходного файла"),
                action("validate_source_step"),
                self._document_read_policy,
            ),
            WorkflowExecutableStep(
                WorkflowStepDefinition("read_source", "Чтение исходного файла"),
                action("read_source_step"),
            ),
            WorkflowExecutableStep(
                WorkflowStepDefinition("analyze_document", "Анализ документа"),
                action("analyze_document_step"),
            ),
            WorkflowExecutableStep(
                WorkflowStepDefinition("prepare_revision", "Подготовка исправленной копии"),
                action("prepare_revision_step"),
            ),
            WorkflowExecutableStep(
                WorkflowStepDefinition(
                    "write_output",
                    "Сохранение новой копии",
                    requires_confirmation=True,
                ),
                action("write_output_step"),
                self._document_write_policy,
            ),
            WorkflowExecutableStep(
                WorkflowStepDefinition(
                    "verify_output",
                    "Проверка сохраненной копии",
                    verification_step=True,
                ),
                action("verify_output_step"),
            ),
            WorkflowExecutableStep(
                WorkflowStepDefinition(
                    "verify_source_unchanged",
                    "Проверка неизменности оригинала",
                    verification_step=True,
                ),
                action("verify_source_unchanged_step"),
            ),
        )
        return WorkflowRunner(
            workflow_id=DOCUMENT_REVIEW_WORKFLOW_ID,
            steps=steps,
            execution_coordinator=self.execution_coordinator,
            policy_boundary=self.policy_boundary,
        )

    @staticmethod
    def _current_document_step_id(method_name: str) -> str:
        return {
            "validate_source_step": "validate_source",
            "read_source_step": "read_source",
            "analyze_document_step": "analyze_document",
            "prepare_revision_step": "prepare_revision",
            "write_output_step": "write_output",
            "verify_output_step": "verify_output",
            "verify_source_unchanged_step": "verify_source_unchanged",
        }[method_name]

    def _document_read_policy(
        self,
        state: DocumentReviewRunState,
        confirmation_present: bool,
    ) -> PolicyRequest:
        return PolicyRequest(
            source="workflow",
            command_id="document_review.local_text",
            action_id="document_review.local_text.read",
            intent_kind="local_command",
            risk="read_only",
            required_capabilities=(PolicyCapability.FILE_READ.value,),
            confirmation_present=True,
            metadata={
                "normalized_text": self.DOCUMENT_REVIEW_PREFIX,
                "workflow_id": DOCUMENT_REVIEW_WORKFLOW_ID,
            },
        )

    def _document_write_policy(
        self,
        state: DocumentReviewRunState,
        confirmation_present: bool,
    ) -> PolicyRequest:
        proposal = state.proposal
        return PolicyRequest(
            source="workflow",
            command_id="document_review.local_text",
            action_id="document_review.local_text.write",
            intent_kind="local_command",
            risk="confirmation_required",
            required_capabilities=(
                PolicyCapability.FILE_READ.value,
                PolicyCapability.FILE_WRITE.value,
            ),
            confirmation_present=confirmation_present,
            metadata={
                "normalized_text": self.DOCUMENT_REVIEW_PREFIX,
                "workflow_id": DOCUMENT_REVIEW_WORKFLOW_ID,
                "source_filename": proposal.source_filename if proposal else None,
                "proposed_output_filename": (
                    proposal.proposed_output_filename if proposal else None
                ),
            },
        )

    def _with_workflow_snapshot(
        self,
        result: AppCommandResult,
        snapshot: WorkflowRunSnapshot | None,
    ) -> AppCommandResult:
        if snapshot is None:
            return result
        return AppCommandResult(
            ok=result.ok,
            input_text=result.input_text,
            output_text=result.output_text,
            source=result.source,
            registry_match_id=result.registry_match_id,
            category=result.category,
            risk_level=result.risk_level,
            executed=result.executed,
            requires_confirmation=result.requires_confirmation,
            network_may_be_used=result.network_may_be_used,
            response_executed_as_command=result.response_executed_as_command,
            error=result.error,
            intent_resolution=result.intent_resolution,
            requires_clarification=result.requires_clarification,
            clarification_question=result.clarification_question,
            clarification_options=result.clarification_options,
            policy_decision=result.policy_decision,
            operation_id=result.operation_id,
            operation_status=result.operation_status,
            idempotency_key=result.idempotency_key,
            duplicate_suppressed=result.duplicate_suppressed,
            cancellable=result.cancellable,
            workflow_id=snapshot.workflow_id,
            workflow_status=snapshot.status.value,
            current_step_id=snapshot.current_step_id,
            current_step_name=snapshot.current_step_name,
            completed_steps=snapshot.completed_step_ids,
            total_steps=snapshot.total_steps,
            progress_percent=snapshot.progress_percent,
            awaiting_confirmation=snapshot.awaiting_confirmation,
            source_filename=result.source_filename,
            proposed_output_filename=result.proposed_output_filename,
            issue_count=result.issue_count,
            issue_summaries=result.issue_summaries,
            proposed_output_path=result.proposed_output_path,
            saved=result.saved,
            verified=result.verified or snapshot.verified,
            user_message=result.user_message,
        )

    def _with_document_review_fields(
        self,
        result: AppCommandResult,
        proposal: DocumentReviewProposal,
        *,
        user_message: str | None = None,
    ) -> AppCommandResult:
        return AppCommandResult(
            ok=result.ok,
            input_text=result.input_text,
            output_text=result.output_text,
            source=result.source,
            registry_match_id=result.registry_match_id,
            category=result.category,
            risk_level=result.risk_level,
            executed=result.executed,
            requires_confirmation=result.requires_confirmation,
            network_may_be_used=result.network_may_be_used,
            response_executed_as_command=result.response_executed_as_command,
            error=result.error,
            intent_resolution=result.intent_resolution,
            requires_clarification=result.requires_clarification,
            clarification_question=result.clarification_question,
            clarification_options=result.clarification_options,
            policy_decision=result.policy_decision,
            operation_id=result.operation_id,
            operation_status=result.operation_status,
            idempotency_key=result.idempotency_key,
            duplicate_suppressed=result.duplicate_suppressed,
            cancellable=result.cancellable,
            workflow_id=proposal.workflow_id,
            workflow_status=result.workflow_status,
            current_step_id=result.current_step_id,
            current_step_name=result.current_step_name,
            completed_steps=result.completed_steps,
            total_steps=result.total_steps,
            progress_percent=result.progress_percent,
            awaiting_confirmation=result.awaiting_confirmation,
            source_filename=proposal.source_filename,
            proposed_output_filename=proposal.proposed_output_filename,
            issue_count=proposal.issue_count,
            issue_summaries=self._issue_summaries(proposal),
            proposed_output_path=proposal.output_path,
            saved=result.saved,
            verified=result.verified,
            user_message=user_message or result.user_message,
        )

    @staticmethod
    def _document_review_review_text(proposal: DocumentReviewProposal) -> str:
        lines = [
            "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 TXT-\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430:",
            f"- workflow status: awaiting_confirmation",
            f"- workflow id: {proposal.workflow_id}",
            f"- source filename: {proposal.source_filename}",
            f"- issues: {proposal.issue_count}",
            f"- proposed output path: {proposal.output_path}",
            "- saved: no",
            "- verified: no",
            "- original modified: no",
            "\u041d\u0430\u0439\u0434\u0435\u043d\u043d\u044b\u0435 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b:",
        ]
        if not proposal.issues:
            lines.append("- \u041f\u0440\u043e\u0431\u043b\u0435\u043c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e; \u0431\u0443\u0434\u0435\u0442 \u0441\u043e\u0437\u0434\u0430\u043d\u0430 \u043a\u043e\u043f\u0438\u044f \u0441 \u0442\u0435\u043c \u0436\u0435 \u0442\u0435\u043a\u0441\u0442\u043e\u043c.")
        else:
            for issue in proposal.issues:
                lines.append(
                    f"- {issue.issue_code}, line {issue.line_number}: {issue.description_ru}"
                )
        lines.append(
            "\u0414\u043b\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f "
            "\u043d\u043e\u0432\u043e\u0439 \u043a\u043e\u043f\u0438\u0438 "
            "\u043e\u0442\u0432\u0435\u0442\u044c\u0442\u0435: \u0434\u0430"
        )
        return "\n".join(lines)

    @staticmethod
    def _document_review_saved_text(proposal: DocumentReviewProposal, output_path: str) -> str:
        return "\n".join(
            [
                "\u041f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043d\u0430\u044f "
                "\u043a\u043e\u043f\u0438\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430:",
                f"- workflow status: succeeded",
                f"- workflow id: {proposal.workflow_id}",
                f"- source filename: {proposal.source_filename}",
                f"- issues fixed: {proposal.issue_count}",
                f"- output path: {output_path}",
                "- saved: yes",
                "- verified: yes",
                "- original modified: no",
            ]
        )

    @staticmethod
    def _parse_category(category: str | None) -> CommandCategory | None:
        if category is None:
            return None
        normalized = str(category or "").strip().lower()
        if not normalized:
            return None
        for command_category in CommandCategory:
            if normalized in {command_category.value, command_category.name.lower()}:
                return command_category
        return None

    @staticmethod
    def _summary_for_metadata(metadata: CommandMetadata) -> str:
        flags = []
        if metadata.requires_network:
            flags.append("требует явной сетевой команды")
        if metadata.requires_ai_key:
            flags.append("может требовать AI ключ")
        if metadata.requires_privacy_check:
            flags.append("требует privacy boundary")
        if metadata.requires_confirmation:
            flags.append("требует подтверждение")
        if metadata.read_only:
            flags.append("read-only")
        flags_text = ", ".join(flags) if flags else "низкий риск"
        return (
            f"{metadata.title_ru}: risk={metadata.risk_level.value}; {flags_text}. "
            "Предпросмотр не выполняет команду."
        )

    @staticmethod
    def _safe_text_preview(text: str) -> str:
        preview = str(text or "").strip()
        preview = re.sub(
            r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+)",
            "[REDACTED]",
            preview,
        )
        if len(preview) > 120:
            preview = preview[:117].rstrip() + "..."
        return preview or "<empty>"

    def _build_audio_lifecycle_controller(self) -> AudioLifecycleController:
        existing_controller = getattr(
            self.command_processor,
            "audio_lifecycle_controller",
            None,
        )
        if existing_controller is not None:
            return existing_controller
        return AudioLifecycleController(
            voice_input_manager=getattr(self.command_processor, "voice_input_manager", None),
            voice_output_manager=getattr(self.command_processor, "voice_output_manager", None),
            microphone_listening_mode_manager=getattr(
                self.command_processor,
                "microphone_listening_mode_manager",
                None,
            ),
            voice_dialogue_mode_manager=getattr(
                self.command_processor,
                "voice_dialogue_mode_manager",
                None,
            ),
            pending_voice_command_checker=getattr(
                self.command_processor,
                "has_pending_voice_command",
                None,
            ),
        )

    def _provider_runtime(self):
        runtime = getattr(self.command_processor, "secure_provider_runtime", None)
        if runtime is not None:
            return runtime
        return SecureProviderRuntime()

    def _get_one_shot_voice_recognition(self):
        if self.one_shot_voice_recognition is not None:
            return self.one_shot_voice_recognition
        recognizer_factory = getattr(
            self.command_processor,
            "_get_one_shot_vosk_real_recognition",
            None,
        )
        if callable(recognizer_factory):
            self.one_shot_voice_recognition = recognizer_factory()
            return self.one_shot_voice_recognition
        from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognition

        self.one_shot_voice_recognition = OneShotVoskRealRecognition()
        return self.one_shot_voice_recognition

    def _cleanup_one_shot_voice_recognition(self):
        recognizer = self.one_shot_voice_recognition
        if recognizer is None:
            return
        for method_name in ("close", "cleanup", "release"):
            method = getattr(recognizer, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass
                return

    def _voice_error_result(
        self,
        error_code: str,
        user_message: str,
        result_type: str,
        voice_capture_succeeded: bool = False,
    ) -> AppVoiceRequestResult:
        return AppVoiceRequestResult(
            ok=False,
            voice_capture_succeeded=voice_capture_succeeded,
            recognition_succeeded=False,
            recognized_text=None,
            text_processing_succeeded=False,
            result_type=result_type,
            category=None,
            requires_confirmation=False,
            error_code=error_code,
            user_message=safe_contract_text(user_message),
            text_result=None,
            secrets_included=False,
            raw_audio_included=False,
            provider_objects_included=False,
            microphone_objects_included=False,
            normalized_text=None,
            normalization_applied=False,
            normalization_rules=(),
        )

    def _voice_message_from_recognition(self, recognition_result, fallback: str) -> str:
        reasons = list(self._get_value(recognition_result, "reasons", ()) or ())
        if reasons:
            return safe_contract_text("; ".join(str(reason) for reason in reasons))
        return fallback

    @staticmethod
    def _voice_error_code_from_reasons(reasons) -> str:
        text = " ".join(str(reason or "").lower() for reason in reasons or ())
        mapping = (
            ("runtime", "vosk_runtime_unavailable"),
            ("vosk", "vosk_unavailable"),
            ("model", "vosk_model_unavailable"),
            ("microphone", "microphone_unavailable"),
            ("audio", "audio_capture_failure"),
            ("timeout", "capture_timeout"),
            ("cancel", "request_cancelled"),
        )
        for marker, code in mapping:
            if marker in text:
                return code
        return "recognition_blocked"

    @staticmethod
    def _get_value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)
