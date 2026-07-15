"""Command metadata registry for JARVIS.

This module is intentionally informational only. It does not execute commands,
read secrets, call networks, or write files.
"""

from dataclasses import dataclass
from enum import Enum
import re


class CommandCategory(Enum):
    SYSTEM = "system"
    PROFILE = "profile"
    MEMORY = "memory"
    IDEAS = "ideas"
    VOICE = "voice"
    AI = "ai"
    AI_PROVIDER = "ai_provider"
    AI_PRIVACY = "ai_privacy"
    AI_FALLBACK = "ai_fallback"
    AI_VERIFICATION = "ai_verification"
    OLLAMA = "ollama"
    SECURE_KEYS = "secure_keys"
    SAFETY = "safety"
    APP = "app"
    FILES_FUTURE = "files_future"
    DEVELOPMENT = "development"
    UNKNOWN = "unknown"


class CommandRiskLevel(Enum):
    READ_ONLY = "read_only"
    CONFIRMATION_REQUIRED = "confirmation_required"
    NETWORK_EXPLICIT = "network_explicit"
    LOCAL_RUNTIME = "local_runtime"
    SENSITIVE = "sensitive"
    DESTRUCTIVE_BLOCKED = "destructive_blocked"
    FUTURE = "future"


@dataclass(frozen=True)
class CommandMetadata:
    command_id: str
    title_ru: str
    description_ru: str
    category: CommandCategory
    aliases: tuple[str, ...]
    risk_level: CommandRiskLevel
    read_only: bool
    voice_auto_allowed: bool
    requires_confirmation: bool
    requires_network: bool
    requires_ai_key: bool
    requires_privacy_check: bool
    ui_visible: bool
    app_ready: bool
    introduced_in: str | None = None
    notes_ru: str | None = None


