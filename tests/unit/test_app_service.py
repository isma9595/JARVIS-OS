from app import AppCommandPreview, AppCommandResult, AppCommandSource, JarvisAppService
from app.text_normalization import normalize_control_text
from core.command_processor import CommandProcessor
from core.execution_journal import ExecutionOperation, ExecutionStatus, safe_journal_metadata, utc_now_iso
from memory import LocalMemoryManager
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult
from voice.speech_synthesis_backend import SpeechSynthesisResult
from voice.voice_output_manager import VoiceOutputManager


LOCAL_TTS_STATUS_COMMAND = (
    "\u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)
LOCAL_TTS_ENABLE_COMMAND = (
    "\u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 "
    "\u0433\u043e\u043b\u043e\u0441"
)
LOCAL_TTS_TEST_COMMAND = (
    "\u0442\u0435\u0441\u0442 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)
ONE_SHOT_REAL_VOSK_COMMAND = (
    "\u0440\u0435\u0430\u043b\u044c\u043d\u043e\u0435 "
    "\u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u0432\u0430\u043d\u0438\u0435 "
    "vosk"
)
RAW_MICROPHONE_ERROR = "Error querying device -1: PaErrorCode -9999; MME error 1"
RAW_RECOGNIZER_ERROR = (
    "backend sounddevice failed at C:/Users/User/vosk/model with raw exception"
)


class FakeLocalTtsBackend:
    def __init__(self, *, available=True, fail_diagnostics=False, synthesize_success=True):
        self.available = available
        self.fail_diagnostics = fail_diagnostics
        self.synthesize_success = synthesize_success
        self.diagnostics_calls = 0
        self.synthesis_calls = []

    def get_name(self):
        return "windows_local_tts"

    def availability_diagnostics(self):
        self.diagnostics_calls += 1
        if self.fail_diagnostics:
            raise RuntimeError("local tts diagnostics failed")
        return {
            "available": self.available,
            "reason": "fake available" if self.available else "fake unavailable",
            "backend_name": self.get_name(),
            "network_used": False,
            "audio_file_saved": False,
        }

    def synthesize(self, text, mode="WINDOWS_LOCAL"):
        self.synthesis_calls.append((text, mode))
        return SpeechSynthesisResult(
            success=self.synthesize_success,
            spoken_text=text,
            backend_name=self.get_name(),
            mode=mode,
            played_audio=False,
            backend_available=True,
            error=None if self.synthesize_success else "fake synthesis failed",
        )


def make_local_tts_service(local_backend):
    voice_output = VoiceOutputManager(windows_local_backend=local_backend)
    processor = CommandProcessor(voice_output_manager=voice_output)
    return JarvisAppService(command_processor=processor), processor


class FakeCommandProcessor:
    def __init__(self):
        self.calls = []
        self.action_router = self.FailingActionRouter()

    class FailingActionRouter:
        def route(self, command):
            raise AssertionError("AppService must not call ActionRouter directly")

    def process(self, text):
        self.calls.append(text)
        if text == "\u0441\u0442\u0430\u0442\u0443\u0441 \u043c\u0438\u043a\u0440\u043e\u0444\u043e\u043d\u0430":
            return {
                "intent": "microphone.mode.status",
                "response": "\u041c\u0438\u043a\u0440\u043e\u0444\u043e\u043d \u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d.",
            }
        if text == "task096 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430":
            return {
                "intent": "unknown",
                "requires_confirmation": False,
                "response": "\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c, \u044f \u043f\u043e\u043a\u0430 \u043d\u0435 \u0443\u043c\u0435\u044e \u0432\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u044d\u0442\u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u0443, \u043d\u043e \u043c\u043e\u0433\u0443 \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0435\u0451 \u043a\u0430\u043a \u0438\u0434\u0435\u044e \u0434\u043b\u044f \u0431\u0443\u0434\u0443\u0449\u0435\u0433\u043e.",
            }
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


class FakePlannerService:
    def __init__(self):
        self.preview_calls = []
        self.handle_calls = []

    def preview_command(self, input_text, normalized_text):
        self.preview_calls.append((input_text, normalized_text))
        if input_text in {"create plan: system status", "show plan", "execute plan", "cancel plan"}:
            return AppCommandPreview(
                input_text=input_text,
                normalized_text=normalized_text,
                registry_match_id="planner.general_multi_step",
                title_ru="General multi-step planner",
                category="planner",
                risk_level="read_only",
                read_only=True,
                voice_auto_allowed=False,
                requires_confirmation=False,
                requires_network=False,
                requires_ai_key=False,
                requires_privacy_check=False,
                app_ready=True,
                known_command=True,
                safe_summary_ru="fake planner preview",
                active_plan_id="plan-fake",
                active_plan_status="proposed",
                active_step_id="step-1",
                active_step_capability_id="system.status",
                active_step_name="System status",
                operation_id=None,
            )
        return None

    def handle_command(self, input_text, source, *, idempotency_key):
        self.handle_calls.append((input_text, source, idempotency_key))
        if input_text in {"create plan: system status", "show plan", "execute plan", "cancel plan"}:
            return AppCommandResult(
                ok=True,
                input_text=input_text,
                output_text=f"fake planner handled: {input_text}",
                source=source,
                registry_match_id="planner.general_multi_step",
                category="planner",
                risk_level="planner_controlled",
                executed=input_text == "execute plan",
                requires_confirmation=False,
                network_may_be_used=False,
                response_executed_as_command=False,
                error=None,
                operation_id="op-fake",
                operation_status="succeeded",
                workflow_id="general_multi_step_plan",
                workflow_status="succeeded",
                current_step_id=None,
                completed_steps=("step-1",),
                total_steps=1,
                progress_percent=100,
                plan_id="plan-fake",
                plan_status="succeeded",
                plan_step_count=1,
            )
        return None


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


def assert_local_tts_result(
    result,
    *,
    ok,
    command_id,
    risk_level,
    operation_status,
    error=None,
):
    assert result.ok is ok
    assert result.registry_match_id == command_id
    assert result.category == "voice"
    assert result.risk_level == risk_level
    assert result.executed is True
    assert result.requires_confirmation is False
    assert result.network_may_be_used is False
    assert result.response_executed_as_command is False
    assert result.operation_id
    assert result.operation_status == operation_status
    assert result.error == error
    assert result.awaiting_confirmation is False


def test_local_tts_preview_remains_side_effect_free_and_unknown():
    backend = FakeLocalTtsBackend(available=True)
    service, processor = make_local_tts_service(backend)

    status = service.preview_command(LOCAL_TTS_STATUS_COMMAND)
    enable = service.preview_command(LOCAL_TTS_ENABLE_COMMAND)
    local_test = service.preview_command(LOCAL_TTS_TEST_COMMAND)

    for preview in (status, enable, local_test):
        assert preview.known_command is False
        assert preview.registry_match_id is None
        assert preview.category is None
        assert preview.risk_level is None
        assert preview.requires_confirmation is True
        assert preview.operation_id is None
    assert backend.diagnostics_calls == 0
    assert backend.synthesis_calls == []
    assert processor.voice_output_manager.mode == "OFF"
    assert service.recent_execution_operations(None) == ()
    assert service.execution_history().entries == ()


def test_execution_history_empty_journal_returns_safe_empty_result():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    result = service.execution_history()

    assert result.ok is True
    assert result.entries == ()
    assert result.empty is True
    assert result.limit == service.DEFAULT_EXECUTION_HISTORY_LIMIT
    assert "no entries" in result.safe_text_ru()


def test_execution_history_returns_recent_entries_newest_first_and_detached(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "history_memory.json")
    )

    first = service.execute_command("remember that history first is north", AppCommandSource.TEST)
    second = service.execute_command("forget history first", AppCommandSource.TEST)
    history = service.execution_history(limit=10)

    assert history.ok is True
    assert [entry.entry_id for entry in history.entries[:2]] == [
        second.operation_id,
        first.operation_id,
    ]
    assert history.entries[0].status == "succeeded"
    assert history.entries[0].succeeded is True
    assert history.entries[0].metadata
    assert isinstance(history.entries[0].metadata, tuple)
    assert all(isinstance(item, tuple) for item in history.entries[0].metadata)


def test_execution_history_enforces_default_and_maximum_limits(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "history_limit_memory.json")
    )
    for index in range(3):
        service.execute_command(f"remember that history limit {index} is value", AppCommandSource.TEST)

    default_history = service.execution_history()
    max_history = service.execution_history(limit=999)
    zero_history = service.execution_history(limit=0)
    invalid_history = service.execution_history(limit="not-a-number")

    assert default_history.limit == service.DEFAULT_EXECUTION_HISTORY_LIMIT
    assert max_history.limit == service.MAX_EXECUTION_HISTORY_LIMIT
    assert zero_history.limit == 1
    assert invalid_history.limit == service.DEFAULT_EXECUTION_HISTORY_LIMIT
    assert len(zero_history.entries) == 1


