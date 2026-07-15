from voice import SafeVoiceCommandAllowlist


def test_audio_lifecycle_status_capabilities_are_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    expected = {
        "статус audio lifecycle": "статус audio lifecycle",
        "статус audio": "статус audio lifecycle",
        "статус аудио": "статус audio lifecycle",
        "статус аудио цикла": "статус audio lifecycle",
        "статус голосового lifecycle": "статус audio lifecycle",
        "статус голосового цикла расширенный": "статус audio lifecycle",
        "audio lifecycle capabilities": "audio lifecycle capabilities",
        "возможности audio lifecycle": "audio lifecycle capabilities",
        "возможности аудио цикла": "audio lifecycle capabilities",
        "возможности голосового цикла": "audio lifecycle capabilities",
    }

    for command, canonical in expected.items():
        decision = allowlist.decide(command)

        assert decision.allowed is True
        assert decision.canonical_command == canonical


def test_audio_lifecycle_reset_stop_start_listening_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "audio lifecycle stop",
        "остановить audio lifecycle",
        "сбросить audio lifecycle",
        "reset audio lifecycle",
        "start audio lifecycle",
        "audio lifecycle start",
        "включи постоянное прослушивание",
        "слушай постоянно",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None


def test_provider_fallback_consensus_secure_key_import_still_not_allowlisted():
    allowlist = SafeVoiceCommandAllowlist()

    for command in (
        "groq реальный запрос: hello",
        "fallback ai запрос: hello",
        "консенсус ai: hello",
        "импортировать groq ключ из env",
        "удалить groq ключ",
        "app preview: статус audio lifecycle",
    ):
        decision = allowlist.decide(command)

        assert decision.allowed is False
        assert decision.canonical_command is None
