import pytest

from core.policy_boundary import PolicyRequest
from planner import (
    MultiStepPlanner,
    PlanCapability,
    PlanCapabilityDescriptor,
    PlanParseStatus,
    PlanSideEffect,
    PlanStatus,
    PlanStepStatus,
    PlannerCapabilityRegistry,
    PlannerCapabilityRegistryError,
    default_plan_step_message,
)


def capability(capability_id):
    is_forget_all = capability_id == "memory.forget_all"
    return PlanCapability(
        PlanCapabilityDescriptor(
            capability_id=capability_id,
            display_name_ru=capability_id,
            display_name_en=capability_id,
            category="test",
            risk_level="confirmation_required" if is_forget_all else "read_only",
            side_effect=PlanSideEffect.BOUNDED_LOCAL_STATE if is_forget_all else PlanSideEffect.READ_ONLY,
            requires_confirmation=is_forget_all,
            argument_schema={},
            safe_description="safe",
        ),
        lambda args: None,
        lambda args, confirmed: PolicyRequest(
            source="test",
            command_id=capability_id,
            risk="read_only",
            required_capabilities=("read_system_state",),
            confirmation_present=True,
        ),
    )


def registry():
    result = PlannerCapabilityRegistry.empty()
    for capability_id in (
        "system.status",
        "startup.profile",
        "language.get",
        "language.set",
        "memory.remember",
        "memory.recall",
        "memory.list",
        "memory.forget",
        "memory.forget_all",
    ):
        result = result.register(capability(capability_id))
    return result


def test_plan_and_step_status_enums_are_typed():
    assert PlanStatus.PROPOSED.value == "proposed"
    assert PlanStepStatus.PENDING.value == "pending"


def test_snapshot_is_immutable_serializable_and_has_no_raw_executor_or_secret():
    planner = MultiStepPlanner(registry())
    parsed = planner.create_from_text("составь план: статус системы; текущий язык", language_code="ru-RU")

    data = parsed.snapshot.to_dict()

    assert data["status"] == "proposed"
    assert data["progress_percent"] == 0
    assert data["steps"][0]["safe_argument_summary"] == "статус системы"
    assert data["steps"][0]["risk_level"] == "read_only"
    assert data["steps"][0]["side_effect"] == "read_only"
    assert "executor" not in str(data).lower()
    assert "callback" not in str(data).lower()
    with pytest.raises(AttributeError):
        parsed.snapshot.plan_id = "changed"


def test_snapshot_steps_are_immutable_and_to_dict_is_defensive():
    planner = MultiStepPlanner(registry())
    parsed = planner.create_from_text(
        "create plan: system status; current language",
        language_code="en-US",
    )
    snapshot = parsed.snapshot
    step = snapshot.steps[0]

    assert isinstance(snapshot.steps, tuple)
    with pytest.raises(AttributeError):
        step.capability_id = "changed"
    with pytest.raises(TypeError):
        snapshot.steps[0] = snapshot.steps[1]

    data = snapshot.to_dict()
    data["plan_id"] = "changed"
    data["steps"][0]["capability_id"] = "changed"

    assert snapshot.plan_id != "changed"
    assert snapshot.steps[0].capability_id == "system.status"
    assert planner.snapshot().plan_id != "changed"
    assert planner.snapshot().steps[0].capability_id == "system.status"


def test_is_current_marker_is_deterministic_for_private_state_snapshots():
    planner = MultiStepPlanner(registry())
    planner.create_from_text("create plan: system status; current language", language_code="en-US")

    proposed = planner.snapshot()
    awaiting = planner.set_status(
        PlanStatus.AWAITING_CONFIRMATION,
        current_step_id="step-2",
    )
    terminal = planner.set_status(
        PlanStatus.CANCELLED,
        current_step_id=None,
    )

    assert [step.is_current for step in proposed.steps] == [False, False]
    assert [step.is_current for step in awaiting.steps] == [False, True]
    assert [step.is_current for step in terminal.steps] == [False, False]


def test_default_step_messages_follow_current_public_status():
    planner = MultiStepPlanner(registry())
    planner.create_from_text("create plan: system status; current language", language_code="en-US")

    awaiting = planner.set_status(
        PlanStatus.AWAITING_CONFIRMATION,
        step_statuses={"step-1": PlanStepStatus.AWAITING_CONFIRMATION},
        current_step_id="step-1",
    )
    skipped = planner.set_status(
        PlanStatus.BLOCKED,
        step_statuses={"step-1": PlanStepStatus.CANCELLED, "step-2": PlanStepStatus.SKIPPED},
        current_step_id=None,
    )

    assert default_plan_step_message(PlanStepStatus.PENDING, "en-US") == "Step is pending."
    assert default_plan_step_message(PlanStepStatus.PENDING, "ru-RU") == "Этап ожидает выполнения."
    assert awaiting.steps[0].safe_message == "awaiting_confirmation"
    assert awaiting.steps[0].safe_message != "Step is pending."
    assert skipped.steps[0].safe_message == "cancelled"
    assert skipped.steps[1].safe_message == "skipped"


def test_registry_rejects_duplicate_and_unregistered_capability():
    first = PlannerCapabilityRegistry.empty().register(capability("system.status"))
    with pytest.raises(PlannerCapabilityRegistryError):
        first.register(capability("system.status"))
    with pytest.raises(PlannerCapabilityRegistryError):
        first.get("unknown")


