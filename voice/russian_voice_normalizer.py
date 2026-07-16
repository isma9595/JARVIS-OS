"""Conservative Russian normalization for one-shot voice command text."""

from __future__ import annotations

from dataclasses import dataclass, fields
import re
from typing import Any


_RU_LOCALES = {"ru", "ru-ru", "ru_ru"}
_STATUS_SYSTEM_COMMAND = "статус системы"
_STATUS_SYSTEM_VARIANTS = {
    "статус системы",
    "статус система",
    "статус систем",
}
_HARMLESS_PREFIXES = (
    "джарвис",
    "jarvis",
    "пожалуйста",
)


@dataclass(frozen=True)
class RussianVoiceNormalizationResult:
    original_text: str
    normalized_text: str
    changed: bool
    applied_rules: tuple[str, ...]
    safe_to_use_as_command_candidate: bool

    def to_dict(self) -> dict[str, object]:
        return {
            field.name: _safe_serializable_value(getattr(self, field.name))
            for field in fields(self)
        }


def normalize_russian_voice_text(
    text: str,
    locale: str = "ru-RU",
) -> RussianVoiceNormalizationResult:
    """Return a safe one-shot voice normalization result without execution."""

    original_text = str(text or "")
    if _normalize_locale(locale) not in _RU_LOCALES:
        return RussianVoiceNormalizationResult(
            original_text=original_text,
            normalized_text=original_text,
            changed=False,
            applied_rules=(),
            safe_to_use_as_command_candidate=False,
        )

    working = original_text
    applied_rules: list[str] = []

    trimmed = working.strip()
    if trimmed != working:
        applied_rules.append("trim_surrounding_whitespace")
    working = trimmed

    collapsed = " ".join(working.split())
    if collapsed != working:
        applied_rules.append("collapse_repeated_whitespace")
    working = collapsed

    lowered = working.lower().replace("ё", "е")
    if lowered != working:
        applied_rules.append("normalize_command_case")
    working = lowered

    direct_candidate = _speech_match_text(working)
    if direct_candidate in _STATUS_SYSTEM_VARIANTS:
        normalized_text = _STATUS_SYSTEM_COMMAND
        if normalized_text != working:
            applied_rules.append("normalize_system_status_phrase")
        return RussianVoiceNormalizationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            changed=normalized_text != original_text,
            applied_rules=tuple(applied_rules),
            safe_to_use_as_command_candidate=True,
        )

    prefixed_candidate = _remove_harmless_prefix_if_status_command(working)
    if prefixed_candidate is not None:
        if prefixed_candidate != working:
            applied_rules.append("remove_harmless_voice_prefix")
        normalized_text = _STATUS_SYSTEM_COMMAND
        if normalized_text != prefixed_candidate:
            applied_rules.append("normalize_system_status_phrase")
        return RussianVoiceNormalizationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            changed=normalized_text != original_text,
            applied_rules=tuple(applied_rules),
            safe_to_use_as_command_candidate=True,
        )

    return RussianVoiceNormalizationResult(
        original_text=original_text,
        normalized_text=working,
        changed=working != original_text,
        applied_rules=tuple(applied_rules),
        safe_to_use_as_command_candidate=False,
    )


def _normalize_locale(locale: str) -> str:
    return str(locale or "").strip().lower().replace("_", "-")


def _speech_match_text(text: str) -> str:
    punctuation_as_space = re.sub(r"[,.!?;:]+", " ", text, flags=re.UNICODE)
    return " ".join(punctuation_as_space.split())


def _remove_harmless_prefix_if_status_command(text: str) -> str | None:
    speech_text = _speech_match_text(text)
    for prefix in _HARMLESS_PREFIXES:
        prefix_with_space = prefix + " "
        if not speech_text.startswith(prefix_with_space):
            continue
        remainder = speech_text[len(prefix_with_space) :].strip()
        if remainder in _STATUS_SYSTEM_VARIANTS:
            return remainder
    return None


def _safe_serializable_value(value: Any) -> object:
    if isinstance(value, tuple):
        return tuple(_safe_serializable_value(item) for item in value)
    return value