def test_execution_history_projects_missing_optional_fields_safely():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    now = utc_now_iso()
    operation = ExecutionOperation(
        operation_id="op-history-missing",
        idempotency_key="idem-history-missing",
        source="test",
        request_fingerprint="fp-history-missing",
        status=ExecutionStatus.CREATED,
        created_at=now,
        updated_at=now,
        command_id=None,
        action_id=None,
        safe_result_summary=None,
        safe_error_code=None,
        metadata=safe_journal_metadata({"unexpected": object()}),
    )
    service.execution_coordinator.journal.add(operation)

    entry = service.execution_history(limit=1).entries[0]

    assert entry.entry_id == "op-history-missing"
    assert entry.command_id is None
    assert entry.action_id is None
    assert entry.operation_type == "operation"
    assert entry.request_summary == "No request summary available."
    assert "Execution history entry:" in entry.details_text()


def test_execution_history_sanitizes_internal_failure_details():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    now = utc_now_iso()
    operation = ExecutionOperation(
        operation_id="op-history-secret",
        idempotency_key="idem-history-secret",
        source="test",
        request_fingerprint="fp-history-secret",
        status=ExecutionStatus.FAILED,
        created_at=now,
        updated_at=now,
        command_id="voice.test",
        safe_result_summary="RuntimeError backend failed at C:/Users/User/device.txt",
        safe_error_code="PaErrorCode -9999 MME error 1 at C:/Users/User/device.txt",
        metadata=safe_journal_metadata(
            {
                "input_preview": "api key sk-test-1234567890secret at C:/Users/User/file.txt",
                "backend": "sounddevice",
                "token": "sk-test-1234567890secret",
            }
        ),
    )
    service.execution_coordinator.journal.add(operation)

    text = service.execution_history(limit=1).entries[0].details_text()

    assert "sk-test-1234567890secret" not in text
    assert "C:/Users/User" not in text
    assert "PaErrorCode" not in text
    assert "MME error" not in text
    assert "sounddevice" not in text
    assert "RuntimeError" not in text


def test_execution_history_handles_journal_access_failure_safely():
    class BrokenCoordinator:
        def recent_operations(self, limit=None):
            raise RuntimeError("Traceback backend C:/Users/User/raw.log")

    service = JarvisAppService(command_processor=FakeCommandProcessor())
    service.execution_coordinator = BrokenCoordinator()

    result = service.execution_history()

    assert result.ok is False
    assert result.entries == ()
    assert result.error == "execution_history_unavailable"
    assert "Traceback" not in result.safe_text_ru()
    assert "C:/Users/User" not in result.safe_text_ru()


