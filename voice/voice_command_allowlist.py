"""Safe allowlist for one-shot voice command auto-execution."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class VoiceAllowlistDecision:
    allowed: bool
    normalized_text: str
    canonical_command: str | None
    reason: str
    safety_notes: list[str]


class SafeVoiceCommandAllowlist:
    """Match only known low-risk read-only and safety-control voice commands."""

    READ_ONLY_SAFETY_NOTES = [
        "Разрешены только заранее известные read-only команды.",
        "Рискованные команды не обходят CommandProcessor и ActionRouter.",
        "Не разрешены file/system/shell/install/download/email/internet/automation/destructive команды.",
    ]

    _ALIASES_BY_CANONICAL = {
        "статус системы": {
            "статус",
            "статус систем",
            "статус система",
            "статусе систем",
            "статусе системы",
            "статус системы",
            "статую система",
            "статую системы",
            "статуя система",
            "статуя системы",
            "как система",
            "состояние системы",
        },
        "статус ai": {
            "статус ai",
            "статус ии",
            "статус искусственного интеллекта",
            "статус ai провайдеров",
            "статус ии провайдеров",
            "ai status",
        },
        "статус openai": {
            "статус openai",
            "статус опенай",
            "openai status",
        },
        "статус gemini": {
            "статус gemini",
            "статус джемини",
            "gemini status",
        },
        "статус groq": {
            "статус groq",
            "статус грок",
            "groq status",
        },
        "статус groq request shape": {
            "статус groq request shape",
            "groq request shape",
            "форма groq запроса",
        },
        "статус openai one shot": {
            "статус openai one shot",
        },
        "статус openai guard": {
            "статус openai guard",
            "статус openai cost guard",
            "лимиты openai",
            "лимит openai запроса",
            "openai guard status",
        },
        "openai модель": {
            "openai модель",
            "openai model",
        },
        "статус gemini guard": {
            "статус gemini guard",
            "статус gemini cost guard",
            "лимиты gemini",
        },
        "gemini модель": {
            "gemini модель",
            "gemini model",
        },
        "статус groq guard": {
            "статус groq guard",
            "статус groq cost guard",
            "лимиты groq",
        },
        "groq модель": {
            "groq модель",
            "groq model",
        },
        "список ai провайдеров": {
            "список ai провайдеров",
            "список ии провайдеров",
            "ai провайдеры",
            "ии провайдеры",
            "провайдеры ai",
        },
        "статус ai конфигурации": {
            "статус ai конфигурации",
            "статус ии конфигурации",
        },
        "статус ai ключей": {
            "статус ai ключей",
            "статус ии ключей",
            "статус api ключей",
            "ai config status",
        },
        "безопасность ai ключей": {
            "безопасность ai ключей",
            "безопасность ии ключей",
            "как хранить ai ключи",
            "как хранить api ключи",
        },
        "проверить groq ключ": {
            "проверить groq ключ",
            "проверить ключ groq",
        },
        "проверить gemini ключ": {
            "проверить gemini ключ",
            "проверить ключ gemini",
        },
        "проверить openai ключ": {
            "проверить openai ключ",
            "проверить ключ openai",
        },
        "помощь": {
            "помощь",
            "помоги",
            "справка",
            "help",
            "команды",
            "что ты умеешь",
            "покажи возможности",
        },
        "статус голосового цикла": {
            "статус голосового цикла",
            "голосовой цикл статус",
            "итог голосового цикла",
            "что умеет голос",
            "список голосовых возможностей",
        },
        "карта голосовых команд": {
            "карта голосовых команд",
        },
        "статус vosk": {
            "статус воск",
            "статус воска",
            "статус vosk",
            "проверить vosk",
            "готов ли vosk",
            "статус распознавания",
            "локальное распознавание",
        },
        "проверить модель vosk": {
            "проверить модель vosk",
            "проверить готовность модели vosk",
            "готовность модели vosk",
            "диагностика модели vosk",
            "модель vosk статус",
            "проверка модели vosk",
        },
        "выключи микрофон": {
            "выключи микрофон",
            "выключить микрофон",
            "отключи микрофон",
            "отключить микрофон",
            "микрофон выключить",
            "микрофон off",
            "mic off",
        },
        "частичное прослушивание": {
            "частичное прослушивание",
            "частичный режим микрофона",
            "включить частичный режим микрофона",
            "микрофон частично",
            "partial microphone mode",
            "mic partial",
        },
        "проверка аудио зависимостей": {
            "проверка аудио зависимости",
            "проверка аудио зависимостей",
            "проверить аудио зависимости",
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
            "как твое имя",
            "как твоё имя",
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
        "последнее распознавание": {
            "последнее распознавание",
            "последнее распознование",
            "последняя голосовая команда",
            "покажи последнюю голосовую команду",
            "что я сказал",
            "что ты услышал",
            "что ты распознал",
        },
        "что ты сказал": {
            "что ты сказал",
            "что ты сказал последний раз",
            "что ты ответил",
            "повтори текстом",
            "повтори последний ответ текстом",
        },
        "объясни короче": {
            "объясни короче",
            "скажи короче",
            "коротко",
            "короче",
        },
        "скажи проще": {
            "скажи проще",
            "объясни проще",
            "проще",
        },
        "история голосовых команд": {
            "история голосовых команд",
            "покажи историю голоса",
            "история распознавания",
            "история распознования",
        },
        "сколько голосовых команд": {
            "сколько голосовых команд",
        },
        "замолчи": {
            "замолчи",
            "тихо",
            "стоп голос",
            "останови голос",
            "остановить голос",
            "перестань говорить",
            "не говори",
            "отключи речь",
            "выключи речь",
        },
        "снова говори": {
            "снова говори",
            "можешь говорить",
            "включи речь",
            "разреши голос",
            "выключи тихий режим",
            "отключи тихий режим",
            "размутить голос",
        },
        "не озвучивай следующий ответ": {
            "не озвучивай следующий ответ",
            "пропусти следующую озвучку",
            "следующий ответ не озвучивай",
            "один ответ без голоса",
        },
        "статус голосовой безопасности": {
            "статус голосовой безопасности",
            "статус тихого режима",
            "статус mute",
            "голос заблокирован",
            "можно ли говорить голосом",
        },
    }

    _RISKY_MARKERS = {
        "автоматизац",
        "браузер",
        "включи постоянное прослушивание",
        "выполни",
        "добавь",
        "запомни",
        "запусти",
        "измени",
        "интернет",
        "очисти",
        "открой",
        "отправь",
        "cmd",
        "powershell",
        "скачай",
        "удали",
        "установи",
        "файл",
        "shell",
    }

    def __init__(self):
        self._canonical_by_alias = {}
        self._normalized_canonicals = set()
        for canonical, aliases in self._ALIASES_BY_CANONICAL.items():
            normalized_canonical = self.normalize(canonical)
            self._normalized_canonicals.add(normalized_canonical)
            self._canonical_by_alias[normalized_canonical] = canonical
            for alias in aliases:
                self._canonical_by_alias[self.normalize(alias)] = canonical

    @classmethod
    def normalize(cls, text):
        normalized = str(text or "").strip().lower().replace("ё", "е")
        normalized = re.sub(r"[^\w\s]+", " ", normalized, flags=re.UNICODE)
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
            reason=(
                "allowlist_match"
                if normalized in self._normalized_canonicals
                else "explicit_safe_alias"
            ),
            safety_notes=list(self.READ_ONLY_SAFETY_NOTES),
        )

    def read_only_commands(self):
        return tuple(self._ALIASES_BY_CANONICAL.keys())

    def read_only_aliases(self, canonical_command):
        aliases = self._ALIASES_BY_CANONICAL.get(canonical_command, set())
        normalized_canonical = self.normalize(canonical_command)
        return tuple(
            sorted(
                alias
                for alias in aliases
                if self.normalize(alias) != normalized_canonical
            )
        )

    def format_read_only_commands(self):
        lines = [
            "Безопасные голосовые команды без подтверждения:",
            "Read-only:",
        ]
        for command in self.read_only_commands():
            lines.append(f"- {command}")
            aliases = self.read_only_aliases(command)
            if aliases:
                lines.append(f"  Алиасы: {', '.join(aliases)}")
        lines.extend(
            [
                "Safe aliases: только явные варианты для read-only команд из списка.",
                "Широкое угадывание и fuzzy matching для рискованных команд не используются.",
                "Все остальные голосовые команды требуют подтверждения.",
                "Все неизвестные и рискованные голосовые команды всё ещё требуют подтверждения.",
                "Рискованные действия не обходят безопасность и всё равно проходят CommandProcessor и ActionRouter.",
            ]
        )
        return "\n".join(lines)
