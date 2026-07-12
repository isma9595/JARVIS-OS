"""Session-only voice recognition correction storage."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re


@dataclass(frozen=True)
class VoiceRecognitionCorrection:
    wrong_text: str
    corrected_text: str
    normalized_wrong_text: str
    normalized_corrected_text: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "user_session_correction"


class VoiceRecognitionCorrectionManager:
    """In-memory correction manager with no persistence or audio storage."""

    def __init__(self, max_corrections=20):
        if max_corrections < 1:
            raise ValueError("max_corrections must be at least 1")
        self.max_corrections = max_corrections
        self._corrections = []

    def add_correction(self, wrong_text, corrected_text):
        wrong = self._clean_text(wrong_text)
        corrected = self._clean_text(corrected_text)
        correction = VoiceRecognitionCorrection(
            wrong_text=wrong,
            corrected_text=corrected,
            normalized_wrong_text=self.normalize(wrong),
            normalized_corrected_text=self.normalize(corrected),
        )
        self._corrections.append(correction)
        if len(self._corrections) > self.max_corrections:
            self._corrections = self._corrections[-self.max_corrections :]
        return correction

    def find_correction(self, text):
        normalized = self.normalize(text)
        if not normalized:
            return None
        for correction in reversed(self._corrections):
            if correction.normalized_wrong_text == normalized:
                return correction
        return None

    def list_corrections(self):
        return list(self._corrections)

    def clear(self):
        self._corrections.clear()

    def count(self):
        return len(self._corrections)

    @classmethod
    def normalize(cls, text):
        normalized = str(text or "").strip().lower().replace("ё", "е")
        normalized = re.sub(r"^[\s,.;:!?\"'()\[\]{}<>]+", "", normalized)
        normalized = re.sub(r"[\s,.;:!?\"'()\[\]{}<>]+$", "", normalized)
        normalized = re.sub(r"[^\w\s]+", " ", normalized, flags=re.UNICODE)
        return " ".join(normalized.split())

    @staticmethod
    def _clean_text(text):
        return " ".join(str(text or "").strip().split())