def test_local_tts_diagnostics_success_projects_voice_metadata():
    backend = FakeLocalTtsBackend(available=True)
    service, _processor = make_local_tts_service(backend)

    result = service.execute_command(LOCAL_TTS_STATUS_COMMAND, AppCommandSource.TEST)

    assert_local_tts_result(
        result,
        ok=True,
        command_id="voice.output.local.status",
        risk_level="read_only",
        operation_status="succeeded",
    )
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_local_tts_diagnostics_failure_projects_failed_voice_metadata():
    backend = FakeLocalTtsBackend(available=True, fail_diagnostics=True)
    service, _processor = make_local_tts_service(backend)

    result = service.execute_command(LOCAL_TTS_STATUS_COMMAND, AppCommandSource.TEST)

    assert result.ok is False
    assert result.registry_match_id == "voice.output.local.status"
    assert result.category == "voice"
    assert result.risk_level == "read_only"
    assert result.executed is False
    assert result.requires_confirmation is False
    assert result.network_may_be_used is False
    assert result.operation_id
    assert result.operation_status == "failed"
    assert result.error == "local tts diagnostics failed"
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_local_tts_enable_success_projects_local_runtime_metadata():
    backend = FakeLocalTtsBackend(available=True)
    service, processor = make_local_tts_service(backend)

    result = service.execute_command(LOCAL_TTS_ENABLE_COMMAND, AppCommandSource.TEST)

    assert_local_tts_result(
        result,
        ok=True,
        command_id="voice.output.windows_local.enable",
        risk_level="local_runtime",
        operation_status="succeeded",
    )
    assert processor.voice_output_manager.mode == "WINDOWS_LOCAL"
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_local_tts_enable_unavailable_projects_failed_voice_metadata():
    backend = FakeLocalTtsBackend(available=False)
    service, processor = make_local_tts_service(backend)

    result = service.execute_command(LOCAL_TTS_ENABLE_COMMAND, AppCommandSource.TEST)

    assert_local_tts_result(
        result,
        ok=False,
        command_id="voice.output.windows_local.enable",
        risk_level="local_runtime",
        operation_status="failed",
        error="voice.output.windows_local.unavailable",
    )
    assert processor.voice_output_manager.mode == "OFF"
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_local_tts_test_before_enable_projects_failed_voice_metadata():
    backend = FakeLocalTtsBackend(available=True)
    service, _processor = make_local_tts_service(backend)

    result = service.execute_command(LOCAL_TTS_TEST_COMMAND, AppCommandSource.TEST)

    assert_local_tts_result(
        result,
        ok=False,
        command_id="voice.output.local_test.not_enabled",
        risk_level="local_runtime",
        operation_status="failed",
        error="voice.output.local_test.not_enabled",
    )
    assert backend.diagnostics_calls == 0
    assert backend.synthesis_calls == []


def test_local_tts_test_after_enable_uses_fake_backend_and_redacted_metadata():
    backend = FakeLocalTtsBackend(available=True)
    service, _processor = make_local_tts_service(backend)
    service.execute_command(LOCAL_TTS_ENABLE_COMMAND, AppCommandSource.TEST)

    result = service.execute_command(LOCAL_TTS_TEST_COMMAND, AppCommandSource.TEST)

    assert_local_tts_result(
        result,
        ok=True,
        command_id="voice.output.spoken",
        risk_level="local_runtime",
        operation_status="succeeded",
    )
    assert len(backend.synthesis_calls) == 1
    spoken_text, mode = backend.synthesis_calls[0]
    assert spoken_text
    assert mode == "WINDOWS_LOCAL"
    operation = service.recent_execution_operations(1)[0]
    metadata_values = " ".join(str(value) for value in operation["metadata"].values())
    assert spoken_text not in metadata_values
    assert "windows_local_tts" not in metadata_values


def test_local_tts_test_after_enable_failure_projects_failed_voice_metadata():
    backend = FakeLocalTtsBackend(available=True, synthesize_success=False)
    service, _processor = make_local_tts_service(backend)
    service.execute_command(LOCAL_TTS_ENABLE_COMMAND, AppCommandSource.TEST)

    result = service.execute_command(LOCAL_TTS_TEST_COMMAND, AppCommandSource.TEST)

    assert_local_tts_result(
        result,
        ok=False,
        command_id="voice.output.spoken",
        risk_level="local_runtime",
        operation_status="failed",
        error="voice.output.local_test.failed",
    )
    assert len(backend.synthesis_calls) == 1


def test_ordinary_speech_output_is_not_relabelled_as_local_tts():
    backend = FakeLocalTtsBackend(available=True)
    service, _processor = make_local_tts_service(backend)
    service.execute_command(LOCAL_TTS_ENABLE_COMMAND, AppCommandSource.TEST)

    result = service.execute_command(
        "\u0441\u043a\u0430\u0436\u0438: "
        "\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 "
        "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
        "\u0433\u043e\u043b\u043e\u0441\u0430",
        AppCommandSource.TEST,
    )

    assert result.registry_match_id is None
    assert result.category is None
    assert result.risk_level is None
    assert result.requires_confirmation is True
    assert result.operation_status == "succeeded"
    assert len(backend.synthesis_calls) == 1


def test_unknown_preview_metadata_is_not_reused_for_known_local_tts_execute():
    backend = FakeLocalTtsBackend(available=True)
    service, _processor = make_local_tts_service(backend)

    preview = service.preview_command(LOCAL_TTS_STATUS_COMMAND)
    result = service.execute_command(LOCAL_TTS_STATUS_COMMAND, AppCommandSource.TEST)

    assert preview.known_command is False
    assert preview.requires_confirmation is True
    assert result.registry_match_id == "voice.output.local.status"
    assert result.category == "voice"
    assert result.requires_confirmation is False


def test_unrelated_unknown_command_keeps_existing_completed_unknown_contract():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    command = (
        "task096 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f "
        "\u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0430\u044f "
        "\u043a\u043e\u043c\u0430\u043d\u0434\u0430"
    )

    result = service.execute_command(command, AppCommandSource.TEST)

    assert result.registry_match_id is None
    assert result.category is None
    assert result.risk_level is None
    assert result.executed is True
    assert result.requires_confirmation is False
    assert result.operation_status == "succeeded"


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


def assert_memory_preview_contract(
    service,
    preview,
    *,
    command_id,
    risk,
    read_only,
    requires_confirmation=False,
):
    assert preview.known_command is True
    assert preview.registry_match_id == command_id
    assert preview.category == "memory"
    assert preview.risk_level == risk
    assert preview.read_only is read_only
    assert preview.requires_confirmation is requires_confirmation
    assert preview.requires_network is False
    assert preview.requires_ai_key is False
    assert preview.requires_privacy_check is False
    assert preview.operation_id is None
    assert service.recent_execution_operations(None) == ()


