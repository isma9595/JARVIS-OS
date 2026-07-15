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
