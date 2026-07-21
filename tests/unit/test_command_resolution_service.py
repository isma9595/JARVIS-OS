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


def make_phase2_service():
    from core.command_processor import CommandProcessor

    attributes = {
        "voice_status": "VOICE_STATUS_COMMANDS",
        "voice_output_status": "VOICE_OUTPUT_STATUS_COMMANDS",
        "speech_backend_status": "SPEECH_BACKEND_STATUS_COMMANDS",
        "vosk_recognition_status": "VOSK_RECOGNITION_STATUS_COMMANDS",
        "vosk_recognition_dry_run": "VOSK_RECOGNITION_DRY_RUN_COMMANDS",
        "vosk_model_path_status": "VOSK_MODEL_PATH_STATUS_COMMANDS",
        "vosk_runtime_status": "VOSK_RUNTIME_STATUS_COMMANDS",
        "microphone_status": "MICROPHONE_STATUS_COMMANDS",
        "microphone_mode_off": "MICROPHONE_MODE_OFF_COMMANDS",
        "microphone_mode_partial": "MICROPHONE_MODE_PARTIAL_COMMANDS",
        "microphone_mode_continuous": "MICROPHONE_MODE_CONTINUOUS_COMMANDS",
        "one_shot_vosk_bridge": "ONE_SHOT_VOSK_BRIDGE_COMMANDS",
        "voice_output_dry_run_enable": "VOICE_OUTPUT_DRY_RUN_ENABLE_COMMANDS",
        "voice_output_disable": "VOICE_OUTPUT_DISABLE_COMMANDS",
        "voice_output_local_status": "VOICE_OUTPUT_LOCAL_STATUS_COMMANDS",
        "assistant_identity": "ASSISTANT_IDENTITY_COMMANDS",
        "assistant_name_reset": "ASSISTANT_NAME_RESET_COMMANDS",
        "assistant_name_change": "ASSISTANT_NAME_CHANGE_PREFIXES",
        "profile_status": "PROFILE_COMMANDS",
        "system_version": "VERSION_COMMANDS",
        "system_services": "SYSTEM_SERVICES_COMMANDS",
        "ai_status": "AI_STATUS_COMMANDS",
        "ai_provider_key_check": "AI_PROVIDER_KEY_CHECK_COMMANDS",
        "secure_key_status": "SECURE_KEY_STATUS_COMMANDS",
        "voice_confirmation": "VOICE_CONFIRMATION_COMMANDS",
        "greeting": "GREETING_COMMANDS",
    }
    groups = {name: getattr(CommandProcessor, attribute) for name, attribute in attributes.items()}
    groups.update(
        {
            "legacy_passthrough_exact": frozenset(
                CommandProcessor.VOICE_CONFIRMATION_COMMANDS
                | CommandProcessor.GREETING_COMMANDS
            ),
            "legacy_passthrough_mapping": {},
            "legacy_passthrough_prefix": (),
        }
    )
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


@pytest.mark.parametrize(
    ("group_name", "command_id", "category"),
    (
        ("language_set", "profile.language.set", "profile"),
        ("language_reset", "profile.language.reset", "profile"),
        ("microphone_mode_off", "microphone.mode.off", "voice"),
        ("microphone_mode_partial", "microphone.mode.partial", "voice"),
        ("microphone_mode_continuous", "microphone.mode.continuous", "voice"),
        ("voice_output_dry_run_enable", "voice.output.dry_run.enabled", "voice"),
        ("voice_output_disable", "voice.output.disable", "voice"),
        ("assistant_name_change", "assistant.name.set", "assistant"),
        ("assistant_name_reset", "assistant.name.reset", "assistant"),
    ),
)
def test_state_changing_resolver_metadata_comes_from_existing_registry(
    group_name,
    command_id,
    category,
):
    from core.command_processor import CommandProcessor

    group_to_attribute = {
        "language_set": None,
        "language_reset": None,
        "microphone_mode_off": "MICROPHONE_MODE_OFF_COMMANDS",
        "microphone_mode_partial": "MICROPHONE_MODE_PARTIAL_COMMANDS",
        "microphone_mode_continuous": "MICROPHONE_MODE_CONTINUOUS_COMMANDS",
        "voice_output_dry_run_enable": "VOICE_OUTPUT_DRY_RUN_ENABLE_COMMANDS",
        "voice_output_disable": "VOICE_OUTPUT_DISABLE_COMMANDS",
        "assistant_name_change": "ASSISTANT_NAME_CHANGE_PREFIXES",
        "assistant_name_reset": "ASSISTANT_NAME_RESET_COMMANDS",
    }
    if group_name == "language_set":
        command = "language English"
    elif group_name == "language_reset":
        command = "reset language"
    elif group_name == "assistant_name_change":
        command = next(iter(CommandProcessor.ASSISTANT_NAME_CHANGE_PREFIXES)) + " TASK096"
    else:
        command = next(iter(getattr(CommandProcessor, group_to_attribute[group_name])))

    resolution = make_phase2_service().resolve(command)

    assert resolution.resolution_status == CommandResolutionStatus.RESOLVED
    assert resolution.command_id == command_id
    assert resolution.category == category
    if resolution.metadata is not None:
        assert resolution.metadata.command_id == command_id
        assert resolution.metadata.category.value == category


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