def test_empty_oversized_control_and_secret_plans_are_rejected():
    planner = MultiStepPlanner(registry())

    assert planner.create_from_text("составь план:", language_code="ru-RU").safe_error_code == "empty_plan"
    assert planner.create_from_text("составь план: " + ("статус системы; " * 200), language_code="ru-RU").safe_error_code in {"plan_text_too_large", "too_many_steps"}
    assert planner.create_from_text("составь план: статус\x01системы", language_code="ru-RU").safe_error_code == "control_characters_rejected"
    secret = planner.create_from_text("составь план: запомни api_key=sk-test123456789 север", language_code="ru-RU")
    assert secret.safe_error_code == "credential_like_value_rejected"
    assert "sk-test" not in secret.safe_message


def test_russian_and_english_plan_parsing_forms():
    planner = MultiStepPlanner(registry())
    ru = planner.create_from_text("составь план: статус системы; текущий язык", language_code="ru-RU")
    connector = planner.create_from_text("создай план: покажи память затем покажи текущий язык", language_code="ru-RU")
    en = planner.create_from_text("create plan: system status; current language", language_code="en-US")

    assert ru.status == PlanParseStatus.CREATED
    assert [step.capability_id for step in ru.snapshot.steps] == ["system.status", "language.get"]
    assert connector.status == PlanParseStatus.CREATED
    assert en.status == PlanParseStatus.CREATED
    assert en.safe_message == "Plan created."


def test_russian_forget_all_natural_word_order_selects_destructive_capability():
    planner = MultiStepPlanner(registry())

    parsed = planner.create_from_text(
        "составь план: забудь всё, что ты обо мне помнишь",
        language_code="ru-RU",
    )

    assert parsed.status == PlanParseStatus.CREATED
    assert parsed.snapshot.total_steps == 1
    step = parsed.snapshot.steps[0]
    assert step.capability_id == "memory.forget_all"
    assert planner.steps()[0].arguments == {}
    assert step.risk_level == "confirmation_required"
    assert step.requires_confirmation is True


def test_russian_forget_all_existing_word_order_remains_supported():
    planner = MultiStepPlanner(registry())

    parsed = planner.create_from_text(
        "составь план: забудь всё, что ты помнишь обо мне",
        language_code="ru-RU",
    )

    assert parsed.status == PlanParseStatus.CREATED
    step = parsed.snapshot.steps[0]
    assert step.capability_id == "memory.forget_all"
    assert planner.steps()[0].arguments == {}
    assert step.requires_confirmation is True


def test_russian_forget_all_uses_existing_punctuation_and_yo_normalization():
    planner = MultiStepPlanner(registry())

    parsed = planner.create_from_text(
        "составь план: забудь все: что ты обо мне помнишь",
        language_code="ru-RU",
    )

    assert parsed.status == PlanParseStatus.CREATED
    assert parsed.snapshot.steps[0].capability_id == "memory.forget_all"


@pytest.mark.parametrize(
    ("phrase", "expected_key"),
    (
        ("забудь ключ", "ключ"),
        ("забудь всё о проекте X", "всё о проекте X"),
        ("забудь всё про работу", "всё про работу"),
        ("забудь всё о настройках", "всё о настройках"),
        ("забудь всё, что касается проекта X", "всё, что касается проекта X"),
        ("забудь маркер аудита 9073", "маркер аудита 9073"),
    ),
)
def test_russian_forget_all_does_not_overmatch_bounded_forget_phrases(phrase, expected_key):
    planner = MultiStepPlanner(registry())

    parsed = planner.create_from_text(f"составь план: {phrase}", language_code="ru-RU")

    assert parsed.status == PlanParseStatus.CREATED
    step = parsed.snapshot.steps[0]
    assert step.capability_id == "memory.forget"
    assert planner.steps()[0].arguments == {"key": expected_key}
    assert step.requires_confirmation is False


def test_unknown_and_ambiguous_steps_reject_full_plan_without_partial_active_plan():
    planner = MultiStepPlanner(registry())
    unknown = planner.create_from_text("составь план: статус системы; неизвестная функция", language_code="ru-RU")
    ambiguous = planner.create_from_text("составь план: покажи статус; текущий язык", language_code="ru-RU")

    assert unknown.safe_error_code == "planner_step_unrecognized"
    assert ambiguous.status == PlanParseStatus.CLARIFICATION_REQUIRED
    assert planner.snapshot() is None


def test_creation_does_not_execute_and_active_plan_replacement_rules():
    calls = []
    reg = registry().register(
        PlanCapability(
            PlanCapabilityDescriptor("extra.test", "extra", "extra", "test", "read_only", PlanSideEffect.READ_ONLY, False, {}, "safe"),
            lambda args: calls.append("executed"),
            lambda args, confirmed: PolicyRequest(source="test", command_id="extra.test", confirmation_present=True),
        )
    )
    planner = MultiStepPlanner(reg)

    first = planner.create_from_text("составь план: статус системы", language_code="ru-RU")
    second = planner.create_from_text("составь план: текущий язык", language_code="ru-RU")

    assert calls == []
    assert first.snapshot.progress_percent == 0
    assert second.snapshot.plan_id != first.snapshot.plan_id
    planner.set_status(PlanStatus.RUNNING)
    blocked = planner.create_from_text("составь план: статус системы", language_code="ru-RU")
    assert blocked.safe_error_code == "active_plan_not_replaceable"

def test_preview_create_from_text_validates_without_active_plan_mutation():
    planner = MultiStepPlanner(registry())

    preview = planner.preview_create_from_text(
        "\u0441\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d: \u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b; \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u044f\u0437\u044b\u043a",
        language_code="ru-RU",
    )

    assert preview.status == PlanParseStatus.CREATED
    assert preview.snapshot.total_steps == 2
    assert preview.snapshot.plan_id == "plan-preview"
    assert planner.snapshot() is None
