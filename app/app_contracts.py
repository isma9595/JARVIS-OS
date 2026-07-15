"""Versioned UI-safe AppService contracts.

The contracts in this module are plain standard-library dataclasses intended
for desktop, mobile, installer, and future admin/support surfaces. They do not
execute commands, call providers, read secrets, or depend on UI internals.
"""

from dataclasses import dataclass, fields
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
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


class _ContractMixin:
    def to_dict(self) -> dict[str, object]:
        return {field.name: _safe_value(getattr(self, field.name)) for field in fields(self)}


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
            f"- network may be used: {'yes' if self.network_may_be_used else 'no'}",
            "- response executed as command: no",
            "- secrets included: no",
        ]
        if self.error:
            lines.append(f"- error: {safe_contract_text(self.error)}")
        if self.output_text:
            lines.extend(["Output:", safe_contract_text(self.output_text)])
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
