import json

from ai import AIProviderConfigManager, OpenAIRequestGate
from ai.provider_session import AIProviderSessionState
from core.command_processor import CommandProcessor
from voice import SafeVoiceCommandAllowlist


class FakeHTTPClient:
    def __init__(self, response=None):
        self.response = response or json.dumps({"output_text": "session answer"})
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "payload": dict(payload),
                "timeout": timeout,
            }
        )
        return self.response


def test_session_state_stores_only_safe_metadata_and_manual_wins():
    state = AIProviderSessionState()

    state.select_manual("Groq", "llama-3.1-8b-instant")
    state.record_success("openai", "gpt-5.6", "chat")
    snapshot = state.snapshot()

    assert snapshot.selected_provider == "groq"
    assert snapshot.selected_model == "llama-3.1-8b-instant"
    assert snapshot.selection_mode == "manual"
    assert snapshot.last_success_provider == "openai"
    assert snapshot.last_success_model == "gpt-5.6"
    assert snapshot.last_success_capability == "chat"
    assert snapshot.request_count == 1
    assert not hasattr(snapshot, "prompt")
    assert not hasattr(snapshot, "response")
    assert not hasattr(snapshot, "api_key")


def test_last_success_pins_when_no_manual_selection():
    state = AIProviderSessionState()

    state.record_success("groq", "llama-3.1-8b-instant", "chat")

    assert state.selected_provider == "groq"
    assert state.selected_model == "llama-3.1-8b-instant"
    assert state.selection_mode == "last_success"


def test_command_processor_manual_selection_is_runtime_only_and_no_network():
    processor = CommandProcessor()

    result = processor.process("ai session select: groq llama-3.1-8b-instant")

    assert result["intent"] == "ai.session.select"
    assert "network: not called" in result["response"]
    assert processor.ai_provider_session_state.selected_provider == "groq"
    assert processor.ai_provider_session_state.selected_model == "llama-3.1-8b-instant"
    assert processor.ai_provider_router.get_default_provider().get_info().name == "dry_run"


def test_russian_manual_selection_command_is_runtime_only_and_no_network():
    processor = CommandProcessor()

    result = processor.process("выбрать ai модель groq llama-3.1-8b-instant")

    assert result["intent"] == "ai.session.select"
    assert "- provider: groq" in result["response"]
    assert "- model: llama-3.1-8b-instant" in result["response"]
    assert "network: not called" in result["response"]
    assert processor.ai_provider_session_state.selected_provider == "groq"
    assert processor.ai_provider_session_state.selected_model == "llama-3.1-8b-instant"


def test_continuation_without_pin_refuses_without_network():
    processor = CommandProcessor()

    result = processor.process("ai continue: hello")

    assert result["intent"] == "ai.session.continuation.unpinned"
    assert "no provider/model is pinned" in result["response"]
    assert "No network call was made" in result["response"]


def test_ai_continuation_is_not_voice_allowlisted():
    decision = SafeVoiceCommandAllowlist().decide("ai continue: hello")

    assert decision.allowed is False


def test_continuation_with_missing_key_keeps_manual_pin():
    processor = CommandProcessor()
    processor.process("ai session select: groq llama-3.1-8b-instant")

    result = processor.process("ai continue: hello")

    assert result["intent"] == "ai.session.continuation.groq.error"
    assert "GROQ_API_KEY is missing" in result["response"]
    assert processor.ai_provider_session_state.selected_provider == "groq"
    assert processor.ai_provider_session_state.selection_mode == "manual"


def test_successful_openai_continuation_uses_manual_model_override_and_records_success():
    client = FakeHTTPClient()
    environ = {"OPENAI_API_KEY": "fake-key"}
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ=environ),
        http_client=client,
        environ=environ,
    )
    processor = CommandProcessor(openai_request_gate=gate)
    processor.process("ai session select: openai gpt-5.6")

    result = processor.process("ai continue: hello")

    assert result["intent"] == "ai.session.continuation.openai"
    assert client.calls[0]["payload"]["model"] == "gpt-5.6"
    assert processor.ai_provider_session_state.selected_provider == "openai"
    assert processor.ai_provider_session_state.last_success_provider == "openai"
    assert processor.ai_provider_session_state.request_count == 1


def test_provider_specific_success_auto_pins_last_success():
    client = FakeHTTPClient()
    environ = {"OPENAI_API_KEY": "fake-key"}
    gate = OpenAIRequestGate(
        config_manager=AIProviderConfigManager(environ=environ),
        http_client=client,
        environ=environ,
    )
    processor = CommandProcessor(openai_request_gate=gate)

    result = processor.process("openai one shot: hello")

    assert result["intent"] == "ai.openai.one_shot"
    assert processor.ai_provider_session_state.selected_provider == "openai"
    assert processor.ai_provider_session_state.selection_mode == "last_success"
    assert processor.ai_provider_session_state.last_success_model == "gpt-5.6"