def test_preview_memory_remember_projects_metadata_without_mutation(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.remember_calls = 0
            self.recall_calls = 0
            self.forget_calls = 0

        def remember_user_fact(self, key, value, *, language_code="ru-RU"):
            self.remember_calls += 1
            return super().remember_user_fact(key, value, language_code=language_code)

        def recall_user_fact(self, key):
            self.recall_calls += 1
            return super().recall_user_fact(key)

        def forget_user_fact(self, key):
            self.forget_calls += 1
            return super().forget_user_fact(key)

    memory = TrackingMemoryManager(tmp_path / "preview_memory_remember.json")
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    preview = service.preview_command("remember that audit091key is north")

    assert_memory_preview_contract(
        service,
        preview,
        command_id="memory.remember",
        risk="local_write",
        read_only=False,
    )
    assert memory.remember_calls == 0
    assert memory.recall_user_fact("audit091key").found is False
    assert memory.recall_calls == 1
    assert memory.forget_calls == 0
    assert service._pending_memory_forget_all is None


def test_preview_memory_recall_projects_metadata_without_retrieving_value(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.recall_calls = 0
            self.forget_calls = 0
            self.remember_calls = 0

        def remember_user_fact(self, key, value, *, language_code="ru-RU"):
            self.remember_calls += 1
            return super().remember_user_fact(key, value, language_code=language_code)

        def recall_user_fact(self, key):
            self.recall_calls += 1
            return super().recall_user_fact(key)

        def forget_user_fact(self, key):
            self.forget_calls += 1
            return super().forget_user_fact(key)

    memory = TrackingMemoryManager(tmp_path / "preview_memory_recall.json")
    memory.remember_user_fact("audit091key", "north")
    memory.recall_calls = 0
    memory.remember_calls = 0
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    preview = service.preview_command("what do you remember about audit091key")

    assert_memory_preview_contract(
        service,
        preview,
        command_id="memory.recall",
        risk="read_only",
        read_only=True,
    )
    assert memory.recall_calls == 0
    assert memory.remember_calls == 0
    assert memory.forget_calls == 0
    assert service._pending_memory_forget_all is None


def test_preview_memory_forget_projects_metadata_without_deletion(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.forget_calls = 0
            self.remember_calls = 0

        def remember_user_fact(self, key, value, *, language_code="ru-RU"):
            self.remember_calls += 1
            return super().remember_user_fact(key, value, language_code=language_code)

        def forget_user_fact(self, key):
            self.forget_calls += 1
            return super().forget_user_fact(key)

    memory = TrackingMemoryManager(tmp_path / "preview_memory_forget.json")
    memory.remember_user_fact("audit091key", "north")
    memory.remember_calls = 0
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    preview = service.preview_command("forget audit091key")

    assert_memory_preview_contract(
        service,
        preview,
        command_id="memory.forget",
        risk="local_write",
        read_only=False,
    )
    assert memory.forget_calls == 0
    assert memory.remember_calls == 0
    assert memory.recall_user_fact("audit091key").value == "north"
    assert service._pending_memory_forget_all is None


def test_preview_memory_forget_all_remains_confirmation_required_and_non_mutating(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.forget_all_calls = 0

        def forget_all_user_facts(self):
            self.forget_all_calls += 1
            return super().forget_all_user_facts()

    memory = TrackingMemoryManager(tmp_path / "preview_memory_forget_all.json")
    memory.remember_user_fact("marker", "survives")
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    preview = service.preview_command("forget everything you remember about me")

    assert_memory_preview_contract(
        service,
        preview,
        command_id="memory.forget_all",
        risk="confirmation_required",
        read_only=False,
        requires_confirmation=True,
    )
    assert memory.forget_all_calls == 0
    assert memory.recall_user_fact("marker").value == "survives"
    assert service._pending_memory_forget_all is None


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


def test_direct_language_set_uses_local_write_operation_metadata(tmp_path):
    from language.language_manager import ApplicationLanguageManager
    from users.user_profile import UserProfileManager

    profile = UserProfileManager(tmp_path / "language_profile.json")
    language = ApplicationLanguageManager.from_profile_manager(profile)
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        language_manager=language,
    )

    preview = service.preview_command("language English")
    result = service.execute_command("language English", AppCommandSource.TEST)
    operation = service.recent_execution_operations(1)[0]

    assert preview.registry_match_id == "profile.language.set"
    assert preview.category == "profile"
    assert preview.read_only is False
    assert preview.requires_confirmation is False
    assert result.registry_match_id == "profile.language.set"
    assert result.category == "profile"
    assert result.risk_level == "local_write"
    assert result.executed is True
    assert result.requires_confirmation is False
    assert result.operation_id == operation["operation_id"]
    assert result.operation_status == "succeeded"
    assert operation["command_id"] == "profile.language.set"
    assert operation["status"] == "succeeded"
    assert operation["metadata"]["category"] == "profile"
    assert operation["metadata"]["risk_level"] == "local_write"
    assert operation["metadata"]["requires_confirmation"] == "no"
    assert operation["metadata"]["network_may_be_used"] == "no"
    assert language.get_preference().language_code == "en-US"


def test_direct_memory_write_and_delete_use_local_write_operation_metadata(tmp_path):
    from memory import LocalMemoryManager

    memory = LocalMemoryManager(tmp_path / "direct_memory.json")
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
    )

    remember = service.execute_command(
        "remember that task096marker is west",
        AppCommandSource.TEST,
    )
    remember_operation = service.recent_execution_operations(1)[0]
    forget = service.execute_command("forget task096marker", AppCommandSource.TEST)
    forget_operation = service.recent_execution_operations(1)[0]

    assert remember.registry_match_id == "memory.remember"
    assert remember.category == "memory"
    assert remember.risk_level == "local_write"
    assert remember.executed is True
    assert remember.operation_id == remember_operation["operation_id"]
    assert remember.operation_status == "succeeded"
    assert remember_operation["command_id"] == "memory.remember"
    assert remember_operation["metadata"]["risk_level"] == "local_write"
    assert remember_operation["metadata"]["input_preview"] == "memory.remember [REDACTED]"
    assert remember_operation["metadata"]["requires_confirmation"] == "no"
    assert remember_operation["metadata"]["network_may_be_used"] == "no"

    assert forget.registry_match_id == "memory.forget"
    assert forget.category == "memory"
    assert forget.risk_level == "local_write"
    assert forget.executed is True
    assert forget.operation_id == forget_operation["operation_id"]
    assert forget.operation_status == "succeeded"
    assert forget_operation["command_id"] == "memory.forget"
    assert forget_operation["metadata"]["risk_level"] == "local_write"
    assert forget_operation["metadata"]["input_preview"] == "memory.forget [REDACTED]"
    assert memory.recall_user_fact("task096marker").found is False


def test_completed_microphone_status_projects_no_confirmation_without_side_effects(tmp_path):
    from memory import LocalMemoryManager

    processor = FakeCommandProcessor()
    memory = LocalMemoryManager(tmp_path / "microphone_status_memory.json")
    service = JarvisAppService(command_processor=processor, memory_manager=memory)
    command = "\u0441\u0442\u0430\u0442\u0443\u0441 \u043c\u0438\u043a\u0440\u043e\u0444\u043e\u043d\u0430"

    preview = service.preview_command(command)
    result = service.execute_command(command, AppCommandSource.TEST)
    operation = service.recent_execution_operations(1)[0]

    assert preview.registry_match_id is None
    assert preview.category is None
    assert preview.risk_level is None
    assert result.registry_match_id is None
    assert result.category is None
    assert result.risk_level is None
    assert result.executed is True
    assert result.operation_status == "succeeded"
    assert result.awaiting_confirmation is False
    assert result.requires_confirmation is False
    assert result.policy_decision.requires_confirmation is False
    assert operation["status"] == "succeeded"
    assert processor.calls == [command]
    assert memory.recall_user_fact("task096marker").found is False


def test_completed_unknown_safe_fallback_projects_no_confirmation_without_side_effects(tmp_path):
    from memory import LocalMemoryManager

    processor = FakeCommandProcessor()
    memory = LocalMemoryManager(tmp_path / "unknown_fallback_memory.json")
    service = JarvisAppService(command_processor=processor, memory_manager=memory)
    command = "task096 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430"

    preview = service.preview_command(command)
    result = service.execute_command(command, AppCommandSource.TEST)
    operation = service.recent_execution_operations(1)[0]

    assert preview.registry_match_id is None
    assert preview.category is None
    assert preview.risk_level is None
    assert result.registry_match_id is None
    assert result.category is None
    assert result.risk_level is None
    assert result.executed is True
    assert result.operation_status == "succeeded"
    assert result.awaiting_confirmation is False
    assert result.requires_confirmation is False
    assert result.policy_decision.requires_confirmation is False
    assert operation["status"] == "succeeded"
    assert processor.calls == [command]
    assert memory.recall_user_fact("task096marker").found is False


def test_direct_memory_exact_duplicate_registers_before_mutation_and_suppresses_second(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path, events):
            super().__init__(path)
            self.events = events
            self.remember_calls = 0

        def remember_user_fact(self, key, value, *, language_code="ru-RU"):
            self.events.append(("mutate", len(service.recent_execution_operations(None))))
            self.remember_calls += 1
            return super().remember_user_fact(key, value, language_code=language_code)

    events = []
    memory = TrackingMemoryManager(tmp_path / "duplicate_memory.json", events)
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    first = service.execute_command(
        "remember that task096 duplicate key is first",
        AppCommandSource.TEST,
        idempotency_key="task096-memory-duplicate",
    )
    second = service.execute_command(
        "remember that task096 duplicate key is first",
        AppCommandSource.TEST,
        idempotency_key="task096-memory-duplicate",
    )
    operations = service.recent_execution_operations(None)

    assert memory.remember_calls == 1
    assert events == [("mutate", 1)]
    assert first.operation_id == second.operation_id
    assert second.duplicate_suppressed is True
    assert len(operations) == 1
    assert operations[0]["duplicate_suppressed"] is True
    assert operations[0]["status"] == "succeeded"


def test_direct_language_exact_duplicate_registers_before_mutation_and_suppresses_second(tmp_path):
    from language.language_manager import ApplicationLanguageManager
    from users.user_profile import UserProfileManager

    class TrackingLanguageManager(ApplicationLanguageManager):
        def __init__(self, profile_manager, events):
            super().__init__(profile_manager=profile_manager)
            self.events = events
            self.set_calls = 0

        def set_preference(self, language_code):
            self.events.append(("mutate", len(service.recent_execution_operations(None))))
            self.set_calls += 1
            return super().set_preference(language_code)

    events = []
    profile = UserProfileManager(tmp_path / "duplicate_language.json")
    language = TrackingLanguageManager(profile, events)
    service = JarvisAppService(command_processor=FakeCommandProcessor(), language_manager=language)

    first = service.execute_command(
        "language English",
        AppCommandSource.TEST,
        idempotency_key="task096-language-duplicate",
    )
    second = service.execute_command(
        "language English",
        AppCommandSource.TEST,
        idempotency_key="task096-language-duplicate",
    )

    assert language.set_calls == 1
    assert events == [("mutate", 1)]
    assert first.operation_id == second.operation_id
    assert second.duplicate_suppressed is True
    assert len(service.recent_execution_operations(None)) == 1
    assert language.get_preference().language_code == "en-US"


def test_direct_memory_idempotency_conflict_denies_without_second_mutation(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.remember_calls = 0

        def remember_user_fact(self, key, value, *, language_code="ru-RU"):
            self.remember_calls += 1
            return super().remember_user_fact(key, value, language_code=language_code)

    memory = TrackingMemoryManager(tmp_path / "conflict_memory.json")
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    first = service.execute_command(
        "remember that task096 conflict key is first",
        AppCommandSource.TEST,
        idempotency_key="task096-memory-conflict",
    )
    second = service.execute_command(
        "remember that task096 conflict key is second",
        AppCommandSource.TEST,
        idempotency_key="task096-memory-conflict",
    )

    assert first.operation_status == "succeeded"
    assert second.operation_status == "denied"
    assert second.error == "idempotency_conflict"
    assert memory.remember_calls == 1
    assert memory.recall_user_fact("task096 conflict key").value == "first"
    assert len(service.recent_execution_operations(None)) == 2


def test_direct_language_idempotency_conflict_denies_without_second_mutation(tmp_path):
    from language.language_manager import ApplicationLanguageManager
    from users.user_profile import UserProfileManager

    class TrackingLanguageManager(ApplicationLanguageManager):
        def __init__(self, profile_manager):
            super().__init__(profile_manager=profile_manager)
            self.set_calls = 0

        def set_preference(self, language_code):
            self.set_calls += 1
            return super().set_preference(language_code)

    profile = UserProfileManager(tmp_path / "conflict_language.json")
    language = TrackingLanguageManager(profile)
    service = JarvisAppService(command_processor=FakeCommandProcessor(), language_manager=language)

    first = service.execute_command(
        "language English",
        AppCommandSource.TEST,
        idempotency_key="task096-language-conflict",
    )
    second = service.execute_command(
        "reset language",
        AppCommandSource.TEST,
        idempotency_key="task096-language-conflict",
    )

    assert first.operation_status == "succeeded"
    assert second.operation_status == "denied"
    assert second.error == "idempotency_conflict"
    assert language.set_calls == 1
    assert language.get_preference().language_code == "en-US"


def test_direct_state_registration_failure_leaves_memory_and_language_unchanged(tmp_path):
    from language.language_manager import ApplicationLanguageManager
    from memory import LocalMemoryManager
    from users.user_profile import UserProfileManager

    class FailingCoordinator:
        def create_request_fingerprint(self, **_kwargs):
            return "sha256:failing"

        def register(self, **_kwargs):
            raise RuntimeError("coordinator unavailable")

    memory = LocalMemoryManager(tmp_path / "registration_failure_memory.json")
    language = ApplicationLanguageManager.from_profile_manager(
        UserProfileManager(tmp_path / "registration_failure_language.json")
    )
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
        language_manager=language,
    )
    service.execution_coordinator = FailingCoordinator()

    memory_result = None
    language_result = None
    try:
        memory_result = service.execute_command("remember that task096 failed key is value", AppCommandSource.TEST)
    except RuntimeError:
        pass
    try:
        language_result = service.execute_command("language English", AppCommandSource.TEST)
    except RuntimeError:
        pass

    assert memory_result is None
    assert language_result is None
    assert memory.recall_user_fact("task096 failed key").found is False
    assert language.get_preference().language_code == "ru-RU"


def test_direct_state_noop_routes_are_coordinated_and_duplicate_checked_before_handler(tmp_path):
    from language.language_manager import ApplicationLanguageManager
    from memory import LocalMemoryManager
    from users.user_profile import UserProfileManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.remember_calls = 0
            self.forget_calls = 0

        def remember_user_fact(self, key, value, *, language_code="ru-RU"):
            self.remember_calls += 1
            return super().remember_user_fact(key, value, language_code=language_code)

        def forget_user_fact(self, key):
            self.forget_calls += 1
            return super().forget_user_fact(key)

    memory = TrackingMemoryManager(tmp_path / "noop_memory.json")
    language = ApplicationLanguageManager.from_profile_manager(
        UserProfileManager(tmp_path / "noop_language.json")
    )
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
        language_manager=language,
    )
    service.execute_command("language English", AppCommandSource.TEST)
    active_language = service.execute_command("language English", AppCommandSource.TEST)
    missing_forget = service.execute_command(
        "forget task096 missing key",
        AppCommandSource.TEST,
        idempotency_key="task096-missing-forget",
    )
    repeated_missing_forget = service.execute_command(
        "forget task096 missing key",
        AppCommandSource.TEST,
        idempotency_key="task096-missing-forget",
    )
    first_remember = service.execute_command("remember that task096 noop key is same", AppCommandSource.TEST)
    identical_remember = service.execute_command(
        "remember that task096 noop key is same",
        AppCommandSource.TEST,
        idempotency_key="task096-identical-remember",
    )
    repeated_identical_remember = service.execute_command(
        "remember that task096 noop key is same",
        AppCommandSource.TEST,
        idempotency_key="task096-identical-remember",
    )

    assert active_language.registry_match_id == "profile.language.set"
    assert active_language.risk_level == "read_only"
    assert active_language.executed is False
    assert active_language.operation_status == "succeeded"
    assert missing_forget.risk_level == "read_only"
    assert missing_forget.executed is False
    assert missing_forget.operation_status == "succeeded"
    assert repeated_missing_forget.operation_id == missing_forget.operation_id
    assert repeated_missing_forget.duplicate_suppressed is True
    assert first_remember.executed is True
    assert identical_remember.risk_level == "read_only"
    assert identical_remember.executed is False
    assert repeated_identical_remember.operation_id == identical_remember.operation_id
    assert repeated_identical_remember.duplicate_suppressed is True
    assert memory.forget_calls == 1
    assert memory.remember_calls == 2


def test_direct_memory_journal_redacts_private_markers_from_metadata(tmp_path):
    from memory import LocalMemoryManager

    private_key = "TASK096_PRIVATE_KEY"
    private_value = "TASK096_PRIVATE_VALUE"
    memory = LocalMemoryManager(tmp_path / "private_memory.json")
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    first = service.execute_command(
        f"remember that {private_key} is {private_value}",
        AppCommandSource.TEST,
        idempotency_key="task096-private",
    )
    duplicate = service.execute_command(
        f"remember that {private_key} is {private_value}",
        AppCommandSource.TEST,
        idempotency_key="task096-private",
    )
    conflict = service.execute_command(
        f"remember that {private_key} is changed",
        AppCommandSource.TEST,
        idempotency_key="task096-private",
    )
    serialized = service.recent_execution_operations(None)
    metadata_text = repr([operation["metadata"] for operation in serialized])
    operation_text = repr(
        [
            {
                "command_id": operation["command_id"],
                "safe_error_code": operation["safe_error_code"],
                "metadata": operation["metadata"],
            }
            for operation in serialized
        ]
    )
    result_metadata_text = repr(
        [
            first.operation_id,
            first.operation_status,
            first.error,
            duplicate.operation_id,
            duplicate.operation_status,
            duplicate.error,
            conflict.operation_id,
            conflict.operation_status,
            conflict.error,
        ]
    )

    for marker in (private_key, private_value):
        assert marker not in metadata_text
        assert marker not in operation_text
        assert marker not in result_metadata_text
    assert serialized[0]["metadata"]["input_preview"] == "memory.remember [REDACTED]"
    assert duplicate.duplicate_suppressed is True
    assert conflict.error == "idempotency_conflict"


def test_direct_state_execution_failure_marks_operation_failed(tmp_path):
    from memory import LocalMemoryManager

    class FailingMemoryManager(LocalMemoryManager):
        def remember_user_fact(self, key, value, *, language_code="ru-RU"):
            raise RuntimeError("memory write failed")

    memory = FailingMemoryManager(tmp_path / "failed_memory.json")
    service = JarvisAppService(command_processor=FakeCommandProcessor(), memory_manager=memory)

    result = service.execute_command("remember that task096 failure key is value", AppCommandSource.TEST)
    operation = service.recent_execution_operations(1)[0]

    assert result.ok is False
    assert result.operation_status == "failed"
    assert result.error == "memory write failed"
    assert operation["status"] == "failed"
    assert operation["safe_error_code"] == "memory write failed"


def test_planner_local_write_policy_matches_capability_metadata(tmp_path):
    from memory import LocalMemoryManager

    memory = LocalMemoryManager(tmp_path / "planner_policy_memory.json")
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
    )

    language = service.planner_registry.get("language.set")
    remember = service.planner_registry.get("memory.remember")
    forget = service.planner_registry.get("memory.forget")

    for capability in (language, remember, forget):
        assert capability.descriptor.risk_level == "local_write"
        request = capability.policy_factory({}, False)
        assert request.command_id == capability.descriptor.capability_id
        assert request.risk == "local_write"
        assert "file_write" in request.required_capabilities
        assert request.confirmation_present is True


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