def test_phase2_voice_vosk_microphone_and_one_shot_routes_resolve_without_execution():
    from core.command_processor import CommandProcessor

    service = make_phase2_service()

    cases = [
        (next(iter(CommandProcessor.VOSK_RECOGNITION_STATUS_COMMANDS)), "speech.backend.vosk.recognition.status", {}),
        (next(iter(CommandProcessor.MICROPHONE_STATUS_COMMANDS)), "microphone.mode.status", {}),
        (next(iter(CommandProcessor.MICROPHONE_MODE_OFF_COMMANDS)), "microphone.mode.off", {"mode": "off"}),
        (next(iter(CommandProcessor.MICROPHONE_MODE_PARTIAL_COMMANDS)), "microphone.mode.partial", {"mode": "partial"}),
        (next(iter(CommandProcessor.MICROPHONE_MODE_CONTINUOUS_COMMANDS)), "microphone.mode.continuous", {"mode": "continuous"}),
        (next(iter(CommandProcessor.ONE_SHOT_VOSK_BRIDGE_COMMANDS)), "speech.backend.vosk.one_shot_bridge", {}),
        (next(iter(CommandProcessor.VOICE_OUTPUT_LOCAL_STATUS_COMMANDS)), "voice.output.local.status", {}),
    ]

    for command, command_id, safe_args in cases:
        resolution = service.resolve(command)

        assert resolution.resolution_status == CommandResolutionStatus.RESOLVED
        assert resolution.command_id == command_id
        assert resolution.safe_args == safe_args
        assert resolution.match_source == "exact_command_group"


def test_phase2_identity_profile_version_services_provider_and_secure_routes_resolve():
    from core.command_processor import CommandProcessor

    service = make_phase2_service()

    cases = [
        (next(iter(CommandProcessor.ASSISTANT_IDENTITY_COMMANDS)), "assistant.identity", {}),
        (next(iter(CommandProcessor.PROFILE_COMMANDS)), "user.profile", {}),
        (next(iter(CommandProcessor.VERSION_COMMANDS)), "system.version", {}),
        (next(iter(CommandProcessor.SYSTEM_SERVICES_COMMANDS)), "system.services", {}),
        (next(iter(CommandProcessor.AI_STATUS_COMMANDS)), "ai.status", {}),
        (next(iter(CommandProcessor.SECURE_KEY_STATUS_COMMANDS)), "secure_keys.status", {}),
    ]

    for command, command_id, safe_args in cases:
        resolution = service.resolve(command)

        assert resolution.resolution_status == CommandResolutionStatus.RESOLVED
        assert resolution.command_id == command_id
        assert resolution.safe_args == safe_args


def test_phase2_assistant_name_and_provider_key_safe_args_are_parsed_without_mutation():
    from core.command_processor import CommandProcessor

    service = make_phase2_service()
    name_prefix = CommandProcessor.ASSISTANT_NAME_CHANGE_PREFIXES[0]
    provider_command, provider = next(iter(CommandProcessor.AI_PROVIDER_KEY_CHECK_COMMANDS.items()))

    assistant = service.resolve(f"{name_prefix} JARVIS")
    provider_key = service.resolve(provider_command)

    assert assistant.resolution_status == CommandResolutionStatus.RESOLVED
    assert assistant.command_id == "assistant.name.set"
    assert assistant.safe_args == {"assistant_name": "JARVIS"}
    assert provider_key.resolution_status == CommandResolutionStatus.RESOLVED
    assert provider_key.command_id == "ai.key_check"
    assert provider_key.safe_args == {"provider": provider}


