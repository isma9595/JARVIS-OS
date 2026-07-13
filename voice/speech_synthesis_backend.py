from dataclasses import dataclass, field


@dataclass(frozen=True)
class SpeechSynthesisResult:
    success: bool
    spoken_text: str
    backend_name: str
    mode: str
    safety_notes: list[str] = field(default_factory=list)
    error: str | None = None
    played_audio: bool = False
    backend_available: bool = True
    error_code: str | None = None


class SpeechSynthesisBackend:
    def get_name(self):
        return "base"

    def synthesize(self, text, mode="OFF"):
        return SpeechSynthesisResult(
            success=False,
            spoken_text=str(text or "").strip(),
            backend_name=self.get_name(),
            mode=mode,
            safety_notes=[
                "Базовый TTS backend не воспроизводит звук.",
                "Облачный TTS не используется.",
                "Аудиофайлы не сохраняются.",
            ],
            error="speech synthesis is not implemented",
        )


class DryRunSpeechSynthesisBackend(SpeechSynthesisBackend):
    def get_name(self):
        return "dry_run"

    def synthesize(self, text, mode="DRY_RUN"):
        spoken_text = str(text or "").strip()
        return SpeechSynthesisResult(
            success=True,
            spoken_text=spoken_text,
            backend_name=self.get_name(),
            mode=mode,
            safety_notes=[
                "Реальный звук не воспроизводился.",
                "Облачный TTS не использовался.",
                "Аудиофайл не сохранялся.",
                "Внешние зависимости не требуются.",
            ],
        )
