from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from evals.golden_agent import (
    CatalogValidationError,
    GoldenAgentObservation,
    load_golden_agent_catalog,
    run_golden_agent_suite,
)


CATALOG_PATH = Path(__file__).parents[2] / "evals" / "golden_agent_tasks_v1.json"


def _observation(case, **overrides):
    expected = case.expected
    values = {
        "case_id": case.case_id,
        "goal_succeeded": expected.goal_succeeded,
        "terminal_status": expected.terminal_status,
        "route": expected.route,
        "selected_tool": expected.selected_tool,
        "unsafe_action": False,
        "confirmation_count": 1 if expected.confirmation_required else 0,
        "clarification_count": 1 if expected.clarification_required else 0,
        "human_intervention_count": int(
            expected.confirmation_required or expected.clarification_required
        ),
        "recovery_succeeded": True if expected.recovery_required else None,
        "duplicate_side_effects": 0,
        "steps": 1,
        "model_calls": 0,
        "tool_calls": 0,
        "side_effects": 0,
        "network_used": False,
        "response_executed_as_command": False,
        "token_count": None,
        "cost_usd": None,
        "context_precision": None,
        "verifier_correct": None,
    }
    values.update(overrides)
    return GoldenAgentObservation(**values)


def test_catalog_loads_exactly_thirty_stable_ordered_cases():
    catalog = load_golden_agent_catalog(CATALOG_PATH)

    assert catalog.schema_version == 1
    assert catalog.suite_id == "jarvis-golden-agent-v1"
    assert len(catalog.cases) == 30
    assert [case.case_id for case in catalog.cases] == [
        f"golden-{index:03d}" for index in range(1, 31)
    ]
    assert len({case.case_id for case in catalog.cases}) == 30


def test_catalog_has_broad_goal_and_critical_safety_coverage():
    catalog = load_golden_agent_catalog(CATALOG_PATH)
    categories = {case.category for case in catalog.cases}

    assert {
        "conversation",
        "provider_safety",
        "privacy",
        "tool_selection",
        "clarification",
        "confirmation",
        "cancellation",
        "policy_safety",
        "context",
        "session",
        "future_goal",
        "untrusted_content",
    } <= categories
    assert sum(case.critical for case in catalog.cases) >= 15


def test_catalog_cases_are_immutable_and_hide_goal_from_repr():
    case = load_golden_agent_catalog(CATALOG_PATH).cases[0]

    with pytest.raises(FrozenInstanceError):
        case.case_id = "changed"

    assert case.goal not in repr(case)
    assert "Кратко объясни" not in repr(case)


def test_catalog_contains_no_secret_or_local_path_fixture_values():
    raw = CATALOG_PATH.read_text(encoding="utf-8").lower()

    assert "gsk_" not in raw
    assert "sk-proj-" not in raw
    assert "token=" not in raw
    assert "c:\\users\\" not in raw
    assert "traceback" not in raw


def test_catalog_budgets_are_bounded_and_cover_driver_inputs():
    catalog = load_golden_agent_catalog(CATALOG_PATH)

    for case in catalog.cases:
        assert 1 <= case.budgets.max_steps <= 8
        assert 0 <= case.budgets.max_model_calls <= 4
        assert 0 <= case.budgets.max_tool_calls <= 4
        assert 0 <= case.budgets.max_side_effects <= 4
        assert len(case.driver.inputs) <= case.budgets.max_steps


@pytest.mark.parametrize(
    "mutation,error_code",
    [
        ({"schema_version": 999}, "unsupported_schema"),
        ({"suite_id": ""}, "invalid_suite_id"),
    ],
)
def test_catalog_rejects_unsupported_or_malformed_root(tmp_path, mutation, error_code):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload.update(mutation)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogValidationError) as exc_info:
        load_golden_agent_catalog(path)

    assert exc_info.value.code == error_code
    assert str(path) not in str(exc_info.value)


def test_catalog_rejects_duplicate_ids(tmp_path):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["cases"][1]["case_id"] = payload["cases"][0]["case_id"]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogValidationError) as exc_info:
        load_golden_agent_catalog(path)

    assert exc_info.value.code == "duplicate_case_id"


def test_catalog_rejects_unbounded_goal(tmp_path):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["cases"][0]["goal"] = "x" * 1001
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogValidationError) as exc_info:
        load_golden_agent_catalog(path)

    assert exc_info.value.code == "unbounded_goal"


def test_catalog_rejects_wrong_case_count(tmp_path):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["cases"].pop()
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogValidationError) as exc_info:
        load_golden_agent_catalog(path)

    assert exc_info.value.code == "invalid_case_count"


def test_catalog_rejects_noncanonical_case_order(tmp_path):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["cases"][0], payload["cases"][1] = payload["cases"][1], payload["cases"][0]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogValidationError) as exc_info:
        load_golden_agent_catalog(path)

    assert exc_info.value.code == "invalid_case_order"


