from app import AppCommandSource, JarvisAppService
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult


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


class FakeOneShotRecognition:
    def __init__(self, result=None, error=None, reentrant_service=None):
        self.calls = 0
        self.closed = False
        self.error = error
        self.reentrant_service = reentrant_service
        self.result = result or OneShotVoskRealRecognitionResult(
            allowed=True,
            completed=True,
            blocked=False,
            recognized_text="СЃС‚Р°С‚СѓСЃ app service",
            capture_seconds=1,
        )

    def run_once(self, explicit_one_shot_requested=False):
        self.calls += 1
        assert explicit_one_shot_requested is True
        if self.reentrant_service is not None:
            self.reentrant_result = self.reentrant_service.process_one_shot_voice_request()
        if self.error is not None:
            raise self.error
        return self.result

    def close(self):
        self.closed = True


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


def test_preview_valid_russian_create_plan_is_known_planner_without_mutation():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    command = "\u0441\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d: \u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b; \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u044f\u0437\u044b\u043a"

    preview = service.preview_command(command)

    assert preview.known_command is True
    assert preview.registry_match_id == "planner.general_multi_step"
    assert preview.category == "planner"
    assert preview.app_ready is True
    assert preview.requires_network is False
    assert preview.requires_confirmation is False
    assert service.multi_step_planner.snapshot() is None
    assert processor.calls == []


def test_preview_show_execute_cancel_plan_are_known_and_read_only():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    show = service.preview_command("\u043f\u043e\u043a\u0430\u0436\u0438 \u043f\u043b\u0430\u043d")
    execute = service.preview_command("\u0432\u044b\u043f\u043e\u043b\u043d\u0438 \u043f\u043b\u0430\u043d")
    cancel = service.preview_command("\u043e\u0442\u043c\u0435\u043d\u0438 \u043f\u043b\u0430\u043d")

    for preview in (show, execute, cancel):
        assert preview.known_command is True
        assert preview.registry_match_id == "planner.general_multi_step"
        assert preview.category == "planner"
        assert preview.app_ready is True
        assert preview.requires_network is False
        assert preview.read_only is True
    assert service.multi_step_planner.snapshot() is None
    assert processor.calls == []


def test_preview_execute_plan_projects_read_only_next_step_without_mutation():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    service.set_language_preference("english")
    created = service.execute_command("create plan: system status", AppCommandSource.TEST)
    before = service.multi_step_planner.snapshot()

    preview = service.preview_command("execute plan")
    after = service.multi_step_planner.snapshot()

    assert created.plan_status == "proposed"
    assert preview.risk_level == "read_only"
    assert preview.read_only is True
    assert preview.requires_confirmation is False
    assert preview.active_plan_id == before.plan_id
    assert preview.active_plan_status == "proposed"
    assert preview.active_step_id == "step-1"
    assert preview.active_step_capability_id == "system.status"
    assert preview.active_step_name == "System status"
    assert preview.operation_id is None
    assert after.to_dict() == before.to_dict()
    assert processor.calls == []


def test_preview_execute_plan_projects_local_write_next_step_without_memory_mutation(tmp_path):
    from memory import LocalMemoryManager

    memory = LocalMemoryManager(tmp_path / "preview_memory.json")
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
    )
    service.set_language_preference("english")
    service.execute_command("create plan: remember test word north", AppCommandSource.TEST)
    before = service.multi_step_planner.snapshot()

    preview = service.preview_command("execute plan")
    after = service.multi_step_planner.snapshot()

    assert preview.risk_level == "local_write"
    assert preview.read_only is False
    assert preview.requires_confirmation is False
    assert preview.active_plan_id == before.plan_id
    assert preview.active_plan_status == "proposed"
    assert preview.active_step_id == "step-1"
    assert preview.active_step_capability_id == "memory.remember"
    assert preview.active_step_name == "Remember fact"
    assert preview.operation_id is None
    assert memory.recall_user_fact("test word").found is False
    assert after.to_dict() == before.to_dict()


def test_preview_execute_plan_projects_destructive_next_step_without_arming_confirmation(tmp_path):
    from memory import LocalMemoryManager

    memory = LocalMemoryManager(tmp_path / "preview_forget_all_memory.json")
    memory.remember_user_fact("marker", "survives")
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
    )
    service.set_language_preference("english")
    service.execute_command("create plan: forget everything you remember about me", AppCommandSource.TEST)
    before = service.multi_step_planner.snapshot()

    preview = service.preview_command("execute plan")
    after = service.multi_step_planner.snapshot()

    assert preview.risk_level == "confirmation_required"
    assert preview.read_only is False
    assert preview.requires_confirmation is True
    assert preview.active_plan_id == before.plan_id
    assert preview.active_plan_status == "proposed"
    assert preview.active_step_id == "step-1"
    assert preview.active_step_capability_id == "memory.forget_all"
    assert preview.operation_id is None
    assert after.awaiting_confirmation is False
    assert after.progress_percent == 0
    assert memory.recall_user_fact("marker").found is True
    assert after.to_dict() == before.to_dict()