def test_russian_forget_all_plan_preview_and_create_are_non_mutating(tmp_path):
    from memory import LocalMemoryManager

    memory = LocalMemoryManager(tmp_path / "russian_forget_all_plan_memory.json")
    memory.remember_user_fact("marker", "survives")
    processor = FakeCommandProcessor()
    service = JarvisAppService(
        command_processor=processor,
        memory_manager=memory,
    )
    text = "составь план: забудь всё, что ты обо мне помнишь"

    preview = service.preview_command(text)
    preview_snapshot = service.multi_step_planner.snapshot()
    created = service.execute_command(text, AppCommandSource.TEST)
    created_snapshot = service.multi_step_planner.snapshot()

    assert preview.known_command is True
    assert preview.registry_match_id == "planner.general_multi_step"
    assert preview.category == "planner"
    assert preview.risk_level == "confirmation_required"
    assert preview.read_only is False
    assert preview.requires_confirmation is True
    assert preview.active_step_capability_id == "memory.forget_all"
    assert preview.operation_id is None
    assert preview_snapshot is None

    assert created.registry_match_id == "planner.general_multi_step"
    assert created.category == "planner"
    assert created.risk_level == "read_only"
    assert created.executed is False
    assert created.requires_confirmation is False
    assert created.operation_id is None
    assert created.plan_status == "proposed"
    assert created_snapshot is not None
    assert [step.capability_id for step in created_snapshot.steps] == [
        "memory.forget_all"
    ]
    assert service.multi_step_planner.steps()[0].arguments == {}
    assert created_snapshot.steps[0].risk_level == "confirmation_required"
    assert created_snapshot.steps[0].requires_confirmation is True
    assert memory.recall_user_fact("marker").found is True
    assert service.recent_execution_operations(1) == ()
    assert processor.calls == []


