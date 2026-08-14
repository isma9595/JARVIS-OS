import importlib
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest


MODULE_NAME = "platform_adapters.user_data_paths"


def _api():
    try:
        return importlib.import_module(MODULE_NAME)
    except ModuleNotFoundError as exc:
        pytest.fail(f"required module is not implemented: {MODULE_NAME}")
        raise AssertionError("unreachable") from exc


def _resolve(*, environment, home, project_root):
    return _api().UserDataPaths.resolve(
        environment=environment,
        home=home,
        project_root=project_root,
    )


def _assert_error(*, code, environment, home, project_root):
    api = _api()
    with pytest.raises(api.UserDataPathResolutionError) as captured:
        api.UserDataPaths.resolve(
            environment=environment,
            home=home,
            project_root=project_root,
        )
    assert captured.value.code == code
    return captured.value


def test_default_paths_are_identical_from_different_working_directories(
    monkeypatch,
    tmp_path,
):
    first_cwd = tmp_path / "cwd-one"
    second_cwd = tmp_path / "cwd-two"
    first_cwd.mkdir()
    second_cwd.mkdir()
    local_app_data = tmp_path / "controlled-local-app-data"
    project_root = tmp_path / "controlled-project"
    environment = {"LOCALAPPDATA": os.fspath(local_app_data)}

    monkeypatch.chdir(first_cwd)
    first = _resolve(
        environment=environment,
        home=tmp_path / "unused-home",
        project_root=project_root,
    )
    monkeypatch.chdir(second_cwd)
    second = _resolve(
        environment=environment,
        home=tmp_path / "unused-home",
        project_root=project_root,
    )

    assert first == second
    assert first.root == local_app_data / "JARVIS-OS" / "data" / "v1"


def test_canonical_layout_v1_is_exact(tmp_path):
    root = tmp_path / "explicit-v1-root"
    paths = _resolve(
        environment={"JARVIS_USER_DATA_DIR": os.fspath(root)},
        home=tmp_path / "unused-home",
        project_root=tmp_path / "project",
    )

    assert paths.layout_version == "v1"
    assert paths.root == root
    assert paths.conversation_sessions == root / "conversation" / "sessions"
    assert paths.memory == root / "memory" / "memory.json"
    assert paths.profile == root / "profiles" / "default_user.json"
    assert paths.ideas == root / "ideas" / "ideas.json"
    assert paths.vosk_settings == root / "voice" / "vosk_settings.json"


def test_resolver_returns_absolute_bounded_paths_and_creates_nothing(tmp_path):
    local_app_data = tmp_path / "missing-local-app-data"
    project_root = tmp_path / "missing-project-root"
    before = set(tmp_path.rglob("*"))

    paths = _resolve(
        environment={"LOCALAPPDATA": os.fspath(local_app_data)},
        home=tmp_path / "missing-home",
        project_root=project_root,
    )

    store_paths = (
        paths.conversation_sessions,
        paths.memory,
        paths.profile,
        paths.ideas,
        paths.vosk_settings,
    )
    assert paths.root.is_absolute()
    assert paths.project_root.is_absolute()
    assert all(path.is_absolute() for path in store_paths)
    assert all(path.relative_to(paths.root) for path in store_paths)
    assert set(tmp_path.rglob("*")) == before


def test_user_data_paths_is_immutable(tmp_path):
    paths = _resolve(
        environment={"LOCALAPPDATA": os.fspath(tmp_path / "local")},
        home=tmp_path / "home",
        project_root=tmp_path / "project",
    )

    with pytest.raises(FrozenInstanceError):
        paths.root = tmp_path / "replacement"


def test_absolute_root_override_has_priority_without_evaluating_lower_sources(tmp_path):
    override = tmp_path / "override-v1"

    paths = _resolve(
        environment={
            "JARVIS_USER_DATA_DIR": os.fspath(override),
            "LOCALAPPDATA": "relative-lower-priority-value",
        },
        home=Path("relative-unused-home"),
        project_root=tmp_path / "project",
    )

    assert paths.root == override


def test_empty_root_override_is_unset_and_uses_absolute_local_app_data(tmp_path):
    local_app_data = tmp_path / "local"

    paths = _resolve(
        environment={
            "JARVIS_USER_DATA_DIR": "",
            "LOCALAPPDATA": os.fspath(local_app_data),
        },
        home=tmp_path / "unused-home",
        project_root=tmp_path / "project",
    )

    assert paths.root == local_app_data / "JARVIS-OS" / "data" / "v1"


@pytest.mark.parametrize(
    ("value", "expected_code"),
    [
        pytest.param("relative-root", "user_data_root_not_absolute", id="relative"),
        pytest.param("invalid\x00private-root", "user_data_root_invalid", id="malformed"),
    ],
)
def test_nonempty_invalid_root_override_fails_at_its_precedence_step(
    tmp_path,
    value,
    expected_code,
):
    error = _assert_error(
        code=expected_code,
        environment={
            "JARVIS_USER_DATA_DIR": value,
            "LOCALAPPDATA": os.fspath(tmp_path / "valid-lower-priority-local"),
        },
        home=tmp_path / "valid-lower-priority-home",
        project_root=tmp_path / "project",
    )

    assert "private-root" not in str(error)
    assert "private-root" not in repr(error)