def test_repeated_execute_plan_while_awaiting_confirmation_is_rejected_without_forgetting_memory(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.forget_all_calls = 0

        def forget_all_user_facts(self):
            self.forget_all_calls += 1
            return super().forget_all_user_facts()

    memory = TrackingMemoryManager(tmp_path / "repeat_execute_forget_all_memory.json")
    memory.remember_user_fact("marker", "survives")
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
    )
    service.set_language_preference("english")

    created = service.execute_command("create plan: forget everything you remember about me", AppCommandSource.TEST)
    first = service.execute_command("execute plan", AppCommandSource.TEST)
    first_snapshot = service.multi_step_planner.snapshot()
    operation_id = first.operation_id
    progress = first.progress_percent
    repeated = service.execute_command("execute plan", AppCommandSource.TEST)
    repeated_snapshot = service.multi_step_planner.snapshot()
    cancelled = service.execute_command("cancel plan", AppCommandSource.TEST)

    assert created.plan_status == "proposed"
    assert first.plan_status == "awaiting_confirmation"
    assert first.requires_confirmation is True
    assert first.awaiting_confirmation is True
    assert operation_id
    assert first_snapshot.operation_id == operation_id
    assert first_snapshot.steps[0].safe_message == "awaiting_confirmation"
    assert first_snapshot.steps[0].safe_message != "Step is pending."

    assert repeated.plan_status == "awaiting_confirmation"
    assert repeated.requires_confirmation is True
    assert repeated.awaiting_confirmation is True
    assert repeated.operation_id == operation_id
    assert repeated.executed is False
    assert repeated.error == "explicit_confirmation_required"
    assert repeated.progress_percent == progress
    assert repeated_snapshot.operation_id == operation_id
    assert repeated_snapshot.awaiting_confirmation is True
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0

    assert cancelled.plan_status == "cancelled"
    assert cancelled.operation_id == operation_id
    assert cancelled.awaiting_confirmation is False
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0


def test_preview_english_planner_commands_are_known():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    create = service.preview_command("create plan: system status; current language")
    show = service.preview_command("show current plan")
    execute = service.preview_command("execute plan")
    cancel = service.preview_command("cancel current plan")

    for preview in (create, show, execute, cancel):
        assert preview.known_command is True
        assert preview.registry_match_id == "planner.general_multi_step"
        assert preview.category == "planner"
        assert preview.app_ready is True
        assert preview.requires_network is False


def test_preview_invalid_planner_text_fails_safely_without_active_plan():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    preview = service.preview_command(
        "\u0441\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d: \u0437\u0430\u043f\u0443\u0441\u0442\u0438 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0443\u044e \u0444\u0443\u043d\u043a\u0446\u0438\u044e"
    )

    assert preview.known_command is False
    assert preview.category == "planner"
    assert preview.app_ready is False
    assert preview.requires_network is False
    assert preview.requires_confirmation is False
    assert service.multi_step_planner.snapshot() is None
    assert processor.calls == []


def test_preview_does_not_execute_capabilities_or_initialize_heavy_components():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    before = service.get_startup_profile()

    service.preview_command(
        "\u0441\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d: \u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b; \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u044f\u0437\u044b\u043a"
    )
    service.preview_command("\u0432\u044b\u043f\u043e\u043b\u043d\u0438 \u043f\u043b\u0430\u043d")
    after = service.get_startup_profile()

    assert processor.calls == []
    assert service.multi_step_planner.snapshot() is None
    assert after.deferred_components == before.deferred_components


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


def test_provider_runtime_methods_are_safe():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    secret = "dummy-test-runtime-secret"

    status_text = service.provider_runtime_status_text_ru()
    credentials_text = service.provider_runtime_credentials_text_ru()

    assert "secure provider runtime: yes" in status_text
    assert "no secrets" in credentials_text
    assert "no network" in credentials_text
    assert secret not in status_text
    assert secret not in credentials_text


def test_provider_runtime_provider_status_works_for_supported_providers():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    for provider in ("groq", "openai", "gemini", "gigachat", "ollama"):
        text = service.provider_runtime_provider_text_ru(provider)
        assert f"- provider: {provider}" in text
        assert "- no secrets" in text
        assert "- no network" in text
        assert "- no provider call" in text


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
    assert any(card.card_id == "secure_provider_runtime" for card in status_cards)
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