def test_russian_forget_all_plan_execution_awaits_confirmation_and_cancel_preserves_memory(tmp_path):
    from memory import LocalMemoryManager

    class TrackingMemoryManager(LocalMemoryManager):
        def __init__(self, path):
            super().__init__(path)
            self.forget_all_calls = 0

        def forget_all_user_facts(self):
            self.forget_all_calls += 1
            return super().forget_all_user_facts()

    memory = TrackingMemoryManager(tmp_path / "russian_forget_all_execution_memory.json")
    memory.remember_user_fact("marker", "survives")
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        memory_manager=memory,
    )
    service.execute_command(
        "составь план: забудь всё, что ты обо мне помнишь",
        AppCommandSource.TEST,
    )

    first = service.execute_command("execute plan", AppCommandSource.TEST)
    first_snapshot = service.multi_step_planner.snapshot()
    cancelled = service.execute_command("cancel plan", AppCommandSource.TEST)
    cancelled_snapshot = service.multi_step_planner.snapshot()

    assert first.plan_status == "awaiting_confirmation"
    assert first.operation_status == "awaiting_confirmation"
    assert first.requires_confirmation is True
    assert first.awaiting_confirmation is True
    assert first.operation_id
    assert first_snapshot.operation_id == first.operation_id
    assert first_snapshot.awaiting_confirmation is True
    assert first_snapshot.steps[0].capability_id == "memory.forget_all"
    assert first_snapshot.steps[0].safe_message == "awaiting_confirmation"
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0

    assert cancelled.plan_status == "cancelled"
    assert cancelled.operation_status == "cancelled"
    assert cancelled.operation_id == first.operation_id
    assert cancelled.awaiting_confirmation is False
    assert cancelled_snapshot.operation_id == first.operation_id
    assert cancelled_snapshot.awaiting_confirmation is False
    assert memory.recall_user_fact("marker").found is True
    assert memory.forget_all_calls == 0


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


