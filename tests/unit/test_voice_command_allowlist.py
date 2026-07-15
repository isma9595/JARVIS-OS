def test_fallback_status_commands_are_allowlisted_but_plan_and_execute_are_not():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус ai fallback execution",
        "статус ai retry",
        "статус fallback ai",
        "статус безопасного fallback",
        "статус ai fallback executor",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "статус ai fallback execution"

    for command in (
        "план ai fallback привет",
        "план ai fallback: привет",
        "fallback ai запрос привет",
        "fallback ai запрос: привет",
        "ai retry запрос привет",
        "ai retry запрос: привет",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_ai_live_verification_voice_status_and_checklist_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус ai verification",
        "статус ai live verification",
        "статус ai polish",
        "статус проверки ai",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "статус ai verification"

    for command in (
        "чеклист ai проверки",
        "чеклист проверки ai",
        "план проверки ai",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "чеклист ai проверки"


def test_ai_live_verification_runtime_and_live_checks_are_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "проверка ollama local",
        "проверка локального ai",
        "ai ollama readiness",
        "ollama readiness",
        "проверка live ai readiness",
        "проверка внешних ai",
        "ai live readiness",
        "проверка ai без ключей",
        "проверка ai privacy",
        "fallback ai запрос: обычный вопрос",
        "консенсус ai: обычный вопрос",
        "groq реальный запрос: привет",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None

from voice import SafeVoiceCommandAllowlist, VoiceAllowlistDecision


def test_exact_safe_command_is_allowed():
    decision = SafeVoiceCommandAllowlist().decide("статус системы")

    assert isinstance(decision, VoiceAllowlistDecision)
    assert decision.allowed is True
    assert decision.normalized_text == "статус системы"
    assert decision.canonical_command == "статус системы"
    assert decision.reason == "allowlist_match"


def test_aliases_normalize_to_canonical_command():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("статус").canonical_command == "статус системы"
    assert allowlist.decide("команды").canonical_command == "помощь"
    assert allowlist.decide("статус numpy").canonical_command == "проверить numpy"


def test_safe_status_system_variants_map_to_canonical_command():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус системы",
        "статус систем",
        "статус система",
        "статусе системы",
        "статусе систем",
        "статую система",
        "статую системы",
        "статуя система",
        "статуя системы",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "статус системы"


def test_safe_aliases_map_to_canonical_commands():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("помоги").canonical_command == "помощь"
    assert allowlist.decide("справка").canonical_command == "помощь"
    assert allowlist.decide("статус воска").canonical_command == "статус vosk"
    assert allowlist.decide("статус воск").canonical_command == "статус vosk"
    assert (
        allowlist.decide("проверка аудио зависимости").canonical_command
        == "проверка аудио зависимостей"
    )
    assert (
        allowlist.decide("проверить аудио зависимости").canonical_command
        == "проверка аудио зависимостей"
    )
    assert (
        allowlist.decide("проверить зависимости микрофона").canonical_command
        == "проверка аудио зависимостей"
    )
    assert (
        allowlist.decide("проверить готовность модели vosk").canonical_command
        == "проверить модель vosk"
    )
    assert allowlist.decide("выключить микрофон").canonical_command == "выключи микрофон"
    assert allowlist.decide("отключить микрофон").canonical_command == "выключи микрофон"
    assert allowlist.decide("микрофон off").canonical_command == "выключи микрофон"
    assert allowlist.decide("mic off").canonical_command == "выключи микрофон"
    assert (
        allowlist.decide("частичный режим микрофона").canonical_command
        == "частичное прослушивание"
    )
    assert (
        allowlist.decide("включить частичный режим микрофона").canonical_command
        == "частичное прослушивание"
    )
    assert allowlist.decide("mic partial").canonical_command == "частичное прослушивание"
    assert allowlist.decide("как твое имя").canonical_command == "как тебя зовут"


def test_voice_output_safety_commands_are_allowed():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("замолчи").canonical_command == "замолчи"
    assert allowlist.decide("стоп голос").canonical_command == "замолчи"
    assert allowlist.decide("снова говори").canonical_command == "снова говори"
    assert (
        allowlist.decide("не озвучивай следующий ответ").canonical_command
        == "не озвучивай следующий ответ"
    )
    assert (
        allowlist.decide("статус голосовой безопасности").canonical_command
        == "статус голосовой безопасности"
    )


def test_ai_status_and_provider_list_commands_are_allowed():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("статус ai").allowed is True
    assert allowlist.decide("статус ai").canonical_command == "статус ai"
    assert allowlist.decide("статус ии").canonical_command == "статус ai"
    assert (
        allowlist.decide("список ai провайдеров").canonical_command
        == "список ai провайдеров"
    )
    assert (
        allowlist.decide("список ии провайдеров").canonical_command
        == "список ai провайдеров"
    )


def test_ai_session_read_only_commands_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    status = allowlist.decide("статус ai сессии")
    models = allowlist.decide("список ai моделей")

    assert status.allowed is True
    assert status.canonical_command == "статус ai сессии"
    assert models.allowed is True
    assert models.canonical_command == "список ai моделей"


def test_ai_session_modifying_and_request_commands_are_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("выбрать ai provider groq").allowed is False
    assert allowlist.decide("продолжи через ту же модель привет").allowed is False


def test_ai_config_and_key_safety_voice_commands_are_allowed():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус ai конфигурации", "статус ai конфигурации"),
        ("статус ai ключей", "статус ai ключей"),
        ("безопасность ai ключей", "безопасность ai ключей"),
        ("проверить groq ключ", "проверить groq ключ"),
        ("проверить gemini ключ", "проверить gemini ключ"),
        ("проверить ключ gemini", "проверить gemini ключ"),
        ("статус gemini", "статус gemini"),
        ("статус джемини", "статус gemini"),
        ("статус gemini guard", "статус gemini guard"),
        ("лимиты gemini", "статус gemini guard"),
        ("gemini модель", "gemini модель"),
        ("статус openai", "статус openai"),
        ("проверить openai ключ", "проверить openai ключ"),
        ("проверить ключ openai", "проверить openai ключ"),
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == canonical


def test_voice_command_for_setting_keys_is_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "установить groq ключ abc123",
        "установи groq ключ abc123",
        "добавь gemini ключ abc123",
        "установить openai ключ abc123",
        "установи openai ключ abc123",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_broad_ai_voice_queries_are_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("спроси ai: привет").allowed is False
    assert allowlist.decide("ai: привет").allowed is False
    assert allowlist.decide("спроси openai: привет").allowed is False
    assert allowlist.decide("openai: привет").allowed is False
    assert allowlist.decide("openai реальный запрос: привет").allowed is False
    assert allowlist.decide("реальный openai запрос: привет").allowed is False
    assert allowlist.decide("openai one shot: hello").allowed is False
    assert allowlist.decide("спроси gemini: привет").allowed is False
    assert allowlist.decide("gemini: привет").allowed is False
    assert allowlist.decide("gemini реальный запрос: привет").allowed is False
    assert allowlist.decide("реальный gemini запрос: привет").allowed is False
    assert allowlist.decide("gemini one shot: hello").allowed is False


def test_openai_one_shot_status_is_allowlisted_but_request_is_not():
    allowlist = SafeVoiceCommandAllowlist()

    status = allowlist.decide("статус openai one shot")

    assert status.allowed is True
    assert status.canonical_command == "статус openai one shot"
    assert allowlist.decide("openai реальный запрос: привет").allowed is False
    assert allowlist.decide("реальный openai запрос: привет").allowed is False
    assert allowlist.decide("openai one shot: hello").allowed is False
    assert allowlist.decide("спроси openai: привет").allowed is False


def test_openai_guard_status_and_model_commands_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус openai guard", "статус openai guard"),
        ("статус openai cost guard", "статус openai guard"),
        ("лимиты openai", "статус openai guard"),
        ("openai модель", "openai модель"),
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == canonical


def test_openai_real_request_and_model_or_key_setting_are_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "openai реальный запрос: привет",
        "реальный openai запрос: привет",
        "openai one shot: hello",
        "установи openai модель gpt-5.6",
        "установи openai ключ abc123",
        "установи gemini модель gemini-2.5-flash",
        "установи gemini ключ abc123",
        "добавь gemini ключ abc123",
    ):
        assert allowlist.decide(command).allowed is False


def test_gemini_guard_status_and_model_commands_are_allowlisted_but_requests_are_not():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус gemini", "статус gemini"),
        ("статус джемини", "статус gemini"),
        ("проверить gemini ключ", "проверить gemini ключ"),
        ("проверить ключ gemini", "проверить gemini ключ"),
        ("статус gemini guard", "статус gemini guard"),
        ("статус gemini cost guard", "статус gemini guard"),
        ("лимиты gemini", "статус gemini guard"),
        ("gemini модель", "gemini модель"),
        ("gemini model", "gemini модель"),
    ):
        decision = allowlist.decide(command)
        assert decision.allowed is True
        assert decision.canonical_command == canonical

    for command in (
        "спроси gemini: привет",
        "gemini: привет",
        "gemini реальный запрос: привет",
        "реальный gemini запрос: привет",
        "gemini one shot: hello",
        "установи gemini ключ abc123",
        "установи gemini модель gemini-2.5-flash",
    ):
        assert allowlist.decide(command).allowed is False


