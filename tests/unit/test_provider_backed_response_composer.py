from dataclasses import replace

from ai import AIProviderCapability, AIProviderSafetyLevel, AIResponse
from cognition import (
    AssistantResponseType,
    ClarificationReason,
    ClarificationRequest,
    ClarificationStatus,
    CompatibilityResponseComposer,
    ConversationContextProjector,
    ConversationSessionService,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    InterpretedIntent,
    ResponseCompositionInput,
)

from app.provider_backed_response_composer import ProviderBackedResponseComposer


class FakeGroqGate:
    def __init__(self, response=None, exception=None):
        self.response = response
        self.exception = exception
        self.calls = []

    def generate_one_shot(self, request, capability=AIProviderCapability.CHAT):
        self.calls.append((request, capability))
        if self.exception is not None:
            raise self.exception
        return self.response


def _response(text="Ответ Groq.", *, error=False):
    return AIResponse(
        text=text,
        provider_name="groq",
        model_name="llama-3.1-8b-instant",
        capability=AIProviderCapability.CHAT.value,
        safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
        is_error=error,
        error_message=text if error else None,
    )


def _composition_input(text="Что такое Земля?", *, prior_turns=()):
    sessions = ConversationSessionService()
    session = sessions.create_session()
    for role, prior_text in prior_turns:
        if role == "user":
            sessions.append_user_turn(session.session_id, prior_text, "test")
        else:
            sessions.append_assistant_turn(session.session_id, prior_text, "test")
    current = sessions.append_user_turn(session.session_id, text, "test")
    source_session, turns = sessions.context_source(session.session_id)
    context = ConversationContextProjector().project(source_session, turns)
    intent = InterpretedIntent(
        category=IntentCategory.QUESTION,
        confidence=IntentConfidence.HIGH,
        safe_user_text=text,
        evidence=(
            IntentEvidence(
                evidence_type="test",
                safe_excerpt=text,
                rule_id="test_question",
            ),
        ),
        requires_reference_resolution=False,
        may_require_clarification=False,
        is_actionable_request=False,
        interpreter_id="test",
        interpreter_version="1",
        context_turn_count_used=context.included_turn_count,
    )
    return ResponseCompositionInput(
        current_user_turn=current,
        context=context,
        source="test",
        locale="ru-RU",
        session=source_session,
        interpreted_intent=intent,
    )


def _composer(gate, fallback_calls):
    return ProviderBackedResponseComposer(
        request_gate=gate,
        fallback=CompatibilityResponseComposer(
            lambda received: fallback_calls.append(received) or "Локальный ответ."
        ),
    )


def test_provider_success_uses_bounded_safe_context_and_returns_untrusted_text_only():
    gate = FakeGroqGate(_response("Земля — третья планета от Солнца."))
    fallback_calls = []
    composition_input = _composition_input(
        prior_turns=(("user", "Мы говорили о космосе."), ("assistant", "Да.")),
    )

    result = _composer(gate, fallback_calls).compose(composition_input)

    assert len(gate.calls) == 1
    request, capability = gate.calls[0]
    assert capability is AIProviderCapability.CHAT
    assert "Мы говорили о космосе." in request.prompt
    assert "Что такое Земля?" in request.prompt
    assert len(request.prompt) <= 900
    assert request.language == "ru"
    assert request.metadata == {"max_output_tokens": "256"}
    assert fallback_calls == []
    assert result.response_type is AssistantResponseType.MESSAGE
    assert result.text == "Земля — третья планета от Солнца."
    assert result.context_turn_count_used == 3
    assert result.composition_source == "primary_provider:groq"


def test_provider_error_or_exception_degrades_to_deterministic_fallback():
    for gate in (
        FakeGroqGate(_response("safe provider error", error=True)),
        FakeGroqGate(exception=RuntimeError("secret local path C:\\private\\token")),
    ):
        fallback_calls = []
        result = _composer(gate, fallback_calls).compose(_composition_input())

        assert len(gate.calls) == 1
        assert len(fallback_calls) == 1
        assert result.text == "Локальный ответ."
        assert "safe provider error" not in result.composition_source
        assert "private" not in result.composition_source
        assert result.composition_source.endswith(
            ":primary_provider=groq,status=fallback"
        )


def test_current_secret_is_not_sent_to_provider_and_falls_back_locally():
    secret = "gsk_test-secret-1234567890"
    gate = FakeGroqGate(_response())
    fallback_calls = []

    result = _composer(gate, fallback_calls).compose(
        _composition_input(f"Объясни этот token={secret}")
    )

    assert gate.calls == []
    assert len(fallback_calls) == 1
    assert secret not in result.text
    assert secret not in result.composition_source
    assert result.composition_source.endswith(
        ":primary_provider=groq,status=privacy_fallback"
    )


def test_clarification_is_owned_by_deterministic_fallback_without_provider_call():
    gate = FakeGroqGate(_response())
    fallback_calls = []
    composition_input = _composition_input("да")
    composition_input = replace(
        composition_input,
        clarification_request=ClarificationRequest(
            status=ClarificationStatus.UNAVAILABLE,
            reason=ClarificationReason.INSUFFICIENT_CONTEXT,
            safe_question=None,
            options=(),
            related_reference_count=0,
            context_turn_count_used=1,
            coordinator_id="test",
            coordinator_version="1",
            rule_id="test_rule",
        ),
    )

    result = _composer(gate, fallback_calls).compose(composition_input)

    assert gate.calls == []
    assert fallback_calls == []
    assert result.text == "Уточните, пожалуйста, что именно вы имеете в виду."
    assert "primary_provider" not in result.composition_source


def test_diagnostic_repr_does_not_include_gate_or_fallback_secrets():
    secret = "gsk_repr-secret-1234567890"
    gate = FakeGroqGate(_response(secret))
    composer = _composer(gate, [])

    diagnostic = repr(composer)

    assert secret not in diagnostic
    assert "request_gate" not in diagnostic
    assert "fallback" not in diagnostic
    assert diagnostic == "ProviderBackedResponseComposer(primary_provider='groq')"
