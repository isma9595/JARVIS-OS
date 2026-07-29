from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction

import pytest

from cognition import (
    ConversationContextContentClassification,
    ConversationContextProjector,
    ConversationRole,
    ConversationSessionNotFoundError,
    ConversationSessionService,
    ConversationSessionStatus,
    InvalidConversationTurnError,
)


def _session_with_turns(count: int) -> tuple[ConversationSessionService, str]:
    service = ConversationSessionService()
    session = service.create_session()
    for index in range(1, count + 1):
        service.append_user_turn(session.session_id, f"turn {index}", "test")
    return service, session.session_id


def test_empty_context_is_valid_and_immutable():
    service = ConversationSessionService()
    session = service.create_session()
    source_session, turns = service.context_source(session.session_id)

    context = ConversationContextProjector().project(source_session, turns)

    assert context.turns == ()
    assert context.total_turn_count == 0
    assert context.included_turn_count == 0
    assert context.omitted_turn_count == 0
    assert context.truncation_reason is None
    with pytest.raises(FrozenInstanceError):
        context.session_id = "changed"


def test_context_preserves_chronological_order_and_retains_newest_turns():
    service, session_id = _session_with_turns(5)
    source_session, turns = service.context_source(session_id)

    context = ConversationContextProjector(max_turns=3).project(source_session, turns)

    assert [turn.sequence for turn in context.turns] == [3, 4, 5]
    assert [turn.safe_text for turn in context.turns] == ["turn 3", "turn 4", "turn 5"]
    assert context.total_turn_count == 5
    assert context.included_turn_count == 3
    assert context.omitted_turn_count == 2
    assert context.first_included_sequence == 3
    assert context.last_included_sequence == 5
    assert context.truncation_reason == "turn_limit"


def test_context_applies_per_turn_and_total_character_bounds_deterministically():
    service = ConversationSessionService()
    session = service.create_session()
    service.append_user_turn(session.session_id, "alpha bravo charlie", "test")
    service.append_user_turn(session.session_id, "delta echo foxtrot", "test")
    service.append_user_turn(session.session_id, "golf hotel india", "test")
    source_session, turns = service.context_source(session.session_id)

    projector = ConversationContextProjector(
        max_turns=5,
        max_turn_chars=10,
        max_total_chars=18,
    )
    first = projector.project(source_session, turns)
    second = projector.project(source_session, turns)

    assert first.to_dict()["turns"] == second.to_dict()["turns"]
    assert sum(len(turn.safe_text) for turn in first.turns) <= 18
    assert all(len(turn.safe_text) <= 10 for turn in first.turns)
    assert [turn.sequence for turn in first.turns] == sorted(
        turn.sequence for turn in first.turns
    )
    assert first.truncation_reason == "total_character_limit"


def test_context_redacts_sensitive_text_and_does_not_mutate_authoritative_state():
    service = ConversationSessionService()
    session = service.create_session()
    service.append_user_turn(
        session.session_id,
        "use token=sk-test-1234567890secret now",
        "test",
    )
    source_session, turns = service.context_source(session.session_id)

    context = ConversationContextProjector().project(source_session, turns)

    assert context.turns[0].safe_text == "[redacted sensitive content]"
    assert context.turns[0].content_classification is (
        ConversationContextContentClassification.REDACTED_SENSITIVE_CONTENT
    )
    assert "sk-test" not in str(context.to_dict())
    assert service.turns_snapshot(session.session_id)[0].text == "use [REDACTED] now"
    assert service.get_snapshot(session.session_id).turn_count == 1


def test_closed_session_context_remains_inspectable_and_unknown_session_is_typed():
    service = ConversationSessionService()
    session = service.create_session()
    service.append_user_turn(session.session_id, "hello", "test")
    service.close_session(session.session_id)

    source_session, turns = service.context_source(session.session_id)
    context = ConversationContextProjector().project(source_session, turns)

    assert context.session_status is ConversationSessionStatus.CLOSED
    assert context.included_turn_count == 1
    with pytest.raises(ConversationSessionNotFoundError):
        service.context_source("missing")


def test_projector_rejects_invalid_bounds_and_misordered_source_turns():
    with pytest.raises(InvalidConversationTurnError):
        ConversationContextProjector(max_turns=0)

    service, session_id = _session_with_turns(2)
    source_session, turns = service.context_source(session_id)

    with pytest.raises(InvalidConversationTurnError):
        ConversationContextProjector().project(source_session, tuple(reversed(turns)))


@pytest.mark.parametrize("field_name", ["max_turns", "max_turn_chars", "max_total_chars"])
@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", None, Decimal("1"), Fraction(1, 1), 0, -1],
)
def test_projector_bounds_require_strict_positive_integers(field_name, bad_value):
    kwargs = {
        "max_turns": 1,
        "max_turn_chars": 1,
        "max_total_chars": 1,
    }
    kwargs[field_name] = bad_value

    with pytest.raises(InvalidConversationTurnError):
        ConversationContextProjector(**kwargs)


def test_projector_bounds_accept_representative_plain_positive_integers():
    projector = ConversationContextProjector(
        max_turns=1,
        max_turn_chars=160,
        max_total_chars=800,
    )

    assert projector.max_turns == 1
    assert projector.max_turn_chars == 160
    assert projector.max_total_chars == 800


def test_context_contract_rejects_malformed_counts():
    service, session_id = _session_with_turns(1)
    source_session, turns = service.context_source(session_id)
    context = ConversationContextProjector().project(source_session, turns)

    with pytest.raises(InvalidConversationTurnError):
        context.__class__(
            session_id=context.session_id,
            session_status=context.session_status,
            projected_at=context.projected_at,
            turns=context.turns,
            total_turn_count=2,
            included_turn_count=1,
            omitted_turn_count=0,
            first_included_sequence=1,
            last_included_sequence=1,
        )


def test_context_projection_does_not_write_to_repository():
    class ReadOnlyRepository:
        def load_records(self):
            from cognition import ConversationPersistenceLoadResult

            return ConversationPersistenceLoadResult()

        def save_record(self, record):
            raise AssertionError("projection must not persist")

        def delete_record(self, session_id):
            raise AssertionError("projection must not delete")

        def close(self):
            return None

    service = ConversationSessionService(repository=ReadOnlyRepository(), load_persisted=True)
    memory_only = ConversationSessionService()
    session = memory_only.create_session()
    memory_only.append_user_turn(session.session_id, "hello", "test")
    source_session, turns = memory_only.context_source(session.session_id)

    context = ConversationContextProjector().project(source_session, turns)

    assert context.included_turn_count == 1
    assert service.persistence_load_result.loaded_count == 0