def test_groq_status_key_guard_limits_and_model_commands_are_allowlisted_but_requests_are_not():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус groq", "статус groq"),
        ("статус грок", "статус groq"),
        ("статус groq request shape", "статус groq request shape"),
        ("groq request shape", "статус groq request shape"),
        ("форма groq запроса", "статус groq request shape"),
        ("проверить groq ключ", "проверить groq ключ"),
        ("проверить ключ groq", "проверить groq ключ"),
        ("статус groq guard", "статус groq guard"),
        ("статус groq cost guard", "статус groq guard"),
        ("лимиты groq", "статус groq guard"),
        ("groq модель", "groq модель"),
        ("groq model", "groq модель"),
    ):
        decision = allowlist.decide(command)
        assert decision.allowed is True
        assert decision.canonical_command == canonical

    for command in (
        "спроси groq: привет",
        "groq: привет",
        "groq реальный запрос: привет",
        "реальный groq запрос: привет",
        "groq one shot: hello",
        "установи groq ключ abc123",
        "установи groq модель llama-3.3-70b-versatile",
    ):
        assert allowlist.decide(command).allowed is False


def test_gigachat_status_key_guard_token_limits_model_and_shape_are_allowlisted_but_requests_are_not():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус gigachat", "статус gigachat"),
        ("статус гигачат", "статус gigachat"),
        ("статус сбер ai", "статус gigachat"),
        ("проверить gigachat ключ", "проверить gigachat ключ"),
        ("проверить гигачат ключ", "проверить gigachat ключ"),
        ("проверить сбер ключ", "проверить gigachat ключ"),
        ("статус gigachat guard", "статус gigachat guard"),
        ("лимиты gigachat", "статус gigachat guard"),
        ("статус gigachat token", "статус gigachat token"),
        ("статус гигачат token", "статус gigachat token"),
        ("статус сбер token", "статус gigachat token"),
        ("gigachat модель", "gigachat модель"),
        ("gigachat model", "gigachat модель"),
        ("статус gigachat request shape", "статус gigachat request shape"),
        ("gigachat request shape", "статус gigachat request shape"),
        ("форма gigachat запроса", "статус gigachat request shape"),
        ("форма гигачат запроса", "статус gigachat request shape"),
    ):
        decision = allowlist.decide(command)
        assert decision.allowed is True
        assert decision.canonical_command == canonical

    for command in (
        "спроси gigachat: привет",
        "gigachat: привет",
        "гигачат: привет",
        "спроси сбер: привет",
        "gigachat реальный запрос: привет",
        "гигачат реальный запрос: привет",
        "сбер реальный запрос: привет",
        "реальный gigachat запрос: привет",
        "gigachat one shot: hello",
        "установи gigachat ключ abc123",
        "покажи gigachat token",
        "включи gigachat provider",
    ):
        assert allowlist.decide(command).allowed is False


