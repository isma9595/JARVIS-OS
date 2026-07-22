from app import AppCommandSource, JarvisAppService
from core.command_processor import CommandProcessor
from voice.speech_synthesis_backend import SpeechSynthesisResult
from voice.voice_output_manager import VoiceOutputManager


LOCAL_TTS_STATUS = (
    "\u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)
ENABLE_LOCAL_TTS = (
    "\u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 "
    "\u0433\u043e\u043b\u043e\u0441"
)
LOCAL_TTS_TEST = (
    "\u0442\u0435\u0441\u0442 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)


class FakeLocalTtsBackend:
    def __init__(self, *, available=True):
        self.available = available
        self.diagnostics_calls = 0
        self.diagnostics_results = []
        self.synthesis_calls = []
        self.synthesis_results = []

    def get_name(self):
        return "windows_local_tts"

    def availability_diagnostics(self):
        self.diagnostics_calls += 1
        result = {
            "available": self.available,
            "reason": "fake backend available" if self.available else "fake backend unavailable",
            "backend_name": self.get_name(),
            "network_used": False,
            "audio_file_saved": False,
        }
        self.diagnostics_results.append(result)
        return result

    def synthesize(self, text, mode="WINDOWS_LOCAL"):
        self.synthesis_calls.append((text, mode))
        result = SpeechSynthesisResult(
            success=True,
            spoken_text=text,
            backend_name=self.get_name(),
            mode=mode,
            safety_notes=[
                "fake backend: no network",
                "fake backend: no audio file",
                "fake backend: no audible speech",
            ],
            played_audio=False,
            backend_available=True,
        )
        self.synthesis_results.append(result)
        return result


def make_service(local_backend):
    voice_output = VoiceOutputManager(windows_local_backend=local_backend)
    processor = CommandProcessor(voice_output_manager=voice_output)
    return JarvisAppService(command_processor=processor), processor


def assert_execute_metadata(
    result,
    *,
    ok,
    registry_match_id,
    category,
    risk_level,
    executed,
    requires_confirmation,
    network_may_be_used,
    response_executed_as_command,
    operation_id_present,
    operation_status,
):
    assert result.ok is ok
    assert result.registry_match_id == registry_match_id
    assert result.category == category
    assert result.risk_level == risk_level
    assert result.executed is executed
    assert result.requires_confirmation is requires_confirmation
    assert result.network_may_be_used is network_may_be_used
    assert result.response_executed_as_command is response_executed_as_command
    if operation_id_present:
        assert result.operation_id
    else:
        assert result.operation_id is None
    assert result.operation_status == operation_status


def test_characterizes_corrected_local_tts_execute_metadata(tmp_path):
    local_backend = FakeLocalTtsBackend(available=True)
    service, processor = make_service(local_backend)

    preview_status = service.preview_command(LOCAL_TTS_STATUS)
    preview_enable = service.preview_command(ENABLE_LOCAL_TTS)
    preview_test_before_enable = service.preview_command(LOCAL_TTS_TEST)

    # Preview remains side-effect free for local TTS commands. TASK-100 fixes
    # completed Execute metadata without broadening Preview recognition.
    assert preview_status.known_command is False
    assert preview_status.registry_match_id is None
    assert preview_status.category is None
    assert preview_status.risk_level is None
    assert preview_status.requires_confirmation is True
    assert preview_enable.known_command is False
    assert preview_enable.registry_match_id is None
    assert preview_enable.category is None
    assert preview_enable.risk_level is None
    assert preview_enable.requires_confirmation is True
    assert preview_test_before_enable.known_command is False
    assert preview_test_before_enable.registry_match_id is None
    assert preview_test_before_enable.category is None
    assert preview_test_before_enable.risk_level is None
    assert preview_test_before_enable.requires_confirmation is True
    assert local_backend.diagnostics_calls == 0
    assert local_backend.synthesis_calls == []

    status = service.execute_command(LOCAL_TTS_STATUS, AppCommandSource.TEST)
    diagnostics_after_status = local_backend.diagnostics_calls
    synthesis_after_status = list(local_backend.synthesis_calls)
    test_before_enable = service.execute_command(LOCAL_TTS_TEST, AppCommandSource.TEST)
    diagnostics_after_disabled_test = local_backend.diagnostics_calls
    synthesis_after_disabled_test = list(local_backend.synthesis_calls)
    enable = service.execute_command(ENABLE_LOCAL_TTS, AppCommandSource.TEST)
    diagnostics_after_enable = local_backend.diagnostics_calls
    synthesis_after_enable = list(local_backend.synthesis_calls)
    test_after_enable = service.execute_command(LOCAL_TTS_TEST, AppCommandSource.TEST)

    assert_execute_metadata(
        status,
        ok=True,
        registry_match_id="voice.output.local.status",
        category="voice",
        risk_level="read_only",
        executed=True,
        requires_confirmation=False,
        network_may_be_used=False,
        response_executed_as_command=False,
        operation_id_present=True,
        operation_status="succeeded",
    )
    assert diagnostics_after_status == 1
    assert synthesis_after_status == []

    assert_execute_metadata(
        test_before_enable,
        ok=False,
        registry_match_id="voice.output.local_test.not_enabled",
        category="voice",
        risk_level="local_runtime",
        executed=True,
        requires_confirmation=False,
        network_may_be_used=False,
        response_executed_as_command=False,
        operation_id_present=True,
        operation_status="failed",
    )
    assert test_before_enable.error == "voice.output.local_test.not_enabled"
    assert diagnostics_after_disabled_test == diagnostics_after_status
    assert synthesis_after_disabled_test == []

    assert_execute_metadata(
        enable,
        ok=True,
        registry_match_id="voice.output.windows_local.enable",
        category="voice",
        risk_level="local_runtime",
        executed=True,
        requires_confirmation=False,
        network_may_be_used=False,
        response_executed_as_command=False,
        operation_id_present=True,
        operation_status="succeeded",
    )
    assert processor.voice_output_manager.mode == "WINDOWS_LOCAL"
    assert diagnostics_after_enable == 2
    assert synthesis_after_enable == []

    assert_execute_metadata(
        test_after_enable,
        ok=True,
        registry_match_id="voice.output.spoken",
        category="voice",
        risk_level="local_runtime",
        executed=True,
        requires_confirmation=False,
        network_may_be_used=False,
        response_executed_as_command=False,
        operation_id_present=True,
        operation_status="succeeded",
    )
    assert len(local_backend.synthesis_calls) == 1
    assert len(local_backend.synthesis_results) == 1
    spoken_text, mode = local_backend.synthesis_calls[0]
    synthesis_result = local_backend.synthesis_results[0]
    assert mode == "WINDOWS_LOCAL"
    assert spoken_text
    assert synthesis_result.played_audio is False
    assert synthesis_result.backend_name == "windows_local_tts"
    assert synthesis_result.spoken_text == spoken_text

    # Safety invariants for the fake local backend.
    assert local_backend.diagnostics_calls == 2
    assert local_backend.diagnostics_results
    assert all(result["network_used"] is False for result in local_backend.diagnostics_results)
    assert all(result["audio_file_saved"] is False for result in local_backend.diagnostics_results)
    assert all(call[1] == "WINDOWS_LOCAL" for call in local_backend.synthesis_calls)
    assert all(result.played_audio is False for result in local_backend.synthesis_results)
    assert all(result.backend_name == "windows_local_tts" for result in local_backend.synthesis_results)
    assert "provider" not in status.output_text.lower()
    assert "provider" not in test_after_enable.output_text.lower()
