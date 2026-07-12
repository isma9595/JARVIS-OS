"""Safe read-only allowlist for one-shot voice command auto-execution."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceAllowlistDecision:
    allowed: bool
    normalized_text: str
    canonical_command: str | None
    reason: str
    safety_notes: list[str]


class SafeVoiceCommandAllowlist:
    """Match only known low-risk read-only voice commands."""

    READ_ONLY_SAFETY_NOTES = [
        "Разрешены только заранее известные read-only команды.",
        "Рискованные команды не обходят CommandProcessor и ActionRouter.",
        "Не разрешены file/system/shell/install/download/email/internet/automation/destructive команды.",
    ]

    _ALIASES_BY_CANONICAL = {
        "статус системы": {
            "статус",
            "статус системы",
            "как система",
            "состояние системы",
        },
        "помощь": {
            "помощь",
            "help",
            "команды",
            "что ты умеешь",
            "покажи возможности",
        },
        "статус vosk": {
            "статус vosk",
            "проверить vosk",
            "готов ли vosk",
            "статус распознавания",
            "локальное распознавание",
        },
        "проверить модель vosk": {
            "проверить модель vosk",
            "готовность модели vosk",
            "диагностика модели vosk",
            "модель vosk статус",
            "проверка модели vosk",
        },
        "проверка аудио зависимостей": {
            "проверка аудио зависимостей",
            "проверить аудио зависимости",
        },
        "проверить зависимости микрофона": {
            "проверить зависимости микрофона",
        },
        "диагностика микрофона": {
            "диагностика микрофона",
            "почему не работает микрофон",
        },
        "проверить numpy": {
            "проверить numpy",
            "статус numpy",
        },
        "проверить sounddevice": {
            "проверить sounddevice",
            "статус sounddevice",
        },
        "проверить vosk пакет": {
            "проверить vosk пакет",
            "статус vosk пакета",
        },
        "как тебя зовут": {
            "как тебя зовут",
            "как зовут ассистента",
            "кто ты",
            "твое имя",
            "твоё имя",
        },
        "имя ассистента": {
            "имя ассистента",
            "покажи имя ассистента",
        },
        "ожидающая голосовая команда": {
            "ожидающая голосовая команда",
            "pending voice command",
            "какая голосовая команда ожидает подтверждения",
        },
        "сколько идей": {
            "сколько идей",
            "количество идей",
            "сколько сохранено идей",
        },
        "список идей": {
            "список идей",
            "покажи идеи",
            "мои идеи",
            "идеи",
        },
        "что ты запомнил": {
            "что ты запомнил",
            "что ты помнишь",
            "покажи память",
            "покажи что ты запомнил",
            "что в памяти",
            "моя память",
            "память",
        },
        "локальная память": {
            "локальная память",
        },
    }

    _RISKY_MARKERS = {
        "автоматизац",
        "браузер",
        "включи постоянное прослушивание",
        "выполни",
        "запомни",
        "запусти",
        "измени",
        "интернет",
        "очисти",
        "открой",
        "отправь",
        "powershell",
        "скачай",
        "удали",
        "установи",
        "файл",
        "shell",
    }

    def __init__(self):
        self._canonical_by_alias = {}
        for canonical, aliases in self._ALIASES_BY_CANONICAL.items():
            self._canonical_by_alias[self.normalize(canonical)] = canonical
            for alias in aliases:
                self._canonical_by_alias[self.normalize(alias)] = canonical

    @classmethod
    def normalize(cls, text):
        normalized = str(text or "").strip().lower().replace("ё", "е")
        return " ".join(normalized.split())

    def decide(self, text):
        normalized = self.normalize(text)
        if not normalized:
            return VoiceAllowlistDecision(
                allowed=False,
                normalized_text="",
                canonical_command=None,
                reason="empty",
                safety_notes=list(self.READ_ONLY_SAFETY_NOTES),
            )

        canonical = self._canonical_by_alias.get(normalized)
        if canonical is None:
            reason = "unknown_command"
            if any(marker in normalized for marker in self._RISKY_MARKERS):
                reason = "risky_or_modifying_command"
            return VoiceAllowlistDecision(
                allowed=False,
                normalized_text=normalized,
                canonical_command=None,
                reason=reason,
                safety_notes=list(self.READ_ONLY_SAFETY_NOTES),
            )

        return VoiceAllowlistDecision(
            allowed=True,
            normalized_text=normalized,
            canonical_command=canonical,
            reason="known_read_only_command",
            safety_notes=list(self.READ_ONLY_SAFETY_NOTES),
        )

    def read_only_commands(self):
        return tuple(self._ALIASES_BY_CANONICAL.keys())

    def format_read_only_commands(self):
        lines = [
            "Безопасные голосовые команды без подтверждения:",
            "Read-only:",
        ]
        lines.extend(f"- {command}" for command in self.read_only_commands())
        lines.extend(
            [
                "Все остальные голосовые команды требуют подтверждения.",
                "Рискованные действия не обходят безопасность и всё равно проходят CommandProcessor и ActionRouter.",
            ]
        )
        return "\n".join(lines)