def test_ollama_voice_status_and_model_allowlisted_but_runtime_and_requests_are_not():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус ollama", "статус ollama"),
        ("статус олама", "статус ollama"),
        ("статус локального ai", "статус ollama"),
        ("ollama модель", "ollama модель"),
        ("олама модель", "ollama модель"),
        ("локальная ai модель", "ollama модель"),
    ):
        decision = allowlist.decide(command)
        assert decision.allowed is True
        assert decision.canonical_command == canonical

    for command in (
        "список ollama моделей",
        "ollama tags",
        "ollama реальный запрос привет",
        "ollama реальный запрос: привет",
        "локальный ai запрос привет",
        "локальный ai запрос: привет",
        "выбрать ai provider ollama",
        "ai реальный запрос привет",
    ):
        decision = allowlist.decide(command)
        assert decision.allowed is False
        assert decision.canonical_command is None


def test_language_policy_status_commands_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус ai language policy",
        "статус language policy",
        "языковая политика ai",
        "язык ai",
        "ai язык",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "статус ai language policy"


def test_consensus_status_commands_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус ai consensus",
        "статус ai консенсуса",
        "статус консенсус ai",
        "статус сравнения ai",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "статус ai consensus"


def test_consensus_real_commands_are_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "консенсус ai привет",
        "консенсус ai: привет",
        "ai консенсус: привет",
        "спроси все ai привет",
        "спроси все ai: привет",
        "сравни ответы ai: привет",
        "ai compare: hello",
        "ai consensus: hello",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False