class CommandRegistry:
    """In-memory capability manifest for command discovery and UI planning."""

    CATEGORY_PURPOSES_RU = {
        CommandCategory.SYSTEM: "базовая справка, статус и выход",
        CommandCategory.PROFILE: "профиль пользователя и имя ассистента",
        CommandCategory.MEMORY: "локальная память",
        CommandCategory.IDEAS: "локальный список идей",
        CommandCategory.VOICE: "голосовой цикл и безопасные голосовые команды",
        CommandCategory.AI: "общие AI-команды и выбор модели",
        CommandCategory.AI_PROVIDER: "провайдеры и реальные one-shot запросы",
        CommandCategory.AI_PRIVACY: "граница приватности AI-контекста",
        CommandCategory.AI_FALLBACK: "явный fallback-план и controlled retry",
        CommandCategory.AI_VERIFICATION: "безопасная live verification диагностика",
        CommandCategory.OLLAMA: "локальный Ollama provider",
        CommandCategory.SECURE_KEYS: "защищенное хранение API-ключей без вывода секретов",
        CommandCategory.SAFETY: "безопасность выполнения и голосовые ограничения",
        CommandCategory.APP: "будущая desktop app поверхность",
        CommandCategory.FILES_FUTURE: "будущие файловые возможности",
        CommandCategory.DEVELOPMENT: "разработка и диагностика",
        CommandCategory.UNKNOWN: "нераспределенные команды",
    }

    def __init__(self, commands: tuple[CommandMetadata, ...] | None = None):
        self._commands = tuple(commands or default_command_metadata())
        self._by_id: dict[str, CommandMetadata] = {}
        self._by_alias: dict[str, CommandMetadata] = {}
        self._duplicate_aliases: tuple[str, ...] = ()
        self._validate()

    @classmethod
    def normalize_alias(cls, text: str) -> str:
        normalized = str(text or "").strip().lower().replace("ё", "е")
        normalized = re.sub(r"[^\w\s:<>.-]+", " ", normalized, flags=re.UNICODE)
        return " ".join(normalized.split())

    @property
    def commands(self) -> tuple[CommandMetadata, ...]:
        return self._commands

    @property
    def duplicate_aliases(self) -> tuple[str, ...]:
        return self._duplicate_aliases

    def _validate(self) -> None:
        duplicate_aliases = []
        for command in self._commands:
            if command.command_id in self._by_id:
                raise ValueError(f"Duplicate command_id: {command.command_id}")
            self._by_id[command.command_id] = command
            if not command.aliases:
                raise ValueError(f"Command has no aliases: {command.command_id}")
            for alias in command.aliases:
                normalized = self.normalize_alias(alias)
                if normalized in self._by_alias:
                    duplicate_aliases.append(normalized)
                    continue
                self._by_alias[normalized] = command
        self._duplicate_aliases = tuple(sorted(set(duplicate_aliases)))
        if self._duplicate_aliases:
            raise ValueError(
                "Duplicate command aliases: " + ", ".join(self._duplicate_aliases)
            )

    def find_by_alias(self, text: str) -> CommandMetadata | None:
        return self._by_alias.get(self.normalize_alias(text))

    def search(self, query: str) -> tuple[CommandMetadata, ...]:
        normalized_query = self.normalize_alias(query)
        if not normalized_query:
            return ()
        tokens = tuple(normalized_query.split())
        matches = []
        for command in self._commands:
            haystack = self.normalize_alias(
                " ".join(
                    (
                        command.command_id,
                        command.title_ru,
                        command.description_ru,
                        command.category.value,
                        command.risk_level.value,
                        " ".join(command.aliases),
                        command.notes_ru or "",
                    )
                )
            )
            if all(token in haystack for token in tokens):
                matches.append(command)
        return tuple(matches)

    def list_by_category(
        self, category: CommandCategory
    ) -> tuple[CommandMetadata, ...]:
        return tuple(command for command in self._commands if command.category == category)

    def categories(self) -> tuple[CommandCategory, ...]:
        return tuple(
            category
            for category in CommandCategory
            if any(command.category == category for command in self._commands)
        )

    def _commands_for_display(
        self, category: CommandCategory | None = None
    ) -> tuple[CommandMetadata, ...]:
        if category is not None:
            return self.list_by_category(category)

        grouped = []
        for ordered_category in self.categories():
            grouped.extend(self.list_by_category(ordered_category))
        return tuple(grouped)

    def status_text_ru(self) -> str:
        duplicate_status = "none" if not self._duplicate_aliases else ", ".join(self._duplicate_aliases)
        return "\n".join(
            [
                "Command registry status:",
                "- enabled: yes",
                "- mode: metadata foundation",
                "- execution source: CommandProcessor remains active",
                "- network: not called",
                "- disk writes: none",
                "- secrets: not used",
                f"- registry command count: {len(self._commands)}",
                f"- categories count: {len(self.categories())}",
                f"- duplicate aliases: {duplicate_status}",
                "- future app use: yes",
            ]
        )

    def categories_text_ru(self) -> str:
        lines = [
            "Command registry categories:",
            "- network: not called",
            "- disk writes: none",
        ]
        for category in self.categories():
            commands = self.list_by_category(category)
            purpose = self.CATEGORY_PURPOSES_RU.get(category, "команды")
            lines.append(f"- {category.value}: {len(commands)} command(s) - {purpose}")
        return "\n".join(lines)

    def list_text_ru(self, category: CommandCategory | None = None) -> str:
        commands = self._commands_for_display(category)
        heading = (
            f"Command registry: {category.value}"
            if category is not None
            else "Command registry manifest"
        )
        lines = [
            heading + ":",
            "- network: not called",
            "- disk writes: none",
            "- execution: metadata only",
        ]
        current_category = None
        for command in commands:
            if category is None and command.category != current_category:
                current_category = command.category
                lines.append(f"\n[{command.category.value}]")
            lines.append(
                "- "
                f"{command.title_ru} | id={command.command_id} | "
                f"risk={command.risk_level.value} | "
                f"voice_auto_allowed={'yes' if command.voice_auto_allowed else 'no'} | "
                f"app_ready={'yes' if command.app_ready else 'no'}"
            )
            lines.append(f"  aliases: {', '.join(command.aliases)}")
            if command.notes_ru:
                lines.append(f"  notes: {command.notes_ru}")
        if not commands:
            lines.append("- no commands")
        return "\n".join(lines)

    def search_text_ru(self, query: str) -> str:
        preview = self._safe_query_preview(query)
        matches = self.search(query)
        lines = [
            "Command registry search:",
            "- network: not called",
            "- disk writes: none",
            "- execution: not performed",
            f"- query preview: {preview}",
            f"- matches: {len(matches)}",
        ]
        for command in matches:
            lines.append(
                "- "
                f"{command.title_ru} | id={command.command_id} | "
                f"category={command.category.value} | "
                f"risk={command.risk_level.value} | "
                f"voice_auto_allowed={'yes' if command.voice_auto_allowed else 'no'} | "
                f"app_ready={'yes' if command.app_ready else 'no'}"
            )
            lines.append(f"  aliases: {', '.join(command.aliases)}")
        return "\n".join(lines)

    def manifest_text_ru(self) -> str:
        return self.list_text_ru()

    def coverage_text_ru(self) -> str:
        category_names = ", ".join(category.value for category in self.categories())
        return "\n".join(
            [
                "Command registry coverage:",
                "- scope: important command families, not every tiny alias",
                f"- commands: {len(self._commands)}",
                f"- categories: {category_names}",
                "- execution source: CommandProcessor remains active",
                "- network: not called",
                "- disk writes: none",
                "- secrets: not used",
            ]
        )

    @staticmethod
    def _safe_query_preview(query: str) -> str:
        text = str(query or "").strip()
        text = re.sub(r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]\s*\S+)", "[REDACTED]", text)
        if len(text) > 80:
            text = text[:77] + "..."
        return text or "<empty>"


