"""Safe app-facing service layer for JARVIS.

The service is a boundary for future UI code. It can inspect command metadata
and delegate execution to CommandProcessor, but it does not execute commands,
call providers, route actions, read arbitrary files, or persist prompts.
"""

from collections.abc import Callable
from dataclasses import dataclass
import re
from threading import Lock
from uuid import uuid4

from app.startup_profiler import StartupProfiler, StartupProfileSnapshot
from app.app_contracts import (
    APP_CONTRACT_SCHEMA_NAME,
    APP_CONTRACT_VERSION,
    ApplicationActivitySnapshotDto,
    AppCommandCard,
    AppCommandPreview,
    AppCommandResult,
    AppCommandSource,
    AppExecutionHistoryEntry,
    AppExecutionHistoryResult,
    AppClarificationOption,
    AppContractManifest,
    AppContractStatus,
    AppExecutionContract,
    AppLanguagePreferenceContract,
    AppPreviewContract,
    AppStatusCard,
    AppVoiceRequestResult,
    safe_contract_text,
    safe_history_text,
)
from app.activity import ApplicationActivityTracker
from app.text_normalization import normalize_control_text
from core.lazy_component import LazyComponent
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
from cognition import (
    CognitiveInteractionResult,
    CognitiveInteractionService,
    CompatibilityResponseComposer,
    ConversationContextProjector,
    ConversationSessionService,
    ConversationSessionSnapshot,
    ConversationTurnInput,
    ResponseCompositionInput,
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
from language.language_manager import ApplicationLanguageManager, SupportedLanguage
from memory import LocalMemoryManager, MemoryOperationResult, SessionConversationContext
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
from workflows.contracts import (
    WorkflowHistoryResult,
    WorkflowCancellationEligibility,
    WorkflowCancellationRejectionReason,
    WorkflowCancellationResult,
    WorkflowCancellationStatus,
    WorkflowResumeEligibility,
    WorkflowResumeRejectionReason,
    WorkflowResumeResult,
    WorkflowResumeStatus,
    WorkflowRunSnapshot,
    WorkflowStepResult,
    WorkflowStepStatus,
)
from workflows.runner import WorkflowExecutableStep, WorkflowRunner
from planner import (
    MultiStepPlanner,
    PlanCapability,
    PlanCapabilityDescriptor,
    PlanExecutor,
    PlanSideEffect,
    PlannerCapabilityRegistry,
)


SAFE_ONE_SHOT_MICROPHONE_FAILURE_MESSAGE = (
    "Не удалось получить доступ к микрофону. "
    "Проверьте разрешение на использование микрофона в настройках Windows. "
    "Убедитесь, что устройство ввода подключено и не используется другим приложением. "
    "После исправления повторите голосовую команду."
)

SAFE_ONE_SHOT_VOICE_FAILURE_MESSAGE = (
    "Голосовой запрос безопасно завершился ошибкой. "
    "Проверьте доступ к микрофону и повторите явную голосовую команду."
)

_RAW_ONE_SHOT_VOICE_ERROR_MARKERS = (
    "paerrorcode",
    "mme error",
    "portaudio",
    "error querying device",
    "device",
    "device id",
    "sounddevice",
    "traceback",
    "runtimeerror",
    "exception",
    "backend",
)
_WINDOWS_PATH_PATTERN = re.compile(r"(?i)\b[a-z]:[\\/]")
_USER_PATH_PATTERN = re.compile(r"(?i)([\\/]|^)(users|home)[\\/][^\\/\s]+")


def _looks_like_raw_voice_error(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return False
    if any(marker in normalized for marker in _RAW_ONE_SHOT_VOICE_ERROR_MARKERS):
        return True
    return bool(
        _WINDOWS_PATH_PATTERN.search(normalized)
        or _USER_PATH_PATTERN.search(normalized)
    )


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
class PendingMemoryForgetAllConfirmation:
    operation_id: str
    active: bool = True
    completed: bool = False


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


@dataclass(frozen=True)
class PlannerCapabilityCallResult:
    safe_message: str


@dataclass(frozen=True)
class DirectStateChangePreparation:
    command_id: str
    category: str
    safe_preview: str
    execute: Callable[[], AppCommandResult | None]


class JarvisAppService:
    """Stable boundary for app/UI code."""

    DEFAULT_EXECUTION_HISTORY_LIMIT = 50
    MAX_EXECUTION_HISTORY_LIMIT = 100
    DEFAULT_WORKFLOW_HISTORY_LIMIT = 25
    MAX_WORKFLOW_HISTORY_LIMIT = 100
    DEFAULT_ACTIVITY_RECENT_LIMIT = 10
    MAX_ACTIVITY_RECENT_LIMIT = 25

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
        memory_manager=None,
        conversation_context=None,
        startup_clock=None,
        provider_runtime_factory=None,
        one_shot_voice_recognition_factory=None,
        planner_service=None,
        cognitive_session_service=None,
        cognitive_session_repository=None,
        cognitive_context_projector=None,
        cognitive_response_composer=None,
        cognitive_interaction_service=None,
    ):
        self._startup_profiler = StartupProfiler(clock=startup_clock)
        self._startup_eager_components = (
            "command_registry",
            "intent_resolver",
            "language_manager",
            "policy_boundary",
            "execution_coordinator",
            "execution_journal",
            "audio_lifecycle_metadata",
            "memory_context",
            "document_review_workflow",
        )
        with self._startup_profiler.phase("command_registry", "Command registry"):
            self.command_registry = command_registry or DEFAULT_COMMAND_REGISTRY
        with self._startup_profiler.phase("command_processor", "Command processor"):
            if command_processor is None:
                from core.command_processor import CommandProcessor

                command_processor = CommandProcessor(command_registry=self.command_registry)
            self.command_processor = command_processor
        with self._startup_profiler.phase("lazy_optional_components", "Lazy optional components"):
            self._provider_runtime_component = LazyComponent(
                "secure_provider_runtime",
                provider_runtime_factory or self._default_provider_runtime_factory,
                failure_error_code="provider_runtime_initialization_failed",
            )
            self._one_shot_voice_component = LazyComponent(
                "one_shot_voice_recognition",
                one_shot_voice_recognition_factory
                or self._default_one_shot_voice_recognition_factory,
                failure_error_code="voice_recognition_initialization_failed",
            )
            self.one_shot_voice_recognition = one_shot_voice_recognition
        with self._startup_profiler.phase("language_manager", "Language manager"):
            self.language_manager = (
                language_manager
                or (
                    ApplicationLanguageManager.from_profile_manager(
                        getattr(command_processor, "user_profile_manager")
                    )
                    if getattr(command_processor, "user_profile_manager", None) is not None
                    else None
                )
                or ApplicationLanguageManager.from_profile(
                    getattr(command_processor, "user_profile", None)
                )
            )
            if hasattr(self.command_processor, "language_manager"):
                self.command_processor.language_manager = self.language_manager
        with self._startup_profiler.phase("memory_context", "Memory conversation context"):
            self.memory_manager = (
                memory_manager
                or getattr(self.command_processor, "memory_manager", None)
                or LocalMemoryManager()
            )
            self.conversation_context = conversation_context or SessionConversationContext()
        self._one_shot_voice_lock = Lock()
        with self._startup_profiler.phase("app_safety_boundaries", "App safety boundaries"):
            self.audio_lifecycle_controller = self._build_audio_lifecycle_controller()
            self.conversational_loop = SafeConversationalLoop(
                app_service=self,
                command_registry=self.command_registry,
            )
            self.cognitive_session_service = (
                cognitive_session_service
                or ConversationSessionService(repository=cognitive_session_repository)
            )
            self.cognitive_context_projector = (
                cognitive_context_projector or ConversationContextProjector()
            )
            self.cognitive_response_composer = (
                cognitive_response_composer
                or CompatibilityResponseComposer(
                    delegate=self._cognitive_compatibility_response,
                )
            )
            self.cognitive_interaction_service = (
                cognitive_interaction_service
                or CognitiveInteractionService(
                    session_service=self.cognitive_session_service,
                    context_projector=self.cognitive_context_projector,
                    response_composer=self.cognitive_response_composer,
                )
            )
            self.intent_resolver = HybridIntentResolver(self.command_registry)
            self.policy_boundary = PolicyDecisionBoundary()
            self.execution_coordinator = ExecutionCoordinator()
            self.activity_tracker = ApplicationActivityTracker(
                recent_limit=self.DEFAULT_ACTIVITY_RECENT_LIMIT,
            )
        self._pending_clarification: ClarificationState | None = None
        self._pending_clarification_operation_id: str | None = None
        self._pending_confirmation: PendingAppConfirmation | None = None
        self._pending_document_review: PendingDocumentReviewConfirmation | None = None
        self._pending_memory_forget_all: PendingMemoryForgetAllConfirmation | None = None
        self._operation_results: dict[str, AppCommandResult] = {}
        self.planner_registry = self._build_planner_registry()
        self.multi_step_planner = MultiStepPlanner(self.planner_registry)
        self.plan_executor = PlanExecutor(
            registry=self.planner_registry,
            execution_coordinator=self.execution_coordinator,
            policy_boundary=self.policy_boundary,
        )
        if planner_service is None:
            from app.services.planner_command_service import PlannerCommandService

            planner_service = PlannerCommandService(
                multi_step_planner=self.multi_step_planner,
                plan_executor=self.plan_executor,
                language_code=lambda: self.language_manager.get_preference().language_code,
                localized_text=self._language_text,
                safe_text_preview=self._safe_text_preview,
            )
        self.planner_service = planner_service
        with self._startup_profiler.phase("document_workflow", "Document workflow"):
            self._local_filesystem = local_filesystem or WindowsLocalFileSystemAdapter()
            self.document_review_workflow = LocalTextDocumentReviewWorkflow(
                filesystem=self._local_filesystem,
            )
            self.document_review_runner = self._build_document_review_runner()
        self._startup_profiler.complete()

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

    def get_startup_profile(self) -> StartupProfileSnapshot:
        return self._startup_profiler.snapshot(
            eager_components=self._startup_eager_components,
            deferred_components=self._lazy_component_snapshots(),
            message="startup completed; optional components initialize on first explicit use",
        )

    def startup_profile_text_ru(self) -> str:
        profile = self.get_startup_profile()
        lines = [
            "Startup profile:",
            f"- startup completed: {'yes' if profile.startup_completed else 'no'}",
            f"- total duration ms: {profile.total_duration_ms:.3f}",
            "- external telemetry: no",
            "- persisted: no",
            "- no secrets",
            "Phases:",
        ]
        for phase in profile.phases:
            lines.append(
                f"- {phase.phase_id}: {phase.duration_ms:.3f} ms | "
                f"succeeded: {'yes' if phase.succeeded else 'no'} | "
                f"error: {phase.error_code or 'none'}"
            )
        lines.append("Optional components:")
        for component in profile.deferred_components:
            lines.append(
                f"- {component.component_id}: {component.state} | "
                f"initialization_count: {component.initialization_count} | "
                f"error: {component.error_code or 'none'}"
            )
        return "\n".join(lines)

    def language_settings(self) -> dict[str, str]:
        return self.language_manager.status_dict()

    def get_language_preference(self) -> AppLanguagePreferenceContract:
        snapshot = self.language_manager.get_preference()
        return AppLanguagePreferenceContract(
            language_code=snapshot.language_code,
            language_name=snapshot.display_name,
            previous_language_code=None,
            changed=False,
            persisted=snapshot.persisted,
            default_language="ru-RU",
            source=snapshot.source,
            is_default=snapshot.is_default,
            message=snapshot.safe_message,
            supported_languages=tuple(language.value for language in SupportedLanguage),
        )

    def set_language_preference(self, language_code) -> AppLanguagePreferenceContract:
        change = self.language_manager.set_preference(language_code)
        self._propagate_language_preference()
        snapshot = self.language_manager.get_preference()
        return AppLanguagePreferenceContract(
            language_code=change.language_code,
            language_name=change.language_name,
            previous_language_code=change.previous_language_code,
            changed=change.changed,
            persisted=change.persisted,
            default_language=change.default_language,
            source=snapshot.source,
            is_default=snapshot.is_default,
            message=change.safe_message,
            supported_languages=tuple(language.value for language in SupportedLanguage),
        )

    def reset_language_preference(self) -> AppLanguagePreferenceContract:
        return self.set_language_preference("ru-RU")

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
            plan_id=result.plan_id,
            plan_status=result.plan_status,
            plan_step_count=result.plan_step_count,
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
            try:
                recognition_result = recognizer.run_once(
                    explicit_one_shot_requested=True,
                    language_code=self.language_manager.runtime_locale(),
                )
            except TypeError:
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
                user_message=self._safe_one_shot_voice_exception_message(exc),
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

    def start_conversation_session(self) -> ConversationSessionSnapshot:
        return self.cognitive_session_service.create_session()

    def conversation_session_snapshot(self, session_id: str) -> ConversationSessionSnapshot:
        return self.cognitive_session_service.get_snapshot(session_id)

    def handle_conversation_turn(
        self,
        text: str,
        source: AppCommandSource | str = AppCommandSource.UNKNOWN,
        session_id: str | None = None,
        locale: str | None = None,
    ) -> CognitiveInteractionResult:
        return self.cognitive_interaction_service.handle_turn(
            ConversationTurnInput(
                text=text,
                source=self._source_value(source),
                session_id=session_id,
                locale=locale,
            )
        )

    def close_conversation_session(self, session_id: str) -> ConversationSessionSnapshot:
        return self.cognitive_session_service.close_session(session_id)

    def _cognitive_compatibility_response(
        self,
        composition_input: ResponseCompositionInput,
    ) -> str:
        result = self.conversational_loop.handle(
            ConversationalRequest(
                text=composition_input.current_user_turn.text,
                source=composition_input.source,
                allow_network=False,
                allow_command_execution=False,
                allow_risky_actions=False,
            )
        )
        return self.conversational_loop.result_text_ru(result)

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
        planner_preview = self._preview_planner_command(input_text, normalized_text)
        if planner_preview is not None:
            return planner_preview
        memory_preview = self._preview_memory_command(input_text, normalized_text)
        if memory_preview is not None:
            return memory_preview
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

    def _preview_planner_command(
        self,
        input_text: str,
        normalized_text: str,
    ) -> AppCommandPreview | None:
        return self.planner_service.preview_command(input_text, normalized_text)

    def _preview_memory_command(
        self,
        input_text: str,
        normalized_text: str,
    ) -> AppCommandPreview | None:
        parsed = self._parse_memory_command(input_text)
        if parsed is None:
            return None
        action, _key, _value = parsed
        memory_metadata = {
            "remember": ("memory.remember", "Remember fact", "local_write", False, False),
            "recall": ("memory.recall", "Recall memory", "read_only", True, False),
            "forget": ("memory.forget", "Forget memory", "local_write", False, False),
            "list": ("memory.list", "List memories", "read_only", True, False),
            "forget_all": (
                "memory.forget_all",
                "Forget all memory",
                "confirmation_required",
                False,
                True,
            ),
        }.get(action)
        if memory_metadata is None:
            return None
        command_id, title_ru, risk_level, read_only, requires_confirmation = memory_metadata
        return AppCommandPreview(
            input_text=input_text,
            normalized_text=normalized_text,
            registry_match_id=command_id,
            title_ru=title_ru,
            category="memory",
            risk_level=risk_level,
            read_only=read_only,
            voice_auto_allowed=False,
            requires_confirmation=requires_confirmation,
            requires_network=False,
            requires_ai_key=False,
            requires_privacy_check=False,
            app_ready=True,
            known_command=True,
            safe_summary_ru=(
                "Memory command recognized from the AppService parser. Preview does not "
                "read or mutate memory, create operations, or arm confirmation."
            ),
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
                f"- active plan id: {preview.active_plan_id or 'none'}",
                f"- active plan status: {preview.active_plan_status or 'none'}",
                f"- active step id: {preview.active_step_id or 'none'}",
                f"- active step capability: {preview.active_step_capability_id or 'none'}",
                f"- active step name: {preview.active_step_name or 'none'}",
                f"- operation id: {preview.operation_id or 'none'}",
                "- executed through AppService: yes",
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
        startup_profile_result = self._handle_startup_profile_command(input_text, source)
        if startup_profile_result is not None:
            return startup_profile_result
        language_preparation = self._prepare_direct_language_state_change(
            input_text,
            source,
        )
        if language_preparation is not None:
            return self._coordinate_prepared_direct_state_change(
                input_text,
                source,
                language_preparation,
                idempotency_key=idempotency_key,
            )
        language_result = self._handle_language_preference_command(input_text, source)
        if language_result is not None:
            return language_result
        memory_control = self._consume_pending_memory_forget_all(input_text, source)
        if memory_control is not None:
            return memory_control
        planner_result = self._handle_planner_command(
            input_text,
            source,
            idempotency_key=idempotency_key,
        )
        if planner_result is not None:
            return planner_result
        memory_preparation = self._prepare_direct_memory_state_change(
            input_text,
            source,
        )
        if memory_preparation is not None:
            return self._coordinate_prepared_direct_state_change(
                input_text,
                source,
                memory_preparation,
                idempotency_key=idempotency_key,
            )
        memory_result = self._handle_memory_command(input_text, source)
        if memory_result is not None:
            return memory_result
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
        elif not result.ok and self._is_local_tts_result(result):
            operation = self.execution_coordinator.mark_failed(
                operation.operation_id,
                error_code=result.error or "command_execution_failed",
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

    def _handle_planner_command(
        self,
        input_text: str,
        source: AppCommandSource,
        *,
        idempotency_key: str | None,
    ) -> AppCommandResult | None:
        return self.planner_service.handle_command(
            input_text,
            source,
            idempotency_key=idempotency_key,
        )

    def _coordinate_prepared_direct_state_change(
        self,
        input_text: str,
        source: AppCommandSource,
        preparation: DirectStateChangePreparation,
        *,
        idempotency_key: str | None,
    ) -> AppCommandResult:
        fingerprint = self.execution_coordinator.create_request_fingerprint(
            source=source.value,
            text=input_text,
            command_id=preparation.command_id,
        )
        registration = self.execution_coordinator.register(
            source=source.value,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            command_id=preparation.command_id,
            metadata={
                "input_preview": preparation.safe_preview,
                "category": preparation.category,
                "risk_level": "local_write",
                "requires_confirmation": "no",
                "network_may_be_used": "no",
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
                output_text="Duplicate request suppressed: operation is already registered.",
                category=preparation.category,
                risk_level="local_write",
            )
        if registration.conflict:
            conflict = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Request denied: idempotency key conflict. Command was not executed.",
                category=preparation.category,
                risk_level="local_write",
                error="idempotency_conflict",
            )
            self._remember_operation_result(conflict)
            return conflict
        try:
            result = preparation.execute()
        except Exception as exc:
            operation = self.execution_coordinator.mark_failed(
                operation.operation_id,
                error_code=str(exc) or "direct_state_change_failed",
            )
            failed = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="",
                category=preparation.category,
                risk_level="local_write",
                error=str(exc),
            )
            self._remember_operation_result(failed)
            return failed
        if result is None:
            operation = self.execution_coordinator.mark_failed(
                operation.operation_id,
                error_code="direct_state_change_not_handled",
            )
            failed = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="",
                category=preparation.category,
                risk_level="local_write",
                error="direct_state_change_not_handled",
            )
            self._remember_operation_result(failed)
            return failed
        if result.requires_confirmation and not result.executed:
            operation = self.execution_coordinator.mark_awaiting_confirmation(
                operation.operation_id
            )
        elif result.ok:
            operation = self.execution_coordinator.mark_succeeded(
                operation.operation_id,
                summary=result.output_text,
            )
        else:
            operation = self.execution_coordinator.mark_failed(
                operation.operation_id,
                error_code=result.error or "direct_state_change_failed",
            )
        coordinated = self._with_operation(result, operation)
        self._remember_operation_result(coordinated)
        return coordinated

    def _coordinate_direct_state_change_result(
        self,
        input_text: str,
        source: AppCommandSource,
        result: AppCommandResult,
        *,
        idempotency_key: str | None,
    ) -> AppCommandResult:
        if result.operation_id is not None:
            return result
        if not result.executed and not result.requires_confirmation:
            return result
        command_id = result.registry_match_id
        fingerprint = self.execution_coordinator.create_request_fingerprint(
            source=source.value,
            text=input_text,
            command_id=command_id,
        )
        registration = self.execution_coordinator.register(
            source=source.value,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            command_id=command_id,
            metadata={
                "input_preview": safe_journal_text(input_text),
                "category": result.category,
                "risk_level": result.risk_level,
                "requires_confirmation": result.requires_confirmation,
                "network_may_be_used": result.network_may_be_used,
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
                category=result.category or "duplicate_suppressed",
                risk_level=result.risk_level or "safe_metadata_only",
            )
        if registration.conflict:
            conflict = self._operation_metadata_result(
                input_text=input_text,
                source=source,
                operation=operation,
                output_text="Запрос отклонён: конфликт idempotency key. Команда не запускалась.",
                category=result.category or "policy_denied",
                risk_level=result.risk_level or "safe_metadata_only",
                error="idempotency_conflict",
            )
            self._remember_operation_result(conflict)
            return conflict
        if result.requires_confirmation and not result.executed:
            operation = self.execution_coordinator.mark_awaiting_confirmation(
                operation.operation_id
            )
        elif result.executed:
            operation = self.execution_coordinator.mark_succeeded(
                operation.operation_id,
                summary=result.output_text,
            )
        coordinated = self._with_operation(result, operation)
        self._remember_operation_result(coordinated)
        return coordinated

    def _execute_command_uncoordinated(
        self,
        text: str,
        source: AppCommandSource = AppCommandSource.DESKTOP_UI,
    ) -> AppCommandResult:
        if not isinstance(source, AppCommandSource):
            source = AppCommandSource.UNKNOWN
        input_text = str(text or "").strip()
        startup_profile_result = self._handle_startup_profile_command(input_text, source)
        if startup_profile_result is not None:
            return startup_profile_result
        language_result = self._handle_language_preference_command(input_text, source)
        if language_result is not None:
            return language_result
        memory_control = self._consume_pending_memory_forget_all(input_text, source)
        if memory_control is not None:
            return memory_control
        memory_result = self._handle_memory_command(input_text, source)
        if memory_result is not None:
            return memory_result
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
        language_result = self._handle_language_preference_command(input_text, source)
        if language_result is not None:
            return language_result
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
            local_tts_metadata = self._local_tts_execution_metadata(
                input_text,
                resolution,
                processor_result,
            )
            requires_confirmation = preview.requires_confirmation
            if not confirmation_present and (
                processor_result.get("requires_confirmation") is False
                or processor_result.get("intent") == "microphone.mode.status"
                or local_tts_metadata is not None
            ):
                requires_confirmation = False
            registry_match_id = preview.registry_match_id
            category = preview.category
            risk_level = preview.risk_level
            network_may_be_used = preview.requires_network
            ok = True
            error = None
            if local_tts_metadata is not None:
                registry_match_id = local_tts_metadata["registry_match_id"]
                category = local_tts_metadata["category"]
                risk_level = local_tts_metadata["risk_level"]
                network_may_be_used = False
                ok = bool(local_tts_metadata["ok"])
                error = local_tts_metadata["error"]
            return AppCommandResult(
                ok=ok,
                input_text=input_text,
                output_text=output_text,
                source=source,
                registry_match_id=registry_match_id,
                category=category,
                risk_level=risk_level,
                executed=True,
                requires_confirmation=requires_confirmation,
                network_may_be_used=network_may_be_used,
                response_executed_as_command=False,
                error=error,
                intent_resolution=resolution,
                policy_decision=policy_decision,
            )
        except Exception as exc:
            if confirmation_present and hasattr(
                self.command_processor,
                "_policy_confirmation_for_command",
            ):
                self.command_processor._policy_confirmation_for_command = previous_confirmation
            local_tts_metadata = self._local_tts_execution_metadata(
                input_text,
                resolution,
                None,
            )
            if local_tts_metadata is not None:
                return AppCommandResult(
                    ok=False,
                    input_text=input_text,
                    output_text="",
                    source=source,
                    registry_match_id=local_tts_metadata["registry_match_id"],
                    category=local_tts_metadata["category"],
                    risk_level=local_tts_metadata["risk_level"],
                    executed=False,
                    requires_confirmation=False,
                    network_may_be_used=False,
                    response_executed_as_command=False,
                    error=str(exc),
                    intent_resolution=resolution,
                    policy_decision=policy_decision,
                )
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

    LOCAL_TTS_STATUS_COMMANDS = frozenset(
        {
            "диагностика локального голоса",
            "проверить локальный голос",
            "проверить голос windows",
            "статус локального голоса windows",
            "доступен ли голос windows",
        }
    )
    LOCAL_TTS_ENABLE_COMMANDS = frozenset(
        {
            "включить локальный голос",
            "включить голос windows",
            "включи локальный голос",
            "режим голоса windows",
            "режим голоса локальный",
        }
    )
    LOCAL_TTS_TEST_COMMANDS = frozenset(
        {
            "тест локального голоса",
            "проверка локального голоса",
        }
    )
    LOCAL_TTS_RESULT_IDS = frozenset(
        {
            "voice.output.local.status",
            "voice.output.windows_local.enable",
            "voice.output.local_test.not_enabled",
            "voice.output.spoken",
        }
    )

    @classmethod
    def _local_tts_execution_metadata(
        cls,
        input_text: str,
        resolution,
        processor_result,
    ) -> dict[str, object] | None:
        processor_result = processor_result or {}
        processor_intent = str(processor_result.get("intent") or "")
        resolver_command_id = str(getattr(resolution, "command_id", "") or "")
        normalized_text = CommandRegistry.normalize_alias(input_text)
        if (
            processor_intent == "voice.output.local.status"
            or resolver_command_id == "voice.output.local.status"
            or (
                not processor_intent
                and normalized_text in cls.LOCAL_TTS_STATUS_COMMANDS
            )
        ):
            return {
                "registry_match_id": "voice.output.local.status",
                "category": "voice",
                "risk_level": "read_only",
                "ok": True,
                "error": None,
            }
        if (
            processor_intent
            in {
                "voice.output.windows_local.enabled",
                "voice.output.windows_local.unavailable",
            }
            or resolver_command_id == "voice.output.windows_local.enable"
            or (
                not processor_intent
                and normalized_text in cls.LOCAL_TTS_ENABLE_COMMANDS
            )
        ):
            ok = processor_intent != "voice.output.windows_local.unavailable"
            return {
                "registry_match_id": "voice.output.windows_local.enable",
                "category": "voice",
                "risk_level": "local_runtime",
                "ok": ok,
                "error": None if ok else "voice.output.windows_local.unavailable",
            }
        if processor_intent == "voice.output.local_test.not_enabled":
            return {
                "registry_match_id": "voice.output.local_test.not_enabled",
                "category": "voice",
                "risk_level": "local_runtime",
                "ok": False,
                "error": "voice.output.local_test.not_enabled",
            }
        if (
            processor_intent == "voice.output.spoken"
            and normalized_text in cls.LOCAL_TTS_TEST_COMMANDS
        ):
            ok = processor_result.get("local_tts_success") is not False
            return {
                "registry_match_id": "voice.output.spoken",
                "category": "voice",
                "risk_level": "local_runtime",
                "ok": ok,
                "error": None if ok else "voice.output.local_test.failed",
            }
        return None

    @classmethod
    def _is_local_tts_result(cls, result: AppCommandResult) -> bool:
        return (
            result.category == "voice"
            and result.registry_match_id in cls.LOCAL_TTS_RESULT_IDS
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

    def execution_history(
        self,
        limit: int | None = None,
    ) -> AppExecutionHistoryResult:
        effective_limit = self._bounded_history_limit(limit)
        try:
            operations = self.execution_coordinator.recent_operations(effective_limit)
            entries = tuple(
                self._history_entry_from_operation(operation)
                for operation in reversed(operations)
            )
            return AppExecutionHistoryResult(
                ok=True,
                entries=entries,
                limit=effective_limit,
                max_limit=self.MAX_EXECUTION_HISTORY_LIMIT,
                empty=not entries,
                error=None,
            )
        except Exception:
            return AppExecutionHistoryResult(
                ok=False,
                entries=(),
                limit=effective_limit,
                max_limit=self.MAX_EXECUTION_HISTORY_LIMIT,
                empty=True,
                error="execution_history_unavailable",
            )

    def execution_history_text_ru(self, limit: int | None = None) -> str:
        return self.execution_history(limit).safe_text_ru()

    def application_activity(self) -> ApplicationActivitySnapshotDto:
        try:
            operations = self.execution_coordinator.recent_operations(
                self.MAX_ACTIVITY_RECENT_LIMIT,
            )
            return self.activity_tracker.snapshot_from_operations(operations)
        except Exception:
            return self.activity_tracker.snapshot_unavailable(
                error="application_activity_unavailable",
            )

    def recent_workflow_runs(self, limit: int | None = None) -> WorkflowHistoryResult:
        effective_limit = self._bounded_workflow_history_limit(limit)
        try:
            runs = self.document_review_runner.recent_run_histories(effective_limit)
            return WorkflowHistoryResult(
                ok=True,
                runs=runs,
                limit=effective_limit,
                max_limit=self.MAX_WORKFLOW_HISTORY_LIMIT,
                empty=not runs,
                error=None,
            )
        except Exception:
            return WorkflowHistoryResult(
                ok=False,
                runs=(),
                limit=effective_limit,
                max_limit=self.MAX_WORKFLOW_HISTORY_LIMIT,
                empty=True,
                error="workflow_history_unavailable",
            )

    def workflow_run_history(self, run_id: str) -> WorkflowHistoryResult:
        try:
            run = self.document_review_runner.run_history(str(run_id or ""))
            return WorkflowHistoryResult(
                ok=True,
                runs=(run,),
                limit=1,
                max_limit=self.MAX_WORKFLOW_HISTORY_LIMIT,
                empty=False,
                error=None,
            )
        except Exception:
            return WorkflowHistoryResult(
                ok=False,
                runs=(),
                limit=1,
                max_limit=self.MAX_WORKFLOW_HISTORY_LIMIT,
                empty=True,
                error="workflow_history_unavailable",
            )

    def workflow_resume_eligibility(self, run_id: str) -> WorkflowResumeEligibility:
        try:
            return self.document_review_runner.resume_eligibility(str(run_id or ""))
        except Exception:
            return WorkflowResumeEligibility(
                eligible=False,
                source_run_id=str(run_id or ""),
                reason=WorkflowResumeRejectionReason.INTERNAL_ERROR,
                safe_message="Workflow resume eligibility is unavailable.",
            )

    def resume_workflow_run(self, run_id: str) -> WorkflowResumeResult:
        source_run_id = safe_journal_text(str(run_id or ""), max_length=80)
        if not source_run_id:
            return WorkflowResumeResult(
                ok=False,
                status=WorkflowResumeStatus.REJECTED,
                source_run_id="",
                rejection_reason=WorkflowResumeRejectionReason.NOT_FOUND,
                safe_message="Workflow run was not found.",
            )
        try:
            eligibility = self.document_review_runner.resume_eligibility(source_run_id)
        except Exception:
            return WorkflowResumeResult(
                ok=False,
                status=WorkflowResumeStatus.REJECTED,
                source_run_id=source_run_id,
                rejection_reason=WorkflowResumeRejectionReason.INTERNAL_ERROR,
                safe_message="Workflow resume eligibility is unavailable.",
            )
        if not eligibility.eligible:
            return WorkflowResumeResult(
                ok=False,
                status=WorkflowResumeStatus.REJECTED,
                source_run_id=source_run_id,
                rejection_reason=eligibility.reason,
                safe_message=eligibility.safe_message,
            )

        policy = self.policy_boundary.evaluate(
            PolicyRequest(
                source=AppCommandSource.DESKTOP_UI.value,
                command_id="workflow.resume",
                action_id="workflow.resume",
                intent_kind="workflow_control",
                risk="confirmation_required",
                required_capabilities=(PolicyCapability.FILE_READ.value, PolicyCapability.FILE_WRITE.value),
                confirmation_present=True,
                metadata={
                    "normalized_text": "workflow resume",
                    "workflow_id": DOCUMENT_REVIEW_WORKFLOW_ID,
                    "workflow_run_id": source_run_id,
                },
            )
        )
        if policy.decision == PolicyDecisionType.DENY:
            return WorkflowResumeResult(
                ok=False,
                status=WorkflowResumeStatus.REJECTED,
                source_run_id=source_run_id,
                resume_step_id=eligibility.resume_step_id,
                resume_step_index=eligibility.resume_step_index,
                rejection_reason=WorkflowResumeRejectionReason.POLICY_DENIED,
                safe_message=policy.user_message,
            )

        fingerprint = self.execution_coordinator.create_request_fingerprint(
            source=AppCommandSource.DESKTOP_UI.value,
            text=f"workflow resume {source_run_id}",
            command_id="workflow.resume",
            action_id="workflow.resume",
        )
        registration = self.execution_coordinator.register(
            source=AppCommandSource.DESKTOP_UI.value,
            idempotency_key=f"workflow-resume:{source_run_id}",
            request_fingerprint=fingerprint,
            command_id="workflow.resume",
            action_id="workflow.resume",
            metadata={
                "workflow_id": DOCUMENT_REVIEW_WORKFLOW_ID,
                "workflow_resume_source_run_id": source_run_id,
                "workflow_resume_start_step_id": eligibility.resume_step_id or "",
                "workflow_resume_start_step_index": (
                    eligibility.resume_step_index
                    if eligibility.resume_step_index is not None
                    else ""
                ),
            },
        )
        operation = registration.operation
        self.execution_coordinator.set_policy_decision(operation.operation_id, policy.to_dict())
        if registration.duplicate or registration.conflict:
            return WorkflowResumeResult(
                ok=False,
                status=WorkflowResumeStatus.CONFLICT,
                source_run_id=source_run_id,
                resumed_run_id=operation.operation_id,
                resume_step_id=eligibility.resume_step_id,
                resume_step_index=eligibility.resume_step_index,
                rejection_reason=WorkflowResumeRejectionReason.CONCURRENT_RESUME_CONFLICT,
                safe_message="Workflow resume request is already in progress.",
            )

        try:
            self.document_review_runner.policy_boundary = self.policy_boundary
            return self.document_review_runner.resume_from_run(
                source_operation_id=source_run_id,
                operation=operation,
                token=registration.token,
            )
        except Exception:
            self.execution_coordinator.mark_failed(
                operation.operation_id,
                error_code="workflow_resume_failed",
            )
            return WorkflowResumeResult(
                ok=False,
                status=WorkflowResumeStatus.FAILED,
                source_run_id=source_run_id,
                resumed_run_id=operation.operation_id,
                resume_step_id=eligibility.resume_step_id,
                resume_step_index=eligibility.resume_step_index,
                rejection_reason=WorkflowResumeRejectionReason.INTERNAL_ERROR,
                safe_message="Workflow resume failed safely.",
            )

    def workflow_cancellation_eligibility(self, run_id: str) -> WorkflowCancellationEligibility:
        try:
            return self.document_review_runner.cancellation_eligibility(str(run_id or ""))
        except Exception:
            return WorkflowCancellationEligibility(
                eligible=False,
                run_id=str(run_id or ""),
                reason=WorkflowCancellationRejectionReason.INTERNAL_ERROR,
                safe_message="Workflow cancellation eligibility is unavailable.",
            )

    def cancel_workflow_run(self, run_id: str) -> WorkflowCancellationResult:
        workflow_run_id = safe_journal_text(str(run_id or ""), max_length=80)
        if not workflow_run_id:
            return WorkflowCancellationResult(
                ok=False,
                status=WorkflowCancellationStatus.REJECTED,
                run_id="",
                rejection_reason=WorkflowCancellationRejectionReason.NOT_FOUND,
                safe_message="Workflow run was not found.",
            )
        try:
            eligibility = self.document_review_runner.cancellation_eligibility(workflow_run_id)
        except Exception:
            return WorkflowCancellationResult(
                ok=False,
                status=WorkflowCancellationStatus.REJECTED,
                run_id=workflow_run_id,
                rejection_reason=WorkflowCancellationRejectionReason.INTERNAL_ERROR,
                safe_message="Workflow cancellation eligibility is unavailable.",
            )
        if not eligibility.eligible:
            status = (
                WorkflowCancellationStatus.ALREADY_CANCELLED
                if eligibility.reason == WorkflowCancellationRejectionReason.ALREADY_CANCELLED
                else WorkflowCancellationStatus.COMPLETED
                if eligibility.reason == WorkflowCancellationRejectionReason.ALREADY_COMPLETED
                else WorkflowCancellationStatus.REJECTED
            )
            return WorkflowCancellationResult(
                ok=False,
                status=status,
                run_id=workflow_run_id,
                rejection_reason=eligibility.reason,
                safe_message=eligibility.safe_message,
            )

        policy = self.policy_boundary.evaluate(
            PolicyRequest(
                source=AppCommandSource.DESKTOP_UI.value,
                command_id="workflow.cancel",
                action_id="workflow.cancel",
                intent_kind="workflow_control",
                risk="confirmation_required",
                required_capabilities=(PolicyCapability.FILE_READ.value,),
                confirmation_present=True,
                metadata={
                    "normalized_text": "workflow cancel",
                    "workflow_id": DOCUMENT_REVIEW_WORKFLOW_ID,
                    "workflow_run_id": workflow_run_id,
                },
            )
        )
        if policy.decision == PolicyDecisionType.DENY:
            return WorkflowCancellationResult(
                ok=False,
                status=WorkflowCancellationStatus.REJECTED,
                run_id=workflow_run_id,
                rejection_reason=WorkflowCancellationRejectionReason.POLICY_DENIED,
                safe_message=policy.user_message or "Workflow cancellation was denied by policy.",
            )

        try:
            result = self.document_review_runner.cancel_workflow_run(
                workflow_run_id,
                reason="workflow_cancelled_by_user",
            )
            return result
        except Exception:
            return WorkflowCancellationResult(
                ok=False,
                status=WorkflowCancellationStatus.FAILED,
                run_id=workflow_run_id,
                rejection_reason=WorkflowCancellationRejectionReason.INTERNAL_ERROR,
                safe_message="Workflow cancellation failed safely.",
            )

    @classmethod
    def _bounded_history_limit(cls, limit: int | None) -> int:
        if limit is None:
            return cls.DEFAULT_EXECUTION_HISTORY_LIMIT
        try:
            value = int(limit)
        except (TypeError, ValueError):
            return cls.DEFAULT_EXECUTION_HISTORY_LIMIT
        if value < 1:
            return 1
        return min(value, cls.MAX_EXECUTION_HISTORY_LIMIT)

    @classmethod
    def _bounded_workflow_history_limit(cls, limit: int | None) -> int:
        if limit is None:
            return cls.DEFAULT_WORKFLOW_HISTORY_LIMIT
        try:
            value = int(limit)
        except (TypeError, ValueError):
            return cls.DEFAULT_WORKFLOW_HISTORY_LIMIT
        if value < 1:
            return 1
        return min(value, cls.MAX_WORKFLOW_HISTORY_LIMIT)

    @classmethod
    def _history_entry_from_operation(
        cls,
        operation: ExecutionOperation,
    ) -> AppExecutionHistoryEntry:
        metadata = cls._safe_history_metadata(getattr(operation, "metadata", None))
        status = safe_history_text(getattr(getattr(operation, "status", None), "value", None))
        if not status:
            status = safe_history_text(getattr(operation, "status", "unknown"))
        safe_error = safe_history_text(getattr(operation, "safe_error_code", None), max_length=120)
        user_message = safe_history_text(
            getattr(operation, "safe_result_summary", None),
            max_length=220,
        )
        command_id = cls._optional_history_text(getattr(operation, "command_id", None), 100)
        action_id = cls._optional_history_text(getattr(operation, "action_id", None), 100)
        operation_type = command_id or action_id or "operation"
        return AppExecutionHistoryEntry(
            entry_id=safe_history_text(getattr(operation, "operation_id", None), max_length=80)
            or "unknown",
            timestamp=safe_history_text(getattr(operation, "created_at", None), max_length=80)
            or "unknown",
            updated_at=safe_history_text(getattr(operation, "updated_at", None), max_length=80)
            or "unknown",
            source=safe_history_text(getattr(operation, "source", None), max_length=80)
            or "unknown",
            command_id=command_id,
            action_id=action_id,
            operation_type=operation_type,
            status=status or "unknown",
            succeeded=cls._history_success(status),
            preview=cls._history_preview_flag(metadata),
            awaiting_confirmation=status == "awaiting_confirmation",
            cancellable=bool(getattr(operation, "cancellable", False)),
            duplicate_suppressed=bool(getattr(operation, "duplicate_suppressed", False)),
            request_summary=cls._history_request_summary(metadata, command_id, action_id),
            user_message=user_message or None,
            safe_error_summary=safe_error or None,
            metadata=metadata,
        )

    @staticmethod
    def _optional_history_text(value, max_length: int) -> str | None:
        text = safe_history_text(value, max_length=max_length)
        return text or None

    @staticmethod
    def _history_success(status: str) -> bool | None:
        if status == "succeeded":
            return True
        if status in {"failed", "denied", "cancelled", "duplicate_suppressed"}:
            return False
        return None

    @staticmethod
    def _safe_history_metadata(metadata) -> tuple[tuple[str, str], ...]:
        if not metadata:
            return ()
        safe_items: list[tuple[str, str]] = []
        try:
            items = metadata.items()
        except AttributeError:
            return ()
        blocked_keys = {
            "policy_decision",
            "request_fingerprint",
            "idempotency_key",
            "exception",
            "traceback",
            "raw_error",
            "raw_audio",
            "document_contents",
            "file_contents",
            "provider_response",
            "provider_client",
            "credentials",
            "token",
            "api_key",
            "authorization",
        }
        for key, value in items:
            raw_key = str(key or "").strip().lower()
            if raw_key in blocked_keys:
                continue
            safe_key = safe_history_text(key, max_length=64)
            if not safe_key:
                continue
            safe_value = safe_history_text(value, max_length=140)
            if safe_value:
                safe_items.append((safe_key, safe_value))
        return tuple(safe_items)

    @staticmethod
    def _history_preview_flag(metadata: tuple[tuple[str, str], ...]) -> bool:
        values = {key.lower(): value.lower() for key, value in metadata}
        return values.get("preview") == "yes" or values.get("executed") == "no"

    @staticmethod
    def _history_request_summary(
        metadata: tuple[tuple[str, str], ...],
        command_id: str | None,
        action_id: str | None,
    ) -> str:
        values = {key.lower(): value for key, value in metadata}
        return (
            values.get("input_preview")
            or values.get("summary")
            or command_id
            or action_id
            or "No request summary available."
        )

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

    def remember_user_fact(self, key, value) -> MemoryOperationResult:
        return self.memory_manager.remember_user_fact(
            key,
            value,
            language_code=self.language_manager.runtime_locale(),
        )

    def recall_user_fact(self, key) -> MemoryOperationResult:
        return self.memory_manager.recall_user_fact(key)

    def list_user_memories(self) -> MemoryOperationResult:
        return self.memory_manager.list_user_facts()

    def forget_user_fact(self, key) -> MemoryOperationResult:
        return self.memory_manager.forget_user_fact(key)

    def _build_planner_registry(self) -> PlannerCapabilityRegistry:
        registry = PlannerCapabilityRegistry.empty()

        def descriptor(
            capability_id: str,
            ru: str,
            en: str,
            category: str,
            risk: str,
            side_effect: PlanSideEffect,
            requires_confirmation: bool,
            schema: dict[str, object] | None = None,
            description: str = "",
        ) -> PlanCapabilityDescriptor:
            return PlanCapabilityDescriptor(
                capability_id=capability_id,
                display_name_ru=ru,
                display_name_en=en,
                category=category,
                risk_level=risk,
                side_effect=side_effect,
                requires_confirmation=requires_confirmation,
                argument_schema=schema or {},
                safe_description=description or capability_id,
            )

        def policy(command_id: str, risk: str, capabilities: tuple[str, ...], normalized: str, confirmation_present: bool):
            return PolicyRequest(
                source="planner",
                command_id=command_id,
                action_id=command_id,
                intent_kind="local_command",
                risk=risk,
                required_capabilities=capabilities,
                confirmation_present=confirmation_present,
                metadata={"normalized_text": normalized},
            )

        def app_status(_args):
            result = self.command_processor.process("статус системы")
            return PlannerCapabilityCallResult(str(result.get("response", result)))

        def startup_profile(_args):
            return PlannerCapabilityCallResult(self.startup_profile_text_ru())

        def language_get(_args):
            return PlannerCapabilityCallResult(self.get_language_preference().message)

        def language_set(args):
            return PlannerCapabilityCallResult(self.set_language_preference(str(args.get("language_code", ""))).message)

        def memory_remember(args):
            result = self.remember_user_fact(args.get("key"), args.get("value"))
            return PlannerCapabilityCallResult(self._memory_response_text(result))

        def memory_recall(args):
            result = self.recall_user_fact(args.get("key"))
            return PlannerCapabilityCallResult(self._memory_response_text(result))

        def memory_list(_args):
            result = self.list_user_memories()
            return PlannerCapabilityCallResult(self._memory_response_text(result))

        def memory_forget(args):
            result = self.forget_user_fact(args.get("key"))
            return PlannerCapabilityCallResult(self._memory_response_text(result))

        def memory_forget_all(_args):
            result = self.memory_manager.forget_all_user_facts()
            return PlannerCapabilityCallResult(self._memory_response_text(result))

        registrations = (
            PlanCapability(
                descriptor("system.status", "Статус системы", "System status", "system", "read_only", PlanSideEffect.READ_ONLY, False, {}, "Read local system status through AppService."),
                app_status,
                lambda args, confirmed: policy("system.status", "read_only", (PolicyCapability.READ_SYSTEM_STATE.value,), "статус системы", True),
            ),
            PlanCapability(
                descriptor("startup.profile", "Профиль запуска", "Startup profile", "app", "read_only", PlanSideEffect.READ_ONLY, False),
                startup_profile,
                lambda args, confirmed: policy("startup.profile", "read_only", (PolicyCapability.READ_SYSTEM_STATE.value,), "startup profile", True),
            ),
            PlanCapability(
                descriptor("language.get", "Текущий язык", "Current language", "profile", "read_only", PlanSideEffect.READ_ONLY, False),
                language_get,
                lambda args, confirmed: policy("language.get", "read_only", (PolicyCapability.READ_SYSTEM_STATE.value,), "current language", True),
            ),
            PlanCapability(
                descriptor("language.set", "Изменить язык", "Set language", "profile", "local_write", PlanSideEffect.BOUNDED_LOCAL_STATE, False, {"language_code": "ru-RU|en-US"}),
                language_set,
                lambda args, confirmed: policy("language.set", "local_write", (PolicyCapability.FILE_WRITE.value,), "set language", True),
            ),
            PlanCapability(
                descriptor("memory.remember", "Запомнить факт", "Remember fact", "memory", "local_write", PlanSideEffect.BOUNDED_LOCAL_STATE, False, {"key": "string", "value": "string"}),
                memory_remember,
                lambda args, confirmed: policy("memory.remember", "local_write", (PolicyCapability.FILE_WRITE.value,), "memory remember", True),
            ),
            PlanCapability(
                descriptor("memory.recall", "Показать память", "Recall memory", "memory", "read_only", PlanSideEffect.READ_ONLY, False, {"key": "string"}),
                memory_recall,
                lambda args, confirmed: policy("memory.recall", "read_only", (PolicyCapability.READ_SYSTEM_STATE.value,), "memory recall", True),
            ),
            PlanCapability(
                descriptor("memory.list", "Список памяти", "List memory", "memory", "read_only", PlanSideEffect.READ_ONLY, False),
                memory_list,
                lambda args, confirmed: policy("memory.list", "read_only", (PolicyCapability.READ_SYSTEM_STATE.value,), "memory list", True),
            ),
            PlanCapability(
                descriptor("memory.forget", "Забыть факт", "Forget fact", "memory", "local_write", PlanSideEffect.BOUNDED_LOCAL_STATE, False, {"key": "string"}),
                memory_forget,
                lambda args, confirmed: policy("memory.forget", "local_write", (PolicyCapability.FILE_WRITE.value,), "memory forget", True),
            ),
            PlanCapability(
                descriptor("memory.forget_all", "Удалить всю память", "Forget all memory", "memory", "confirmation_required", PlanSideEffect.BOUNDED_LOCAL_STATE, True),
                memory_forget_all,
                lambda args, confirmed: policy("memory.forget_all", "confirmation_required", (PolicyCapability.FILE_WRITE.value,), "забудь все что ты помнишь обо мне", confirmed),
            ),
        )
        for capability in registrations:
            registry = registry.register(capability)
        return registry

    def request_forget_all_memories(self) -> MemoryOperationResult:
        operation_id = "memory-forget-all-" + uuid4().hex
        self._pending_memory_forget_all = PendingMemoryForgetAllConfirmation(
            operation_id=operation_id,
        )
        return MemoryOperationResult(
            ok=True,
            action="forget_all.request",
            memory_id=None,
            key=None,
            value=None,
            changed=False,
            persisted=False,
            found=False,
            safe_message=self._language_text(
                "Удалить все явные пользовательские воспоминания? Ответьте: да или отмена.",
                "Delete all explicit user memories? Reply: yes or cancel.",
            ),
            awaiting_confirmation=True,
            operation_id=operation_id,
        )

    def confirm_forget_all_memories(self) -> MemoryOperationResult:
        pending = self._pending_memory_forget_all
        if pending is None:
            return MemoryOperationResult(
                ok=True,
                action="forget_all.confirm",
                memory_id=None,
                key=None,
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message=self._language_text(
                    "Нет ожидающего подтверждения удаления памяти.",
                    "There is no pending memory deletion confirmation.",
                ),
                operation_id=None,
            )
        if pending.completed:
            return MemoryOperationResult(
                ok=True,
                action="forget_all.confirm",
                memory_id=None,
                key=None,
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message=self._language_text(
                    "Эта операция удаления памяти уже завершена.",
                    "This memory deletion operation is already complete.",
                ),
                operation_id=pending.operation_id,
            )
        result = self.memory_manager.forget_all_user_facts()
        self._pending_memory_forget_all = PendingMemoryForgetAllConfirmation(
            operation_id=pending.operation_id,
            active=False,
            completed=True,
        )
        return MemoryOperationResult(
            ok=result.ok,
            action=result.action,
            memory_id=None,
            key=None,
            value=None,
            changed=result.changed,
            persisted=result.persisted,
            found=result.found,
            safe_message=self._language_text(
                result.safe_message,
                "All explicit user memories were deleted." if result.changed else "There were no explicit user memories to delete.",
            ),
            operation_id=pending.operation_id,
        )

    def get_conversation_context_snapshot(self):
        return self.conversation_context.snapshot()

    def _consume_pending_memory_forget_all(
        self,
        input_text: str,
        source: AppCommandSource,
    ) -> AppCommandResult | None:
        pending = self._pending_memory_forget_all
        if pending is None or not pending.active:
            return None
        normalized = self._normalize_memory_text(input_text)
        if normalized in {"да", "подтверждаю", "подтвердить", "yes"}:
            operation = self.confirm_forget_all_memories()
            return self._memory_app_result(
                input_text,
                source,
                operation,
                side_effecting=operation.changed,
            )
        if normalized in {"нет", "отмена", "отмени", "cancel", "no"}:
            self._pending_memory_forget_all = None
            operation = MemoryOperationResult(
                ok=True,
                action="forget_all.cancel",
                memory_id=None,
                key=None,
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message=self._language_text(
                    "Удаление памяти отменено. Записи сохранены.",
                    "Memory deletion cancelled. Memories were preserved.",
                ),
                operation_id=pending.operation_id,
            )
            return self._memory_app_result(input_text, source, operation)
        operation = MemoryOperationResult(
            ok=True,
            action="forget_all.awaiting_confirmation",
            memory_id=None,
            key=None,
            value=None,
            changed=False,
            persisted=False,
            found=False,
            safe_message=self._language_text(
                "Нужно подтверждение: да или отмена.",
                "Confirmation required: yes or cancel.",
            ),
            awaiting_confirmation=True,
            operation_id=pending.operation_id,
        )
        return self._memory_app_result(input_text, source, operation)

    def _handle_memory_command(
        self,
        input_text: str,
        source: AppCommandSource,
    ) -> AppCommandResult | None:
        parsed = self._parse_memory_command(input_text)
        if parsed is None:
            return None
        action, key, value = parsed
        if action == "repeat_last_memory":
            turn = self.conversation_context.last_read_only_memory_turn()
            if turn is None:
                operation = MemoryOperationResult(
                    ok=True,
                    action="repeat",
                    memory_id=None,
                    key=None,
                    value=None,
                    changed=False,
                    persisted=False,
                    found=False,
                    safe_message=self._language_text(
                        "Нет безопасного ответа из памяти, который можно повторить.",
                        "There is no safe memory answer to repeat.",
                    ),
                )
                return self._memory_app_result(input_text, source, operation)
            result = AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=turn.assistant_summary,
                source=source,
                registry_match_id="memory.repeat",
                category="memory",
                risk_level="read_only",
                executed=False,
                requires_confirmation=False,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
            )
            self.conversation_context.add_turn(
                user_text=input_text,
                assistant_text=result.output_text,
                intent_id="memory.recall",
                topic_key=turn.topic_key,
                read_only=True,
                side_effecting=False,
                outcome="repeated",
            )
            return result
        if action == "vague":
            operation = MemoryOperationResult(
                ok=True,
                action="clarify",
                memory_id=None,
                key=key,
                value=None,
                changed=False,
                persisted=False,
                found=False,
                safe_message=self._language_text(
                    "Уточните конкретный ключ и значение памяти. Я не буду угадывать.",
                    "Please specify the exact memory key and value. I will not guess.",
                ),
                safe_error_code="memory_command_needs_clarification",
            )
            return self._memory_app_result(input_text, source, operation)
        if action == "remember":
            operation = self.remember_user_fact(key, value)
            return self._memory_app_result(
                input_text,
                source,
                operation,
                side_effecting=operation.changed,
            )
        if action == "recall":
            operation = self.recall_user_fact(key)
            return self._memory_app_result(input_text, source, operation)
        if action == "list":
            operation = self.list_user_memories()
            return self._memory_app_result(input_text, source, operation)
        if action == "forget":
            operation = self.forget_user_fact(key)
            return self._memory_app_result(
                input_text,
                source,
                operation,
                side_effecting=operation.changed,
            )
        if action == "forget_all":
            operation = self.request_forget_all_memories()
            return self._memory_app_result(input_text, source, operation)
        return None

    def _memory_app_result(
        self,
        input_text: str,
        source: AppCommandSource,
        operation: MemoryOperationResult,
        *,
        side_effecting: bool = False,
    ) -> AppCommandResult:
        output_text = self._memory_response_text(operation)
        if operation.action == "recall" or operation.action == "repeat":
            intent_id = "memory.recall"
        elif operation.action == "list":
            intent_id = "memory.list"
        else:
            intent_id = f"memory.{operation.action}"
        topic_key = (
            LocalMemoryManager.normalize_user_fact_key(operation.key)
            if operation.key
            else None
        )
        self.conversation_context.add_turn(
            user_text=input_text,
            assistant_text=output_text,
            intent_id=intent_id,
            topic_key=topic_key,
            read_only=not side_effecting,
            side_effecting=side_effecting,
            outcome=operation.action,
        )
        return AppCommandResult(
            ok=operation.ok,
            input_text=input_text,
            output_text=output_text,
            source=source,
            registry_match_id=intent_id,
            category="memory",
            risk_level="local_write" if side_effecting else "read_only",
            executed=side_effecting,
            requires_confirmation=operation.awaiting_confirmation,
            network_may_be_used=False,
            response_executed_as_command=False,
            error=operation.safe_error_code,
            operation_id=operation.operation_id,
            operation_status="awaiting_confirmation" if operation.awaiting_confirmation else "succeeded",
            awaiting_confirmation=operation.awaiting_confirmation,
        )

    def _prepare_direct_memory_state_change(
        self,
        input_text: str,
        source: AppCommandSource,
    ) -> DirectStateChangePreparation | None:
        parsed = self._parse_memory_command(input_text)
        if parsed is None:
            return None
        action, _key, _value = parsed
        if action == "remember":
            return DirectStateChangePreparation(
                command_id="memory.remember",
                category="memory",
                safe_preview="memory.remember [REDACTED]",
                execute=lambda: self._handle_memory_command(input_text, source),
            )
        if action == "forget":
            return DirectStateChangePreparation(
                command_id="memory.forget",
                category="memory",
                safe_preview="memory.forget [REDACTED]",
                execute=lambda: self._handle_memory_command(input_text, source),
            )
        return None

    def _prepare_direct_language_state_change(
        self,
        input_text: str,
        source: AppCommandSource,
    ) -> DirectStateChangePreparation | None:
        normalized = self.command_registry.normalize_alias(input_text)
        reset_commands = {
            "\u0441\u0431\u0440\u043e\u0441\u0438\u0442\u044c \u044f\u0437\u044b\u043a",
            "reset language",
        }
        set_prefixes = (
            "\u044f\u0437\u044b\u043a ",
            "\u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c ",
            "\u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u044f\u0437\u044b\u043a ",
            "\u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a",
            "\u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a",
            "\u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u044f\u0437\u044b\u043a \u043d\u0430 ",
            "language ",
            "set language to ",
        )
        if normalized in reset_commands:
            return DirectStateChangePreparation(
                command_id="profile.language.reset",
                category="profile",
                safe_preview="profile.language.reset",
                execute=lambda: self._handle_language_preference_command(input_text, source),
            )
        if self._extract_language_setting_text(normalized, set_prefixes) is not None:
            return DirectStateChangePreparation(
                command_id="profile.language.set",
                category="profile",
                safe_preview="profile.language.set",
                execute=lambda: self._handle_language_preference_command(input_text, source),
            )
        return None

    def _memory_response_text(self, operation: MemoryOperationResult) -> str:
        english = self.language_manager.get_preference().language_code == "en-US"
        if operation.action == "remember":
            if not operation.ok:
                return operation.safe_message
            if operation.previous_value is not None:
                return (
                    f"Updated remembered fact: {operation.key} = {operation.value}."
                    if english
                    else f"Обновил запомненный факт: {operation.key} = {operation.value}."
                )
            return (
                f"Remembered: {operation.key} = {operation.value}."
                if english
                else f"Запомнил: {operation.key} = {operation.value}."
            )
        if operation.action == "recall":
            if operation.found:
                return (
                    f"I remember: {operation.key} = {operation.value}."
                    if english
                    else f"Я помню: {operation.key} — {operation.value}."
                )
            return (
                f"I do not remember {operation.key}."
                if english
                else f"Я не помню: {operation.key}."
            )
        if operation.action == "list":
            if not operation.entries:
                return (
                    "I do not have explicit user memories yet."
                    if english
                    else "В явной пользовательской памяти пока нет записей."
                )
            lines = ["Explicit user memories:" if english else "Явная пользовательская память:"]
            for entry in operation.entries:
                lines.append(f"- {entry.display_key}: {entry.value}")
            return "\n".join(lines)
        if operation.action == "forget":
            if operation.changed:
                return (
                    f"Forgot: {operation.key}."
                    if english
                    else f"Забыл: {operation.key}."
                )
            return (
                f"No memory existed for: {operation.key}."
                if english
                else f"В памяти не было записи: {operation.key}."
            )
        if operation.action.startswith("forget_all"):
            return operation.safe_message
        if operation.action == "clarify":
            return operation.safe_message
        return operation.safe_message

    def _parse_memory_command(self, text: str) -> tuple[str, str | None, str | None] | None:
        raw = str(text or "").strip()
        normalized = self._normalize_memory_text(raw)
        if not normalized:
            return None
        vague = {
            "запомни это",
            "помни",
            "забудь это",
            "удали память",
            "remember this",
            "forget it",
        }
        if normalized in vague:
            return ("vague", None, None)
        if normalized in {"покажи еще раз", "покажи ещё раз", "show again", "repeat that"}:
            return ("repeat_last_memory", None, None)
        if normalized in {
            "сделай это еще раз",
            "сделай это ещё раз",
            "выполни это еще раз",
            "выполни это ещё раз",
            "do it again",
        }:
            return ("vague", None, None)
        if normalized in {
            "забудь все что ты помнишь обо мне",
            "забудь все, что ты помнишь обо мне",
            "forget everything you remember about me",
        }:
            return ("forget_all", None, None)
        if normalized in {
            "покажи что ты помнишь обо мне",
            "покажи, что ты помнишь обо мне",
            "what do you remember about me",
            "show what you remember about me",
        }:
            return ("list", None, None)
        remember = self._parse_remember_command(raw, normalized)
        if remember is not None:
            return remember
        forget = self._parse_forget_command(raw, normalized)
        if forget is not None:
            return forget
        recall = self._parse_recall_command(raw, normalized)
        if recall is not None:
            return recall
        return None

    def _parse_remember_command(self, raw: str, normalized: str):
        match = re.match(
            r"(?is)^\s*(?:запомни(?:\s*,?\s*что|:)?|сохрани\s+в\s+памяти(?:\s*,?\s*что)?|remember(?:\s+that|:)?)\s+(.+?)\s*$",
            raw,
        )
        if match is None:
            return None
        raw_body = match.group(1).strip()
        key_value = self._split_memory_key_value(raw_body)
        if key_value is None:
            return ("vague", None, None)
        key, value = key_value
        return ("remember", key, value)

    def _parse_forget_command(self, raw: str, normalized: str):
        prefixes = (
            "забудь ",
            "удали из памяти ",
            "forget ",
            "delete ",
        )
        for prefix in prefixes:
            if normalized.startswith(prefix):
                key = raw[len(prefix) :].strip()
                if normalized.startswith("delete ") and self._normalize_memory_text(key).endswith(" from memory"):
                    key = key[: -len(" from memory")].strip()
                if self._normalize_memory_text(key) in {"это", "it", "memory", "память", ""}:
                    return ("vague", key, None)
                return ("forget", key, None)
        return None

    def _parse_recall_command(self, raw: str, normalized: str):
        prefixes = (
            "какой мой ",
            "какой моё ",
            "какой мое ",
            "какое моё ",
            "какое мое ",
            "какая моя ",
            "что ты помнишь о ",
            "что ты помнишь об ",
            "что ты помнишь про ",
            "что ты запомнил про ",
            "what is my ",
            "what do you remember about ",
        )
        for prefix in prefixes:
            if normalized.startswith(prefix):
                key = raw[len(prefix) :].strip()
                return ("recall", key, None)
        return None

    def _split_memory_key_value(self, body: str) -> tuple[str, str] | None:
        for separator in (" — ", " – ", " - ", "=", ":"):
            if separator in body:
                left, right = body.split(separator, 1)
                return left.strip(), right.strip()
        match = re.match(r"(?is)^(.+?)\s+is\s+(.+)$", body.strip())
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None

    @staticmethod
    def _normalize_memory_text(text: str) -> str:
        return normalize_control_text(text)

    def _handle_language_preference_command(
        self,
        input_text: str,
        source: AppCommandSource,
    ) -> AppCommandResult | None:
        normalized = self.command_registry.normalize_alias(input_text)
        status_commands = {
            "какой язык",
            "текущий язык",
            "покажи язык",
            "current language",
            "show language",
        }
        reset_commands = {"сбросить язык", "reset language"}
        vague_commands = {"поменяй язык", "другой язык", "translate everything"}
        set_prefixes = (
            "язык ",
            "установить ",
            "установить язык ",
            "установить русский язык",
            "установить английский язык",
            "переключить язык на ",
            "language ",
            "set language to ",
        )

        if normalized in status_commands:
            contract = self.get_language_preference()
            return self._language_result(
                input_text,
                source,
                contract.message,
                changed=False,
                command_id="profile.language.status",
            )

        if normalized in reset_commands:
            contract = self.reset_language_preference()
            return self._language_result(
                input_text,
                source,
                contract.message,
                changed=contract.changed,
                command_id="profile.language.reset",
            )

        if normalized in vague_commands:
            options = (
                AppClarificationOption(
                    option_id="language_ru",
                    label_ru="Русский / Russian",
                    command_text="язык русский",
                    command_id="profile.language.set",
                ),
                AppClarificationOption(
                    option_id="language_en",
                    label_ru="Английский / English",
                    command_text="язык английский",
                    command_id="profile.language.set",
                ),
            )
            self._pending_clarification = ClarificationState(
                question_ru=self._language_text(
                    "Выберите язык: русский или английский.",
                    "Choose a language: Russian or English.",
                ),
                options=options,
                original_text=input_text,
                source=source.value,
            )
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=self._language_clarification_text(
                    self._pending_clarification.question_ru,
                    options,
                ),
                source=source,
                registry_match_id="profile.language.clarify",
                category="clarification",
                risk_level="read_only",
                executed=False,
                requires_confirmation=False,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
                requires_clarification=True,
                clarification_question=self._pending_clarification.question_ru,
                clarification_options=options,
            )

        language_text = self._extract_language_setting_text(normalized, set_prefixes)
        if language_text is None:
            return None
        contract = self.set_language_preference(language_text)
        return self._language_result(
            input_text,
            source,
            contract.message,
            changed=contract.changed,
            command_id="profile.language.set",
            ok=True,
        )

    def _language_result(
        self,
        input_text: str,
        source: AppCommandSource,
        output_text: str,
        *,
        changed: bool,
        command_id: str,
        ok: bool = True,
    ) -> AppCommandResult:
        return AppCommandResult(
            ok=ok,
            input_text=input_text,
            output_text=output_text,
            source=source,
            registry_match_id=command_id,
            category="profile",
            risk_level="local_write" if changed else "read_only",
            executed=changed,
            requires_confirmation=False,
            network_may_be_used=False,
            response_executed_as_command=False,
            error=None,
        )

    @staticmethod
    def _extract_language_setting_text(normalized: str, prefixes: tuple[str, ...]) -> str | None:
        exact = {
            "язык русский": "русский",
            "установить русский язык": "русский",
            "переключить язык на русский": "русский",
            "язык английский": "английский",
            "установить английский язык": "английский",
            "переключить язык на английский": "английский",
            "language russian": "russian",
            "set language to russian": "russian",
            "language english": "english",
            "set language to english": "english",
        }
        if normalized in exact:
            return exact[normalized]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                value = normalized[len(prefix) :].strip()
                if value:
                    return value
        return None

    def _language_text(self, ru_text: str, en_text: str) -> str:
        return (
            en_text
            if self.language_manager.get_preference().language_code == "en-US"
            else ru_text
        )

    def _language_clarification_text(
        self,
        question: str | None,
        options: tuple[AppClarificationOption, ...],
    ) -> str:
        if self.language_manager.get_preference().language_code == "en-US":
            lines = [
                "Clarification required:",
                question or "Choose an option.",
                "",
                "Options:",
            ]
        else:
            lines = [
                "Требуется уточнение:",
                question or "Уточните вариант.",
                "",
                "Варианты:",
            ]
        lines.extend(f"- {option.label_ru}" for option in options)
        return "\n".join(lines)

    def _propagate_language_preference(self) -> None:
        if hasattr(self.command_processor, "language_manager"):
            self.command_processor.language_manager = self.language_manager
        recognizer = self.one_shot_voice_recognition
        if recognizer is not None and hasattr(recognizer, "preferred_language_code"):
            recognizer.preferred_language_code = self.language_manager.runtime_locale()

    def _handle_startup_profile_command(
        self,
        input_text: str,
        source: AppCommandSource,
    ) -> AppCommandResult | None:
        normalized = self.command_registry.normalize_alias(input_text)
        if normalized not in {
            "статус запуска",
            "профиль запуска",
            "startup status",
            "startup profile",
        }:
            return None
        return AppCommandResult(
            ok=True,
            input_text=input_text,
            output_text=self.startup_profile_text_ru(),
            source=source,
            registry_match_id="app.startup_profile",
            category="app",
            risk_level="read_only",
            executed=False,
            requires_confirmation=False,
            network_may_be_used=False,
            response_executed_as_command=False,
            error=None,
        )

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

    @staticmethod
    def _source_value(source: AppCommandSource | str) -> str:
        return source.value if isinstance(source, AppCommandSource) else str(source or "unknown")

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
        return self._provider_runtime_component.get()

    def _get_one_shot_voice_recognition(self):
        if self.one_shot_voice_recognition is not None:
            return self.one_shot_voice_recognition
        self.one_shot_voice_recognition = self._one_shot_voice_component.get()
        return self.one_shot_voice_recognition

    def _default_provider_runtime_factory(self):
        runtime = getattr(self.command_processor, "secure_provider_runtime", None)
        if runtime is not None:
            if isinstance(runtime, LazyComponent):
                return runtime.get()
            return runtime
        return SecureProviderRuntime()

    def _default_one_shot_voice_recognition_factory(self):
        recognizer = getattr(self.command_processor, "one_shot_vosk_real_recognition", None)
        if recognizer is not None:
            if isinstance(recognizer, LazyComponent):
                return recognizer.get()
            return recognizer
        recognizer_factory = getattr(
            self.command_processor,
            "_get_one_shot_vosk_real_recognition",
            None,
        )
        if callable(recognizer_factory):
            return recognizer_factory()
        from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognition

        return OneShotVoskRealRecognition()

    def _lazy_component_snapshots(self):
        snapshots = [
            self._provider_runtime_component.snapshot(),
            self._one_shot_voice_component.snapshot(),
        ]
        for name in (
            "secure_provider_runtime",
            "ai_provider_router",
            "openai_request_gate",
            "gemini_request_gate",
            "groq_request_gate",
            "gigachat_request_gate",
            "ollama_request_gate",
            "voice_output_manager",
            "one_shot_vosk_real_recognition",
        ):
            component = getattr(self.command_processor, name, None)
            if isinstance(component, LazyComponent):
                snapshots.append(component.snapshot())
        return tuple(snapshots)

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
            safe_reasons = [
                self._safe_one_shot_voice_reason(reason)
                for reason in reasons
                if str(reason or "").strip()
            ]
            return safe_contract_text("; ".join(safe_reasons) or fallback)
        return fallback

    @classmethod
    def _safe_one_shot_voice_exception_message(cls, exc) -> str:
        text = str(exc or "").strip()
        if _looks_like_raw_voice_error(text):
            return SAFE_ONE_SHOT_MICROPHONE_FAILURE_MESSAGE
        return SAFE_ONE_SHOT_VOICE_FAILURE_MESSAGE

    @staticmethod
    def _safe_one_shot_voice_reason(reason) -> str:
        text = str(reason or "").strip()
        if not text:
            return ""
        if _looks_like_raw_voice_error(text):
            return SAFE_ONE_SHOT_MICROPHONE_FAILURE_MESSAGE
        return text

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
