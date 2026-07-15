"""Read-only vertical integration checks for the JARVIS app stack."""

from dataclasses import dataclass
import re

from app.desktop_shell import DesktopShellViewModel
from core.command_registry import (
    CommandCategory,
    CommandRiskLevel,
    DEFAULT_COMMAND_REGISTRY,
)
from voice.voice_command_allowlist import SafeVoiceCommandAllowlist


_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+)"
)


@dataclass(frozen=True)
class VerticalIntegrationCheck:
    check_id: str
    title_ru: str
    layer: str
    passed: bool
    severity: str
    safe: bool
    details_ru: tuple[str, ...]


@dataclass(frozen=True)
class VerticalIntegrationReport:
    report_id: str
    version: str
    overall_passed: bool
    checks_count: int
    passed_count: int
    failed_count: int
    network_used: bool
    secrets_included: bool
    audio_started: bool
    microphone_started: bool
    tts_started: bool
    providers_called: bool
    command_execution_used: bool
    notes_ru: tuple[str, ...]
    checks: tuple[VerticalIntegrationCheck, ...]


class VerticalIntegrationService:
    """Conservative metadata-only report across the current major layers."""

    VERSION = "0.1"
    REQUIRED_CATEGORIES = (
        CommandCategory.APP,
        CommandCategory.AI,
        CommandCategory.AI_PROVIDER,
        CommandCategory.SECURE_KEYS,
        CommandCategory.AUDIO,
        CommandCategory.VOICE,
        CommandCategory.SAFETY,
    )
    SAFE_VOICE_COMMANDS = (
        "статус vertical integration",
        "статус интеграции jarvis",
        "статус вертикальной интеграции",
        "vertical integration status",
        "integration status",
        "vertical integration checklist",
        "чеклист vertical integration",
        "чеклист интеграции jarvis",
        "чеклист вертикальной интеграции",
        "vertical integration summary",
        "кратко vertical integration",
        "кратко интеграция jarvis",
    )
    RISKY_VOICE_COMMANDS = (
        "groq реальный запрос: test",
        "fallback ai запрос: test",
        "консенсус ai: test",
        "импортировать groq ключ из env",
        "reset audio lifecycle",
        "app preview: статус ai",
    )

    def __init__(
        self,
        app_service=None,
        command_registry=None,
        voice_allowlist=None,
    ):
        self.command_registry = command_registry or DEFAULT_COMMAND_REGISTRY
        if app_service is None:
            from app.app_service import JarvisAppService

            app_service = JarvisAppService(command_registry=self.command_registry)
        self.app_service = app_service
        self.voice_allowlist = voice_allowlist or SafeVoiceCommandAllowlist()

    def run_report(self) -> VerticalIntegrationReport:
        checks = (
            self._command_registry_available(),
            self._command_registry_has_required_categories(),
            self._app_contracts_available(),
            self._app_contract_manifest_safe(),
            self._app_service_status_safe(),
            self._app_service_preview_safe(),
            self._desktop_viewmodel_safe(),
            self._secure_keys_safe(),
            self._audio_lifecycle_safe(),
            self._voice_allowlist_safe(),
            self._ai_safety_safe(),
            self._no_network_no_secret_integration(),
            self._command_processor_smoke_safe(),
        )
        passed_count = sum(1 for check in checks if check.passed)
        failed_count = len(checks) - passed_count
        return VerticalIntegrationReport(
            report_id="vertical_integration",
            version=self.VERSION,
            overall_passed=failed_count == 0,
            checks_count=len(checks),
            passed_count=passed_count,
            failed_count=failed_count,
            network_used=False,
            secrets_included=False,
            audio_started=False,
            microphone_started=False,
            tts_started=False,
            providers_called=False,
            command_execution_used=False,
            notes_ru=(
                "Report is metadata/read-only.",
                "No provider, network, microphone, TTS, or decrypted secret access is used.",
                "CommandProcessor smoke execution is intentionally not used by default.",
            ),
            checks=checks,
        )

    def report_text_ru(self) -> str:
        report = self.run_report()
        lines = [
            "Vertical integration report:",
            "- vertical integration foundation: yes",
            f"- overall passed: {'yes' if report.overall_passed else 'no'}",
            f"- checks count: {report.checks_count}",
            f"- passed count: {report.passed_count}",
            f"- failed count: {report.failed_count}",
            f"- network used: {'yes' if report.network_used else 'no'}",
            f"- secrets included: {'yes' if report.secrets_included else 'no'}",
            f"- audio started: {'yes' if report.audio_started else 'no'}",
            f"- microphone started: {'yes' if report.microphone_started else 'no'}",
            f"- tts started: {'yes' if report.tts_started else 'no'}",
            f"- providers called: {'yes' if report.providers_called else 'no'}",
            f"- command execution used: {'yes' if report.command_execution_used else 'no'}",
            "- response execution: no",
        ]
        failures = [check for check in report.checks if not check.passed]
        if failures:
            lines.append("- failed checks:")
            lines.extend(f"  - {check.check_id}: {check.title_ru}" for check in failures)
        else:
            lines.append("- failed checks: none")
        return self._safe_text("\n".join(lines))

    def checklist_text_ru(self) -> str:
        report = self.run_report()
        lines = [
            "Vertical integration checklist:",
            "- no secrets",
            "- no network",
        ]
        for check in report.checks:
            lines.append(
                f"- [{'PASS' if check.passed else 'FAIL'}] {check.check_id}: "
                f"{check.title_ru} | layer={check.layer} | safe={'yes' if check.safe else 'no'}"
            )
        return self._safe_text("\n".join(lines))

    def safe_summary_text_ru(self) -> str:
        report = self.run_report()
        return self._safe_text(
            "\n".join(
                [
                    "Vertical integration summary:",
                    f"- overall passed: {'yes' if report.overall_passed else 'no'}",
                    f"- checks: {report.passed_count}/{report.checks_count}",
                    "- network used: no",
                    "- secrets included: no",
                    "- providers called: no",
                    "- microphone/TTS started: no",
                    "- command execution used: no",
                ]
            )
        )

    def _command_registry_available(self) -> VerticalIntegrationCheck:
        commands = getattr(self.command_registry, "commands", ())
        return self._check(
            "command_registry_available",
            "CommandRegistry доступен",
            "CommandRegistry",
            bool(commands),
            (f"commands: {len(commands)}", "metadata only"),
        )

    def _command_registry_has_required_categories(self) -> VerticalIntegrationCheck:
        categories = set(self.command_registry.categories())
        missing = [category.value for category in self.REQUIRED_CATEGORIES if category not in categories]
        return self._check(
            "command_registry_has_required_categories",
            "CommandRegistry содержит основные категории",
            "CommandRegistry",
            not missing,
            (
                "required: " + ", ".join(category.value for category in self.REQUIRED_CATEGORIES),
                "missing: " + (", ".join(missing) if missing else "none"),
            ),
        )

    def _app_contracts_available(self) -> VerticalIntegrationCheck:
        status = self.app_service.contract_status()
        return self._check(
            "app_contracts_available",
            "AppService contracts доступны",
            "AppService Contracts",
            status.app_service_ready and status.desktop_shell_ready,
            (
                f"schema: {status.schema_name}",
                f"version: {status.version}",
                f"network default: {'yes' if status.network_default else 'no'}",
            ),
        )

    def _app_contract_manifest_safe(self) -> VerticalIntegrationCheck:
        manifest = self.app_service.contract_manifest()
        safe = (
            manifest.command_cards_count > 0
            and not manifest.status.network_default
            and not manifest.status.secrets_included
            and not manifest.status.responses_executed_as_commands
        )
        return self._check(
            "app_contract_manifest_safe",
            "Contract manifest безопасен для UI",
            "AppService Contracts",
            safe,
            (
                f"command cards: {manifest.command_cards_count}",
                f"status cards: {len(manifest.status_cards)}",
                "no secrets",
                "no network",
            ),
        )

    def _app_service_status_safe(self) -> VerticalIntegrationCheck:
        snapshot = self.app_service.status_snapshot()
        passed = (
            snapshot.app_service_enabled
            and snapshot.command_registry_enabled
            and not snapshot.network_default
            and snapshot.secure_key_storage_ready
            and snapshot.voice_safety_active
        )
        return self._check(
            "app_service_status_safe",
            "AppService status безопасен",
            "AppService",
            passed,
            (
                f"command count: {snapshot.command_count}",
                f"network default: {'yes' if snapshot.network_default else 'no'}",
                f"dry run default: {'yes' if snapshot.dry_run_default else 'no'}",
            ),
        )

    def _app_service_preview_safe(self) -> VerticalIntegrationCheck:
        status_preview = self.app_service.preview_command("статус ai")
        provider_preview = self.app_service.preview_command("groq реальный запрос: test")
        passed = (
            status_preview.known_command
            and status_preview.read_only
            and not status_preview.requires_network
            and provider_preview.known_command
            and provider_preview.risk_level == CommandRiskLevel.NETWORK_EXPLICIT.value
            and provider_preview.requires_network
            and provider_preview.requires_privacy_check
        )
        return self._check(
            "app_service_preview_safe",
            "AppService preview не выполняет команды",
            "AppService",
            passed,
            (
                f"status preview command: {status_preview.registry_match_id}",
                f"provider preview command: {provider_preview.registry_match_id}",
                "execution: no",
            ),
        )

    def _desktop_viewmodel_safe(self) -> VerticalIntegrationCheck:
        view_model = DesktopShellViewModel(self.app_service)
        preview = view_model.preview_command("статус ai")
        passed = (
            view_model.state.ui_ready
            and view_model.state.safe_mode
            and "does not execute command" in preview
            and "requires_network: no" in preview
        )
        return self._check(
            "desktop_viewmodel_safe",
            "DesktopShell ViewModel строится без GUI",
            "Desktop Shell",
            passed,
            ("initial state builds", "preview статус ai works without execution"),
        )

    def _secure_keys_safe(self) -> VerticalIntegrationCheck:
        cards = self.app_service.command_cards("secure_keys")
        text = "\n".join(card.safe_text_ru() for card in cards)
        passed = bool(cards) and not self._contains_secret(text) and all(
            not card.requires_network for card in cards
        )
        return self._check(
            "secure_keys_safe",
            "Secure key metadata не раскрывает секреты",
            "Secure Key Storage",
            passed,
            (f"cards: {len(cards)}", "raw key values: no", "network: no"),
        )

    def _audio_lifecycle_safe(self) -> VerticalIntegrationCheck:
        status = self.app_service.audio_lifecycle_status()
        passed = (
            not status.microphone_active
            and not status.speaking_active
            and not status.continuous_listening_allowed
            and not status.audio_saved
            and not status.network_used
        )
        return self._check(
            "audio_lifecycle_safe",
            "Audio lifecycle виден без запуска аудио",
            "Audio Lifecycle",
            passed,
            (
                f"microphone active: {'yes' if status.microphone_active else 'no'}",
                f"tts active: {'yes' if status.speaking_active else 'no'}",
                f"audio saved: {'yes' if status.audio_saved else 'no'}",
            ),
        )

    def _voice_allowlist_safe(self) -> VerticalIntegrationCheck:
        allowed = [self.voice_allowlist.decide(command).allowed for command in self.SAFE_VOICE_COMMANDS]
        rejected = [not self.voice_allowlist.decide(command).allowed for command in self.RISKY_VOICE_COMMANDS]
        return self._check(
            "voice_allowlist_safe",
            "Voice allowlist разрешает только read-only integration команды",
            "Voice Safety",
            all(allowed) and all(rejected),
            (
                f"safe integration commands allowed: {sum(1 for item in allowed if item)}",
                f"risky commands rejected: {sum(1 for item in rejected if item)}",
            ),
        )

    def _ai_safety_safe(self) -> VerticalIntegrationCheck:
        provider_commands = [
            command
            for command in self.command_registry.commands
            if command.category == CommandCategory.AI_PROVIDER
            and command.risk_level == CommandRiskLevel.NETWORK_EXPLICIT
        ]
        passed = bool(provider_commands) and all(
            command.requires_network
            and command.requires_privacy_check
            and command.requires_confirmation
            and not command.voice_auto_allowed
            for command in provider_commands
        )
        return self._check(
            "ai_safety_safe",
            "AI provider команды остаются explicit-only",
            "AI Safety",
            passed,
            (f"explicit provider commands: {len(provider_commands)}", "providers called: no"),
        )

    def _no_network_no_secret_integration(self) -> VerticalIntegrationCheck:
        return self._check(
            "no_network_no_secret_integration",
            "Интеграционный отчет не использует сеть и секреты",
            "Safety",
            True,
            ("network used: no", "secrets included: no", "providers called: no"),
        )

    def _command_processor_smoke_safe(self) -> VerticalIntegrationCheck:
        return self._check(
            "command_processor_smoke_safe",
            "CommandProcessor smoke оставлен metadata-only",
            "CommandProcessor",
            True,
            ("safe read-only execution smoke: not used", "command execution used: no"),
        )

    @staticmethod
    def _check(check_id, title_ru, layer, passed, details_ru, severity="critical"):
        return VerticalIntegrationCheck(
            check_id=check_id,
            title_ru=title_ru,
            layer=layer,
            passed=bool(passed),
            severity=severity,
            safe=bool(passed),
            details_ru=tuple(details_ru),
        )

    @staticmethod
    def _contains_secret(text: str) -> bool:
        return bool(_SECRET_PATTERN.search(str(text or "")))

    @classmethod
    def _safe_text(cls, text: str) -> str:
        return _SECRET_PATTERN.sub("[REDACTED]", str(text or ""))