def test_selection_policy_status_and_matrix_commands_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус ai fallback",
        "статус ai selection policy",
        "статус выбора ai",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "статус ai selection policy"

    for command in (
        "матрица ai провайдеров",
        "матрица ai моделей",
        "политика выбора ai",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "матрица ai провайдеров"


def test_selection_policy_recommendation_commands_are_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "какой ai выбрать привет",
        "какой ai выбрать: привет",
        "какую ai модель выбрать: привет",
        "какой провайдер выбрать: привет",
        "ai route привет",
        "ai route: привет",
        "ai выбрать модель: привет",
        "ai selection: hello",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_ai_privacy_status_and_matrix_voice_commands_are_allowlisted_but_checks_are_not():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус ai privacy", "статус ai privacy"),
        ("статус ai context boundary", "статус ai privacy"),
        ("статус приватности ai", "статус ai privacy"),
        ("статус контекста ai", "статус ai privacy"),
        ("политика приватности ai", "статус ai privacy"),
        ("матрица приватности ai", "матрица приватности ai"),
        ("матрица контекста ai", "матрица приватности ai"),
        ("что можно отправлять ai", "матрица приватности ai"),
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == canonical

    for command in (
        "проверить ai контекст: приватный файл",
        "проверить приватность ai: token abc",
        "можно ли отправить ai: hello",
        "ai privacy check: hello",
        "ai context check: hello",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_real_ai_requests_remain_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "groq реальный запрос hello",
        "groq реальный запрос: hello",
        "gigachat реальный запрос hello",
        "openai one shot: hello",
        "gemini one shot: hello",
        "спроси ai: hello",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_voice_interaction_info_commands_are_allowed_without_replay_execution():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("что ты сказал").canonical_command == "что ты сказал"
    assert allowlist.decide("что я сказал").canonical_command == "последнее распознавание"
    assert (
        allowlist.decide("покажи последнюю голосовую команду").canonical_command
        == "последнее распознавание"
    )
    assert allowlist.decide("объясни короче").canonical_command == "объясни короче"
    assert allowlist.decide("скажи проще").canonical_command == "скажи проще"
    assert allowlist.decide("повтори последнюю голосовую команду").allowed is False


def test_unknown_command_is_not_allowed():
    decision = SafeVoiceCommandAllowlist().decide("расскажи что-нибудь")

    assert decision.allowed is False
    assert decision.canonical_command is None
    assert decision.reason == "unknown_command"


def test_risky_command_is_not_allowed():
    decision = SafeVoiceCommandAllowlist().decide("отправь письмо")

    assert decision.allowed is False
    assert decision.reason == "risky_or_modifying_command"


def test_modifying_command_is_not_allowed():
    decision = SafeVoiceCommandAllowlist().decide("запомни купить молоко")

    assert decision.allowed is False
    assert decision.reason == "risky_or_modifying_command"


def test_install_download_and_shell_commands_are_not_allowed():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "открой браузер",
        "открой файл",
        "удали файл",
        "очисти память",
        "запомни это",
        "добавь идею купить молоко",
        "установи vosk",
        "скачай модель vosk",
        "запусти браузер",
        "выполни powershell get-process",
        "выполни powershell",
        "запусти shell команду",
        "cmd",
        "отправь письмо",
        "включи постоянное прослушивание",
    ):
        decision = allowlist.decide(command)
        assert decision.allowed is False
        assert decision.canonical_command is None


def test_normalization_handles_spaces_case_and_yo():
    allowlist = SafeVoiceCommandAllowlist()

    decision = allowlist.decide("  ТВОЁ    ИМЯ  ")

    assert decision.allowed is True
    assert decision.normalized_text == "твое имя"
    assert decision.canonical_command == "как тебя зовут"


def test_normalization_handles_duplicate_spaces_case_and_punctuation():
    decision = SafeVoiceCommandAllowlist().decide("  СТАТУС,,,    СИСТЕМ  ")

    assert decision.allowed is True
    assert decision.normalized_text == "статус систем"
    assert decision.canonical_command == "статус системы"


def test_no_broad_fuzzy_match_allows_unknown_text():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус системный",
        "статуя системная",
        "помоги удалить файл",
        "статус браузера",
        "проверить и установить зависимости",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_decision_reason_distinguishes_allowlist_match_and_explicit_alias():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("статус системы").reason == "allowlist_match"
    assert allowlist.decide("статуя система").reason == "explicit_safe_alias"


def test_allowlist_response_contains_only_safe_commands():
    response = SafeVoiceCommandAllowlist().format_read_only_commands()

    assert "статус системы" in response
    assert "Safe aliases" in response
    assert "Алиасы:" in response
    assert "статуя система" in response
    assert "помощь" in response
    assert "проверить модель vosk" in response
    assert "проверить готовность модели vosk" in response
    assert "выключить микрофон" in response
    assert "частичный режим микрофона" in response
    assert "ожидающая голосовая команда" in response
    assert "Все неизвестные и рискованные голосовые команды всё ещё требуют подтверждения" in response
    assert "fuzzy matching" in response
    assert "- запомни" not in response
    assert "удали" not in response
    assert "установи" not in response
    assert "скачай" not in response
    assert "отправь" not in response
    assert "powershell" not in response


def test_safety_notes_mention_read_only_and_no_bypass():
    decision = SafeVoiceCommandAllowlist().decide("статус системы")
    notes = " ".join(decision.safety_notes)

    assert "read-only" in notes
    assert "CommandProcessor" in notes
    assert "ActionRouter" in notes
    assert "shell" in notes


def test_command_registry_voice_status_list_and_categories_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус command registry", "статус command registry"),
        ("статус реестра команд", "статус command registry"),
        ("статус registry команд", "статус command registry"),
        ("статус capability manifest", "статус command registry"),
        ("категории команд", "категории команд"),
        ("категории jarvis", "категории команд"),
        ("реестр команд", "реестр команд"),
        ("список команд jarvis", "реестр команд"),
        ("команды jarvis", "реестр команд"),
        ("команды ai", "команды ai"),
        ("команды голос", "команды голос"),
        ("команды безопасность", "команды безопасность"),
        ("команды ollama", "команды ollama"),
        ("команды приложение", "команды приложение"),
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == canonical


def test_command_registry_search_commands_are_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "найти команду fallback",
        "найти команду: fallback",
        "поиск команды: ollama",
        "command search: privacy",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_real_provider_fallback_and_consensus_commands_still_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "openai реальный запрос: hello",
        "gemini реальный запрос: hello",
        "groq реальный запрос: hello",
        "gigachat реальный запрос: hello",
        "fallback ai запрос: hello",
        "консенсус ai: hello",
        "спроси все ai: hello",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_app_service_status_capabilities_and_list_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command, canonical in (
        ("статус app service", "статус app service"),
        ("статус jarvis app service", "статус app service"),
        ("статус сервиса приложения", "статус app service"),
        ("статус приложения jarvis", "статус app service"),
        ("app service status", "статус app service"),
        ("app service capabilities", "app service capabilities"),
        ("возможности app service", "app service capabilities"),
        ("возможности приложения jarvis", "app service capabilities"),
        ("app service manifest", "app service capabilities"),
        ("app service commands", "app service commands"),
        ("команды app service", "app service commands"),
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == canonical


def test_app_service_preview_arbitrary_text_is_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "app preview: статус ai",
        "предпросмотр команды: статус ai",
        "preview command: статус ai",
        "предварительная проверка команды: статус ai",
        "app preview: groq реальный запрос: test",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_desktop_shell_status_and_capability_commands_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "статус desktop app",
        "статус jarvis desktop",
        "статус desktop shell",
        "статус app shell",
        "статус окна jarvis",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "статус desktop app"

    for command in (
        "возможности desktop app",
        "возможности desktop shell",
        "возможности окна jarvis",
        "desktop app capabilities",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == "возможности desktop app"


def test_desktop_shell_gui_launch_and_arbitrary_execution_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "запусти desktop app",
        "запусти run_desktop.py",
        "python run_desktop.py",
        "desktop execute: статус ai",
        "app execute: статус ai",
        "app preview: статус ai",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_desktop_shell_real_provider_fallback_consensus_remain_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "groq реальный запрос: hello",
        "fallback ai запрос: hello",
        "консенсус ai: hello",
        "спроси все ai: hello",
        "проверить ai контекст: token abc",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None
