from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction

import pytest

from cognition import (
    AssistantResponseType,
    ConversationContextContentClassification,
    ConversationContextSnapshot,
    ConversationContextTurn,
    ConversationRole,
    ConversationSessionClosedError,
    ConversationSessionNotFoundError,
    ConversationSessionService,
    ConversationSessionStatus,
    ConversationTurnInput,
    InvalidConversationTurnError,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    IntentInterpretationInput,
    InterpretedIntent,
    ResponseCompositionResult,
)


def test_conversation_turn_input_is_immutable_json_safe_and_validates_text():
    turn_input = ConversationTurnInput(
        text="hello api key=sk-test-1234567890secret",
        source="test",
    )

    assert turn_input.text == "hello [REDACTED]"
    assert turn_input.to_dict() == {
        "text": "hello [REDACTED]",
        "source": "test",
        "session_id": None,
        "locale": None,
    }
    with pytest.raises(FrozenInstanceError):
        turn_input.text = "changed"
    with pytest.raises(InvalidConversationTurnError):
        ConversationTurnInput(text=" ", source="test")


def test_session_creation_snapshot_and_unique_ids():
    service = ConversationSessionService()

    first = service.create_session()
    second = service.create_session()

    assert first.session_id.startswith("cog-session-")
    assert second.session_id.startswith("cog-session-")
    assert first.session_id != second.session_id
    assert first.status is ConversationSessionStatus.ACTIVE
    assert first.turn_count == 0
    assert first.last_turn_id is None
    assert first.to_dict()["status"] == "active"


def test_session_turns_are_ordered_and_turn_count_is_deterministic():
    service = ConversationSessionService()
    session = service.create_session()

    user = service.append_user_turn(session.session_id, "hello", "test")
    assistant = service.append_assistant_turn(session.session_id, "hi", "assistant")
    snapshot = service.get_snapshot(session.session_id)
    turns = service.turns_snapshot(session.session_id)

    assert [turn.sequence for turn in turns] == [1, 2]
    assert [turn.role for turn in turns] == [ConversationRole.USER, ConversationRole.ASSISTANT]
    assert snapshot.turn_count == 2
    assert snapshot.last_turn_id == assistant.turn_id
    assert user.turn_id != assistant.turn_id


def test_session_snapshots_and_turns_are_detached_from_internal_state():
    service = ConversationSessionService()
    session = service.create_session()
    service.append_user_turn(session.session_id, "hello", "test")

    turns = service.turns_snapshot(session.session_id)
    mutated_copy = turns + turns

    assert len(mutated_copy) == 2
    assert service.get_snapshot(session.session_id).turn_count == 1


def test_unknown_session_and_closed_session_fail_safely():
    service = ConversationSessionService()

    with pytest.raises(ConversationSessionNotFoundError):
        service.get_snapshot("missing")

    session = service.create_session()
    closed = service.close_session(session.session_id)

    assert closed.status is ConversationSessionStatus.CLOSED
    with pytest.raises(ConversationSessionClosedError):
        service.append_user_turn(session.session_id, "hello", "test")


def test_concurrent_session_creation_has_unique_stable_ids():
    service = ConversationSessionService()

    with ThreadPoolExecutor(max_workers=8) as executor:
        sessions = tuple(executor.map(lambda _: service.create_session(), range(40)))

    session_ids = {session.session_id for session in sessions}
    assert len(session_ids) == 40
    assert all(session.turn_count == 0 for session in sessions)


def test_concurrent_turn_append_preserves_per_session_sequence():
    service = ConversationSessionService()
    session = service.create_session()

    with ThreadPoolExecutor(max_workers=8) as executor:
        tuple(
            executor.map(
                lambda index: service.append_user_turn(
                    session.session_id,
                    f"turn {index}",
                    "test",
                ),
                range(50),
            )
        )

    turns = service.turns_snapshot(session.session_id)
    assert [turn.sequence for turn in turns] == list(range(1, 51))
    assert service.get_snapshot(session.session_id).turn_count == 50


def test_minimal_response_type_does_not_speculate_about_future_states():
    assert {item.value for item in AssistantResponseType} == {"message", "error"}


