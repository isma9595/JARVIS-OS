from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.app_service import JarvisAppService, create_default_desktop_app_service
from platform_adapters.user_data_paths import UserDataPaths


def _environment(tmp_path: Path) -> dict[str, str]:
    return {
        "LOCALAPPDATA": str(tmp_path / "local-app-data"),
        "APPDATA": str(tmp_path / "roaming-app-data"),
    }


def _paths(tmp_path: Path, environment: dict[str, str]) -> UserDataPaths:
    return UserDataPaths.resolve(
        environment=environment,
        home=tmp_path / "home",
        project_root=tmp_path / "project",
    )


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")


def _legacy_sources(paths: UserDataPaths, environment: dict[str, str]) -> dict[str, Path]:
    return {
        "conversation": Path(environment["LOCALAPPDATA"]) / "JARVIS-OS" / "data" / "v1" / "cognition" / "sessions",
        "memory": paths.project_root / "memory" / "local" / "memory.json",
        "profile": paths.project_root / "users" / "profiles" / "default_user.json",
        "ideas": paths.project_root / "ideas" / "ideas.json",
        "vosk_settings": paths.project_root / "config" / "local" / "vosk_settings.json",
    }


def test_default_desktop_composition_migrates_then_injects_one_canonical_layout(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    paths = _paths(tmp_path, environment)
    legacy = _legacy_sources(paths, environment)
    legacy["conversation"].mkdir(parents=True)
    _write(legacy["memory"], {"version": "0.1", "items": []})
    _write(legacy["profile"], {"language": "ru"})
    _write(legacy["ideas"], {"ideas": []})
    _write(legacy["vosk_settings"], {"language": "ru"})

    service = create_default_desktop_app_service(
        environment=environment,
        home=tmp_path / "home",
        project_root=paths.project_root,
    )

    assert service.user_data_paths is paths or service.user_data_paths == paths
    assert service.command_processor.memory_manager.storage_path == paths.memory
    assert service.command_processor.idea_manager.storage_path == paths.ideas
    assert service.command_processor.user_profile_manager.profile_path == paths.profile
    assert service.memory_manager is service.command_processor.memory_manager
    assert service.command_processor.voice_input_manager._vosk_backend.settings_manager.settings_path == paths.vosk_settings
    assert service.command_processor.one_shot_vosk_real_recognition.settings_manager.settings_path == paths.vosk_settings
    assert service.cognitive_session_service._repository.storage_dir == paths.conversation_sessions
    assert all(path.exists() for path in legacy.values())
    assert tuple(store.code for store in service.persistence_health().stores[:5]) == ("ready",) * 5
    assert service.migration_report.completed is True
    health_card = service.persistence_health_status_card()
    assert health_card is not None
    assert health_card.card_id == "persistence_health"
    assert str(tmp_path) not in repr(health_card)
    assert all(str(tmp_path) not in value for value in health_card.details_ru)


def test_desktop_composition_is_cwd_independent_and_uses_exact_conversation_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    override = tmp_path / "explicit-session-override"
    environment["JARVIS_COGNITIVE_SESSION_DIR"] = str(override)
    project_root = tmp_path / "project"
    first_cwd = tmp_path / "cwd-one"
    second_cwd = tmp_path / "cwd-two"
    first_cwd.mkdir()
    second_cwd.mkdir()

    monkeypatch.chdir(first_cwd)
    first = create_default_desktop_app_service(
        environment=environment,
        home=tmp_path / "home",
        project_root=project_root,
    )
    monkeypatch.chdir(second_cwd)
    second = create_default_desktop_app_service(
        environment=environment,
        home=tmp_path / "home",
        project_root=project_root,
    )

    assert first.user_data_paths == second.user_data_paths
    assert first.cognitive_session_service._repository.storage_dir == override
    assert second.cognitive_session_service._repository.storage_dir == override
    assert next(store for store in second.persistence_health().stores if store.store_id == "conversation").code == "missing"


def test_blocking_migration_prevents_all_ordinary_owner_construction(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    paths = _paths(tmp_path, environment)
    legacy = _legacy_sources(paths, environment)
    _write(legacy["memory"], {"version": "0.1", "items": "corrupt"})

    with pytest.raises(RuntimeError, match="user_data_migration_blocked:memory"):
        create_default_desktop_app_service(
            environment=environment,
            home=tmp_path / "home",
            project_root=paths.project_root,
        )

    assert not paths.ideas.exists()
    assert not paths.profile.exists()
    assert not paths.vosk_settings.exists()


def test_direct_app_service_remains_in_memory_and_does_not_resolve_user_data(tmp_path: Path) -> None:
    before = tuple(tmp_path.rglob("*"))

    service = JarvisAppService()

    assert not hasattr(service, "user_data_paths") or service.user_data_paths is None
    assert service.cognitive_session_service._repository is None
    assert tuple(tmp_path.rglob("*")) == before


def test_cli_composition_uses_same_paths_and_existing_vosk_injections(tmp_path: Path) -> None:
    from run import create_default_cli_composition

    environment = _environment(tmp_path)
    project_root = tmp_path / "project"

    composition = create_default_cli_composition(
        environment=environment,
        home=tmp_path / "home",
        project_root=project_root,
    )

    assert composition.paths == _paths(tmp_path, environment)
    assert composition.migration_report.completed is True
    assert composition.kernel.memory_manager.storage_path == composition.paths.memory
    assert composition.kernel.idea_manager.storage_path == composition.paths.ideas
    assert composition.profile_manager.profile_path == composition.paths.profile
    assert composition.kernel.voice_input_manager._vosk_backend.settings_manager.settings_path == composition.paths.vosk_settings
    assert composition.kernel.command_processor.one_shot_vosk_real_recognition.settings_manager.settings_path == composition.paths.vosk_settings


def test_cli_first_launch_profile_is_loaded_before_kernel_services_are_built(
    tmp_path: Path,
) -> None:
    from run import create_default_cli_composition

    environment = _environment(tmp_path)
    setup_calls: list[Path] = []

    def setup_profile(profile_manager) -> None:
        setup_calls.append(profile_manager.profile_path)
        profile_manager.create_profile(
            user_name="Ismail",
            preferred_name="Ismail",
            assistant_name="JARVIS",
            language="ru",
        )

    composition = create_default_cli_composition(
        environment=environment,
        home=tmp_path / "home",
        project_root=tmp_path / "project",
        profile_setup=setup_profile,
    )

    assert setup_calls == [composition.paths.profile]
    assert composition.kernel.get_user_display_name() == "Ismail"
    assert composition.kernel.command_processor.user_profile["preferred_name"] == "Ismail"


def test_explicit_store_overrides_remain_authoritative_and_skip_default_migration(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    memory_override = tmp_path / "overrides" / "memory.json"
    ideas_override = tmp_path / "overrides" / "ideas.json"
    _write(memory_override, {"version": "0.1", "items": []})

    service = create_default_desktop_app_service(
        environment=environment,
        home=tmp_path / "home",
        project_root=tmp_path / "project",
        store_overrides={
            "memory": memory_override,
            "ideas": ideas_override,
        },
    )

    assert service.command_processor.memory_manager.storage_path == memory_override
    assert service.command_processor.idea_manager.storage_path == ideas_override
    assert ideas_override.is_file()
    assert not service.user_data_paths.memory.exists()
    assert not service.user_data_paths.ideas.exists()
