"""Safe conversational loop foundation for JARVIS.

This module classifies ordinary user text and returns a display-safe response.
It does not execute commands, call providers, use network, open browsers, read
secrets, start audio, or persist prompts.
"""

from dataclasses import dataclass
from enum import Enum
import re

from core.command_registry import CommandRegistry, DEFAULT_COMMAND_REGISTRY


class ConversationIntent(Enum):
    KNOWN_COMMAND = "known_command"
    SMALL_TALK = "small_talk"
    AI_QUESTION = "ai_question"
    DRAFTING_TASK = "drafting_task"
    SIMPLE_ACTION = "simple_action"
    RESEARCH_TASK = "research_task"
    COMPLEX_AGENT_TASK = "complex_agent_task"
    RISKY_ACTION = "risky_action"
    UNKNOWN = "unknown"


class ConversationRoute(Enum):
    COMMAND_PREVIEW = "command_preview"
    COMMAND_EXECUTION_SAFE_READ_ONLY = "command_execution_safe_read_only"
    LOCAL_SMALL_TALK = "local_small_talk"
    AI_DRY_RUN_SAFE = "ai_dry_run_safe"
    DRAFT_PLAN = "draft_plan"
    SIMPLE_ACTION_PLAN = "simple_action_plan"
    RESEARCH_PLAN = "research_plan"
    AGENT_PLAN = "agent_plan"
    RISKY_BLOCKED_OR_CONFIRMATION_REQUIRED = "risky_blocked_or_confirmation_required"
    CLARIFY = "clarify"


class ConversationSafetyLevel(Enum):
    SAFE_READ_ONLY = "safe_read_only"
    SAFE_METADATA_ONLY = "safe_metadata_only"
    NEEDS_CONFIRMATION = "needs_confirmation"
    NETWORK_EXPLICIT_REQUIRED = "network_explicit_required"
    RISKY_BLOCKED = "risky_blocked"


@dataclass(frozen=True)
class ConversationalRequest:
    text: str
    source: str
    allow_network: bool = False
    allow_command_execution: bool = False
    allow_risky_actions: bool = False
    preferred_provider: str | None = None


@dataclass(frozen=True)
class ConversationalResult:
    input_text: str
    normalized_text: str
    intent: str
    route: str
    safety_level: str
    known_command: bool
    command_id: str | None
    command_category: str | None
    command_risk: str | None
    answer_text_ru: str
    plan_steps_ru: tuple[str, ...]
    requires_confirmation: bool
    requires_network: bool
    requires_ai_provider: bool
    providers_called: bool
    network_used: bool
    command_executed: bool
    audio_started: bool
    microphone_started: bool
    tts_started: bool
    secrets_included: bool
    response_executed_as_command: bool
    safe_to_display: bool
    notes_ru: tuple[str, ...]