def _meta(
    command_id: str,
    title_ru: str,
    description_ru: str,
    category: CommandCategory,
    aliases: tuple[str, ...],
    risk_level: CommandRiskLevel = CommandRiskLevel.READ_ONLY,
    read_only: bool = True,
    voice_auto_allowed: bool = False,
    requires_confirmation: bool = False,
    requires_network: bool = False,
    requires_ai_key: bool = False,
    requires_privacy_check: bool = False,
    ui_visible: bool = True,
    app_ready: bool = True,
    introduced_in: str | None = "TASK-068",
    notes_ru: str | None = None,
) -> CommandMetadata:
    return CommandMetadata(
        command_id=command_id,
        title_ru=title_ru,
        description_ru=description_ru,
        category=category,
        aliases=aliases,
        risk_level=risk_level,
        read_only=read_only,
        voice_auto_allowed=voice_auto_allowed,
        requires_confirmation=requires_confirmation,
        requires_network=requires_network,
        requires_ai_key=requires_ai_key,
        requires_privacy_check=requires_privacy_check,
        ui_visible=ui_visible,
        app_ready=app_ready,
        introduced_in=introduced_in,
        notes_ru=notes_ru,
    )


def _real_provider(
    provider: str,
    title_ru: str,
    status_aliases: tuple[str, ...],
    request_aliases: tuple[str, ...],
) -> tuple[CommandMetadata, CommandMetadata]:
    request_title_ru = f"{title_ru.removeprefix('Статус ').strip()} реальный запрос"
    return (
        _meta(
            f"ai_provider.{provider}.status",
            title_ru,
            f"Статус провайдера {provider} без сетевого запроса.",
            CommandCategory.AI_PROVIDER,
            status_aliases,
            voice_auto_allowed=True,
            notes_ru="status only; no network",
        ),
        _meta(
            f"ai_provider.{provider}.real_request",
            request_title_ru,
            f"Явный one-shot запрос к {provider}.",
            CommandCategory.AI_PROVIDER,
            request_aliases,
            risk_level=CommandRiskLevel.NETWORK_EXPLICIT,
            read_only=False,
            requires_confirmation=True,
            requires_network=True,
            requires_ai_key=True,
            requires_privacy_check=True,
            voice_auto_allowed=False,
            notes_ru="explicit only; response is not executed as command",
        ),
    )


