from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction

import pytest

from cognition import (
    ClarificationCoordinationInput,
    ClarificationOption,
    ClarificationReason,
    ClarificationRequest,
    ClarificationStatus,
    ConversationContextProjector,
    ConversationRole,
    ConversationSessionService,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    InterpretedIntent,
    InvalidClarificationInputError,
    InvalidConversationTurnError,
    ReferenceCandidate,
    ReferenceResolutionInput,
    ReferenceResolutionResult,
    ReferenceResolutionStatus,
    RuleBasedClarificationCoordinator,
    RuleBasedReferenceResolver,
)
from cognition.contracts import (
    MAX_CLARIFICATION_COORDINATOR_ID_LENGTH,
    MAX_CLARIFICATION_COORDINATOR_VERSION_LENGTH,
    MAX_CLARIFICATION_RULE_ID_LENGTH,
)


def _intent(category=IntentCategory.CONVERSATION, text="hello"):
    return InterpretedIntent(
        category=category,
        confidence=IntentConfidence.MEDIUM,
        safe_user_text=text,
        evidence=(IntentEvidence(evidence_type="rule", safe_excerpt=text, rule_id="test"),),
        requires_reference_resolution=False,
        may_require_clarification=category is IntentCategory.ACTION_REQUEST,
        is_actionable_request=category is IntentCategory.ACTION_REQUEST,
        interpreter_id="test",
        interpreter_version="1",
        context_turn_count_used=1,
    )


def _coordination_input(*turns, current_text="hello", category=IntentCategory.CONVERSATION):
    session_service = ConversationSessionService()
    session = session_service.create_session()
    for role, text in turns:
        if role == "assistant":
            session_service.append_assistant_turn(session.session_id, text, "assistant")
        else:
            session_service.append_user_turn(session.session_id, text, "test")
    current_turn = session_service.append_user_turn(session.session_id, current_text, "test")
    source_session, source_turns = session_service.context_source(session.session_id)
    context = ConversationContextProjector().project(source_session, source_turns)
    intent = _intent(category, current_text)
    references = RuleBasedReferenceResolver().resolve(
        ReferenceResolutionInput(
            current_user_turn=current_turn,
            context=context,
            interpreted_intent=intent,
        )
    )
    return session_service, ClarificationCoordinationInput(
        current_user_turn=current_turn,
        context=context,
        interpreted_intent=intent,
        reference_resolution=references,
    )


def _coordinate(coordination_input):
    return RuleBasedClarificationCoordinator().coordinate(coordination_input)


def _clarification_request_values(**overrides):
    values = {
        "status": ClarificationStatus.NEEDED,
        "reason": ClarificationReason.UNCLEAR_CONFIRMATION,
        "safe_question": "What are you confirming?",
        "options": (),
        "related_reference_count": 0,
        "context_turn_count_used": 0,
        "coordinator_id": "test",
        "coordinator_version": "1",
        "rule_id": "test_rule",
    }
    values.update(overrides)
    return values


def test_clarification_contracts_are_immutable_json_safe_and_provider_neutral():
    option = ClarificationOption(
        safe_label="Previous assistant response",
        candidate_turn_sequence=1,
        candidate_id=None,
        safe_excerpt="secret api key=sk-test-1234567890secret",
        source_reason="bounded_context_turn",
        ordinal=1,
    )
    request = ClarificationRequest(
        status=ClarificationStatus.NEEDED,
        reason=ClarificationReason.AMBIGUOUS_REFERENCE,
        safe_question="Which one token=sk-test-1234567890secret?",
        options=(option,),
        related_reference_count=1,
        context_turn_count_used=2,
        coordinator_id="test",
        coordinator_version="1",
        rule_id="test_rule",
    )

    assert request.to_dict() == {
        "status": "needed",
        "reason": "ambiguous_reference",
        "safe_question": "Which one [REDACTED]",
        "options": (
            {
                "safe_label": "Previous assistant response",
                "candidate_turn_sequence": 1,
                "candidate_id": None,
                "safe_excerpt": "secret [REDACTED]",
                "source_reason": "bounded_context_turn",
                "ordinal": 1,
            },
        ),
        "related_reference_count": 1,
        "context_turn_count_used": 2,
        "coordinator_id": "test",
        "coordinator_version": "1",
        "rule_id": "test_rule",
    }
    assert "metadata" not in request.to_dict()
    assert "command" not in request.to_dict()
    assert "workflow" not in request.to_dict()
    assert "provider" not in request.to_dict()
    with pytest.raises(FrozenInstanceError):
        request.status = ClarificationStatus.NOT_NEEDED