def test_one_shot_voice_success_forwards_recognized_text_to_execute_contract():
    processor = FakeCommandProcessor()
    recognizer = FakeOneShotRecognition()
    service = JarvisAppService(
        command_processor=processor,
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert recognizer.calls == 1
    assert processor.calls == ["СЃС‚Р°С‚СѓСЃ app service"]
    assert result.ok is True
    assert result.voice_capture_succeeded is True
    assert result.recognition_succeeded is True
    assert result.recognized_text == "СЃС‚Р°С‚СѓСЃ app service"
    assert result.text_processing_succeeded is True
    assert result.text_result is not None
    assert result.text_result.source == "test"
    assert recognizer.closed is True
    assert service.audio_lifecycle_status().one_shot_active is False


def test_one_shot_voice_runtime_language_defaults_to_ru_ru_and_vosk_ru():
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=FakeOneShotRecognition(
            OneShotVoskRealRecognitionResult(
                allowed=True,
                completed=True,
                blocked=False,
                recognized_text="статус app service",
                capture_seconds=1,
            )
        ),
    )

    settings = service.language_settings()

    assert settings["runtime_locale"] == "ru-RU"
    assert settings["command_language"] == "ru"
    assert settings["speech_recognition_language"] == "ru"
    assert settings["ui_language"] == "ru"
    assert settings["assistant_response_language"] == "ru"


def test_one_shot_voice_does_not_call_text_path_after_empty_recognition():
    processor = FakeCommandProcessor()
    recognizer = FakeOneShotRecognition(
        OneShotVoskRealRecognitionResult(
            allowed=True,
            completed=True,
            blocked=False,
            recognized_text=None,
            capture_seconds=1,
        )
    )
    service = JarvisAppService(
        command_processor=processor,
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is False
    assert result.error_code == "empty_recognition"
    assert result.voice_capture_succeeded is True
    assert result.recognition_succeeded is False
    assert processor.calls == []
    assert recognizer.closed is True


def test_one_shot_voice_blocks_without_provider_call_after_recognition_failure():
    processor = FakeCommandProcessor()
    recognizer = FakeOneShotRecognition(
        OneShotVoskRealRecognitionResult(
            allowed=False,
            completed=False,
            blocked=True,
            recognized_text=None,
            capture_seconds=0,
            reasons=["Vosk runtime unavailable"],
        )
    )
    service = JarvisAppService(
        command_processor=processor,
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is False
    assert result.error_code == "vosk_runtime_unavailable"
    assert processor.calls == []
    assert recognizer.closed is True


def test_one_shot_voice_text_processing_failure_is_serializable_and_redacted():
    class FailingProcessor(FakeCommandProcessor):
        def process(self, text):
            self.calls.append(text)
            raise RuntimeError("api key sk-test-1234567890secret failed")

    service = JarvisAppService(
        command_processor=FailingProcessor(),
        one_shot_voice_recognition=FakeOneShotRecognition(),
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)
    data = result.to_dict()
    text = result.safe_text_ru()

    assert result.ok is False
    assert result.text_processing_succeeded is False
    assert result.error_code == "text_processing_failed"
    assert data["text_result"]["error"] == "[REDACTED] failed"
    assert "sk-test-1234567890secret" not in text


def test_one_shot_voice_failure_message_is_russian_and_safe():
    class BrokenRecognizer:
        def run_once(self, explicit_one_shot_requested=False):
            raise RuntimeError("device exploded")

    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=BrokenRecognizer(),
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is False
    assert result.error_code == "one_shot_voice_failure"
    assert "Голосовой запрос безопасно завершился ошибкой" in result.user_message
    assert "Traceback" not in result.user_message


def test_one_shot_voice_empty_recognition_message_is_russian():
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=FakeOneShotRecognition(
            OneShotVoskRealRecognitionResult(
                allowed=True,
                completed=True,
                blocked=False,
                recognized_text="",
                capture_seconds=1,
            )
        ),
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is False
    assert result.error_code == "empty_recognition"
    assert "полезный текст речи не найден" in result.user_message


def test_one_shot_voice_rejects_overlapping_request_and_cleans_state():
    recognizer = FakeOneShotRecognition()
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=recognizer,
    )
    recognizer.reentrant_service = service

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is True
    assert recognizer.reentrant_result.ok is False
    assert recognizer.reentrant_result.error_code == "overlapping_one_shot_request"
    assert recognizer.closed is True
    assert service.audio_lifecycle_status().one_shot_active is False


def test_one_shot_voice_allows_repeated_request_after_failure():
    recognizer = FakeOneShotRecognition(error=RuntimeError("capture timeout"))
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=recognizer,
    )

    first = service.process_one_shot_voice_request(AppCommandSource.TEST)
    recognizer.error = None
    second = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert first.ok is False
    assert second.ok is True
    assert recognizer.calls == 2
    assert service.audio_lifecycle_status().one_shot_active is False