def default_command_metadata() -> tuple[CommandMetadata, ...]:
    commands = [
        _meta("system.help", "Помощь", "Краткая справка по возможностям.", CommandCategory.SYSTEM, ("помощь", "команды", "help"), voice_auto_allowed=True),
        _meta("system.status", "Статус системы", "Локальный статус JARVIS.", CommandCategory.SYSTEM, ("статус", "статус системы"), voice_auto_allowed=True),
        _meta("system.exit", "Выход", "Завершение CLI-сессии.", CommandCategory.SYSTEM, ("выход",), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("profile.whoami", "Кто я", "Показать локальный профиль пользователя.", CommandCategory.PROFILE, ("кто я", "как меня зовут")),
        _meta("profile.assistant_name", "Имя ассистента", "Показать имя ассистента.", CommandCategory.PROFILE, ("имя ассистента", "как тебя зовут"), voice_auto_allowed=True),
        _meta("profile.assistant_name_change", "Сменить имя ассистента", "Изменить локальное имя ассистента.", CommandCategory.PROFILE, ("сменить имя ассистента", "изменить имя ассистента на <имя>"), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("profile.assistant_name_reset", "Сбросить имя ассистента", "Вернуть имя ассистента по умолчанию.", CommandCategory.PROFILE, ("сбросить имя ассистента",), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("voice.cycle_status", "Статус голосового цикла", "Сводка голосового pipeline.", CommandCategory.VOICE, ("статус голосового цикла",), voice_auto_allowed=True),
        _meta("voice.command_map", "Карта голосовых команд", "Список голосовых возможностей.", CommandCategory.VOICE, ("карта голосовых команд",), voice_auto_allowed=True),
        _meta("voice.safe_commands", "Безопасные голосовые команды", "Read-only allowlist для авто-выполнения.", CommandCategory.VOICE, ("безопасные голосовые команды",), voice_auto_allowed=True),
        _meta("voice.simulate_recognition", "Симулируй распознавание", "Текстовая симуляция распознавания.", CommandCategory.VOICE, ("симулируй распознавание: <текст>",), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("voice.pending_command", "Ожидающая голосовая команда", "Показать команду, ожидающую подтверждения.", CommandCategory.VOICE, ("ожидающая голосовая команда",), voice_auto_allowed=True),
        _meta("voice.safety_status", "Статус голосовой безопасности", "Статус голосовых safety gates.", CommandCategory.SAFETY, ("статус голосовой безопасности",), voice_auto_allowed=True),
        _meta("voice.output_status", "Статус голосового ответа", "Статус TTS/озвучки.", CommandCategory.VOICE, ("статус голосового ответа",), voice_auto_allowed=True),
        _meta("ai.status", "Статус AI", "Статус AI foundation без сети.", CommandCategory.AI, ("статус ai", "статус ии"), voice_auto_allowed=True),
        _meta("ai.provider_list", "Список AI провайдеров", "Список провайдеров без сетевых вызовов.", CommandCategory.AI, ("список ai провайдеров",), voice_auto_allowed=True),
        _meta("ai.ask_dry_run", "Спроси AI", "Dry-run/offline AI запрос.", CommandCategory.AI, ("спроси ai: <текст>",), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("ai.language_policy_status", "Статус AI language policy", "Русский-first language policy.", CommandCategory.AI, ("статус ai language policy",), voice_auto_allowed=True),
        _meta("ai.session_status", "Статус AI сессии", "Текущий provider/model pin.", CommandCategory.AI, ("статус ai сессии",), voice_auto_allowed=True),
        _meta("ai.model_list", "Список AI моделей", "Локальный список доступных моделей.", CommandCategory.AI, ("список ai моделей",), voice_auto_allowed=True),
        _meta("ai.select_provider", "Выбрать AI provider", "Ручной выбор provider.", CommandCategory.AI, ("выбрать ai provider <provider>",), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("ai.select_model", "Выбрать AI модель", "Ручной выбор модели provider.", CommandCategory.AI, ("выбрать ai модель <provider> <model>",), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("ai.session_reset", "Сбросить AI сессию", "Сбросить ручной provider/model pin.", CommandCategory.AI, ("сбросить ai сессию",), risk_level=CommandRiskLevel.CONFIRMATION_REQUIRED, read_only=False, requires_confirmation=True),
        _meta("ai.fallback_status", "Статус AI fallback", "Матрица выбора provider без сети.", CommandCategory.AI_FALLBACK, ("статус ai fallback",), voice_auto_allowed=True),
        _meta("ai.provider_matrix", "Матрица AI провайдеров", "Сравнение provider policy.", CommandCategory.AI, ("матрица ai провайдеров",), voice_auto_allowed=True),
        _meta("ai.selection_recommendation", "Какой AI выбрать", "Рекомендация provider без выполнения.", CommandCategory.AI, ("какой ai выбрать: <text>",), risk_level=CommandRiskLevel.SENSITIVE, requires_privacy_check=True),
        _meta("ai.consensus_status", "Статус AI consensus", "Статус multi-provider consensus.", CommandCategory.AI, ("статус ai consensus",), voice_auto_allowed=True),
        _meta("ai.consensus", "Консенсус AI", "Явный multi-provider запрос.", CommandCategory.AI_PROVIDER, ("консенсус ai: <text>", "спроси все ai: <text>", "сравни ответы ai: <text>"), risk_level=CommandRiskLevel.NETWORK_EXPLICIT, read_only=False, requires_confirmation=True, requires_network=True, requires_ai_key=True, requires_privacy_check=True),
        _meta("ai.privacy_status", "Статус AI privacy", "Статус границы приватности.", CommandCategory.AI_PRIVACY, ("статус ai privacy",), voice_auto_allowed=True),
        _meta("ai.privacy_matrix", "Матрица приватности AI", "Что можно отправлять разным target.", CommandCategory.AI_PRIVACY, ("матрица приватности ai",), voice_auto_allowed=True),
        _meta("ai.privacy_check", "Проверить AI контекст", "Проверить произвольный текст до отправки.", CommandCategory.AI_PRIVACY, ("проверить ai контекст: <text>", "проверить приватность ai: <text>"), risk_level=CommandRiskLevel.SENSITIVE, requires_privacy_check=True),
        _meta("ai.fallback_execution_status", "Статус AI fallback execution", "Статус controlled retry.", CommandCategory.AI_FALLBACK, ("статус ai fallback execution",), voice_auto_allowed=True),
        _meta("ai.fallback_plan", "План AI fallback", "План retry без сетевого запроса.", CommandCategory.AI_FALLBACK, ("план ai fallback: <text>",), risk_level=CommandRiskLevel.SENSITIVE, requires_privacy_check=True),
        _meta("ai.fallback_request", "Fallback AI запрос", "Явный controlled provider retry.", CommandCategory.AI_FALLBACK, ("fallback ai запрос: <text>",), risk_level=CommandRiskLevel.NETWORK_EXPLICIT, read_only=False, requires_confirmation=True, requires_network=True, requires_ai_key=True, requires_privacy_check=True),
        _meta("ai.verification_status", "Статус AI verification", "Статус live verification foundation.", CommandCategory.AI_VERIFICATION, ("статус ai verification",), voice_auto_allowed=True),
        _meta("ai.verification_checklist", "Чеклист AI проверки", "Безопасный чеклист live verification.", CommandCategory.AI_VERIFICATION, ("чеклист ai проверки",), voice_auto_allowed=True),
        _meta("ai.verification_no_keys", "Проверка AI без ключей", "No-key verification без сети.", CommandCategory.AI_VERIFICATION, ("проверка ai без ключей",), risk_level=CommandRiskLevel.SENSITIVE),
        _meta("ai.verification_privacy", "Проверка AI privacy", "Privacy verification без real provider.", CommandCategory.AI_VERIFICATION, ("проверка ai privacy",), risk_level=CommandRiskLevel.SENSITIVE, requires_privacy_check=True),
        _meta("ai.verification_live_readiness", "Проверка live AI readiness", "Инструкции для явной live проверки.", CommandCategory.AI_VERIFICATION, ("проверка live ai readiness",), risk_level=CommandRiskLevel.SENSITIVE),
        _meta("ai.verification_ollama_local", "Проверка Ollama local", "Локальная проверка Ollama runtime.", CommandCategory.OLLAMA, ("проверка ollama local",), risk_level=CommandRiskLevel.LOCAL_RUNTIME),
        _meta("ollama.status", "Статус Ollama", "Локальный status без внешней сети.", CommandCategory.OLLAMA, ("статус ollama",), voice_auto_allowed=True),
        _meta("ollama.model_list", "Список Ollama моделей", "Локальный /api/tags список моделей.", CommandCategory.OLLAMA, ("список ollama моделей",), risk_level=CommandRiskLevel.LOCAL_RUNTIME),
        _meta("ollama.real_request", "Ollama реальный запрос", "Явный localhost-only запрос.", CommandCategory.OLLAMA, ("ollama реальный запрос: <text>",), risk_level=CommandRiskLevel.LOCAL_RUNTIME, read_only=False, requires_confirmation=True, requires_privacy_check=True),
        _meta("secure_keys.status", "Статус secure keys", "Статус защищенного хранилища ключей без вывода секретов.", CommandCategory.SECURE_KEYS, ("статус secure keys", "статус key storage", "статус хранилища ключей", "статус api keys", "статус api ключей", "статус безопасного хранилища ключей"), voice_auto_allowed=True, introduced_in="TASK-071", notes_ru="status only; no secrets; no network"),
        _meta("secure_keys.list", "Список API ключей", "Список признаков наличия ключей без вывода значений.", CommandCategory.SECURE_KEYS, ("список api ключей", "список secure keys", "какие ключи сохранены", "статус ключей ai"), voice_auto_allowed=True, introduced_in="TASK-071", notes_ru="PRESENT/MISSING only; no secrets; no network"),
        _meta("secure_keys.help", "Безопасность API ключей", "Справка по безопасному хранению API ключей.", CommandCategory.SECURE_KEYS, ("безопасность api ключей", "помощь api keys", "помощь secure keys"), voice_auto_allowed=True, introduced_in="TASK-071", notes_ru="help only; do not paste keys"),
        _meta("secure_keys.import_from_env", "Импорт API ключа из env", "Импорт ключа провайдера только из переменной окружения.", CommandCategory.SECURE_KEYS, ("импортировать openai ключ из env", "импортировать gemini ключ из env", "импортировать groq ключ из env", "импортировать gigachat ключ из env", "сохранить openai ключ из env", "сохранить gemini ключ из env", "сохранить groq ключ из env", "сохранить gigachat ключ из env"), risk_level=CommandRiskLevel.SENSITIVE, read_only=False, requires_confirmation=True, requires_network=False, requires_ai_key=False, voice_auto_allowed=False, introduced_in="TASK-071", notes_ru="no raw key argument; no network validation"),
        _meta("secure_keys.delete", "Удалить API ключ", "Явное удаление сохраненного ключа провайдера.", CommandCategory.SECURE_KEYS, ("удалить openai ключ", "удалить gemini ключ", "удалить groq ключ", "удалить gigachat ключ", "удалить openai ключ из хранилища", "удалить gemini ключ из хранилища", "удалить groq ключ из хранилища", "удалить gigachat ключ из хранилища"), risk_level=CommandRiskLevel.SENSITIVE, read_only=False, requires_confirmation=True, requires_network=False, requires_ai_key=False, voice_auto_allowed=False, introduced_in="TASK-071", notes_ru="explicit delete only; no secrets printed"),
        _meta("app_service.status", "Статус App Service", "Статус app-facing service layer без сети.", CommandCategory.APP, ("статус app service", "статус jarvis app service", "статус сервиса приложения", "статус приложения jarvis", "app service status"), voice_auto_allowed=True, introduced_in="TASK-069", notes_ru="status only; no network"),
        _meta("app_service.capabilities", "Возможности App Service", "Возможности будущего UI boundary без сети.", CommandCategory.APP, ("app service capabilities", "возможности app service", "возможности приложения jarvis", "app service manifest"), voice_auto_allowed=True, introduced_in="TASK-069", notes_ru="capabilities only; no network"),
        _meta("app_service.preview", "Предпросмотр команды App Service", "Предпросмотр произвольной команды по metadata без выполнения.", CommandCategory.APP, ("app preview: <text>", "предпросмотр команды: <text>", "preview command: <text>", "предварительная проверка команды: <text>"), risk_level=CommandRiskLevel.SENSITIVE, requires_privacy_check=True, voice_auto_allowed=False, introduced_in="TASK-069", notes_ru="preview only; target command is not executed"),
        _meta("app_service.commands", "Команды App Service", "Список app-facing команд через CommandRegistry.", CommandCategory.APP, ("app service commands", "команды app service"), voice_auto_allowed=True, introduced_in="TASK-069", notes_ru="list only; no network"),
        _meta("app_contracts.status", "Статус AppService contracts", "Версия и safety-status контрактов AppService без сети.", CommandCategory.APP, ("статус app contracts", "статус app service contracts", "статус контрактов приложения", "статус контрактов appservice", "app contracts status"), voice_auto_allowed=True, introduced_in="TASK-073", notes_ru="contract status only; no secrets; no network"),
        _meta("app_contracts.manifest", "Манифест AppService contracts", "Манифест версии, status cards, command cards и категорий без выполнения.", CommandCategory.APP, ("app contracts manifest", "manifest app contracts", "манифест контрактов приложения", "app service contract manifest"), voice_auto_allowed=True, introduced_in="TASK-073", notes_ru="manifest only; no secrets; no network; no execution"),
        _meta("app_contracts.status_cards", "Карточки статуса приложения", "UI-safe status cards для будущих приложений.", CommandCategory.APP, ("app status cards", "карточки статуса приложения"), voice_auto_allowed=True, introduced_in="TASK-073", notes_ru="status cards only; no secrets; no network"),
        _meta("app_contracts.command_cards", "Карточки команд приложения", "UI-safe command cards из CommandRegistry metadata.", CommandCategory.APP, ("app command cards", "карточки команд приложения"), voice_auto_allowed=True, introduced_in="TASK-073", notes_ru="command cards only; no secrets; no network"),
        _meta("desktop_shell.status", "Статус Desktop App Shell", "Статус безопасного desktop shell prototype без сети.", CommandCategory.APP, ("статус desktop app", "статус jarvis desktop", "статус desktop shell", "статус app shell", "статус окна jarvis"), voice_auto_allowed=True, introduced_in="TASK-070", notes_ru="status only; no network; run_desktop.py is separate from run.py"),
        _meta("desktop_shell.capabilities", "Возможности Desktop App Shell", "Возможности desktop shell prototype и будущие экраны.", CommandCategory.APP, ("возможности desktop app", "возможности desktop shell", "возможности окна jarvis", "desktop app capabilities"), voice_auto_allowed=True, introduced_in="TASK-070", notes_ru="capabilities only; no network"),
        _meta("app.launch_future", "Приложение JARVIS", "Будущая desktop app команда.", CommandCategory.APP, ("приложение jarvis",), risk_level=CommandRiskLevel.FUTURE, read_only=False, app_ready=False, notes_ru="future/not implemented"),
        _meta("app.settings_future", "Настройки JARVIS", "Будущие настройки приложения.", CommandCategory.APP, ("настройки jarvis",), risk_level=CommandRiskLevel.FUTURE, read_only=False, app_ready=False, notes_ru="future/not implemented"),
        _meta("app.ai_provider_settings_future", "AI provider settings", "Будущий экран настроек provider/API keys.", CommandCategory.APP, ("ai provider settings",), risk_level=CommandRiskLevel.FUTURE, read_only=False, app_ready=False, notes_ru="future/not implemented"),
        _meta("files.future", "Файлы и документы", "Будущие file/document возможности.", CommandCategory.FILES_FUTURE, ("файлы jarvis", "документы jarvis"), risk_level=CommandRiskLevel.FUTURE, read_only=False, app_ready=False, notes_ru="future/not implemented"),
    ]
    for provider, title_ru, status_aliases, request_aliases in (
        ("openai", "Статус OpenAI", ("статус openai",), ("openai реальный запрос: <text>",)),
        ("gemini", "Статус Gemini", ("статус gemini",), ("gemini реальный запрос: <text>",)),
        ("groq", "Статус Groq", ("статус groq",), ("groq реальный запрос: <text>",)),
        ("gigachat", "Статус GigaChat", ("статус gigachat",), ("gigachat реальный запрос: <text>",)),
    ):
        commands.extend(_real_provider(provider, title_ru, status_aliases, request_aliases))
    return tuple(commands)


DEFAULT_COMMAND_REGISTRY = CommandRegistry()
