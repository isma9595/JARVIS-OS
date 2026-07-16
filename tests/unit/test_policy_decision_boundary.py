import json

from core.command_registry import DEFAULT_COMMAND_REGISTRY
from core.policy_boundary import (
    PolicyDecisionBoundary,
    PolicyDecisionType,
    policy_request_from_metadata,
)


def _metadata(text):
    exact = DEFAULT_COMMAND_REGISTRY.find_by_alias(text)
    if exact is not None:
        return exact
    normalized = DEFAULT_COMMAND_REGISTRY.normalize_alias(text)
    for command in DEFAULT_COMMAND_REGISTRY.commands:
        for alias in command.aliases:
            normalized_alias = DEFAULT_COMMAND_REGISTRY.normalize_alias(alias)
            if "<text>" not in normalized_alias:
                continue
            prefix = normalized_alias.split("<text>", 1)[0].strip()
            if prefix and normalized.startswith(prefix):
                return command
    return None


def _decision(text, confirmation=False, clarification_resolved=True):
    return PolicyDecisionBoundary().evaluate(
        policy_request_from_metadata(
            source="test",
            text=text,
            metadata=_metadata(text),
            intent_kind="local_command",
            confirmation_present=confirmation,
            clarification_resolved=clarification_resolved,
        )
    )


def test_read_only_system_status_returns_allow():
    decision = _decision("статус системы")

    assert decision.decision == PolicyDecisionType.ALLOW
    assert decision.safe_to_execute is True
    assert decision.requires_confirmation is False
    assert "read_system_state" in decision.required_capabilities


def test_exact_risky_delete_requires_confirmation():
    decision = _decision("удали файл test.txt")

    assert decision.decision == PolicyDecisionType.REQUIRE_CONFIRMATION
    assert decision.safe_to_execute is False
    assert decision.requires_confirmation is True
    assert "file_delete" in decision.required_capabilities


def test_forbidden_system_deletion_returns_deny():
    decision = _decision("удали System32")

    assert decision.decision == PolicyDecisionType.DENY
    assert decision.safe_to_execute is False
    assert "dangerous_system_target" in decision.reason_codes


def test_vague_risky_phrase_is_denied():
    decision = _decision("удали это")

    assert decision.decision == PolicyDecisionType.DENY
    assert "missing_action_target" in decision.reason_codes


def test_clarification_does_not_count_as_confirmation():
    decision = _decision("системы", clarification_resolved=False)

    assert decision.decision == PolicyDecisionType.DENY
    assert decision.safe_to_execute is False
    assert "clarification_unresolved" in decision.reason_codes


def test_confirmation_allows_only_same_request_shape():
    confirmed = _decision("удали файл test.txt", confirmation=True)
    unconfirmed_other = _decision("удали файл other.txt", confirmation=False)

    assert confirmed.decision == PolicyDecisionType.ALLOW
    assert unconfirmed_other.decision == PolicyDecisionType.REQUIRE_CONFIRMATION


def test_provider_request_requires_network_provider_capability():
    decision = _decision("groq реальный запрос: привет")

    assert decision.decision == PolicyDecisionType.REQUIRE_CONFIRMATION
    assert "network_provider_request" in decision.required_capabilities
    assert "credential_use" in decision.required_capabilities


def test_policy_dto_serialization_is_safe_and_keeps_cyrillic():
    decision = PolicyDecisionBoundary().evaluate(
        policy_request_from_metadata(
            source="test",
            text="удали файл test.txt sk-secret-token",
            metadata=None,
            intent_kind="local_command",
        )
    )
    data = decision.to_dict()
    payload = json.dumps(data, ensure_ascii=False)

    assert "sk-secret-token" not in payload
    assert "Требуется подтверждение" in payload


def test_policy_boundary_has_no_execution_dependencies(monkeypatch):
    calls = {"router": 0, "provider": 0, "credentials": 0}

    def called(*_args, **_kwargs):
        calls["router"] += 1
        raise AssertionError("execution dependency called")

    monkeypatch.setattr("core.action_router.SafeActionRouter.route", called)
    decision = _decision("удали файл test.txt")

    assert decision.decision == PolicyDecisionType.REQUIRE_CONFIRMATION
    assert calls == {"router": 0, "provider": 0, "credentials": 0}
