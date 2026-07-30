import ast
import builtins
import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path
import subprocess
import sys

import pytest

from cognition import (
    BOUNDED_CANDIDATE_TTL_SECONDS,
    ExistingMemoryRecordSummary,
    MemoryMutationInstruction,
    MemoryOrigin,
    MemoryPolicy,
    MemoryPolicyDecision,
    MemoryPolicyDecisionType,
    MemoryPolicyOperation,
    MemoryPolicyReasonCode,
    MemoryPolicyRequest,
    MemoryRetentionClass,
    MemorySensitivity,
    MemorySubjectKind,
)


def _record(
    record_id="memory-1",
    key="favorite color",
    value="green",
):
    return ExistingMemoryRecordSummary(
        record_id=record_id,
        key=key,
        value=value,
    )


def _request(
    *,
    operation=MemoryPolicyOperation.UPSERT,
    origin=MemoryOrigin.EXPLICIT_USER_COMMAND,
    subject_kind=MemorySubjectKind.USER_FACT,
    key="favorite color",
    value="green",
    target_record_id=None,
    existing_records=(),
    approval_verified=False,
):
    return MemoryPolicyRequest(
        operation=operation,
        origin=origin,
        subject_kind=subject_kind,
        key=key,
        value=value,
        target_record_id=target_record_id,
        existing_records=existing_records,
        approval_verified=approval_verified,
    )


def _reason_values(decision):
    return tuple(reason.value for reason in decision.reason_codes)


def test_safe_explicit_fact_is_allowed_until_user_forgets():
    decision = MemoryPolicy().evaluate(_request())

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.mutation_instruction is MemoryMutationInstruction.CREATE
    assert decision.retention_class is MemoryRetentionClass.UNTIL_USER_FORGETS
    assert decision.retention_duration_seconds is None
    assert decision.approval_required is False
    assert decision.sensitivity is MemorySensitivity.GENERAL_PERSONAL
    assert _reason_values(decision) == ("allowed_explicit_user_fact",)