@pytest.mark.parametrize(
    "field_name",
    ["candidate_turn_sequence", "ordinal"],
)
@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", None, Decimal("1"), Fraction(1, 1), 0, -1],
)
def test_clarification_option_integer_fields_are_strict(field_name, bad_value):
    values = {
        "safe_label": "Previous user request",
        "candidate_turn_sequence": 1,
        "candidate_id": None,
        "safe_excerpt": "safe",
        "source_reason": "test",
        "ordinal": 1,
    }
    values[field_name] = bad_value
    if field_name == "candidate_turn_sequence" and bad_value is None:
        values["candidate_id"] = None

    with pytest.raises(InvalidConversationTurnError):
        ClarificationOption(**values)


@pytest.mark.parametrize(
    "field_name",
    ["related_reference_count", "context_turn_count_used"],
)
@pytest.mark.parametrize(
    "bad_value",
    [True, False, 1.0, 1.5, "1", None, Decimal("1"), Fraction(1, 1), -1],
)
def test_clarification_request_integer_fields_are_strict(field_name, bad_value):
    with pytest.raises(InvalidConversationTurnError):
        ClarificationRequest(
            **_clarification_request_values(**{field_name: bad_value})
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("status", "approved"),
        ("status", True),
        ("reason", "authorization_denied"),
        ("reason", "_".join(("missing", "subject"))),
        ("reason", "_".join(("conflicting", "signals"))),
        ("reason", object()),
    ],
)
def test_clarification_request_enum_fields_are_validated(field_name, bad_value):
    with pytest.raises(InvalidConversationTurnError):
        ClarificationRequest(
            **_clarification_request_values(**{field_name: bad_value})
        )


def test_clarification_reason_enum_matches_implemented_deterministic_rules():
    assert {reason.value for reason in ClarificationReason} == {
        "ambiguous_reference",
        "unresolved_reference",
        "unclear_confirmation",
        "unclear_rejection",
        "insufficient_context",
        "unsupported_ambiguity",
        "none",
    }


def test_remaining_clarification_reasons_are_emitted_by_coordinator_rules():
    observed = set()
    scenarios = (
        _coordination_input(
            ("user", "first target"),
            ("assistant", "second target"),
            current_text="do it",
            category=IntentCategory.ACTION_REQUEST,
        )[1],
        _coordination_input(
            ("user", "same target"),
            ("user", "same target"),
            current_text="do it",
            category=IntentCategory.ACTION_REQUEST,
        )[1],
        _coordination_input(
            current_text="do it",
            category=IntentCategory.ACTION_REQUEST,
        )[1],
        _coordination_input(
            current_text="yes",
            category=IntentCategory.CONFIRMATION,
        )[1],
        _coordination_input(
            current_text="no",
            category=IntentCategory.REJECTION,
        )[1],
        _coordination_input(
            current_text="the first one",
            category=IntentCategory.CLARIFICATION_RESPONSE,
        )[1],
        _coordination_input(current_text="hello")[1],
    )

    for scenario in scenarios:
        observed.add(_coordinate(scenario).reason)

    assert observed == set(ClarificationReason)


