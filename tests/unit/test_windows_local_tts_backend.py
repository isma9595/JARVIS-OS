import subprocess

from voice.windows_local_tts_backend import (
    WINDOWS_LOCAL_TTS_DIAGNOSTIC_SCRIPT,
    WINDOWS_LOCAL_TTS_SPEAK_SCRIPT,
    WindowsLocalSpeechSynthesisBackend,
)


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_backend_reports_unavailable_on_non_windows(monkeypatch):
    monkeypatch.setattr("voice.windows_local_tts_backend.platform.system", lambda: "Linux")

    backend = WindowsLocalSpeechSynthesisBackend()
    diagnostics = backend.availability_diagnostics()

    assert diagnostics["available"] is False
    assert "Windows" in diagnostics["reason"]


def test_availability_check_uses_safe_non_speaking_subprocess(monkeypatch):
    calls = []
    monkeypatch.setattr("voice.windows_local_tts_backend.platform.system", lambda: "Windows")
    monkeypatch.setattr("voice.windows_local_tts_backend.shutil.which", lambda _name: "powershell")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed(returncode=0)

    monkeypatch.setattr("voice.windows_local_tts_backend.subprocess.run", fake_run)

    backend = WindowsLocalSpeechSynthesisBackend()
    assert backend.is_available() is True

    command, kwargs = calls[0]
    assert kwargs["shell"] is False
    assert WINDOWS_LOCAL_TTS_DIAGNOSTIC_SCRIPT in command
    assert "Speak(" not in WINDOWS_LOCAL_TTS_DIAGNOSTIC_SCRIPT


def test_speak_uses_shell_false_and_env_text(monkeypatch):
    calls = []
    monkeypatch.setattr(
        WindowsLocalSpeechSynthesisBackend,
        "availability_diagnostics",
        lambda self: {"available": True, "reason": "ok", "backend_name": self.get_name()},
    )

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed(returncode=0)

    monkeypatch.setattr("voice.windows_local_tts_backend.subprocess.run", fake_run)

    backend = WindowsLocalSpeechSynthesisBackend()
    result = backend.synthesize("текст; Remove-Item C:\\")

    assert result.success is True
    command, kwargs = calls[0]
    assert kwargs["shell"] is False
    assert kwargs["env"]["JARVIS_TTS_TEXT"] == "текст; Remove-Item C:\\"
    assert "текст; Remove-Item" not in " ".join(command)
    assert "$env:JARVIS_TTS_TEXT" in WINDOWS_LOCAL_TTS_SPEAK_SCRIPT


def test_speak_returns_success_on_zero_returncode(monkeypatch):
    monkeypatch.setattr(
        WindowsLocalSpeechSynthesisBackend,
        "availability_diagnostics",
        lambda self: {"available": True, "reason": "ok", "backend_name": self.get_name()},
    )
    monkeypatch.setattr(
        "voice.windows_local_tts_backend.subprocess.run",
        lambda *args, **kwargs: Completed(returncode=0),
    )

    result = WindowsLocalSpeechSynthesisBackend().synthesize("тест")

    assert result.success is True
    assert result.played_audio is True
    assert result.backend_available is True


def test_speak_returns_safe_error_on_failure(monkeypatch):
    monkeypatch.setattr(
        WindowsLocalSpeechSynthesisBackend,
        "availability_diagnostics",
        lambda self: {"available": True, "reason": "ok", "backend_name": self.get_name()},
    )
    monkeypatch.setattr(
        "voice.windows_local_tts_backend.subprocess.run",
        lambda *args, **kwargs: Completed(returncode=1, stderr="bad\nfailure"),
    )

    result = WindowsLocalSpeechSynthesisBackend().synthesize("тест")

    assert result.success is False
    assert result.played_audio is False
    assert result.error == "bad failure"
    assert result.error_code == "playback_failed"


def test_speak_returns_timeout_error(monkeypatch):
    monkeypatch.setattr(
        WindowsLocalSpeechSynthesisBackend,
        "availability_diagnostics",
        lambda self: {"available": True, "reason": "ok", "backend_name": self.get_name()},
    )

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=1)

    monkeypatch.setattr("voice.windows_local_tts_backend.subprocess.run", fake_run)

    result = WindowsLocalSpeechSynthesisBackend().synthesize("тест")

    assert result.success is False
    assert result.error_code == "timeout"
    assert "лимит времени" in result.error


def test_empty_text_is_rejected(monkeypatch):
    monkeypatch.setattr(
        WindowsLocalSpeechSynthesisBackend,
        "is_available",
        lambda self: True,
    )

    result = WindowsLocalSpeechSynthesisBackend().synthesize("   ")

    assert result.success is False
    assert result.error_code == "empty_text"


def test_long_text_is_capped(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        WindowsLocalSpeechSynthesisBackend,
        "availability_diagnostics",
        lambda self: {"available": True, "reason": "ok", "backend_name": self.get_name()},
    )

    def fake_run(command, **kwargs):
        captured["text"] = kwargs["env"]["JARVIS_TTS_TEXT"]
        return Completed(returncode=0)

    monkeypatch.setattr("voice.windows_local_tts_backend.subprocess.run", fake_run)
    backend = WindowsLocalSpeechSynthesisBackend()

    result = backend.synthesize("а" * (backend.MAX_TEXT_LENGTH + 20))

    assert result.success is True
    assert len(result.spoken_text) == backend.MAX_TEXT_LENGTH
    assert len(captured["text"]) == backend.MAX_TEXT_LENGTH


def test_no_file_write_api_is_used():
    source = WindowsLocalSpeechSynthesisBackend.synthesize.__code__.co_names

    assert "open" not in source
    assert "write" not in source
