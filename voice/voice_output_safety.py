from dataclasses import dataclass, field


@dataclass(frozen=True)
class VoiceOutputSafetyDecision:
    allowed: bool
    reason: str | None
    muted: bool
    skip_next: bool
    safety_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VoiceOutputSafetyStatus:
    muted: bool
    skip_next: bool
    last_stop_requested: bool
    safety_notes: list[str] = field(default_factory=list)


class VoiceOutputSafetyController:
    def __init__(self):
        self.muted = False
        self.skip_next = False
        self.last_stop_requested = False

    def mute(self, reason: str | None = None):
        self.muted = True
        if reason == "stop_requested":
            self.last_stop_requested = True
        return self.status()

    def unmute(self):
        self.muted = False
        self.last_stop_requested = False
        return self.status()

    def request_stop(self):
        self.last_stop_requested = True
        self.muted = True
        return self.status()

    def skip_next_speech(self):
        self.skip_next = True
        return self.status()

    def clear_skip_next(self):
        self.skip_next = False
        return self.status()

    def can_speak(self, source: str | None = None):
        notes = self._safety_notes(source=source)
        if self.muted:
            return VoiceOutputSafetyDecision(
                allowed=False,
                reason="muted",
                muted=self.muted,
                skip_next=self.skip_next,
                safety_notes=notes + ["Тихий режим блокирует голосовую озвучку."],
            )
        if self.skip_next:
            return VoiceOutputSafetyDecision(
                allowed=False,
                reason="skip_next",
                muted=self.muted,
                skip_next=self.skip_next,
                safety_notes=notes + ["Следующая озвучка пропускается один раз."],
            )
        return VoiceOutputSafetyDecision(
            allowed=True,
            reason=None,
            muted=self.muted,
            skip_next=self.skip_next,
            safety_notes=notes,
        )

    def consume_skip_if_needed(self):
        if self.skip_next:
            self.skip_next = False
            return True
        return False

    def status(self):
        return VoiceOutputSafetyStatus(
            muted=self.muted,
            skip_next=self.skip_next,
            last_stop_requested=self.last_stop_requested,
            safety_notes=self._safety_notes(),
        )

    def reset(self):
        self.muted = False
        self.skip_next = False
        self.last_stop_requested = False
        return self.status()

    @staticmethod
    def _safety_notes(source: str | None = None):
        notes = [
            "Состояние голосовой безопасности хранится только в памяти текущей сессии.",
            "Облачный TTS не используется.",
            "Аудиофайлы не сохраняются.",
        ]
        if source:
            notes.append(f"Источник запроса озвучки: {source}.")
        return notes
