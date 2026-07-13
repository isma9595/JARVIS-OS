import os
import platform
import shutil
import subprocess

from voice.speech_synthesis_backend import SpeechSynthesisBackend, SpeechSynthesisResult


WINDOWS_LOCAL_TTS_DIAGNOSTIC_SCRIPT = """
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Dispose()
exit 0
""".strip()

WINDOWS_LOCAL_TTS_SPEAK_SCRIPT = """
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$text = $env:JARVIS_TTS_TEXT
if ([string]::IsNullOrWhiteSpace($text)) { exit 2 }
$synth.Speak($text)
$synth.Dispose()
exit 0
""".strip()


class WindowsLocalSpeechSynthesisBackend(SpeechSynthesisBackend):
    backend_name = "windows_local_tts"
    mode = "WINDOWS_LOCAL"
    MAX_TEXT_LENGTH = 500
    DEFAULT_TIMEOUT_SECONDS = 10

    def __init__(self, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds

    def get_name(self):
        return self.backend_name

    def is_available(self):
        return self.availability_diagnostics()["available"]

    def availability_diagnostics(self):
        if platform.system() != "Windows":
            return {
                "available": False,
                "reason": "локальный Windows TTS доступен только на Windows",
                "backend_name": self.backend_name,
            }

        powershell_path = shutil.which("powershell")
        if not powershell_path:
            return {
                "available": False,
                "reason": "PowerShell не найден",
                "backend_name": self.backend_name,
            }

        try:
            completed = subprocess.run(
                self._powershell_command(WINDOWS_LOCAL_TTS_DIAGNOSTIC_SCRIPT, powershell_path),
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "reason": "проверка System.Speech превысила лимит времени",
                "backend_name": self.backend_name,
            }
        except OSError as exc:
            return {
                "available": False,
                "reason": self._safe_error(exc),
                "backend_name": self.backend_name,
            }

        if completed.returncode != 0:
            return {
                "available": False,
                "reason": self._subprocess_error(completed, "System.Speech недоступен"),
                "backend_name": self.backend_name,
            }

        return {
            "available": True,
            "reason": "System.Speech доступен",
            "backend_name": self.backend_name,
        }

    def synthesize(self, text, mode=mode):
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return self._failure(
                normalized_text,
                mode,
                "Укажите текст для озвучки.",
                "empty_text",
                backend_available=self.is_available(),
            )

        diagnostics = self.availability_diagnostics()
        if not diagnostics["available"]:
            return self._failure(
                normalized_text,
                mode,
                diagnostics["reason"],
                "backend_unavailable",
                backend_available=False,
            )

        env = os.environ.copy()
        env["JARVIS_TTS_TEXT"] = normalized_text

        try:
            completed = subprocess.run(
                self._powershell_command(WINDOWS_LOCAL_TTS_SPEAK_SCRIPT),
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return self._failure(
                normalized_text,
                mode,
                "локальная озвучка превысила лимит времени",
                "timeout",
                backend_available=True,
            )
        except OSError as exc:
            return self._failure(
                normalized_text,
                mode,
                self._safe_error(exc),
                "subprocess_error",
                backend_available=True,
            )

        if completed.returncode != 0:
            return self._failure(
                normalized_text,
                mode,
                self._subprocess_error(completed, "PowerShell TTS завершился с ошибкой"),
                "playback_failed",
                backend_available=True,
            )

        return SpeechSynthesisResult(
            success=True,
            spoken_text=normalized_text,
            backend_name=self.get_name(),
            mode=mode,
            safety_notes=self._safety_notes(),
            played_audio=True,
            backend_available=True,
        )

    def _powershell_command(self, script, powershell_path="powershell"):
        return [
            powershell_path,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ]

    def _normalize_text(self, text):
        normalized = " ".join(str(text or "").strip().split())
        if len(normalized) > self.MAX_TEXT_LENGTH:
            return normalized[: self.MAX_TEXT_LENGTH].rstrip()
        return normalized

    def _failure(self, text, mode, error, error_code, backend_available):
        return SpeechSynthesisResult(
            success=False,
            spoken_text=text,
            backend_name=self.get_name(),
            mode=mode,
            safety_notes=self._safety_notes(),
            error=error,
            played_audio=False,
            backend_available=backend_available,
            error_code=error_code,
        )

    def _safety_notes(self):
        return [
            "Используется только локальный Windows TTS.",
            "Облачный TTS не используется.",
            "Аудиофайлы не сохраняются.",
            "Текст передаётся через переменную окружения, а не через командную строку.",
        ]

    def _subprocess_error(self, completed, fallback):
        stderr = self._safe_error(completed.stderr)
        stdout = self._safe_error(completed.stdout)
        details = stderr or stdout
        if details:
            return details
        return f"{fallback}; код возврата: {completed.returncode}"

    def _safe_error(self, value):
        text = str(value or "").strip().replace("\r", " ").replace("\n", " ")
        text = " ".join(text.split())
        if len(text) > 200:
            return text[:200].rstrip()
        return text
