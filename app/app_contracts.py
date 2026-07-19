"""Versioned UI-safe AppService contracts.

The contracts in this module are plain standard-library dataclasses intended
for desktop, mobile, installer, and future admin/support surfaces. They do not
execute commands, call providers, read secrets, or depend on UI internals.
"""

from dataclasses import dataclass, fields
from enum import Enum
import re
from typing import Any


APP_CONTRACT_VERSION = "0.1"
APP_CONTRACT_SCHEMA_NAME = "jarvis.app_service.contracts"


_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+)"
)


def safe_contract_text(text: str) -> str:
    """Return text suitable for UI serialization without obvious secrets."""

    return _SECRET_PATTERN.sub("[REDACTED]", str(text or ""))


def _safe_value(value: Any) -> object:
    if isinstance(value, str):
        return safe_contract_text(value)
    if isinstance(value, tuple):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, list):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


class _ContractMixin:
    def to_dict(self) -> dict[str, object]:
        return {field.name: _safe_value(getattr(self, field.name)) for field in fields(self)}


class AppCommandSource(Enum):
    CLI = "cli"
    DESKTOP_UI = "desktop_ui"
    VOICE = "voice"
    TEST = "test"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AppClarificationOption(_ContractMixin):
    option_id: str
    label_ru: str
    command_text: str
    command_id: str | None


@dataclass(frozen=True)
class AppIntentResolutionContract(_ContractMixin):
    original_text: str
    processing_text: str
    intent_kind: str
    resolution_status: str
    matched_command: str | None
    confidence: str
    reason_codes: tuple[str, ...]
    clarification_question: str | None
    clarification_options: tuple[AppClarificationOption, ...]
    requires_clarification: bool
    source: str


@dataclass(frozen=True)
class AppContractStatus(_ContractMixin):
    schema_name: str
    version: str
    stable: bool
    app_service_ready: bool
    desktop_shell_ready: bool
    secure_key_storage_ready: bool
    provider_settings_ui_ready: bool
    installer_ready: bool
    mobile_ready: bool
    admin_support_ready: bool
    network_default: bool
    secrets_included: bool
    responses_executed_as_commands: bool
    notes_ru: tuple[str, ...]

    def safe_text_ru(self) -> str:
        return "\n".join(
            [
                "AppService contracts status:",
                f"- schema name: {self.schema_name}",
                f"- contract version: {self.version}",
                f"- stable: {'yes' if self.stable else 'no'}",
                f"- app service ready: {'yes' if self.app_service_ready else 'no'}",
                f"- desktop shell ready: {'yes' if self.desktop_shell_ready else 'no'}",
                f"- secure key storage ready: {'yes' if self.secure_key_storage_ready else 'no'}",
                f"- provider settings UI ready: {'yes' if self.provider_settings_ui_ready else 'no'}",
                f"- installer ready: {'yes' if self.installer_ready else 'no'}",
                f"- mobile ready: {'yes' if self.mobile_ready else 'no'}",
                f"- admin/support ready: {'yes' if self.admin_support_ready else 'planned/no'}",
                f"- network default: {'yes' if self.network_default else 'no'}",
                f"- secrets included: {'yes' if self.secrets_included else 'no'}",
                f"- responses executed as commands: {'yes' if self.responses_executed_as_commands else 'no'}",
                *[f"- note: {safe_contract_text(note)}" for note in self.notes_ru],
            ]
        )


@dataclass(frozen=True)
class AppLanguagePreferenceContract(_ContractMixin):
    language_code: str
    language_name: str
    previous_language_code: str | None
    changed: bool
    persisted: bool
    default_language: str
    source: str
    is_default: bool
    message: str
    supported_languages: tuple[str, ...]

    def safe_text_ru(self) -> str:
        return "\n".join(
            [
                "Language preference:",
                f"- language code: {safe_contract_text(self.language_code)}",
                f"- language name: {safe_contract_text(self.language_name)}",
                f"- default language: {safe_contract_text(self.default_language)}",
                f"- persisted: {'yes' if self.persisted else 'no'}",
                f"- source: {safe_contract_text(self.source)}",
                f"- supported: {', '.join(self.supported_languages)}",
                f"- message: {safe_contract_text(self.message)}",
                "- secrets included: no",
            ]
        )


@dataclass(frozen=True)
class AppStatusCard(_ContractMixin):
    card_id: str
    title_ru: str
    value_ru: str
    status: str
    category: str
    safe: bool
    ui_visible: bool
    details_ru: tuple[str, ...]

    def safe_text_ru(self) -> str:
        detail = "; ".join(safe_contract_text(item) for item in self.details_ru)
        return (
            f"{self.title_ru}: {self.value_ru} | status={self.status} | "
            f"category={self.category} | safe={'yes' if self.safe else 'no'}"
            + (f" | {detail}" if detail else "")
        )