@pytest.mark.parametrize(
    ("field_name", "max_length"),
    [
        ("coordinator_id", MAX_CLARIFICATION_COORDINATOR_ID_LENGTH),
        ("coordinator_version", MAX_CLARIFICATION_COORDINATOR_VERSION_LENGTH),
        ("rule_id", MAX_CLARIFICATION_RULE_ID_LENGTH),
    ],
)
def test_clarification_provenance_fields_are_bounded_redacted_and_required(
    field_name,
    max_length,
):
    long_secret_value = "prefix " + ("x" * (max_length + 30)) + " token=sk-test-1234567890secret"

    request = ClarificationRequest(
        **_clarification_request_values(**{field_name: long_secret_value})
    )

    value = getattr(request, field_name)
    assert len(value) <= max_length
    assert "sk-test" not in value
    assert str(request.to_dict()[field_name]) == value

    for bad_value in (
        "",
        "   ",
        None,
        True,
        False,
        object(),
        "token=sk-test-1234567890secret",
        "[redacted sensitive content]",
    ):
        with pytest.raises(InvalidConversationTurnError):
            ClarificationRequest(
                **_clarification_request_values(**{field_name: bad_value})
            )


def test_no_ambiguity_and_unique_reference_are_not_needed():
    _, none_input = _coordination_input(current_text="hello")
    _, resolved_input = _coordination_input(
        ("assistant", "single target"),
        current_text="do it",
        category=IntentCategory.ACTION_REQUEST,
    )

    assert _coordinate(none_input).status is ClarificationStatus.NOT_NEEDED
    assert _coordinate(resolved_input).status is ClarificationStatus.NOT_NEEDED


def test_ambiguous_reference_with_distinguishable_candidates_needs_one_question():
    _, coordination_input = _coordination_input(
        ("user", "first target"),
        ("assistant", "second target"),
        current_text="do it",
        category=IntentCategory.ACTION_REQUEST,
    )

    first = _coordinate(coordination_input)
    second = _coordinate(coordination_input)

    assert first.to_dict() == second.to_dict()
    assert first.status is ClarificationStatus.NEEDED
    assert first.reason is ClarificationReason.AMBIGUOUS_REFERENCE
    assert first.safe_question == "Which one did you mean?"
    assert [option.safe_excerpt for option in first.options] == [
        "second target",
        "first target",
    ]
    assert [option.ordinal for option in first.options] == [1, 2]
    assert coordination_input.reference_resolution.references[0].status is (
        ReferenceResolutionStatus.AMBIGUOUS
    )
    assert coordination_input.reference_resolution.references[0].selected_candidate is None


def test_ambiguous_reference_with_indistinguishable_options_is_unavailable():
    _, coordination_input = _coordination_input(
        ("user", "same target"),
        ("user", "same target"),
        current_text="do it",
        category=IntentCategory.ACTION_REQUEST,
    )

    result = _coordinate(coordination_input)

    assert result.status is ClarificationStatus.UNAVAILABLE
    assert result.reason is ClarificationReason.UNSUPPORTED_AMBIGUITY
    assert result.options == ()


def test_unresolved_action_reference_needs_referent_question_without_command_reconstruction():
    _, coordination_input = _coordination_input(
        current_text="do it",
        category=IntentCategory.ACTION_REQUEST,
    )

    result = _coordinate(coordination_input)

    assert result.status is ClarificationStatus.NEEDED
    assert result.reason is ClarificationReason.UNRESOLVED_REFERENCE
    assert result.safe_question == "What does 'it' refer to?"
    assert "do it" not in result.safe_question.casefold()
    assert result.options == ()


def test_unresolved_ordinary_conversation_reference_is_not_needed():
    _, coordination_input = _coordination_input(current_text="that")

    result = _coordinate(coordination_input)

    assert result.status is ClarificationStatus.NOT_NEEDED


def test_cancellation_suppresses_clarification():
    _, coordination_input = _coordination_input(
        ("assistant", "target"),
        current_text="cancel",
        category=IntentCategory.CANCELLATION,
    )

    assert _coordinate(coordination_input).status is ClarificationStatus.NOT_NEEDED


