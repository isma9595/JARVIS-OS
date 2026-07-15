"""Runtime-only AI provider session selection state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class AIProviderSessionSnapshot:
    selected_provider: str | None
    selected_model: str | None
    selection_mode: str
    last_success_provider: str | None
    last_success_model: str | None
    last_success_capability: str | None
    updated_at: str | None
    request_count: int


class AIProviderSessionState:
    """Keep safe provider/model metadata for the current process only."""

    VALID_SELECTION_MODES = {"none", "manual", "last_success"}

    def __init__(self):
        self.selected_provider: str | None = None
        self.selected_model: str | None = None
        self.selection_mode = "none"
        self.last_success_provider: str | None = None
        self.last_success_model: str | None = None
        self.last_success_capability: str | None = None
        self.updated_at: str | None = None
        self.request_count = 0

    def select_manual(self, provider: str, model: str):
        self.selected_provider = self._normalize_provider(provider)
        self.selected_model = self._normalize_model(model)
        self.selection_mode = "manual"
        self._touch()

    def reset_selection(self):
        self.selected_provider = None
        self.selected_model = None
        self.selection_mode = "none"
        self._touch()

    def record_success(self, provider: str, model: str, capability: str):
        safe_provider = self._normalize_provider(provider)
        safe_model = self._normalize_model(model)
        self.last_success_provider = safe_provider
        self.last_success_model = safe_model
        self.last_success_capability = str(capability or "").strip() or None
        self.request_count += 1
        if self.selection_mode != "manual":
            self.selected_provider = safe_provider
            self.selected_model = safe_model
            self.selection_mode = "last_success"
        self._touch()

    def snapshot(self) -> AIProviderSessionSnapshot:
        return AIProviderSessionSnapshot(
            selected_provider=self.selected_provider,
            selected_model=self.selected_model,
            selection_mode=self.selection_mode,
            last_success_provider=self.last_success_provider,
            last_success_model=self.last_success_model,
            last_success_capability=self.last_success_capability,
            updated_at=self.updated_at,
            request_count=self.request_count,
        )

    def status_text_ru(self) -> str:
        snapshot = self.snapshot()
        return "\n".join(
            [
                "AI provider session:",
                f"- selected provider: {snapshot.selected_provider or 'none'}",
                f"- selected model: {snapshot.selected_model or 'none'}",
                f"- selection mode: {snapshot.selection_mode}",
                f"- last success provider: {snapshot.last_success_provider or 'none'}",
                f"- last success model: {snapshot.last_success_model or 'none'}",
                f"- last success capability: {snapshot.last_success_capability or 'none'}",
                f"- updated at: {snapshot.updated_at or 'none'}",
                f"- request count: {snapshot.request_count}",
                "- runtime only: not persisted to disk",
                "- stored data: provider/model metadata only",
                "- prompts, responses, keys, tokens, memory, files and logs are not stored",
                "- dry_run remains default; network is still explicit one-shot only",
            ]
        )

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        return str(provider or "").strip().lower()

    @staticmethod
    def _normalize_model(model: str) -> str:
        return str(model or "").strip()

    def _touch(self):
        self.updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
