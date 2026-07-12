from voice import SafeVoiceCommandAllowlist, VoiceAllowlistDecision


def test_exact_safe_command_is_allowed():
    decision = SafeVoiceCommandAllowlist().decide("статус системы")

    assert isinstance(decision, VoiceAllowlistDecision)
    assert decision.allowed is True
    assert decision.normalized_text == "статус системы"
    assert decision.canonical_command == "статус системы"
    assert decision.reason == "known_read_only_command"


def test_aliases_normalize_to_canonical_command():
    allowlist = SafeVoiceCommandAllowlist()

    assert allowlist.decide("статус").canonical_command == "статус системы"
    assert allowlist.decide("команды").canonical_command == "помощь"
    assert allowlist.decide("статус numpy").canonical_command == "проверить numpy"


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
        "установи vosk",
        "скачай модель vosk",
        "выполни powershell get-process",
        "запусти shell команду",
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


def test_allowlist_response_contains_only_safe_commands():
    response = SafeVoiceCommandAllowlist().format_read_only_commands()

    assert "статус системы" in response
    assert "помощь" in response
    assert "проверить модель vosk" in response
    assert "ожидающая голосовая команда" in response
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