@pytest.mark.parametrize(
    "environment",
    [
        pytest.param({}, id="absent"),
        pytest.param({"LOCALAPPDATA": ""}, id="empty"),
    ],
)
def test_absent_or_empty_local_app_data_uses_absolute_home_fallback(
    tmp_path,
    environment,
):
    home = tmp_path / "controlled-home"

    paths = _resolve(
        environment=environment,
        home=home,
        project_root=tmp_path / "project",
    )

    assert paths.root == home / ".jarvis-os" / "data" / "v1"
    assert paths.root.is_absolute()


def test_absolute_local_app_data_is_used_as_parent_of_layout_root(tmp_path):
    local_app_data = tmp_path / "local-app-data"

    paths = _resolve(
        environment={"LOCALAPPDATA": os.fspath(local_app_data)},
        home=tmp_path / "unused-home",
        project_root=tmp_path / "project",
    )

    assert paths.root == local_app_data / "JARVIS-OS" / "data" / "v1"


@pytest.mark.parametrize(
    ("value", "expected_code"),
    [
        pytest.param("relative-local", "local_app_data_not_absolute", id="relative"),
        pytest.param("invalid\x00local", "local_app_data_invalid", id="malformed"),
    ],
)
def test_present_invalid_local_app_data_fails_without_home_fallback(
    tmp_path,
    value,
    expected_code,
):
    _assert_error(
        code=expected_code,
        environment={"LOCALAPPDATA": value},
        home=tmp_path / "valid-home-that-must-not-be-used",
        project_root=tmp_path / "project",
    )


@pytest.mark.parametrize(
    "home",
    [
        pytest.param(Path("relative-home"), id="relative"),
        pytest.param("invalid\x00home", id="malformed"),
    ],
)
def test_unusable_home_fallback_has_one_safe_code(tmp_path, home):
    _assert_error(
        code="user_data_root_unavailable",
        environment={},
        home=home,
        project_root=tmp_path / "project",
    )


def test_relative_inputs_are_never_resolved_through_cwd(monkeypatch, tmp_path):
    first_cwd = tmp_path / "first-private-cwd"
    second_cwd = tmp_path / "second-private-cwd"
    first_cwd.mkdir()
    second_cwd.mkdir()

    for cwd in (first_cwd, second_cwd):
        monkeypatch.chdir(cwd)
        _assert_error(
            code="user_data_root_not_absolute",
            environment={"JARVIS_USER_DATA_DIR": "relative-root"},
            home=tmp_path / "home",
            project_root=tmp_path / "project",
        )
        _assert_error(
            code="local_app_data_not_absolute",
            environment={"LOCALAPPDATA": "relative-local"},
            home=tmp_path / "home",
            project_root=tmp_path / "project",
        )


def test_resolution_error_string_and_repr_are_privacy_safe(tmp_path):
    rejected = "relative/SECRET-ACCOUNT-NAME"
    error = _assert_error(
        code="user_data_root_not_absolute",
        environment={"JARVIS_USER_DATA_DIR": rejected},
        home=tmp_path / "home",
        project_root=tmp_path / "project",
    )

    assert str(error) == "user_data_root_not_absolute"
    assert repr(error) == (
        "UserDataPathResolutionError(code='user_data_root_not_absolute')"
    )
    assert rejected not in str(error)
    assert rejected not in repr(error)
    assert "SECRET-ACCOUNT-NAME" not in str(error)
    assert "SECRET-ACCOUNT-NAME" not in repr(error)


def test_absolute_test_project_root_is_cwd_independent(monkeypatch, tmp_path):
    first_cwd = tmp_path / "cwd-a"
    second_cwd = tmp_path / "cwd-b"
    first_cwd.mkdir()
    second_cwd.mkdir()
    project_root = tmp_path / "absolute-project"
    environment = {"LOCALAPPDATA": os.fspath(tmp_path / "local")}

    monkeypatch.chdir(first_cwd)
    first = _resolve(
        environment=environment,
        home=tmp_path / "home",
        project_root=project_root,
    )
    monkeypatch.chdir(second_cwd)
    second = _resolve(
        environment=environment,
        home=tmp_path / "home",
        project_root=project_root,
    )

    assert first.project_root == project_root
    assert second.project_root == project_root


def test_relative_test_project_root_is_rejected_with_exact_code(tmp_path):
    _assert_error(
        code="project_root_not_absolute",
        environment={"LOCALAPPDATA": os.fspath(tmp_path / "local")},
        home=tmp_path / "home",
        project_root=Path("relative-project-root"),
    )


def test_derived_store_path_escape_is_rejected(monkeypatch, tmp_path):
    api = _api()
    escaped_layout = dict(api._STORE_RELATIVE_PARTS)
    escaped_layout["memory"] = ("..", "escaped-memory.json")
    monkeypatch.setattr(api, "_STORE_RELATIVE_PARTS", escaped_layout)

    with pytest.raises(api.UserDataPathResolutionError) as captured:
        api.UserDataPaths.resolve(
            environment={"LOCALAPPDATA": os.fspath(tmp_path / "local")},
            home=tmp_path / "home",
            project_root=tmp_path / "project",
        )

    assert captured.value.code == "user_data_path_outside_root"
