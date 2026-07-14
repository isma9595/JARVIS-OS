"""Core AI provider contracts.

TASK-051 intentionally defines only offline-safe interfaces. Real external
providers, API keys, network calls, and tool execution are out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class AIProviderCapability(str, Enum):
    CHAT = "chat"
    SUMMARY = "summary"
    CLASSIFICATION = "classification"
    CODE = "code"
    VISION = "vision"
    TOOL_PLANNING = "tool_planning"


class AIProviderSafetyLevel(str, Enum):
    OFFLINE_DETERMINISTIC = "offline_deterministic"
    LOCAL_ONLY = "local_only"
    EXTERNAL_API = "external_api"


@dataclass
class AIRequest:
    prompt: str
    task_type: str = "chat"
    language: str = "ru"
    max_chars: int | None = None
    metadata: dict[str, str] | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def validation_error(self) -> str | None:
        if not isinstance(self.prompt, str):
            return "AI prompt must be a string."
        if not self.prompt.strip():
            return "AI prompt is empty."
        if self.max_chars is not None and self.max_chars <= 0:
            return "AI max_chars must be positive."
        if self.metadata is None:
            self.metadata = {}
        if not isinstance(self.metadata, dict):
            return "AI metadata must be a dictionary."
        return None


@dataclass
class AIResponse:
    text: str
    provider_name: str
    model_name: str
    capability: str
    safety_level: str
    is_error: bool = False
    error_message: str | None = None


@dataclass
class AIProviderInfo:
    name: str
    model_name: str
    capabilities: list[str] = field(default_factory=list)
    safety_level: str = AIProviderSafetyLevel.OFFLINE_DETERMINISTIC.value
    enabled: bool = True
    description: str = ""


class AIProvider(Protocol):
    def get_info(self) -> AIProviderInfo:
        ...

    def supports(self, capability: AIProviderCapability) -> bool:
        ...

    def generate(self, request: AIRequest) -> AIResponse:
        ...
