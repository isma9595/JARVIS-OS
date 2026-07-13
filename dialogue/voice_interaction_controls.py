"""Session-only repeat, clarify, and last voice interaction helpers."""

from dataclasses import dataclass
import re


NO_LAST_ASSISTANT_RESPONSE = "В этой сессии ещё нет ответа JARVIS для повторения."
NO_LAST_VOICE_RECOGNITION = "В этой сессии ещё нет распознанной голосовой команды."


@dataclass(frozen=True)
class VoiceInteractionSummary:
    recognized_text: str | None
    canonical_command: str | None
    source: str | None
    status: str | None
    corrected_text: str | None = None


class VoiceInteractionControls:
    """Safe in-memory controls for current-session voice dialogue context."""

    def __init__(self, assistant_response_history, voice_command_history=None):
        self.assistant_response_history = assistant_response_history
        self.voice_command_history = voice_command_history

    def get_last_assistant_response(self):
        entry = self.assistant_response_history.last_speakable_response()
        if entry is None:
            return None
        return entry.text

    def get_short_last_assistant_response(self, max_chars=180):
        text = self.get_last_assistant_response()
        if text is None:
            return None
        return self._trim_to_sentence_or_limit(text, max_chars=max_chars)

    def get_simple_last_assistant_response(self, max_chars=220):
        text = self.get_last_assistant_response()
        if text is None:
            return None
        return self._trim_to_sentence_or_limit(text, max_chars=max_chars)

    def get_last_voice_recognition_summary(self):
        entry = self._last_voice_entry()
        if entry is None:
            return None
        return VoiceInteractionSummary(
            recognized_text=entry.recognized_text,
            canonical_command=entry.canonical_command,
            source=entry.source,
            status=entry.status,
            corrected_text=entry.corrected_text,
        )

    def format_last_voice_command_for_display(self):
        summary = self.get_last_voice_recognition_summary()
        if summary is None:
            return NO_LAST_VOICE_RECOGNITION

        canonical = summary.canonical_command or "нет"
        source = self._source_label(summary.source)
        status = self._status_label(summary.status)
        lines = [
            "Последняя распознанная голосовая команда:",
            f"Распознано: {summary.recognized_text or 'пусто / речь не распознана'}",
            f"Каноническая команда: {canonical}",
            f"Источник: {source}",
            f"Статус: {status}",
        ]
        if summary.corrected_text:
            lines.insert(3, f"Исправлено на: {summary.corrected_text}")
        return "\n".join(lines)

    def decide_repeat_target(self, command_text):
        normalized = " ".join(str(command_text or "").strip().lower().split())
        if "голосов" in normalized and (
            "команд" in normalized or "что я сказал" in normalized
        ):
            return "last_voice_command"
        return "last_assistant_response"

    def _last_voice_entry(self):
        if self.voice_command_history is None:
            return None
        return self.voice_command_history.last_entry()

    @staticmethod
    def _source_label(source):
        labels = {
            "one_shot_vosk": "one-shot Vosk",
            "typed_simulation": "текстовая симуляция",
            "user_session_correction": "исправление текущей сессии",
        }
        return labels.get(source, source or "unknown")

    @staticmethod
    def _status_label(status):
        labels = {
            "recognized": "распознано",
            "correction_added": "исправление добавлено",
            "correction_applied": "исправление применено",
            "allowlisted_executed": "выполнено как безопасная read-only команда",
            "pending_confirmation": "ожидает подтверждения",
            "confirmed_executed": "подтверждено и передано в безопасную обработку",
            "confirmed_safe_processing": "подтверждено и передано в безопасную обработку",
            "confirmed_requires_additional_safety_confirmation": "требует дополнительного подтверждения безопасности",
            "canceled": "отменено",
            "blocked": "заблокировано",
            "empty": "пусто / речь не распознана",
            "failed": "ошибка распознавания",
            "unknown_confirmation": "неизвестный ответ на подтверждение",
        }
        return labels.get(status, status or "unknown")

    @staticmethod
    def _trim_to_sentence_or_limit(text, max_chars):
        normalized = " ".join(str(text or "").split())
        if len(normalized) <= max_chars:
            return normalized

        first_sentence = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)[0]
        if first_sentence and len(first_sentence) <= max_chars:
            return first_sentence

        return normalized[: max_chars - 3].rstrip() + "..."
