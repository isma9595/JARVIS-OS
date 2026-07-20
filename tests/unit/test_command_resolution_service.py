import pytest

from core.command_resolution_service import (
    CommandResolutionService,
    CommandResolutionStatus,
)
from core.command_registry import DEFAULT_COMMAND_REGISTRY


def make_service():
    groups = {
        "memory_add": (
            "запомни что",
            "запомни",
            "сохрани в память что",
            "сохрани в память",
            "сохрани это в память что",
            "сохрани это в память",
        ),
        "memory_delete": {
            "забудь всё",
            "забудь все",
            "очисти память",
            "удали память",
        },
        "memory_search": (
            "вспомни про",
            "что ты помнишь про",
            "найди в памяти",
            "поиск в памяти",
            "вспомни",
        ),
        "command_registry_search": (
            "найти команду:",
            "поиск команды:",
            "command search:",
        ),
        "language_status": (
            "какой язык",
            "текущий язык",
            "покажи язык",
            "current language",
            "show language",
        ),
        "language_reset": ("сбросить язык", "reset language"),
        "language_set": {
            "язык русский": "русский",
            "установить русский язык": "русский",
            "переключить язык на русский": "русский",
            "язык английский": "английский",
            "установить английский язык": "английский",
            "переключить язык на английский": "английский",
            "language russian": "russian",
            "set language to russian": "russian",
            "language english": "english",
            "set language to english": "english",
        },
        "legacy_passthrough_exact": {"привет"},
        "legacy_passthrough_mapping": {},
        "legacy_passthrough_prefix": (),
    }
    return CommandResolutionService(
        command_registry=DEFAULT_COMMAND_REGISTRY,
        command_groups=groups,
    )


def test_exact_system_command_resolves_without_execution():
    resolution = make_service().resolve("статус системы")

    assert resolution.resolution_status == CommandResolutionStatus.RESOLVED
    assert resolution.command_id == "system.status"
    assert resolution.category == "system"
    assert resolution.safe_args == {}
    assert resolution.match_source == "registry_alias"


def test_exact_language_get_and_set_routes_resolve_with_safe_args():
    service = make_service()

    status = service.resolve("current language")
    set_en = service.resolve("language English")

    assert status.resolution_status == CommandResolutionStatus.RESOLVED
    assert status.command_id == "profile.language.status"
    assert status.safe_args == {}
    assert set_en.resolution_status == CommandResolutionStatus.RESOLVED
    assert set_en.command_id == "profile.language.set"
    assert set_en.safe_args == {"language": "english"}


def test_known_phase1_excluded_route_is_explicit_legacy_passthrough():
    resolution = make_service().resolve("привет")

    assert resolution.resolution_status == CommandResolutionStatus.LEGACY_PASSTHROUGH
    assert resolution.unknown is False
    assert resolution.safe_reason_code == "phase1_legacy_passthrough"


def test_ambiguous_status_requires_clarification_without_execution():
    resolution = make_service().resolve("покажи статус")

    assert resolution.resolution_status == CommandResolutionStatus.REQUIRES_CLARIFICATION
    assert resolution.clarification_required is True
    assert resolution.command_id is None
    assert tuple(option.option_id for option in resolution.clarification_candidates) == (
        "system",
        "ai",
        "microphone",
        "app_service",
    )


def test_clarification_continuation_selects_existing_command_without_execution():
    service = make_service()
    pending = service.resolve("покажи статус")
    state = pending.to_dict()

    from app.intent_resolver import ClarificationState

    selected = service.resolve(
        "системы",
        pending_clarification=ClarificationState(
            question_ru=pending.clarification_prompt,
            options=pending.clarification_candidates,
            original_text=state["original_text"],
            source="test",
        ),
    )

    assert selected.command_id == "system.status"
    assert selected.command_text == "статус системы"
    assert selected.match_source == "clarification_selection"


def test_exact_memory_remember_form_extracts_safe_content_without_mutation():
    resolution = make_service().resolve("запомни что task094 marker north")

    assert resolution.command_id == "memory.add"
    assert resolution.safe_args == {"content": "task094 marker north"}