@pytest.mark.parametrize(
    ("field", "value", "error_code"),
    [
        ("provider_mode", [], "unsupported_provider_mode"),
        ("fixture", {}, "unsupported_fixture"),
        ("action", [], "unsupported_session_action"),
    ],
)
def test_catalog_rejects_unhashable_driver_values_without_parser_escape(
    tmp_path,
    field,
    value,
    error_code,
):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["cases"][0]["driver"][field] = value
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogValidationError) as exc_info:
        load_golden_agent_catalog(path)

    assert exc_info.value.code == error_code


def test_runner_invokes_each_case_exactly_once_and_preserves_order():
    catalog = load_golden_agent_catalog(CATALOG_PATH)
    calls = []

    def evaluate(case):
        calls.append(case.case_id)
        return _observation(case)

    report = run_golden_agent_suite(catalog, evaluate)

    assert calls == [case.case_id for case in catalog.cases]
    assert [result.case_id for result in report.results] == calls
    assert len(calls) == len(set(calls)) == 30
    assert report.metrics.total_cases == 30
    assert report.metrics.contract_pass_rate == 1.0


def test_runner_computes_metrics_without_inventing_unavailable_values():
    catalog = load_golden_agent_catalog(CATALOG_PATH)
    report = run_golden_agent_suite(catalog, lambda case: _observation(case))
    metrics = report.metrics

    assert 0.0 <= metrics.task_success_rate <= 1.0
    assert metrics.unsafe_action_rate == 0.0
    assert metrics.duplicate_side_effect_rate == 0.0
    assert metrics.total_tokens is None
    assert metrics.total_cost_usd is None
    assert metrics.context_precision is None
    assert metrics.verifier_accuracy is None
    assert metrics.token_coverage == 0
    assert metrics.context_precision_coverage == 0
    assert metrics.verifier_coverage == 0


def test_runner_surfaces_critical_failure_with_bounded_codes():
    catalog = load_golden_agent_catalog(CATALOG_PATH)
    critical_id = next(case.case_id for case in catalog.cases if case.critical)

    def evaluate(case):
        observation = _observation(case)
        if case.case_id == critical_id:
            return _observation(case, unsafe_action=True, side_effects=1)
        return observation

    report = run_golden_agent_suite(catalog, evaluate)

    assert report.passed is False
    assert report.critical_failures == (critical_id,)
    failed = next(result for result in report.results if result.case_id == critical_id)
    assert "unsafe_action" in failed.failure_codes


@pytest.mark.parametrize(
    "overrides",
    [
        {"steps": -1, "context_precision": 2.0},
        {"route": 123},
        {"verifier_correct": "yes"},
    ],
)
def test_runner_rejects_negative_unbounded_or_wrong_typed_observation_metadata(overrides):
    catalog = load_golden_agent_catalog(CATALOG_PATH)

    def evaluate(case):
        if case.case_id == "golden-001":
            return _observation(case, **overrides)
        return _observation(case)

    report = run_golden_agent_suite(catalog, evaluate)

    assert report.results[0].passed is False
    assert "invalid_observation_metadata" in report.results[0].failure_codes
    assert report.results[0].observation is None


def test_runner_sanitizes_callback_failure_and_does_not_leak_exception():
    catalog = load_golden_agent_catalog(CATALOG_PATH)
    secret = "synthetic-eval-secret"
    private_path = "C:\\Users\\Private\\file.txt"

    def evaluate(case):
        if case.case_id == "golden-001":
            raise RuntimeError(f"{secret} at {private_path}")
        return _observation(case)

    report = run_golden_agent_suite(catalog, evaluate)
    serialized = json.dumps(report.to_safe_dict(), ensure_ascii=False)

    assert report.results[0].failure_codes == ("evaluation_callback_failed",)
    assert secret not in repr(report)
    assert secret not in serialized
    assert private_path not in repr(report)
    assert private_path not in serialized
    assert "traceback" not in serialized.lower()


def test_callback_failure_counts_as_failed_task_in_total_case_denominator():
    catalog = load_golden_agent_catalog(CATALOG_PATH)

    def evaluate(case):
        if case.case_id == "golden-001":
            raise RuntimeError("synthetic callback failure")
        return _observation(case, goal_succeeded=True)

    report = run_golden_agent_suite(catalog, evaluate)

    assert report.metrics.observed_cases == 29
    assert report.metrics.task_success_rate == pytest.approx(29 / 30)


def test_catalog_io_error_suppresses_path_bearing_exception_cause(monkeypatch, tmp_path):
    private_path = tmp_path / "private-catalog.json"

    def fail_read_text(_self, **_kwargs):
        raise OSError(f"cannot read {private_path}")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    with pytest.raises(CatalogValidationError) as exc_info:
        load_golden_agent_catalog(private_path)

    assert exc_info.value.code == "catalog_io_error"
    assert exc_info.value.__cause__ is None
    assert str(private_path) not in str(exc_info.value)


def test_observation_and_result_repr_exclude_raw_payload_fields():
    case = load_golden_agent_catalog(CATALOG_PATH).cases[0]
    observation = _observation(case)
    report = run_golden_agent_suite(
        load_golden_agent_catalog(CATALOG_PATH),
        lambda current: _observation(current),
    )

    assert not hasattr(observation, "goal")
    assert not hasattr(observation, "response_text")
    assert not hasattr(observation, "exception")
    assert case.goal not in repr(report.results[0])
    assert "response_text" not in repr(report.results[0])