@dataclass(frozen=True)
class AppCommandCard(_ContractMixin):
    command_id: str
    title_ru: str
    description_ru: str
    category: str
    aliases: tuple[str, ...]
    risk_level: str
    read_only: bool
    voice_auto_allowed: bool
    requires_confirmation: bool
    requires_network: bool
    requires_ai_key: bool
    requires_privacy_check: bool
    app_ready: bool
    ui_visible: bool
    notes_ru: str | None

    def safe_text_ru(self) -> str:
        return (
            f"{self.title_ru} | id={self.command_id} | category={self.category} | "
            f"risk={self.risk_level} | read_only={'yes' if self.read_only else 'no'} | "
            f"network={'yes' if self.requires_network else 'no'} | "
            f"app_ready={'yes' if self.app_ready else 'no'}"
        )


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
    active_plan_id: str | None = None
    active_plan_status: str | None = None
    active_step_id: str | None = None
    active_step_capability_id: str | None = None
    active_step_name: str | None = None
    operation_id: str | None = None


@dataclass(frozen=True)
class AppPreviewContract(_ContractMixin):
    input_text: str
    known_command: bool
    command_id: str | None
    title_ru: str | None
    category: str
    risk_level: str
    read_only: bool
    requires_confirmation: bool
    requires_network: bool
    requires_privacy_check: bool
    voice_auto_allowed: bool
    app_ready: bool
    safe_summary_ru: str
    secrets_included: bool
    executed: bool

    def safe_text_ru(self) -> str:
        return "\n".join(
            [
                "App preview contract:",
                "- executed: no",
                f"- input preview: {safe_contract_text(self.input_text)}",
                f"- known command: {'yes' if self.known_command else 'no'}",
                f"- command id: {self.command_id or 'none'}",
                f"- category: {self.category}",
                f"- risk: {self.risk_level}",
                f"- requires network: {'yes' if self.requires_network else 'no'}",
                f"- requires privacy check: {'yes' if self.requires_privacy_check else 'no'}",
                f"- voice auto allowed: {'yes' if self.voice_auto_allowed else 'no'}",
                f"- app ready: {'yes' if self.app_ready else 'no'}",
                f"- safe summary: {safe_contract_text(self.safe_summary_ru)}",
                "- secrets included: no",
            ]
        )


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
    plan_id: str | None = None
    plan_status: str | None = None
    plan_step_count: int | None = None


@dataclass(frozen=True)
class AppExecutionContract(_ContractMixin):
    ok: bool
    input_text: str
    output_text: str
    source: str
    command_id: str | None
    category: str | None
    risk_level: str | None
    executed: bool
    requires_confirmation: bool
    network_may_be_used: bool
    response_executed_as_command: bool
    secrets_included: bool
    error: str | None
    intent_resolution: AppIntentResolutionContract | None = None
    requires_clarification: bool = False
    clarification_question: str | None = None
    clarification_options: tuple[AppClarificationOption, ...] = ()
    policy_decision: dict[str, object] | None = None
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
    plan_id: str | None = None
    plan_status: str | None = None
    plan_step_count: int | None = None

    def safe_text_ru(self) -> str:
        lines = [
            "App execution contract:",
            f"- ok: {'yes' if self.ok else 'no'}",
            f"- source: {self.source}",
            f"- command id: {self.command_id or 'none'}",
            f"- category: {self.category or 'unknown'}",
            f"- risk: {self.risk_level or 'unknown'}",
            f"- executed: {'yes' if self.executed else 'no'}",
            f"- requires confirmation: {'yes' if self.requires_confirmation else 'no'}",
            f"- requires clarification: {'yes' if self.requires_clarification else 'no'}",
            f"- operation id: {self.operation_id or 'none'}",
            f"- operation status: {self.operation_status or 'none'}",
            f"- duplicate suppressed: {'yes' if self.duplicate_suppressed else 'no'}",
            f"- cancellable: {'yes' if self.cancellable else 'no'}",
            f"- network may be used: {'yes' if self.network_may_be_used else 'no'}",
            "- response executed as command: no",
            "- secrets included: no",
        ]
        if self.workflow_id:
            lines.extend(
                [
                    f"- workflow id: {safe_contract_text(self.workflow_id)}",
                    f"- workflow status: {safe_contract_text(self.workflow_status or 'none')}",
                    f"- current step id: {safe_contract_text(self.current_step_id or 'none')}",
                    f"- current step name: {safe_contract_text(self.current_step_name or 'none')}",
                    f"- completed steps: {len(self.completed_steps)}",
                    f"- total steps: {self.total_steps if self.total_steps is not None else 0}",
                    f"- progress percent: {self.progress_percent if self.progress_percent is not None else 0}",
                    f"- awaiting confirmation: {'yes' if self.awaiting_confirmation else 'no'}",
                    f"- source filename: {safe_contract_text(self.source_filename or 'none')}",
                    f"- issue count: {self.issue_count if self.issue_count is not None else 0}",
                    f"- proposed output filename: {safe_contract_text(self.proposed_output_filename or 'none')}",
                    f"- proposed output path: {safe_contract_text(self.proposed_output_path or 'none')}",
                    f"- saved: {'yes' if self.saved else 'no'}",
                    f"- verified: {'yes' if self.verified else 'no'}",
                ]
            )
            if self.issue_summaries:
                lines.append("Issue summaries:")
                for issue in self.issue_summaries:
                    lines.append(
                        "- "
                        + safe_contract_text(
                            f"{issue.get('issue_code', 'unknown')} line {issue.get('line_number', '?')}: "
                            f"{issue.get('description_ru', '')}"
                        )
                    )
            if self.user_message:
                lines.append(f"- user message: {safe_contract_text(self.user_message)}")
        if self.policy_decision:
            lines.append(f"- policy decision: {self.policy_decision.get('decision', 'unknown')}")
        if self.plan_id:
            lines.extend(
                [
                    f"- plan id: {safe_contract_text(self.plan_id)}",
                    f"- plan status: {safe_contract_text(self.plan_status or 'none')}",
                    f"- plan step count: {self.plan_step_count if self.plan_step_count is not None else 0}",
                ]
            )
        if self.clarification_question:
            lines.append("Требуется уточнение:")
            lines.append(safe_contract_text(self.clarification_question))
        if self.clarification_options:
            lines.append("Варианты:")
            lines.extend(
                f"- {safe_contract_text(option.label_ru)}"
                for option in self.clarification_options
            )
        if self.error:
            lines.append(f"- error: {safe_contract_text(self.error)}")
        if self.output_text:
            lines.extend(["Output:", safe_contract_text(self.output_text)])
        return "\n".join(lines)


