"""Safe app-facing service layer for JARVIS.

The service is a boundary for future UI code. It can inspect command metadata
and delegate execution to CommandProcessor, but it does not execute commands,
call providers, route actions, read arbitrary files, or persist prompts.
"""

from dataclasses import dataclass
from enum import Enum
import re

from app.app_contracts import (
    APP_CONTRACT_SCHEMA_NAME,
    APP_CONTRACT_VERSION,
    AppCommandCard,
    AppContractManifest,
    AppContractStatus,
    AppExecutionContract,
    AppPreviewContract,
    AppStatusCard,
    safe_contract_text,
)
from core.command_registry import (
    CommandCategory,
    CommandMetadata,
    CommandRegistry,
    DEFAULT_COMMAND_REGISTRY,
)
from voice.audio_lifecycle import AudioLifecycleController, AudioLifecycleStatus


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

    def __init__(self, command_processor=None, command_registry=None):
        self.command_registry = command_registry or DEFAULT_COMMAND_REGISTRY
        if command_processor is None:
            from core.command_processor import CommandProcessor

            command_processor = CommandProcessor(command_registry=self.command_registry)
        self.command_processor = command_processor
        self.audio_lifecycle_controller = self._build_audio_lifecycle_controller()

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
            network_default=False,
            dry_run_default=True,
            privacy_boundary_active=True,
            fallback_explicit_only=True,
            consensus_explicit_only=True,
            voice_safety_active=True,
        )

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
    ) -> AppExecutionContract:
        result = self.execute_command(text, source)
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
        )

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
    ) -> AppCommandResult:
        if not isinstance(source, AppCommandSource):
            source = AppCommandSource.UNKNOWN
        input_text = str(text or "").strip()
        preview = self.preview_command(input_text)
        try:
            processor_result = self.command_processor.process(input_text)
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
            )
        except Exception as exc:
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
            )

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
        for command in self.command_registry.commands:
            for alias in command.aliases:
                normalized_alias = self.command_registry.normalize_alias(alias)
                if "<text>" not in normalized_alias:
                    continue
                prefix = normalized_alias.split("<text>", 1)[0].strip()
                if prefix and normalized_text.startswith(prefix):
                    return command
        return None

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
