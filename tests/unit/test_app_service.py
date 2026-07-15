from app import AppCommandSource, JarvisAppService


class FakeCommandProcessor:
    def __init__(self):
        self.calls = []
        self.action_router = self.FailingActionRouter()

    class FailingActionRouter:
        def route(self, command):
            raise AssertionError("AppService must not call ActionRouter directly")

    def process(self, text):
        self.calls.append(text)
        return {"intent": "fake.intent", "response": f"processed: {text}"}


def test_app_service_status_snapshot_safe():
    snapshot = JarvisAppService(command_processor=FakeCommandProcessor()).status_snapshot()

    assert snapshot.app_service_enabled is True
    assert snapshot.execution_source == "CommandProcessor remains active"
    assert snapshot.command_registry_enabled is True
    assert snapshot.command_count > 0
    assert snapshot.categories_count > 0
    assert snapshot.ui_ready is False
    assert snapshot.installer_ready is False
    assert snapshot.secure_key_storage_ready is True
    assert snapshot.network_default is False
    assert snapshot.dry_run_default is True
    assert snapshot.privacy_boundary_active is True
    assert snapshot.fallback_explicit_only is True
    assert snapshot.consensus_explicit_only is True
    assert snapshot.voice_safety_active is True


def test_status_text_has_safe_boundaries():
    text = JarvisAppService(command_processor=FakeCommandProcessor()).status_text_ru()

    assert "network default: no" in text
    assert "dry_run default: yes" in text
    assert "no secrets" in text
    assert "no response execution" in text


def test_list_categories_and_search_use_registry():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    listing = service.list_commands()
    app_listing = service.list_commands("app")
    categories = service.categories_text_ru()

    assert "Command registry manifest" in listing
    assert "app_service.status" in app_listing
    assert "Command registry categories" in categories
    assert "app:" in categories


def test_search_commands_finds_fallback_ollama_and_app():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    assert "ai_fallback" in service.search_commands("fallback")
    assert "ollama" in service.search_commands("ollama")
    assert "app_service" in service.search_commands("app service")


def test_preview_command_known_status_command():
    preview = JarvisAppService(command_processor=FakeCommandProcessor()).preview_command(
        "статус app service"
    )

    assert preview.known_command is True
    assert preview.registry_match_id == "app_service.status"
    assert preview.category == "app"
    assert preview.risk_level == "read_only"
    assert preview.read_only is True
    assert preview.voice_auto_allowed is True
    assert preview.requires_network is False
    assert preview.app_ready is True


def test_preview_command_unknown_command_safe():
    preview = JarvisAppService(command_processor=FakeCommandProcessor()).preview_command(
        "неизвестная команда"
    )

    assert preview.known_command is False
    assert preview.registry_match_id is None
    assert preview.requires_network is False
    assert preview.voice_auto_allowed is False
    assert "не выполнял" in preview.safe_summary_ru


def test_preview_real_provider_request_marks_network_risk_and_privacy():
    preview = JarvisAppService(command_processor=FakeCommandProcessor()).preview_command(
        "groq реальный запрос: test"
    )

    assert preview.known_command is True
    assert preview.registry_match_id == "ai_provider.groq.real_request"
    assert preview.risk_level == "network_explicit"
    assert preview.requires_network is True
    assert preview.requires_ai_key is True
    assert preview.requires_privacy_check is True


def test_preview_command_does_not_execute_command_processor():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    service.preview_command("статус ai")
    service.preview_text_ru("groq реальный запрос: test")

    assert processor.calls == []


def test_conversational_status_text_ru_works():
    text = JarvisAppService(command_processor=FakeCommandProcessor()).conversational_status_text_ru()

    assert "Conversational loop status:" in text
    assert "no network by default" in text
    assert "no providers called" in text
    assert "no microphone/TTS" in text


def test_conversational_preview_text_ru_greeting_safe():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    text = service.conversational_preview_text_ru("привет")
    result = service.conversational_preview("привет")

    assert result.intent == "small_talk"
    assert "Привет, Исмаил" in text
    assert result.network_used is False
    assert result.providers_called is False
    assert result.command_executed is False
    assert processor.calls == []


def test_conversational_preview_text_ru_known_command():
    result = JarvisAppService(
        command_processor=FakeCommandProcessor()
    ).conversational_preview("статус ai")

    assert result.intent == "known_command"
    assert result.known_command is True
    assert result.command_id == "ai.status"
    assert result.command_executed is False


def test_conversational_preview_text_ru_risky_requires_confirmation_or_blocked():
    result = JarvisAppService(
        command_processor=FakeCommandProcessor()
    ).conversational_preview("удали все файлы")

    assert result.intent == "risky_action"
    assert result.requires_confirmation is True
    assert result.safety_level == "risky_blocked"
    assert result.network_used is False
    assert result.providers_called is False
    assert result.secrets_included is False


