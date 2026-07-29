from dataclasses import FrozenInstanceError

import pytest

from cognition import (
    ConversationContextProjector,
    ConversationRole,
    ConversationSessionService,
    IntentCategory,
    IntentConfidence,
    IntentInterpretationInput,
    InvalidIntentInputError,
    RuleBasedIntentInterpreter,
)


def _input_for(text: str, *, assistant_prompt: str | None = None):
    session_service = ConversationSessionService()
    session = session_service.create_session()
    if assistant_prompt is not None:
        session_service.append_assistant_turn(session.session_id, assistant_prompt, "assistant")
    user_turn = session_service.append_user_turn(session.session_id, text, "test")
    source_session, turns = session_service.context_source(session.session_id)
    context = ConversationContextProjector().project(source_session, turns)
    return session_service, IntentInterpretationInput(
        current_user_turn=user_turn,
        context=context,
        source="test",
        locale="en-US",
    )


@pytest.mark.parametrize(
    ("text", "category", "confidence"),
    [
        ("token=sk-test-1234567890secret", IntentCategory.UNKNOWN, IntentConfidence.LOW),
        ("hello there", IntentCategory.CONVERSATION, IntentConfidence.LOW),
        ("what is the status?", IntentCategory.QUESTION, IntentConfidence.MEDIUM),
        ("tell me about sessions", IntentCategory.INFORMATION_REQUEST, IntentConfidence.MEDIUM),
        ("open settings", IntentCategory.ACTION_REQUEST, IntentConfidence.MEDIUM),
        ("cancel", IntentCategory.CANCELLATION, IntentConfidence.HIGH),
        ("confirm", IntentCategory.CONFIRMATION, IntentConfidence.HIGH),
        ("no", IntentCategory.REJECTION, IntentConfidence.HIGH),
        ("\u0447\u0442\u043e \u044d\u0442\u043e?", IntentCategory.QUESTION, IntentConfidence.MEDIUM),
        ("\u0437\u0430\u043f\u0443\u0441\u0442\u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0443", IntentCategory.ACTION_REQUEST, IntentConfidence.MEDIUM),
    ],
)
def test_rule_based_interpreter_classifies_broad_intent_deterministically(
    text,
    category,
    confidence,
):
    _, interpretation_input = _input_for(text)
    interpreter = RuleBasedIntentInterpreter()

    first = interpreter.interpret(interpretation_input)
    second = interpreter.interpret(interpretation_input)

    assert first.category is category
    assert first.confidence is confidence
    assert first.to_dict() == second.to_dict()
    assert first.context_turn_count_used == interpretation_input.context.included_turn_count
    assert first.interpreter_id == "rule_based_intent_interpreter"
    assert first.interpreter_version == "1"


def test_clarification_response_requires_prior_assistant_question_context():
    _, standalone = _input_for("yes")
    _, contextual = _input_for("yes", assistant_prompt="Which file should I use?")
    interpreter = RuleBasedIntentInterpreter()

    standalone_intent = interpreter.interpret(standalone)
    contextual_intent = interpreter.interpret(contextual)

    assert standalone_intent.category is IntentCategory.CONFIRMATION
    assert contextual_intent.category is IntentCategory.CLARIFICATION_RESPONSE
    assert contextual_intent.evidence[0].rule_id == "prior_assistant_question"
    assert "Which file" in contextual_intent.evidence[0].safe_excerpt


def test_interpreter_uses_chronological_context_and_current_turn_only():
    session_service = ConversationSessionService()
    session = session_service.create_session()
    session_service.append_assistant_turn(session.session_id, "Which file?", "assistant")
    first_user = session_service.append_user_turn(session.session_id, "project.md", "test")
    session_service.append_assistant_turn(session.session_id, "Thanks.", "assistant")
    current_user = session_service.append_user_turn(session.session_id, "yes", "test")
    source_session, turns = session_service.context_source(session.session_id)
    context = ConversationContextProjector().project(source_session, turns)

    intent = RuleBasedIntentInterpreter().interpret(
        IntentInterpretationInput(
            current_user_turn=current_user,
            context=context,
            source="test",
        )
    )

    assert first_user.sequence < current_user.sequence
    assert intent.category is IntentCategory.CONFIRMATION


def test_interpreter_output_is_safe_bounded_and_immutable():
    _, interpretation_input = _input_for(
        "tell me " + ("x" * 400) + " token=sk-test-1234567890secret"
    )

    intent = RuleBasedIntentInterpreter().interpret(interpretation_input)

    assert len(intent.safe_user_text) <= 240
    assert len(intent.evidence[0].safe_excerpt) <= 120
    assert "sk-test" not in str(intent.to_dict())
    with pytest.raises(FrozenInstanceError):
        intent.safe_user_text = "changed"


def test_interpreter_rejects_malformed_input_with_typed_error():
    with pytest.raises(InvalidIntentInputError):
        RuleBasedIntentInterpreter().interpret(object())


def test_interpreter_does_not_mutate_session_or_context():
    session_service, interpretation_input = _input_for("open settings")
    before = session_service.turns_snapshot(
        interpretation_input.current_user_turn.session_id
    )

    intent = RuleBasedIntentInterpreter().interpret(interpretation_input)
    after = session_service.turns_snapshot(interpretation_input.current_user_turn.session_id)

    assert intent.is_actionable_request is True
    assert [(turn.sequence, turn.role) for turn in before] == [
        (turn.sequence, turn.role) for turn in after
    ]
    assert interpretation_input.context.turns[-1].safe_text == "open settings"
