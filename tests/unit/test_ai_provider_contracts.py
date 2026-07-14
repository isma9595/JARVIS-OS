from ai import (
    AIProviderCapability,
    AIProviderInfo,
    AIProviderSafetyLevel,
    AIRequest,
    AIResponse,
)


def test_ai_request_defaults_and_validation():
    request = AIRequest(prompt="привет")

    assert request.task_type == "chat"
    assert request.language == "ru"
    assert request.max_chars is None
    assert request.metadata == {}
    assert request.validation_error() is None


def test_ai_request_validation_errors():
    assert AIRequest(prompt="").validation_error() == "AI prompt is empty."
    assert AIRequest(prompt="x", max_chars=0).validation_error() == (
        "AI max_chars must be positive."
    )
    assert AIRequest(prompt=123).validation_error() == "AI prompt must be a string."
    assert AIRequest(prompt="x", metadata=[]).validation_error() == (
        "AI metadata must be a dictionary."
    )


def test_ai_response_fields():
    response = AIResponse(
        text="ответ",
        provider_name="dry_run",
        model_name="jarvis-dry-run-v0",
        capability="chat",
        safety_level="offline_deterministic",
    )

    assert response.text == "ответ"
    assert response.provider_name == "dry_run"
    assert response.is_error is False
    assert response.error_message is None


def test_ai_provider_info_fields():
    info = AIProviderInfo(
        name="dry_run",
        model_name="jarvis-dry-run-v0",
        capabilities=["chat"],
        safety_level="offline_deterministic",
        enabled=True,
        description="offline",
    )

    assert info.name == "dry_run"
    assert info.capabilities == ["chat"]
    assert info.enabled is True


def test_capability_enum_values():
    assert AIProviderCapability.CHAT.value == "chat"
    assert AIProviderCapability.SUMMARY.value == "summary"
    assert AIProviderCapability.CLASSIFICATION.value == "classification"
    assert AIProviderCapability.CODE.value == "code"
    assert AIProviderCapability.VISION.value == "vision"
    assert AIProviderCapability.TOOL_PLANNING.value == "tool_planning"


def test_safety_enum_values():
    assert AIProviderSafetyLevel.OFFLINE_DETERMINISTIC.value == "offline_deterministic"
    assert AIProviderSafetyLevel.LOCAL_ONLY.value == "local_only"
    assert AIProviderSafetyLevel.EXTERNAL_API.value == "external_api"