def test_execute_command_calls_command_processor_once_and_wraps_result():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_command("статус app service", AppCommandSource.TEST)

    assert processor.calls == ["статус app service"]
    assert result.ok is True
    assert result.output_text == "processed: статус app service"
    assert result.source == AppCommandSource.TEST
    assert result.registry_match_id == "app_service.status"
    assert result.executed is True
    assert result.response_executed_as_command is False


def test_execute_command_does_not_call_action_router_directly():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_command("unknown command")

    assert result.ok is True
    assert processor.calls == ["unknown command"]


def test_no_secrets_in_text_outputs():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    secret = "sk-test-1234567890secret"

    preview_text = service.preview_text_ru(f"проверить ai контекст: api key {secret}")
    execute_text = service.execute_command_text_ru("статус app service")

    assert secret not in preview_text
    assert "[REDACTED]" in preview_text
    assert "no secrets" in preview_text
    assert "no secrets" in execute_text


def test_status_and_capabilities_mention_secure_key_storage_safely():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    secret = "dummy-test-key-for-storage-only"

    status = service.status_text_ru()
    capabilities = service.capabilities_text_ru()
    snapshot = service.status_snapshot()

    assert snapshot.secure_key_storage_ready is True
    assert "secure key storage foundation: available" in status
    assert "secure key storage foundation available" in capabilities
    assert "future AI Provider Settings UI will use secure key storage" in capabilities
    assert secret not in status
    assert secret not in capabilities
    assert "no secrets" in status
    assert "no secrets" in capabilities


def test_contract_status_manifest_and_cards_work():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    status = service.contract_status()
    manifest = service.contract_manifest()
    status_cards = service.status_cards()
    command_cards = service.command_cards()

    assert status.schema_name == "jarvis.app_service.contracts"
    assert status.version == "0.1"
    assert manifest.command_cards_count == len(command_cards)
    assert status_cards
    assert any(card.card_id == "network_default" for card in status_cards)
    assert any(card.card_id == "audio_lifecycle" for card in status_cards)
    assert any(card.command_id == "app_contracts.status" for card in command_cards)


def test_audio_lifecycle_status_method_and_card_are_safe():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    status = service.audio_lifecycle_status()
    card = service.audio_status_card()
    text = service.audio_lifecycle_status_text_ru()

    assert status.lifecycle_enabled is True
    assert status.network_used is False
    assert status.audio_saved is False
    assert status.auto_listening_on_startup is False
    assert card.card_id == "audio_lifecycle"
    assert card.safe is True
    assert "network used: no" in text
    assert "audio saved: no" in text


def test_vertical_integration_report_text_is_safe_and_no_unsafe_execution():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    text = service.vertical_integration_report_text_ru()
    report = service.vertical_integration_report()

    assert report.overall_passed is True
    assert report.network_used is False
    assert report.secrets_included is False
    assert report.providers_called is False
    assert report.command_execution_used is False
    assert "network used: no" in text
    assert "secrets included: no" in text
    assert "providers called: no" in text
    assert processor.calls == []


def test_command_cards_filter_app_ai_and_secure_keys():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    app_cards = service.command_cards("app")
    ai_cards = service.command_cards("ai")
    secure_cards = service.command_cards("secure_keys")

    assert app_cards
    assert ai_cards
    assert secure_cards
    assert all(card.category == "app" for card in app_cards)
    assert all(card.category == "ai" for card in ai_cards)
    assert all(card.category == "secure_keys" for card in secure_cards)


def test_preview_contract_does_not_execute_command_processor():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    preview = service.preview_contract("app contracts status")

    assert preview.command_id == "app_contracts.status"
    assert preview.executed is False
    assert processor.calls == []


def test_execute_contract_calls_normal_execution_path_once():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_contract("app contracts status", AppCommandSource.TEST)

    assert processor.calls == ["app contracts status"]
    assert result.ok is True
    assert result.command_id == "app_contracts.status"
    assert result.response_executed_as_command is False


def test_contract_outputs_contain_no_secrets():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    secret = "sk-test-1234567890secret"

    preview = service.preview_contract(f"app contracts status api key={secret}")
    output = service.execute_contract(f"app contracts status api key={secret}")
    text = "\n".join(
        [
            service.contract_status_text_ru(),
            service.contract_manifest_text_ru(),
            service.status_cards_text_ru(),
            service.command_cards_text_ru(),
            preview.safe_text_ru(),
            output.safe_text_ru(),
        ]
    )

    assert secret not in text