def test_context_contracts_are_immutable_json_safe_and_provider_neutral():
    context_turn = ConversationContextTurn(
        turn_id="turn-1",
        sequence=1,
        role=ConversationRole.USER,
        source="test",
        safe_text="hello api key=sk-test-1234567890secret",
        created_at="2026-07-29T00:00:00+00:00",
        content_classification=ConversationContextContentClassification.BOUNDED_SAFE_TEXT,
        redaction_reason="bounded",
    )
    context = ConversationContextSnapshot(
        session_id="cog-session-test",
        session_status=ConversationSessionStatus.ACTIVE,
        projected_at="2026-07-29T00:00:01+00:00",
        turns=(context_turn,),
        total_turn_count=1,
        included_turn_count=1,
        omitted_turn_count=0,
        first_included_sequence=1,
        last_included_sequence=1,
    )

    payload = context.to_dict()

    assert payload["turns"][0]["safe_text"] == "hello [REDACTED]"
    assert payload["turns"][0]["role"] == "user"
    assert payload["session_status"] == "active"
    assert "metadata" not in payload
    assert "provider" not in payload
    assert "token_count" not in payload
    with pytest.raises(FrozenInstanceError):
        context_turn.safe_text = "changed"


def test_context_contract_rejects_invalid_ordering_and_counts():
    later = ConversationContextTurn(
        turn_id="turn-2",
        sequence=2,
        role=ConversationRole.USER,
        source="test",
        safe_text="later",
        created_at="2026-07-29T00:00:02+00:00",
        content_classification=ConversationContextContentClassification.BOUNDED_SAFE_TEXT,
    )
    earlier = ConversationContextTurn(
        turn_id="turn-1",
        sequence=1,
        role=ConversationRole.USER,
        source="test",
        safe_text="earlier",
        created_at="2026-07-29T00:00:01+00:00",
        content_classification=ConversationContextContentClassification.BOUNDED_SAFE_TEXT,
    )

    with pytest.raises(InvalidConversationTurnError):
        ConversationContextSnapshot(
            session_id="cog-session-test",
            session_status=ConversationSessionStatus.ACTIVE,
            projected_at="2026-07-29T00:00:03+00:00",
            turns=(later, earlier),
            total_turn_count=2,
            included_turn_count=2,
            omitted_turn_count=0,
            first_included_sequence=2,
            last_included_sequence=1,
        )


def test_response_composition_result_is_immutable_and_rejects_bad_counts():
    result = ResponseCompositionResult(
        response_type=AssistantResponseType.MESSAGE,
        text="reply token=sk-test-1234567890secret",
        context_turn_count_used=1,
        composition_source="test",
    )

    assert result.to_dict() == {
        "response_type": "message",
        "text": "reply [REDACTED]",
        "context_turn_count_used": 1,
        "composition_source": "test",
    }
    with pytest.raises(FrozenInstanceError):
        result.text = "changed"
    with pytest.raises(InvalidConversationTurnError):
        ResponseCompositionResult(
            response_type=AssistantResponseType.MESSAGE,
            text="reply",
            context_turn_count_used=-1,
            composition_source="test",
        )


@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", None, Decimal("1"), Fraction(1, 1), 0, -1],
)
def test_context_turn_sequence_requires_strict_positive_integer(bad_value):
    with pytest.raises(InvalidConversationTurnError):
        ConversationContextTurn(
            turn_id="turn-1",
            sequence=bad_value,
            role=ConversationRole.USER,
            source="test",
            safe_text="hello",
            created_at="2026-07-29T00:00:00+00:00",
            content_classification=ConversationContextContentClassification.BOUNDED_SAFE_TEXT,
        )


@pytest.mark.parametrize(
    "field_name",
    ["total_turn_count", "included_turn_count", "omitted_turn_count"],
)
@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", None, Decimal("1"), Fraction(1, 1), -1],
)
def test_context_snapshot_counters_require_strict_nonnegative_integers(
    field_name,
    bad_value,
):
    values = {
        "session_id": "cog-session-test",
        "session_status": ConversationSessionStatus.ACTIVE,
        "projected_at": "2026-07-29T00:00:01+00:00",
        "turns": (),
        "total_turn_count": 0,
        "included_turn_count": 0,
        "omitted_turn_count": 0,
    }
    values[field_name] = bad_value

    with pytest.raises(InvalidConversationTurnError):
        ConversationContextSnapshot(**values)


@pytest.mark.parametrize(
    "field_name",
    ["first_included_sequence", "last_included_sequence"],
)
@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", Decimal("1"), Fraction(1, 1), 0, -1],
)
def test_context_snapshot_optional_sequences_require_strict_positive_integers(
    field_name,
    bad_value,
):
    values = {
        "session_id": "cog-session-test",
        "session_status": ConversationSessionStatus.ACTIVE,
        "projected_at": "2026-07-29T00:00:01+00:00",
        "turns": (),
        "total_turn_count": 0,
        "included_turn_count": 0,
        "omitted_turn_count": 0,
        field_name: bad_value,
    }

    with pytest.raises(InvalidConversationTurnError):
        ConversationContextSnapshot(**values)