class SafeConversationalLoop:
    """Classify and preview conversational user text without side effects."""

    DIALOG_PREFIXES = (
        "диалог:",
        "чат:",
        "jarvis:",
        "джарвис:",
        "поговори:",
        "conversational preview:",
        "предпросмотр диалога:",
    )
    SMALL_TALK = {"привет", "здравствуй", "здравствуйте", "салам", "добрый день"}
    CAPABILITY_QUESTIONS = {
        "что ты умеешь",
        "что умеешь",
        "расскажи что ты умеешь",
        "покажи возможности",
        "возможности",
    }
    RISKY_MARKERS = (
        "удали",
        "сотри",
        "очисти диск",
        "форматируй",
        "сломай",
        "убей процесс",
        "rm -rf",
        "del ",
        "delete all",
        "стереть",
    )
    DRAFT_MARKERS = ("напиши", "составь", "подготовь текст", "письмо", "резюме", "заявление")
    RESEARCH_MARKERS = ("покажи закон", "найди закон", "покажи мне закон", "исследуй", "узнай")
    SIMPLE_ACTION_MARKERS = ("открой папку", "открой документы", "открой файл", "покажи папку")

    def __init__(self, app_service=None, command_registry: CommandRegistry | None = None):
        self.app_service = app_service
        self.command_registry = command_registry or DEFAULT_COMMAND_REGISTRY

    def status(self) -> dict[str, object]:
        return {
            "ready": True,
            "safe": True,
            "network_default": False,
            "providers_called": False,
            "command_execution_default": False,
            "audio_started": False,
            "microphone_started": False,
            "tts_started": False,
            "secrets_included": False,
            "response_executed_as_command": False,
        }

    def status_text_ru(self) -> str:
        return "\n".join(
            [
                "Conversational loop status:",
                "- foundation ready: yes",
                "- safe mode: yes",
                "- no network by default",
                "- no command execution by default",
                "- no providers called",
                "- no microphone/TTS",
                "- AI responses are not executed as commands",
                "- secrets included: no",
            ]
        )

    def capabilities_text_ru(self) -> str:
        return "\n".join(
            [
                "Разговорный режим JARVIS:",
                "Исмаил, я могу безопасно понять обычный текст и разложить его по типу задачи.",
                "- известные команды: покажу безопасный предпросмотр",
                "- простые действия: составлю план без выполнения",
                "- вопросы к AI: пока только безопасный dry-run без провайдера",
                "- тексты и письма: подготовлю план черновика",
                "- исследование и браузерные задачи: отмечу, что позже нужна явная сеть",
                "- сложные агентные задачи: разложу на шаги и остановлюсь до подтверждения",
                "- рискованные запросы: заблокирую или потребую подтверждение",
            ]
        )

    def classify(self, text: str) -> ConversationIntent:
        normalized = self._normalize(self._strip_dialog_prefix(text))
        if not normalized:
            return ConversationIntent.UNKNOWN
        if self._contains_any(normalized, self.RISKY_MARKERS):
            return ConversationIntent.RISKY_ACTION
        if normalized in self.SMALL_TALK:
            return ConversationIntent.SMALL_TALK
        if normalized in self.CAPABILITY_QUESTIONS:
            return ConversationIntent.AI_QUESTION
        if "найди" in normalized and "запусти" in normalized:
            return ConversationIntent.COMPLEX_AGENT_TASK
        if self._contains_any(normalized, self.RESEARCH_MARKERS):
            return ConversationIntent.RESEARCH_TASK
        if self._contains_any(normalized, self.SIMPLE_ACTION_MARKERS):
            return ConversationIntent.SIMPLE_ACTION
        if self._contains_any(normalized, self.DRAFT_MARKERS):
            return ConversationIntent.DRAFTING_TASK
        if self._match_registry_command(normalized) is not None:
            return ConversationIntent.KNOWN_COMMAND
        if "?" in str(text or "") or normalized.startswith(("почему", "как ", "что такое")):
            return ConversationIntent.AI_QUESTION
        return ConversationIntent.UNKNOWN

    def preview(self, text: str) -> ConversationalResult:
        return self.handle(
            ConversationalRequest(
                text=text,
                source="preview",
                allow_network=False,
                allow_command_execution=False,
                allow_risky_actions=False,
            )
        )

    def handle(self, request: ConversationalRequest) -> ConversationalResult:
        input_text = str(request.text or "").strip()
        conversational_text = self._strip_dialog_prefix(input_text)
        normalized = self._normalize(conversational_text)
        intent = self.classify(conversational_text)
        metadata = self._match_registry_command(normalized)
        route, safety = self._route_for_intent(intent)
        answer, steps, notes = self._response_for(
            intent=intent,
            text=conversational_text,
            metadata=metadata,
            allow_network=request.allow_network,
            allow_command_execution=request.allow_command_execution,
        )
        requires_network = intent in {
            ConversationIntent.RESEARCH_TASK,
            ConversationIntent.COMPLEX_AGENT_TASK,
        }
        requires_confirmation = intent == ConversationIntent.RISKY_ACTION
        if intent == ConversationIntent.SIMPLE_ACTION:
            requires_confirmation = True
        if metadata is not None:
            requires_confirmation = requires_confirmation or metadata.requires_confirmation
            requires_network = requires_network or metadata.requires_network

        return ConversationalResult(
            input_text=input_text,
            normalized_text=normalized,
            intent=intent.value,
            route=route.value,
            safety_level=safety.value,
            known_command=metadata is not None and intent == ConversationIntent.KNOWN_COMMAND,
            command_id=metadata.command_id if metadata is not None else None,
            command_category=metadata.category.value if metadata is not None else None,
            command_risk=metadata.risk_level.value if metadata is not None else None,
            answer_text_ru=self._safe_text(answer),
            plan_steps_ru=tuple(self._safe_text(step) for step in steps),
            requires_confirmation=requires_confirmation,
            requires_network=requires_network,
            requires_ai_provider=intent in {
                ConversationIntent.AI_QUESTION,
                ConversationIntent.RESEARCH_TASK,
                ConversationIntent.COMPLEX_AGENT_TASK,
            },
            providers_called=False,
            network_used=False,
            command_executed=False,
            audio_started=False,
            microphone_started=False,
            tts_started=False,
            secrets_included=False,
            response_executed_as_command=False,
            safe_to_display=True,
            notes_ru=tuple(self._safe_text(note) for note in notes),
        )

    def result_text_ru(self, result: ConversationalResult) -> str:
        lines = [
            result.answer_text_ru,
            "",
            "Безопасность:",
            f"- intent: {result.intent}",
            f"- route: {result.route}",
            f"- known command: {'yes' if result.known_command else 'no'}",
            f"- command id: {result.command_id or 'none'}",
            f"- requires confirmation: {'yes' if result.requires_confirmation else 'no'}",
            f"- requires network later: {'yes' if result.requires_network else 'no'}",
            "- providers called: no",
            "- network used: no",
            "- command executed: no",
            "- microphone/TTS started: no",
            "- no secrets",
            "- response executed as command: no",
        ]
        if result.plan_steps_ru:
            lines.insert(1, "План:\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(result.plan_steps_ru, 1)))
        return "\n".join(lines)

    def _response_for(self, intent, text, metadata, allow_network, allow_command_execution):
        if intent == ConversationIntent.SMALL_TALK:
            return (
                "Привет, Исмаил. Я на связи. Могу принять команду, помочь с текстом или разобрать задачу.",
                (),
                ("Локальный ответ без AI provider.",),
            )
        if intent == ConversationIntent.AI_QUESTION:
            return (
                "Исмаил, я понял это как вопрос к ассистенту. Сейчас отвечаю безопасно локально: могу объяснить возможности, составить план или подготовить черновик. Реальный AI-провайдер в этой задаче не вызывается.",
                (),
                ("AI provider не вызван.",),
            )
        if intent == ConversationIntent.KNOWN_COMMAND and metadata is not None:
            return (
                f"Понял как известную команду: {metadata.title_ru}. Сейчас показываю только безопасный предпросмотр; выполнение команды отдельно не запускаю.",
                (),
                ("CommandRegistry match найден.",),
            )
        if intent == ConversationIntent.DRAFTING_TASK:
            return (
                "Понял. Я могу подготовить проект текста. Сначала нужно уточнить тему, адресата, цель и тон.",
                ("Уточнить адресата и тему.", "Выбрать тон: официальный, спокойный или жёсткий.", "Собрать ключевые факты.", "Подготовить черновик после подтверждения."),
                ("Документ не создан.",),
            )
        if intent == ConversationIntent.SIMPLE_ACTION:
            return (
                "Понял как простое действие. В TASK-076 я только классифицирую действие; реальное открытие папок будет добавлено позже через безопасный action layer.",
                ("Определить точный объект действия.", "Показать план.", "В будущем выполнить только через подтверждённый безопасный слой действий."),
                ("Файлы и ОС не тронуты.",),
            )
        if intent == ConversationIntent.RESEARCH_TASK:
            return (
                "Понял как исследовательскую задачу. Сейчас сеть и браузер не запускаю; позже это должно идти через явное разрешение на поиск.",
                ("Уточнить источник или юрисдикцию.", "В будущем открыть поиск/браузер только после явного разрешения.", "Собрать источники.", "Дать краткое объяснение и ссылки.", "Не выполнять действий без подтверждения."),
                ("Network/browser не использованы.",),
            )
        if intent == ConversationIntent.COMPLEX_AGENT_TASK:
            return (
                "Понял как сложную агентную задачу: здесь смешаны поиск, выбор и действие. Сейчас я только составляю безопасный план.",
                ("Уточнить жанр, настроение и ограничения.", "Найти варианты только после явного разрешения на сеть.", "Сравнить варианты через AI после отдельного разрешения.", "Показать варианты Исмаилу.", "Запустить что-либо только после подтверждения."),
                ("Player/browser не запущены.",),
            )
        if intent == ConversationIntent.RISKY_ACTION:
            return (
                "Остановил запрос как рискованный. Я не удаляю файлы и не выполняю разрушительные действия в разговорном режиме.",
                ("Не выполнять действие.", "Попросить точное безопасное намерение.", "Для будущих опасных операций требовать отдельное подтверждение и защитный слой."),
                ("Рискованное действие заблокировано.",),
            )
        return (
            "Исмаил, я не до конца понял задачу. Напиши чуть конкретнее: это команда, вопрос, текст, поиск или действие?",
            (),
            ("Нужна конкретизация.",),
        )

    def _route_for_intent(self, intent):
        if intent == ConversationIntent.KNOWN_COMMAND:
            return ConversationRoute.COMMAND_PREVIEW, ConversationSafetyLevel.SAFE_METADATA_ONLY
        if intent == ConversationIntent.SMALL_TALK:
            return ConversationRoute.LOCAL_SMALL_TALK, ConversationSafetyLevel.SAFE_READ_ONLY
        if intent == ConversationIntent.AI_QUESTION:
            return ConversationRoute.AI_DRY_RUN_SAFE, ConversationSafetyLevel.SAFE_METADATA_ONLY
        if intent == ConversationIntent.DRAFTING_TASK:
            return ConversationRoute.DRAFT_PLAN, ConversationSafetyLevel.SAFE_METADATA_ONLY
        if intent == ConversationIntent.SIMPLE_ACTION:
            return ConversationRoute.SIMPLE_ACTION_PLAN, ConversationSafetyLevel.NEEDS_CONFIRMATION
        if intent == ConversationIntent.RESEARCH_TASK:
            return ConversationRoute.RESEARCH_PLAN, ConversationSafetyLevel.NETWORK_EXPLICIT_REQUIRED
        if intent == ConversationIntent.COMPLEX_AGENT_TASK:
            return ConversationRoute.AGENT_PLAN, ConversationSafetyLevel.NETWORK_EXPLICIT_REQUIRED
        if intent == ConversationIntent.RISKY_ACTION:
            return (
                ConversationRoute.RISKY_BLOCKED_OR_CONFIRMATION_REQUIRED,
                ConversationSafetyLevel.RISKY_BLOCKED,
            )
        return ConversationRoute.CLARIFY, ConversationSafetyLevel.SAFE_METADATA_ONLY

    def _match_registry_command(self, text: str):
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

    @classmethod
    def _strip_dialog_prefix(cls, text: str) -> str:
        raw = str(text or "").strip()
        normalized = cls._normalize(raw)
        for prefix in cls.DIALOG_PREFIXES:
            if normalized.startswith(prefix):
                return raw[len(prefix) :].strip()
        return raw

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = str(text or "").strip().lower().replace("ё", "е")
        return " ".join(normalized.split())

    @staticmethod
    def _contains_any(text: str, markers) -> bool:
        return any(marker in text for marker in markers)

    @staticmethod
    def _safe_text(text: str) -> str:
        return re.sub(
            r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+)",
            "[REDACTED]",
            str(text or ""),
        )