def test_app_service_delegates_planner_preview_and_preserves_preview_fields():
    planner = FakePlannerService()
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        planner_service=planner,
    )

    preview = service.preview_command("create plan: system status")

    assert planner.preview_calls == [("create plan: system status", "create plan: system status")]
    assert preview.registry_match_id == "planner.general_multi_step"
    assert preview.category == "planner"
    assert preview.risk_level == "read_only"
    assert preview.active_plan_id == "plan-fake"
    assert preview.active_step_capability_id == "system.status"
    assert preview.operation_id is None


def test_app_service_delegates_planner_execute_without_duplicate_handling():
    planner = FakePlannerService()
    processor = FakeCommandProcessor()
    service = JarvisAppService(
        command_processor=processor,
        planner_service=planner,
    )

    result = service.execute_command(
        "execute plan",
        AppCommandSource.TEST,
        idempotency_key="planner-idempotency",
    )

    assert planner.handle_calls == [
        ("execute plan", AppCommandSource.TEST, "planner-idempotency")
    ]
    assert processor.calls == []
    assert result.output_text == "fake planner handled: execute plan"
    assert result.operation_id == "op-fake"
    assert result.workflow_id == "general_multi_step_plan"
    assert result.progress_percent == 100


def test_app_service_delegates_planner_show_and_cancel():
    planner = FakePlannerService()
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        planner_service=planner,
    )

    show = service.execute_command("show plan", AppCommandSource.TEST)
    cancel = service.execute_command("cancel plan", AppCommandSource.TEST)

    assert planner.handle_calls == [
        ("show plan", AppCommandSource.TEST, None),
        ("cancel plan", AppCommandSource.TEST, None),
    ]
    assert show.registry_match_id == "planner.general_multi_step"
    assert cancel.registry_match_id == "planner.general_multi_step"
    assert show.plan_id == "plan-fake"
    assert cancel.operation_id == "op-fake"