def test_confirmation_and_rejection_target_rules_are_deterministic():
    _, confirmation_clear = _coordination_input(
        ("assistant", "Which one did you mean?"),
        current_text="yes",
        category=IntentCategory.CONFIRMATION,
    )
    _, confirmation_unclear = _coordination_input(
        current_text="yes",
        category=IntentCategory.CONFIRMATION,
    )
    _, rejection_clear = _coordination_input(
        ("assistant", "Which one did you mean?"),
        current_text="no",
        category=IntentCategory.REJECTION,
    )
    _, rejection_unclear = _coordination_input(
        current_text="no",
        category=IntentCategory.REJECTION,
    )

    assert _coordinate(confirmation_clear).status is ClarificationStatus.NOT_NEEDED
    assert _coordinate(confirmation_unclear).safe_question == "What are you confirming?"
    assert _coordinate(rejection_clear).status is ClarificationStatus.NOT_NEEDED
    assert _coordinate(rejection_unclear).safe_question == "What are you rejecting?"


def test_clarification_response_without_prior_question_is_unavailable():
    _, clear = _coordination_input(
        ("assistant", "Which one did you mean?"),
        current_text="the first one",
        category=IntentCategory.CLARIFICATION_RESPONSE,
    )
    _, missing = _coordination_input(
        current_text="the first one",
        category=IntentCategory.CLARIFICATION_RESPONSE,
    )

    assert _coordinate(clear).status is ClarificationStatus.NOT_NEEDED
    assert _coordinate(missing).status is ClarificationStatus.UNAVAILABLE


def test_russian_templates_are_narrow_and_deterministic():
    _, coordination_input = _coordination_input(
        current_text="\u0441\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e",
        category=IntentCategory.ACTION_REQUEST,
    )

    result = _coordinate(coordination_input)

    assert result.status is ClarificationStatus.NEEDED
    assert result.safe_question == "\u041a \u0447\u0435\u043c\u0443 \u043e\u0442\u043d\u043e\u0441\u0438\u0442\u0441\u044f \u00ab\u044d\u0442\u043e\u00bb?"
    assert "\u0441\u0434\u0435\u043b\u0430\u0439" not in result.safe_question.casefold()


def test_options_are_bounded_redacted_and_input_is_not_mutated():
    candidates = tuple(
        ReferenceCandidate(
            turn_id=f"turn-{index}",
            turn_sequence=index,
            role=ConversationRole.USER,
            safe_excerpt=f"candidate {index} token=sk-test-1234567890secret",
            match_reason="bounded_context_turn",
            recency_rank=index,
            confidence=IntentConfidence.LOW,
        )
        for index in range(1, 6)
    )
    _, coordination_input = _coordination_input(current_text="do it")
    reference = coordination_input.reference_resolution.references[0]
    rebuilt = ReferenceResolutionResult(
        references=(
            type(reference)(
                detected_reference=reference.detected_reference,
                status=ReferenceResolutionStatus.AMBIGUOUS,
                selected_candidate=None,
                candidates=candidates,
                confidence=IntentConfidence.LOW,
                context_turn_count_used=1,
                resolver_id="test",
                resolver_version="1",
            ),
        ),
        has_unresolved_references=False,
        has_ambiguous_references=True,
        context_turn_count_used=1,
        resolver_id="test",
        resolver_version="1",
    )
    rebuilt_input = ClarificationCoordinationInput(
        current_user_turn=coordination_input.current_user_turn,
        context=coordination_input.context,
        interpreted_intent=coordination_input.interpreted_intent,
        reference_resolution=rebuilt,
    )

    result = _coordinate(rebuilt_input)

    assert len(result.options) == 3
    assert "sk-test" not in str(result.to_dict())
    assert rebuilt.references[0].candidates == candidates


def test_malformed_input_uses_typed_error_and_coordinator_has_no_hidden_state():
    coordinator = RuleBasedClarificationCoordinator()

    with pytest.raises(InvalidClarificationInputError):
        coordinator.coordinate(object())
    assert coordinator.__dict__ == {
        "coordinator_id": "rule_based_clarification_coordinator",
        "coordinator_version": "1",
    }