@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", None, Decimal("1"), Fraction(1, 1), -1],
)
def test_response_composition_context_count_requires_strict_nonnegative_integer(
    bad_value,
):
    with pytest.raises(InvalidConversationTurnError):
        ResponseCompositionResult(
            response_type=AssistantResponseType.MESSAGE,
            text="reply",
            context_turn_count_used=bad_value,
            composition_source="test",
        )


def test_context_numeric_contracts_accept_plain_integers_only():
    context_turn = ConversationContextTurn(
        turn_id="turn-1",
        sequence=1,
        role=ConversationRole.USER,
        source="test",
        safe_text="hello",
        created_at="2026-07-29T00:00:00+00:00",
        content_classification=ConversationContextContentClassification.BOUNDED_SAFE_TEXT,
    )
    context = ConversationContextSnapshot(
        session_id="cog-session-test",
        session_status=ConversationSessionStatus.ACTIVE,
        projected_at="2026-07-29T00:00:01+00:00",
        turns=(context_turn,),
        total_turn_count=1,
        included_turn_count=1,
        omitted_turn_count=0,
        first_included_sequence=1,
        last_included_sequence=1,
    )
    result = ResponseCompositionResult(
        response_type=AssistantResponseType.MESSAGE,
        text="reply",
        context_turn_count_used=0,
        composition_source="test",
    )

    assert context.turns[0].sequence == 1
    assert context.omitted_turn_count == 0
    assert result.context_turn_count_used == 0


def test_intent_contracts_are_immutable_json_safe_and_provider_neutral():
    service = ConversationSessionService()
    session = service.create_session()
    user_turn = service.append_user_turn(
        session.session_id,
        "tell me token=sk-test-1234567890secret",
        "test",
    )
    context = ConversationContextSnapshot(
        session_id=session.session_id,
        session_status=ConversationSessionStatus.ACTIVE,
        projected_at="2026-07-29T00:00:01+00:00",
        turns=(),
        total_turn_count=0,
        included_turn_count=0,
        omitted_turn_count=0,
    )
    evidence = IntentEvidence(
        evidence_type="rule",
        safe_excerpt="matched token=sk-test-1234567890secret",
        rule_id="rule.test",
    )
    intent = InterpretedIntent(
        category=IntentCategory.INFORMATION_REQUEST,
        confidence=IntentConfidence.MEDIUM,
        safe_user_text=user_turn.text,
        evidence=(evidence,),
        requires_reference_resolution=False,
        may_require_clarification=False,
        is_actionable_request=False,
        interpreter_id="test",
        interpreter_version="1",
        context_turn_count_used=0,
    )
    interpretation_input = IntentInterpretationInput(
        current_user_turn=user_turn,
        context=context,
        source="test",
    )

    assert intent.to_dict() == {
        "category": "information_request",
        "confidence": "medium",
        "safe_user_text": "tell me [REDACTED]",
        "evidence": (
            {
                "evidence_type": "rule",
                "safe_excerpt": "matched [REDACTED]",
                "rule_id": "rule.test",
            },
        ),
        "requires_reference_resolution": False,
        "may_require_clarification": False,
        "is_actionable_request": False,
        "interpreter_id": "test",
        "interpreter_version": "1",
        "context_turn_count_used": 0,
    }
    assert interpretation_input.current_user_turn is user_turn
    assert "metadata" not in intent.to_dict()
    assert "provider" not in intent.to_dict()
    assert "command" not in intent.to_dict()
    with pytest.raises(FrozenInstanceError):
        intent.category = IntentCategory.UNKNOWN


def test_intent_evidence_is_bounded_and_rejects_empty_fields():
    evidence = IntentEvidence(
        evidence_type="rule",
        safe_excerpt="x" * 200,
        rule_id="rule.long",
    )

    assert len(evidence.safe_excerpt) <= 120
    with pytest.raises(InvalidConversationTurnError):
        IntentEvidence(evidence_type="", safe_excerpt="value", rule_id="rule.test")


@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", None, Decimal("1"), Fraction(1, 1), -1],
)
def test_intent_context_count_requires_strict_nonnegative_integer(bad_value):
    with pytest.raises(InvalidConversationTurnError):
        InterpretedIntent(
            category=IntentCategory.CONVERSATION,
            confidence=IntentConfidence.LOW,
            safe_user_text="hello",
            evidence=(
                IntentEvidence(
                    evidence_type="rule",
                    safe_excerpt="hello",
                    rule_id="rule.test",
                ),
            ),
            requires_reference_resolution=False,
            may_require_clarification=False,
            is_actionable_request=False,
            interpreter_id="test",
            interpreter_version="1",
            context_turn_count_used=bad_value,
        )