def test_app_service_continues_to_handle_non_planner_commands_itself():
    planner = FakePlannerService()
    processor = FakeCommandProcessor()
    service = JarvisAppService(
        command_processor=processor,
        planner_service=planner,
    )

    result = service.execute_command("статус app service", AppCommandSource.TEST)

    assert planner.handle_calls == [("статус app service", AppCommandSource.TEST, None)]
    assert processor.calls == ["статус app service"]
    assert result.registry_match_id == "app_service.status"
    assert result.category == "app"
    assert result.executed is True


def test_memory_and_confirmation_normalization_share_exact_helper():
    assert normalize_control_text("  YES  ") == "yes"
    assert normalize_control_text("\u0414\u0430, \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c") == "\u0434\u0430 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c"
    assert normalize_control_text("\u0442\u0435\u0441\u0442: \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435; \u0435\u0449\u0451") == "\u0442\u0435\u0441\u0442 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u0435\u0449\u0435"
    assert normalize_control_text(None) == ""

    samples = (
        "  YES  ",
        "Да, подтвердить",
        "тест: значение; ещё",
        None,
    )

    for sample in samples:
        assert JarvisAppService._normalize_memory_text(sample) == normalize_control_text(sample)


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


def test_one_shot_voice_sanitizes_raw_microphone_blocked_reason():
    recognizer = FakeOneShotRecognition(
        OneShotVoskRealRecognitionResult(
            allowed=False,
            completed=False,
            blocked=True,
            recognized_text=None,
            capture_seconds=0,
            reasons=[RAW_MICROPHONE_ERROR],
            next_steps=["Проверьте микрофон."],
        )
    )
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=recognizer,
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)
    safe_text = result.safe_text_ru()

    assert result.ok is False
    assert result.result_type == "voice_recognition_blocked"
    assert result.error_code == "recognition_blocked"
    assert result.operation_id is None
    assert result.operation_status is None
    assert result.requires_confirmation is False
    assert "Не удалось получить доступ к микрофону." in result.user_message
    assert "PaErrorCode" not in result.user_message
    assert "MME error" not in result.user_message
    assert "Error querying device" not in result.user_message
    assert "PaErrorCode" not in safe_text
    assert "MME error" not in safe_text
    assert "Error querying device" not in safe_text


def test_one_shot_voice_sanitizes_unexpected_recognizer_exception_details():
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=FakeOneShotRecognition(
            error=RuntimeError(RAW_RECOGNIZER_ERROR)
        ),
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)
    safe_text = result.safe_text_ru()

    assert result.ok is False
    assert result.error_code == "one_shot_voice_failure"
    assert result.requires_confirmation is False
    assert "Не удалось получить доступ к микрофону." in result.user_message
    assert "sounddevice" not in result.user_message
    assert "C:/Users/User" not in result.user_message
    assert "backend" not in result.user_message.lower()
    assert "raw exception" not in result.user_message
    assert "sounddevice" not in safe_text
    assert "C:/Users/User" not in safe_text
    assert "backend" not in safe_text.lower()


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
            raise RuntimeError("opaque recognizer failure")

    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        one_shot_voice_recognition=BrokenRecognizer(),
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is False
    assert result.error_code == "one_shot_voice_failure"
    assert "Голосовой запрос безопасно завершился ошибкой." in result.user_message
    assert "opaque recognizer failure" not in result.user_message
    assert "Traceback" not in result.user_message


def test_text_one_shot_vosk_command_sanitizes_raw_hardware_reason_in_output_and_journal():
    recognizer = FakeOneShotRecognition(
        OneShotVoskRealRecognitionResult(
            allowed=False,
            completed=False,
            blocked=True,
            recognized_text=None,
            capture_seconds=0,
            reasons=[RAW_MICROPHONE_ERROR],
            next_steps=["Проверьте микрофон."],
        )
    )
    processor = CommandProcessor(one_shot_vosk_real_recognition=recognizer)
    service = JarvisAppService(command_processor=processor)

    preview = service.preview_command(ONE_SHOT_REAL_VOSK_COMMAND)
    result = service.execute_command(ONE_SHOT_REAL_VOSK_COMMAND, AppCommandSource.TEST)
    journal_text = str(service.recent_execution_operations())

    assert preview.known_command is False
    assert result.ok is True
    assert result.operation_status == "succeeded"
    assert "Не удалось получить доступ к микрофону." in result.output_text
    assert "PaErrorCode" not in result.output_text
    assert "MME error" not in result.output_text
    assert "Error querying device" not in result.output_text
    assert "PaErrorCode" not in journal_text
    assert "MME error" not in journal_text
    assert "Error querying device" not in journal_text


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