def test_task095_shared_alias_precedence_matches_existing_first_reachable_routes():
    from core.command_processor import CommandProcessor

    processor = CommandProcessor()
    service = CommandResolutionService(
        command_registry=processor.command_registry,
        command_groups=processor._command_resolution_groups(),
    )

    recognition = service.resolve("тест распознавания")
    model_path = service.resolve("путь модели vosk")
    microphone = service.resolve("выключи микрофон")

    assert recognition.resolution_status == CommandResolutionStatus.RESOLVED
    assert recognition.command_id == "speech.backend.vosk.recognition.dry_run"
    assert model_path.resolution_status == CommandResolutionStatus.RESOLVED
    assert model_path.command_id == "speech.backend.vosk.model.path.status"
    assert microphone.resolution_status == CommandResolutionStatus.RESOLVED
    assert microphone.command_id == "microphone.mode.off"
    assert microphone.safe_args == {"mode": "off"}


def test_task095_overlapping_legacy_long_forms_remain_reachable():
    from core.command_processor import CommandProcessor

    processor = CommandProcessor()
    service = CommandResolutionService(
        command_registry=processor.command_registry,
        command_groups=processor._command_resolution_groups(),
    )

    typed_simulation = service.resolve("тест распознавания включи свет")
    vosk_model_set = service.resolve("путь модели vosk C:\\models\\vosk-small-ru")
    microphone_stop = service.resolve("перестань слушать")

    assert (
        typed_simulation.resolution_status
        == CommandResolutionStatus.LEGACY_PASSTHROUGH
    )
    assert vosk_model_set.resolution_status == CommandResolutionStatus.LEGACY_PASSTHROUGH
    assert microphone_stop.resolution_status == CommandResolutionStatus.LEGACY_PASSTHROUGH


def test_task095_manual_smoke_text_resolves_to_current_command_ids():
    from core.command_processor import CommandProcessor

    processor = CommandProcessor()
    service = CommandResolutionService(
        command_registry=processor.command_registry,
        command_groups=processor._command_resolution_groups(),
    )

    cases = [
        ("тест распознавания", "speech.backend.vosk.recognition.dry_run", "voice"),
        ("путь модели vosk", "speech.backend.vosk.model.path.status", "voice"),
        ("статус микрофона", "microphone.mode.status", "voice"),
        ("профиль", "user.profile", "profile"),
        ("версия", "system.version", "system"),
        ("покажи сервисы", "system.services", "system"),
        ("статус голосового ответа", "voice.output.status", "voice"),
        ("как тебя зовут", "assistant.identity", "assistant"),
    ]

    for text, command_id, category in cases:
        resolution = service.resolve(text)

        assert resolution.resolution_status == CommandResolutionStatus.RESOLVED
        assert resolution.command_id == command_id
        assert resolution.category == category
        assert resolution.match_source == "exact_command_group"


def test_phase2_legacy_confirmation_greeting_unknown_and_determinism_invariants():
    from core.command_processor import CommandProcessor

    service = make_phase2_service()
    confirmation = service.resolve(next(iter(CommandProcessor.VOICE_CONFIRMATION_COMMANDS)))
    greeting = service.resolve(next(iter(CommandProcessor.GREETING_COMMANDS)))
    unknown = service.resolve("task095 genuinely unknown route")
    first = service.resolve(next(iter(CommandProcessor.SECURE_KEY_STATUS_COMMANDS)))
    second = service.resolve(next(iter(CommandProcessor.SECURE_KEY_STATUS_COMMANDS)))

    assert confirmation.resolution_status == CommandResolutionStatus.LEGACY_PASSTHROUGH
    assert greeting.resolution_status == CommandResolutionStatus.LEGACY_PASSTHROUGH
    assert unknown.resolution_status == CommandResolutionStatus.UNKNOWN
    assert first == second
    assert "operation" not in first.to_dict()

    with pytest.raises(TypeError):
        first.safe_args["provider"] = "changed"


def test_phase2_resolver_source_has_no_execution_side_effect_dependencies():
    from pathlib import Path

    source = Path("core/command_resolution_service.py").read_text(encoding="utf-8")
    forbidden = [
        "from core.command_processor",
        "start_listening",
        "listen_once_from_microphone",
        "run_once(",
        "speak(",
        "generate(",
        "save_profile",
        "import_from_env",
        "delete_provider_key",
        "register_operation",
        "action_router.route",
    ]

    for token in forbidden:
        assert token not in source
