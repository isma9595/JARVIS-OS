from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceDialogueModeStatus:
    enabled: bool
    mode: str
    reason: str | None = None
    safety_notes: list[str] | None = None


class VoiceDialogueModeManager:
    OFF = "OFF"
    MANUAL = "MANUAL"
    MAX_SPEAKABLE_LENGTH = 500

    CONTROL_COMMANDS = {
        "статус голосового диалога",
        "режим голосового диалога",
        "включить голосовой диалог",
        "включи голосовой диалог",
        "включить ручной голосовой диалог",
        "включи ручной голосовой диалог",
        "говори ответы голосом",
        "озвучивай ответы",
        "озвучивай текущие ответы",
        "выключить голосовой диалог",
        "выключи голосовой диалог",
        "отключить голосовой диалог",
        "не озвучивай ответы",
        "перестань озвучивать ответы",
        "статус голосового ответа",
        "статус голоса",
        "голосовой ответ статус",
        "включить тестовый голос",
        "включи тестовый голос",
        "включить локальный голос",
        "включить голос windows",
        "включи локальный голос",
        "выключить голос",
        "выключи голос",
        "отключить голосовой ответ",
        "тест голоса",
        "проверка голоса",
        "тест локального голоса",
        "проверка локального голоса",
        "последний ответ",
        "покажи последний ответ",
        "озвучь последний ответ",
        "скажи последний ответ",
        "произнеси последний ответ",
        "повтори голосом",
        "повтори последний ответ голосом",
        "история ответов",
        "история ответов jarvis",
        "сколько ответов",
        "очистить историю ответов",
        "очисти историю ответов",
        "помощь",
        "команды",
        "help",
    }

    CONTROL_PREFIXES = (
        "скажи:",
        "произнеси:",
        "озвучь:",
        "симулируй распознавание:",
        "проверить голосовую команду:",
        "проверь голосовую команду:",
    )

    def __init__(self):
        self.mode = self.OFF

    def enable_manual(self):
        self.mode = self.MANUAL
        return self.status(reason="manual_enabled")

    def disable(self):
        self.mode = self.OFF
        return self.status(reason="disabled")

    def status(self, reason=None):
        return VoiceDialogueModeStatus(
            enabled=self.is_manual_enabled(),
            mode=self.mode,
            reason=reason,
            safety_notes=[
                "Постоянное прослушивание не включается.",
                "Облачный TTS не используется.",
                "Аудиофайлы не сохраняются.",
                "Режим не сохраняется на диск.",
            ],
        )

    def is_manual_enabled(self):
        return self.mode == self.MANUAL

    def should_speak_response(self, text, source_command=None, speakable=True):
        if not self.is_manual_enabled():
            return False
        if not speakable:
            return False

        normalized_text = " ".join(str(text or "").split())
        if not normalized_text:
            return False
        if len(normalized_text) > self.MAX_SPEAKABLE_LENGTH:
            return False

        normalized_command = " ".join(str(source_command or "").strip().lower().split())
        if not normalized_command:
            return True
        if normalized_command in self.CONTROL_COMMANDS:
            return False
        return not any(
            normalized_command.startswith(prefix) for prefix in self.CONTROL_PREFIXES
        )