@dataclass(frozen=True)
class AppVoiceRequestResult(_ContractMixin):
    ok: bool
    voice_capture_succeeded: bool
    recognition_succeeded: bool
    recognized_text: str | None
    text_processing_succeeded: bool
    result_type: str
    category: str | None
    requires_confirmation: bool
    error_code: str | None
    user_message: str
    text_result: AppExecutionContract | None
    secrets_included: bool
    raw_audio_included: bool
    provider_objects_included: bool
    microphone_objects_included: bool
    normalized_text: str | None = None
    normalization_applied: bool = False
    normalization_rules: tuple[str, ...] = ()
    operation_id: str | None = None
    operation_status: str | None = None
    idempotency_key: str | None = None
    duplicate_suppressed: bool = False
    cancellable: bool = False

    def safe_text_ru(self) -> str:
        lines = [
            "App one-shot voice request:",
            f"- ok: {'yes' if self.ok else 'no'}",
            f"- voice capture succeeded: {'yes' if self.voice_capture_succeeded else 'no'}",
            f"- recognition succeeded: {'yes' if self.recognition_succeeded else 'no'}",
            f"- recognized text: {safe_contract_text(self.recognized_text or 'none')}",
            f"- normalized text: {safe_contract_text(self.normalized_text or 'none')}",
            f"- normalization applied: {'yes' if self.normalization_applied else 'no'}",
            "- normalization rules: "
            + (", ".join(self.normalization_rules) if self.normalization_rules else "none"),
            f"- text processing succeeded: {'yes' if self.text_processing_succeeded else 'no'}",
            f"- result type: {self.result_type}",
            f"- category: {self.category or 'unknown'}",
            f"- operation id: {self.operation_id or 'none'}",
            f"- operation status: {self.operation_status or 'none'}",
            f"- duplicate suppressed: {'yes' if self.duplicate_suppressed else 'no'}",
            f"- requires confirmation: {'yes' if self.requires_confirmation else 'no'}",
            f"- error code: {self.error_code or 'none'}",
            f"- message: {safe_contract_text(self.user_message)}",
            "- secrets included: no",
            "- raw audio included: no",
            "- provider objects included: no",
            "- microphone objects included: no",
        ]
        if self.text_result is not None:
            lines.append("Text result:")
            lines.append(self.text_result.safe_text_ru())
        return "\n".join(lines)


@dataclass(frozen=True)
class AppContractManifest(_ContractMixin):
    schema_name: str
    version: str
    status: AppContractStatus
    status_cards: tuple[AppStatusCard, ...]
    command_cards_count: int
    categories: tuple[str, ...]

    def safe_text_ru(self) -> str:
        return "\n".join(
            [
                "AppService contracts manifest:",
                f"- schema name: {self.schema_name}",
                f"- version: {self.version}",
                f"- status cards count: {len(self.status_cards)}",
                f"- command cards count: {self.command_cards_count}",
                f"- categories: {', '.join(self.categories)}",
                "- no secrets",
                "- no network",
                "- no execution",
            ]
        )