def test_exact_memory_recall_form_extracts_safe_query_without_reading_memory():
    resolution = make_service().resolve("вспомни про task094 marker")

    assert resolution.command_id == "memory.search"
    assert resolution.safe_args == {"query": "task094 marker"}


def test_exact_memory_forget_form_resolves_without_deletion():
    resolution = make_service().resolve("забудь всё")

    assert resolution.command_id == "memory.delete.requested"
    assert resolution.safe_args == {}


def test_existing_russian_forget_all_limitation_remains_unknown():
    resolution = make_service().resolve("забудь всё что ты помнишь обо мне")

    assert resolution.resolution_status == CommandResolutionStatus.UNKNOWN
    assert resolution.command_id is None
    assert resolution.unknown is True


def test_unknown_command_uses_existing_unknown_fallback_classification():
    resolution = make_service().resolve("запусти космический режим")

    assert resolution.resolution_status == CommandResolutionStatus.UNKNOWN
    assert resolution.unknown is True
    assert resolution.match_source == "action_router_fallback"
    assert resolution.safe_reason_code == "legacy_unknown_fallback"


def test_safe_args_mapping_rejects_mutation_and_caller_dict_is_copied():
    from core.command_resolution_service import CommandResolution

    caller_args = {"x": "original"}
    resolution = CommandResolution(
        original_text="x",
        normalized_text="x",
        resolution_status=CommandResolutionStatus.RESOLVED,
        command_id="test.command",
        category="test",
        safe_args=caller_args,
        clarification_required=False,
        clarification_prompt=None,
        clarification_candidates=(),
        confidence="high",
        match_source="test",
        safe_reason_code=None,
        unknown=False,
    )
    caller_args["x"] = "changed"

    with pytest.raises(TypeError):
        resolution.safe_args["x"] = "changed"

    assert resolution.safe_args == {"x": "original"}
    assert resolution.to_dict()["safe_args"] == {"x": "original"}


def test_command_group_inputs_are_defensively_copied():
    groups = {"legacy_passthrough_exact": {"привет"}}
    service = CommandResolutionService(
        command_registry=DEFAULT_COMMAND_REGISTRY,
        command_groups=groups,
    )
    groups["legacy_passthrough_exact"].add("новая команда")

    assert (
        service.resolve("новая команда").resolution_status
        == CommandResolutionStatus.UNKNOWN
    )


def test_resolution_contract_is_immutable_and_serialization_is_copy():
    resolution = make_service().resolve("покажи статус")

    with pytest.raises(Exception):
        resolution.command_id = "system.status"
    with pytest.raises(AttributeError):
        resolution.clarification_candidates.append("bad")

    data = resolution.to_dict()
    data["safe_args"]["x"] = "changed"

    assert resolution.safe_args == {}
    assert isinstance(resolution.clarification_candidates, tuple)


def test_resolution_is_deterministic_and_does_not_create_operation_id():
    service = make_service()

    first = service.resolve("статус системы")
    second = service.resolve("статус системы")

    assert first == second
    assert "operation" not in first.to_dict()


def test_invalid_clarification_answer_keeps_pending_without_execution():
    service = make_service()
    pending = service.resolve("покажи статус")

    from app.intent_resolver import ClarificationState

    selected = service.resolve(
        "непонятно",
        pending_clarification=ClarificationState(
            question_ru=pending.clarification_prompt,
            options=pending.clarification_candidates,
            original_text=pending.original_text,
            source="test",
        ),
    )

    assert selected.resolution_status == CommandResolutionStatus.REQUIRES_CLARIFICATION
    assert selected.match_source == "invalid_clarification_answer"
    assert selected.clarification_candidates == pending.clarification_candidates


def test_unrelated_known_command_during_clarification_is_legacy_passthrough():
    service = make_service()
    pending = service.resolve("покажи статус")

    from app.intent_resolver import ClarificationState

    unrelated = service.resolve(
        "привет",
        pending_clarification=ClarificationState(
            question_ru=pending.clarification_prompt,
            options=pending.clarification_candidates,
            original_text=pending.original_text,
            source="test",
        ),
    )

    assert unrelated.resolution_status == CommandResolutionStatus.LEGACY_PASSTHROUGH