def test_inferred_fact_requires_approval_and_uses_bounded_candidate_ttl():
    decision = MemoryPolicy().evaluate(
        _request(origin=MemoryOrigin.INFERRED_CONVERSATION)
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REQUIRE_APPROVAL
    assert decision.approval_required is True
    assert decision.mutation_instruction is MemoryMutationInstruction.CREATE
    assert decision.retention_class is MemoryRetentionClass.BOUNDED_CANDIDATE
    assert decision.retention_duration_seconds == 86_400
    assert BOUNDED_CANDIDATE_TTL_SECONDS == 86_400
    assert _reason_values(decision) == ("approval_required_for_inferred_fact",)


def test_approved_inferred_fact_is_allowed_until_forgotten():
    decision = MemoryPolicy().evaluate(
        _request(
            origin=MemoryOrigin.INFERRED_CONVERSATION,
            approval_verified=True,
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.approval_required is False
    assert decision.retention_class is MemoryRetentionClass.UNTIL_USER_FORGETS
    assert decision.retention_duration_seconds is None
    assert _reason_values(decision) == ("approved_inferred_fact",)


@pytest.mark.parametrize(
    "origin",
    [MemoryOrigin.SYSTEM_DERIVED, MemoryOrigin.PROVIDER_DERIVED],
)
def test_derived_fact_without_approval_is_rejected(origin):
    decision = MemoryPolicy().evaluate(_request(origin=origin))

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.approval_required is False
    assert decision.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert decision.mutation_instruction is None
    assert _reason_values(decision) == ("derived_write_rejected",)


@pytest.mark.parametrize(
    "origin",
    [MemoryOrigin.SYSTEM_DERIVED, MemoryOrigin.PROVIDER_DERIVED],
)
def test_approved_derived_fact_is_allowed(origin):
    decision = MemoryPolicy().evaluate(
        _request(origin=origin, approval_verified=True)
    )

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.mutation_instruction is MemoryMutationInstruction.CREATE
    assert decision.retention_class is MemoryRetentionClass.UNTIL_USER_FORGETS
    assert _reason_values(decision) == ("approved_derived_fact",)


@pytest.mark.parametrize("origin", tuple(MemoryOrigin))
@pytest.mark.parametrize("approval_verified", [False, True])
@pytest.mark.parametrize(
    "secret",
    [
        "api key sk-test-1234567890secret",
        "password=hunter2",
        "token=private-token-value",
        "-----BEGIN PRIVATE KEY----- value",
    ],
)
def test_secret_like_values_are_rejected_for_every_origin_and_approval(
    origin,
    approval_verified,
    secret,
):
    decision = MemoryPolicy().evaluate(
        _request(
            origin=origin,
            value=secret,
            approval_verified=approval_verified,
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.sensitivity is MemorySensitivity.SECRET_LIKE
    assert decision.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert decision.approval_required is False
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
    assert _reason_values(decision) == ("secret_like_content",)
    assert secret not in json.dumps(decision.to_dict())


@pytest.mark.parametrize(
    "subject_kind",
    [
        MemorySubjectKind.CONVERSATION_SESSION,
        MemorySubjectKind.WORKFLOW_STATE,
        MemorySubjectKind.EXECUTION_OPERATION,
        MemorySubjectKind.DESKTOP_DIAGNOSTIC,
        MemorySubjectKind.PROVIDER_CONTEXT,
    ],
)
def test_foreign_subject_domains_are_rejected(subject_kind):
    decision = MemoryPolicy().evaluate(_request(subject_kind=subject_kind))

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert _reason_values(decision) == ("wrong_authority",)


def test_profile_preference_has_separate_authority_reason():
    decision = MemoryPolicy().evaluate(
        _request(subject_kind=MemorySubjectKind.PROFILE_PREFERENCE)
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert _reason_values(decision) == ("profile_subsystem_authority",)


def test_sensitivity_classification_is_deterministic_and_memory_domain_specific():
    policy = MemoryPolicy()

    general_first = policy.classify("favorite color", "green")
    general_second = policy.classify("favorite color", "green")
    sensitive_first = policy.classify("passport number", "1234 567890")
    sensitive_second = policy.classify("passport number", "1234 567890")

    assert general_first is general_second is MemorySensitivity.GENERAL_PERSONAL
    assert (
        sensitive_first
        is sensitive_second
        is MemorySensitivity.SENSITIVE_PERSONAL
    )


def test_unknown_sensitivity_fails_closed():
    decision = MemoryPolicy().evaluate(_request(value="\x00"))

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.sensitivity is MemorySensitivity.UNKNOWN
    assert decision.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert _reason_values(decision) == ("unknown_sensitivity",)


def test_unicode_normalized_exact_duplicate_is_noop():
    existing = _record(
        record_id="memory-cafe",
        key="Caf\u00e9 preference",
        value="green",
    )
    decision = MemoryPolicy().evaluate(
        _request(
            key="  CAFE\u0301   PREFERENCE ",
            value=" green ",
            existing_records=(existing,),
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.mutation_instruction is MemoryMutationInstruction.NOOP_DUPLICATE
    assert decision.existing_record_id == "memory-cafe"
    assert _reason_values(decision) == (
        "allowed_explicit_user_fact",
        "exact_duplicate",
    )


def test_same_normalized_key_with_new_value_supersedes_existing():
    decision = MemoryPolicy().evaluate(
        _request(
            value="blue",
            existing_records=(_record(),),
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.mutation_instruction is MemoryMutationInstruction.SUPERSEDE_EXISTING
    assert decision.existing_record_id == "memory-1"
    assert _reason_values(decision) == (
        "allowed_explicit_user_fact",
        "supersedes_existing",
    )


def test_inferred_supersession_requires_approval():
    decision = MemoryPolicy().evaluate(
        _request(
            origin=MemoryOrigin.INFERRED_CONVERSATION,
            value="blue",
            existing_records=(_record(),),
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REQUIRE_APPROVAL
    assert decision.mutation_instruction is MemoryMutationInstruction.SUPERSEDE_EXISTING
    assert decision.existing_record_id == "memory-1"
    assert decision.retention_duration_seconds == 86_400
    assert _reason_values(decision) == (
        "approval_required_for_inferred_fact",
        "supersedes_existing",
    )


def test_multiple_same_key_records_fail_closed():
    decision = MemoryPolicy().evaluate(
        _request(
            existing_records=(
                _record("memory-1"),
                _record("memory-2"),
            )
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
    assert _reason_values(decision) == ("ambiguous_existing_record",)


def test_exact_delete_requires_one_exact_existing_target():
    decision = MemoryPolicy().evaluate(
        _request(
            operation=MemoryPolicyOperation.DELETE_EXACT,
            key=None,
            value=None,
            target_record_id="memory-2",
            existing_records=(
                _record("memory-1"),
                _record("memory-2", key="city", value="Grozny"),
            ),
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.mutation_instruction is MemoryMutationInstruction.DELETE_EXACT
    assert decision.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert decision.existing_record_id == "memory-2"
    assert _reason_values(decision) == ("exact_delete_allowed",)


@pytest.mark.parametrize("target", [None, "", "missing"])
def test_missing_or_unknown_exact_delete_target_is_rejected(target):
    decision = MemoryPolicy().evaluate(
        _request(
            operation=MemoryPolicyOperation.DELETE_EXACT,
            key=None,
            value=None,
            target_record_id=target,
            existing_records=(_record(),),
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.mutation_instruction is None
    assert _reason_values(decision) == ("missing_exact_target",)


def test_ambiguous_exact_delete_target_is_rejected():
    decision = MemoryPolicy().evaluate(
        _request(
            operation=MemoryPolicyOperation.DELETE_EXACT,
            key=None,
            value=None,
            target_record_id="memory-1",
            existing_records=(
                _record("memory-1"),
                _record("memory-1", key="city", value="Grozny"),
            ),
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
    assert _reason_values(decision) == ("ambiguous_exact_target",)


def test_forget_all_requires_approval_without_storing_confirmation_state():
    policy = MemoryPolicy()
    request = _request(
        operation=MemoryPolicyOperation.DELETE_ALL,
        key=None,
        value=None,
    )

    first = policy.evaluate(request)
    second = policy.evaluate(request)

    assert first == second
    assert first.decision_type is MemoryPolicyDecisionType.REQUIRE_APPROVAL
    assert first.approval_required is True
    assert first.mutation_instruction is MemoryMutationInstruction.DELETE_ALL
    assert first.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert _reason_values(first) == ("forget_all_requires_approval",)
    assert policy.__dict__ == {}


def test_approved_forget_all_is_allowed():
    decision = MemoryPolicy().evaluate(
        _request(
            operation=MemoryPolicyOperation.DELETE_ALL,
            key=None,
            value=None,
            approval_verified=True,
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.approval_required is False
    assert decision.mutation_instruction is MemoryMutationInstruction.DELETE_ALL
    assert _reason_values(decision) == ("forget_all_approved",)


@pytest.mark.parametrize(
    "policy_request",
    [
        None,
        "not-a-request",
        _request(operation="unknown"),
        _request(origin="unknown"),
        _request(subject_kind="unknown"),
        _request(approval_verified="yes"),
        _request(existing_records=(object(),)),
    ],
)
def test_malformed_and_unknown_requests_fail_closed(policy_request):
    decision = MemoryPolicy().evaluate(policy_request)

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.retention_class is MemoryRetentionClass.DO_NOT_STORE
    assert decision.mutation_instruction is None
    assert _reason_values(decision) == ("malformed_request",)


def test_upsert_missing_key_and_value_have_stable_reasons():
    missing_key = MemoryPolicy().evaluate(_request(key=" "))
    missing_value = MemoryPolicy().evaluate(_request(value=None))

    assert _reason_values(missing_key) == ("missing_required_key",)
    assert _reason_values(missing_value) == ("missing_required_value",)


def test_request_summary_and_decision_are_immutable_and_collections_become_tuples():
    records = [_record()]
    request = _request(existing_records=records)
    decision = MemoryPolicy().evaluate(request)

    records.append(_record("memory-2"))

    assert isinstance(request.existing_records, tuple)
    assert len(request.existing_records) == 1
    assert isinstance(decision.reason_codes, tuple)
    with pytest.raises(FrozenInstanceError):
        request.key = "changed"
    with pytest.raises(FrozenInstanceError):
        request.existing_records[0].value = "changed"
    with pytest.raises(FrozenInstanceError):
        decision.approval_required = True


def test_repeated_evaluation_is_equal_and_does_not_mutate_input():
    record = _record()
    request = _request(value="blue", existing_records=(record,))
    before = (
        request.operation,
        request.origin,
        request.subject_kind,
        request.key,
        request.value,
        request.target_record_id,
        request.existing_records,
        request.approval_verified,
    )

    first = MemoryPolicy().evaluate(request)
    second = MemoryPolicy().evaluate(request)

    assert first == second
    assert before == (
        request.operation,
        request.origin,
        request.subject_kind,
        request.key,
        request.value,
        request.target_record_id,
        request.existing_records,
        request.approval_verified,
    )
    assert request.existing_records == (record,)


def test_decision_projection_is_json_safe_and_does_not_expose_inputs_or_records():
    raw_key = "private-key-name"
    raw_value = "api key sk-test-1234567890secret"
    record = _record("memory-sensitive", key=raw_key, value=raw_value)
    decision = MemoryPolicy().evaluate(
        _request(
            key=raw_key,
            value=raw_value,
            existing_records=(record,),
            approval_verified=True,
        )
    )

    payload = decision.to_dict()
    serialized = json.dumps(payload, sort_keys=True)

    assert payload == {
        "decision_type": "reject",
        "reason_codes": ["secret_like_content"],
        "approval_required": False,
        "sensitivity": "secret_like",
        "retention_class": "do_not_store",
        "retention_duration_seconds": None,
        "mutation_instruction": None,
        "existing_record_id": None,
    }
    assert raw_key not in serialized
    assert raw_value not in serialized
    assert "memory-sensitive" not in serialized
    assert "sk-test" not in serialized


def test_policy_does_not_read_or_write_filesystem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    decision = MemoryPolicy().evaluate(_request())

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert tuple(tmp_path.iterdir()) == ()


def test_memory_policy_module_has_only_standard_library_imports():
    source_path = Path("cognition") / "memory_policy.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "re",
        "typing",
        "unicodedata",
    }
    assert not {
        item
        for item in imports
        if item.startswith(
            (
                "ai",
                "app",
                "core.execution",
                "memory",
                "pathlib",
                "socket",
                "urllib",
                "workflow",
            )
        )
    }


def test_required_reason_codes_are_stable_json_safe_values():
    assert {item.value for item in MemoryPolicyReasonCode} == {
        "allowed_explicit_user_fact",
        "approval_required_for_inferred_fact",
        "approved_inferred_fact",
        "derived_write_rejected",
        "approved_derived_fact",
        "secret_like_content",
        "wrong_authority",
        "profile_subsystem_authority",
        "malformed_request",
        "missing_required_key",
        "missing_required_value",
        "exact_duplicate",
        "supersedes_existing",
        "ambiguous_existing_record",
        "exact_delete_allowed",
        "missing_exact_target",
        "ambiguous_exact_target",
        "forget_all_requires_approval",
        "forget_all_approved",
        "unknown_sensitivity",
    }


@pytest.mark.parametrize("origin", tuple(MemoryOrigin))
@pytest.mark.parametrize("approval_verified", [False, True])
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("password", "synthetic-password-material"),
        ("пароль", "synthetic-password-material"),
        ("credential", "synthetic-credential-material"),
        ("credentials", "synthetic-credential-material"),
    ],
)
def test_structural_secret_labels_are_rejected_for_every_origin_and_approval(
    origin,
    approval_verified,
    key,
    value,
):
    decision = MemoryPolicy().evaluate(
        _request(
            origin=origin,
            approval_verified=approval_verified,
            key=key,
            value=value,
        )
    )

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.sensitivity is MemorySensitivity.SECRET_LIKE
    assert decision.approval_required is False
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
    assert _reason_values(decision) == ("secret_like_content",)


@pytest.mark.parametrize("origin", tuple(MemoryOrigin))
@pytest.mark.parametrize("approval_verified", [False, True])
@pytest.mark.parametrize(
    "secret_value",
    [
        "password=synthetic-password-material",
        "password: synthetic-password-material",
        "пароль=synthetic-password-material",
        "пароль: synthetic-password-material",
        "credential=synthetic-credential-material",
        "credentials: synthetic-credential-material",
        "Authorization: Bearer synthetic-bearer-material",
        "Bearer synthetic-bearer-material",
    ],
)
def test_credential_value_forms_are_rejected_for_every_origin_and_approval(
    origin,
    approval_verified,
    secret_value,
):
    decision = MemoryPolicy().evaluate(
        _request(
            origin=origin,
            approval_verified=approval_verified,
            value=secret_value,
        )
    )
    serialized = json.dumps(decision.to_dict(), sort_keys=True)

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.sensitivity is MemorySensitivity.SECRET_LIKE
    assert decision.approval_required is False
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
    assert _reason_values(decision) == ("secret_like_content",)
    assert secret_value not in serialized
    assert "synthetic-bearer-material" not in serialized
    assert "synthetic-credential-material" not in serialized
    assert "synthetic-password-material" not in serialized


@pytest.mark.parametrize(
    "value",
    [
        "здоровье",
        "медицинский диагноз",
        "кредитная карта",
        "банковская карта",
    ],
)
def test_russian_sensitive_personal_categories_are_recognized(value):
    assert (
        MemoryPolicy().classify("personal fact", value)
        is MemorySensitivity.SENSITIVE_PERSONAL
    )


@pytest.mark.parametrize(
    "value",
    ["карта города", "карта района", "карта метро", "green"],
)
def test_non_sensitive_map_facts_are_not_overclassified(value):
    assert (
        MemoryPolicy().classify("favorite map", value)
        is MemorySensitivity.GENERAL_PERSONAL
    )


def test_safe_opaque_record_ids_support_all_successful_decision_projections():
    noop_id = "memory-allow-noop-sentinel"
    supersede_id = "memory-allow-super-sentinel"
    approval_id = "memory-require-super-sentinel"
    delete_id = "550e8400-e29b-41d4-a716-446655440000"
    cases = (
        (
            MemoryPolicy().evaluate(
                _request(existing_records=(_record(noop_id),))
            ),
            MemoryPolicyDecisionType.ALLOW,
            MemoryMutationInstruction.NOOP_DUPLICATE,
            noop_id,
        ),
        (
            MemoryPolicy().evaluate(
                _request(
                    value="blue",
                    existing_records=(_record(supersede_id),),
                )
            ),
            MemoryPolicyDecisionType.ALLOW,
            MemoryMutationInstruction.SUPERSEDE_EXISTING,
            supersede_id,
        ),
        (
            MemoryPolicy().evaluate(
                _request(
                    origin=MemoryOrigin.INFERRED_CONVERSATION,
                    value="blue",
                    existing_records=(_record(approval_id),),
                )
            ),
            MemoryPolicyDecisionType.REQUIRE_APPROVAL,
            MemoryMutationInstruction.SUPERSEDE_EXISTING,
            approval_id,
        ),
        (
            MemoryPolicy().evaluate(
                _request(
                    operation=MemoryPolicyOperation.DELETE_EXACT,
                    key=None,
                    value=None,
                    target_record_id=delete_id,
                    existing_records=(_record(delete_id),),
                )
            ),
            MemoryPolicyDecisionType.ALLOW,
            MemoryMutationInstruction.DELETE_EXACT,
            delete_id,
        ),
    )

    for decision, decision_type, mutation, expected_id in cases:
        payload = decision.to_dict()
        serialized = json.dumps(payload, sort_keys=True)

        assert decision.decision_type is decision_type
        assert decision.mutation_instruction is mutation
        assert decision.existing_record_id == expected_id
        assert payload["existing_record_id"] == expected_id
        assert "favorite color" not in serialized
        assert "green" not in serialized


@pytest.mark.parametrize(
    ("policy_request", "unsafe_fragment"),
    [
        (
            _request(
                existing_records=(
                    _record("token=synthetic-record-id-secret"),
                )
            ),
            "synthetic-record-id-secret",
        ),
        (
            _request(
                value="blue",
                existing_records=(
                    _record("token=synthetic-record-id-secret"),
                ),
            ),
            "synthetic-record-id-secret",
        ),
        (
            _request(
                operation=MemoryPolicyOperation.DELETE_EXACT,
                key=None,
                value=None,
                target_record_id="token=synthetic-record-id-secret",
                existing_records=(
                    _record("token=synthetic-record-id-secret"),
                ),
            ),
            "synthetic-record-id-secret",
        ),
    ],
)
def test_unsafe_record_ids_fail_closed_without_serialization_leak(
    policy_request,
    unsafe_fragment,
):
    decision = MemoryPolicy().evaluate(policy_request)
    serialized = json.dumps(decision.to_dict(), sort_keys=True)

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
    assert _reason_values(decision) == ("malformed_request",)
    assert unsafe_fragment not in serialized


@pytest.mark.parametrize(
    "unsafe_id",
    [
        " memory-1",
        "memory 1",
        "memory\n1",
        "memory\x011",
        "ｍemory-1",
        ".memory-1",
        "_memory-1",
        ":memory-1",
        "-memory-1",
        "x" * 129,
    ],
)
def test_malformed_opaque_record_ids_fail_closed(unsafe_id):
    duplicate = MemoryPolicy().evaluate(
        _request(existing_records=(_record(unsafe_id),))
    )
    exact_delete = MemoryPolicy().evaluate(
        _request(
            operation=MemoryPolicyOperation.DELETE_EXACT,
            key=None,
            value=None,
            target_record_id=unsafe_id,
            existing_records=(_record("memory-1"),),
        )
    )

    for decision in (duplicate, exact_delete):
        assert decision.decision_type is MemoryPolicyDecisionType.REJECT
        assert decision.mutation_instruction is None
        assert decision.existing_record_id is None


def test_existing_record_order_does_not_change_decisions():
    matching = _record("memory-match", value="green")
    unrelated = _record("memory-other", key="city", value="Grozny")
    forward = _request(existing_records=(matching, unrelated))
    reverse = _request(existing_records=(unrelated, matching))

    assert MemoryPolicy().evaluate(forward) == MemoryPolicy().evaluate(reverse)

    ambiguous_forward = _request(
        existing_records=(
            _record("memory-first"),
            _record("memory-second"),
        )
    )
    ambiguous_reverse = _request(
        existing_records=tuple(reversed(ambiguous_forward.existing_records))
    )
    assert MemoryPolicy().evaluate(ambiguous_forward) == MemoryPolicy().evaluate(
        ambiguous_reverse
    )


@pytest.mark.parametrize("mutable_value", [[], {}, set(), bytearray(b"mutable")])
def test_summary_rejects_mutable_scalar_values_at_construction(mutable_value):
    with pytest.raises(TypeError):
        ExistingMemoryRecordSummary(
            record_id="memory-1",
            key="favorite color",
            value=mutable_value,
        )


@pytest.mark.parametrize(
    ("field", "mutable_value"),
    [
        ("key", []),
        ("value", {}),
        ("target_record_id", set()),
        ("value", ({"nested": "mutable"},)),
        ("key", bytearray(b"mutable")),
        ("value", (bytearray(b"nested"),)),
    ],
)
def test_request_rejects_direct_and_nested_mutable_scalars(
    field,
    mutable_value,
):
    kwargs = {field: mutable_value}
    with pytest.raises(TypeError):
        _request(**kwargs)


@pytest.mark.parametrize(
    ("field", "mutable_value"),
    [
        ("record_id", []),
        ("key", {}),
        ("value", set()),
        ("value", (["nested"],)),
        ("record_id", bytearray(b"mutable")),
        ("key", (bytearray(b"nested"),)),
    ],
)
def test_summary_rejects_direct_and_nested_mutable_fields(
    field,
    mutable_value,
):
    kwargs = {
        "record_id": "memory-1",
        "key": "favorite color",
        "value": "green",
    }
    kwargs[field] = mutable_value
    with pytest.raises(TypeError):
        ExistingMemoryRecordSummary(**kwargs)


def test_request_rejects_mutable_record_nested_inside_existing_records():
    with pytest.raises(TypeError):
        _request(existing_records=([_record()],))


def test_decision_snapshots_reason_list_and_rejects_mutable_scalars():
    reasons = [MemoryPolicyReasonCode.ALLOWED_EXPLICIT_USER_FACT]
    decision = MemoryPolicyDecision(
        decision_type=MemoryPolicyDecisionType.ALLOW,
        reason_codes=reasons,
        approval_required=False,
        sensitivity=MemorySensitivity.GENERAL_PERSONAL,
        retention_class=MemoryRetentionClass.UNTIL_USER_FORGETS,
        retention_duration_seconds=None,
        mutation_instruction=MemoryMutationInstruction.CREATE,
        existing_record_id=None,
    )
    reasons.append(MemoryPolicyReasonCode.EXACT_DUPLICATE)

    assert decision.reason_codes == (
        MemoryPolicyReasonCode.ALLOWED_EXPLICIT_USER_FACT,
    )
    with pytest.raises(TypeError):
        MemoryPolicyDecision(
            decision_type=[],
            reason_codes=(),
            approval_required=False,
            sensitivity=MemorySensitivity.UNKNOWN,
            retention_class=MemoryRetentionClass.DO_NOT_STORE,
            retention_duration_seconds=None,
            mutation_instruction=None,
            existing_record_id=None,
        )
    with pytest.raises(TypeError):
        MemoryPolicyDecision(
            decision_type=MemoryPolicyDecisionType.REJECT,
            reason_codes=([MemoryPolicyReasonCode.MALFORMED_REQUEST],),
            approval_required=False,
            sensitivity=MemorySensitivity.UNKNOWN,
            retention_class=MemoryRetentionClass.DO_NOT_STORE,
            retention_duration_seconds=None,
            mutation_instruction=None,
            existing_record_id=None,
        )
    with pytest.raises(TypeError):
        MemoryPolicyDecision(
            decision_type=MemoryPolicyDecisionType.REJECT,
            reason_codes=(MemoryPolicyReasonCode.MALFORMED_REQUEST,),
            approval_required=False,
            sensitivity=MemorySensitivity.UNKNOWN,
            retention_class=MemoryRetentionClass.DO_NOT_STORE,
            retention_duration_seconds=None,
            mutation_instruction=None,
            existing_record_id=[],
        )
    with pytest.raises(TypeError):
        MemoryPolicyDecision(
            decision_type=MemoryPolicyDecisionType.REJECT,
            reason_codes=(MemoryPolicyReasonCode.MALFORMED_REQUEST,),
            approval_required=False,
            sensitivity=MemorySensitivity.UNKNOWN,
            retention_class=MemoryRetentionClass.DO_NOT_STORE,
            retention_duration_seconds=None,
            mutation_instruction=bytearray(b"mutable"),
            existing_record_id=None,
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [(42, "green"), ("favorite color", 42), (True, "green")],
)
def test_wrong_immutable_key_and_value_types_fail_closed(key, value):
    decision = MemoryPolicy().evaluate(_request(key=key, value=value))

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None


def test_all_enum_values_are_stable_json_safe_strings():
    expected = {
        MemoryPolicyDecisionType: {"allow", "require_approval", "reject"},
        MemoryPolicyOperation: {"upsert", "delete_exact", "delete_all"},
        MemoryOrigin: {
            "explicit_user_command",
            "inferred_conversation",
            "system_derived",
            "provider_derived",
        },
        MemorySubjectKind: {
            "user_fact",
            "profile_preference",
            "conversation_session",
            "workflow_state",
            "execution_operation",
            "desktop_diagnostic",
            "provider_context",
        },
        MemorySensitivity: {
            "general_personal",
            "sensitive_personal",
            "secret_like",
            "unknown",
        },
        MemoryRetentionClass: {
            "until_user_forgets",
            "bounded_candidate",
            "do_not_store",
        },
        MemoryMutationInstruction: {
            "create",
            "noop_duplicate",
            "supersede_existing",
            "delete_exact",
            "delete_all",
        },
    }

    for enum_type, values in expected.items():
        assert {item.value for item in enum_type} == values
        assert all(isinstance(item.value, str) for item in enum_type)


def test_allow_require_approval_and_delete_projections_are_safe_json():
    raw_key = "raw-key-projection-sentinel"
    raw_value = "raw-value-projection-sentinel"
    cases = (
        MemoryPolicy().evaluate(_request(key=raw_key, value=raw_value)),
        MemoryPolicy().evaluate(
            _request(
                origin=MemoryOrigin.INFERRED_CONVERSATION,
                key=raw_key,
                value=raw_value,
            )
        ),
        MemoryPolicy().evaluate(
            _request(
                operation=MemoryPolicyOperation.DELETE_EXACT,
                key=None,
                value=None,
                target_record_id="memory-delete-projection",
                existing_records=(
                    _record(
                        "memory-delete-projection",
                        key=raw_key,
                        value=raw_value,
                    ),
                ),
            )
        ),
    )

    assert tuple(decision.decision_type for decision in cases) == (
        MemoryPolicyDecisionType.ALLOW,
        MemoryPolicyDecisionType.REQUIRE_APPROVAL,
        MemoryPolicyDecisionType.ALLOW,
    )
    for decision in cases:
        serialized = json.dumps(decision.to_dict(), sort_keys=True)
        assert raw_key not in serialized
        assert raw_value not in serialized
        assert "synthetic-record-id-secret" not in serialized


def test_evaluate_does_not_call_common_filesystem_apis(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("filesystem access is forbidden")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(os, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(Path, "read_text", forbidden)
        patch.setattr(Path, "write_text", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(Path, "write_bytes", forbidden)
        decision = MemoryPolicy().evaluate(_request())

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert calls == []


def test_isolated_cognition_import_has_no_external_side_effects(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    script = (
        "import sys;"
        f"sys.path.insert(0, {str(repository_root)!r});"
        "import cognition;"
        "assert cognition.MemoryPolicy().__dict__ == {}"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert tuple(tmp_path.iterdir()) == ()


_CREDENTIAL_LIKE_OPAQUE_IDS = (
    "token-synthetic-record-id-secret",
    "bearer:synthetic-bearer-material",
    "authorization:bearer-synthetic-material",
    "credential-synthetic-credential-material",
    "credentials:synthetic-credential-material",
    "password:synthetic-password-material",
    "sk-synthetic-key-material",
    "api-key:synthetic-api-key-material",
    "private-key:synthetic-private-key-material",
)


@pytest.mark.parametrize("unsafe_id", _CREDENTIAL_LIKE_OPAQUE_IDS)
@pytest.mark.parametrize(
    "scenario",
    [
        "exact_duplicate",
        "explicit_supersession",
        "inferred_supersession",
        "approved_inferred_supersession",
        "delete_exact_target",
    ],
)
def test_record_id_credential_guard_fails_closed_in_every_policy_path(
    unsafe_id,
    scenario,
):
    if scenario == "delete_exact_target":
        policy_request = _request(
            operation=MemoryPolicyOperation.DELETE_EXACT,
            key=None,
            value=None,
            target_record_id=unsafe_id,
            existing_records=(_record("memory-safe-delete-target"),),
            approval_verified=True,
        )
    else:
        request_kwargs = {
            "existing_records": (_record(unsafe_id),),
        }
        if scenario != "exact_duplicate":
            request_kwargs["value"] = "blue"
        if scenario in {
            "inferred_supersession",
            "approved_inferred_supersession",
        }:
            request_kwargs["origin"] = MemoryOrigin.INFERRED_CONVERSATION
        if scenario == "approved_inferred_supersession":
            request_kwargs["approval_verified"] = True
        policy_request = _request(**request_kwargs)

    decision = MemoryPolicy().evaluate(policy_request)
    serialized = json.dumps(decision.to_dict(), sort_keys=True)

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.reason_codes == (
        MemoryPolicyReasonCode.MALFORMED_REQUEST,
    )
    assert decision.approval_required is False
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
    assert unsafe_id not in serialized
    assert "synthetic" not in serialized


@pytest.mark.parametrize("unsafe_id", _CREDENTIAL_LIKE_OPAQUE_IDS)
def test_decision_constructor_rejects_credential_like_opaque_id(unsafe_id):
    with pytest.raises(TypeError):
        MemoryPolicyDecision(
            decision_type=MemoryPolicyDecisionType.ALLOW,
            reason_codes=(MemoryPolicyReasonCode.ALLOWED_EXPLICIT_USER_FACT,),
            approval_required=False,
            sensitivity=MemorySensitivity.GENERAL_PERSONAL,
            retention_class=MemoryRetentionClass.UNTIL_USER_FORGETS,
            retention_duration_seconds=None,
            mutation_instruction=MemoryMutationInstruction.NOOP_DUPLICATE,
            existing_record_id=unsafe_id,
        )


@pytest.mark.parametrize(
    "safe_id",
    [
        "550e8400-e29b-41d4-a716-446655440000",
        "memory-token-cache",
        "memory-bearer-cache",
        "contest-password-score",
    ],
)
def test_record_id_guard_does_not_reject_safe_noncredential_ids(safe_id):
    decision = MemoryPolicy().evaluate(
        _request(existing_records=(_record(safe_id),))
    )

    assert decision.decision_type is MemoryPolicyDecisionType.ALLOW
    assert decision.mutation_instruction is MemoryMutationInstruction.NOOP_DUPLICATE
    assert decision.existing_record_id == safe_id


@pytest.mark.parametrize(
    "field",
    ["operation", "origin", "subject_kind", "approval_verified"],
)
@pytest.mark.parametrize(
    "mutable_value",
    [[], {}, set(), bytearray(b"mutable")],
)
def test_request_rejects_mutable_remaining_scalar_fields(
    field,
    mutable_value,
):
    with pytest.raises(TypeError):
        _request(**{field: mutable_value})


@pytest.mark.parametrize(
    "field",
    ["operation", "origin", "subject_kind", "approval_verified"],
)
@pytest.mark.parametrize(
    "nested_value",
    [
        (["nested"],),
        ({"nested": "mutable"},),
        (set(["nested"]),),
        (bytearray(b"nested"),),
        (frozenset({"safe"}), (bytearray(b"deeply-nested"),)),
    ],
)
def test_request_rejects_nested_mutable_remaining_scalar_fields(
    field,
    nested_value,
):
    with pytest.raises(TypeError):
        _request(**{field: nested_value})


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "operation": ("upsert",),
            "approval_verified": True,
        },
        {
            "origin": ("explicit_user_command",),
            "approval_verified": True,
        },
        {
            "subject_kind": ("user_fact",),
            "approval_verified": True,
        },
        {
            "approval_verified": 1,
        },
    ],
)
def test_wrong_immutable_request_scalars_fail_closed_even_with_approval(kwargs):
    decision = MemoryPolicy().evaluate(_request(**kwargs))

    assert decision.decision_type is MemoryPolicyDecisionType.REJECT
    assert decision.reason_codes == (
        MemoryPolicyReasonCode.MALFORMED_REQUEST,
    )
    assert decision.approval_required is False
    assert decision.mutation_instruction is None
    assert decision.existing_record_id is None
