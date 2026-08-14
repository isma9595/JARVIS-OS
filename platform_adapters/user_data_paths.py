"""Pure resolution of canonical local user-data paths."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
from typing import ClassVar


USER_DATA_LAYOUT_VERSION = "v1"

_MISSING = object()
_STORE_RELATIVE_PARTS: dict[str, tuple[str, ...]] = {
    "conversation_sessions": ("conversation", "sessions"),
    "memory": ("memory", "memory.json"),
    "profile": ("profiles", "default_user.json"),
    "ideas": ("ideas", "ideas.json"),
    "vosk_settings": ("voice", "vosk_settings.json"),
}


class UserDataPathResolutionError(ValueError):
    """Stable path-resolution failure that retains no rejected path value."""

    def __init__(self, code: str):
        self.code = str(code)
        super().__init__(self.code)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r})"


@dataclass(frozen=True, slots=True)
class UserDataPaths:
    """Absolute canonical paths shared by one supported composition root."""

    layout_version: str
    root: Path
    conversation_sessions: Path
    memory: Path
    profile: Path
    ideas: Path
    vosk_settings: Path
    project_root: Path

    LAYOUT_VERSION: ClassVar[str] = USER_DATA_LAYOUT_VERSION

    @classmethod
    def resolve(
        cls,
        *,
        environment: Mapping[str, object] | None = None,
        home: str | os.PathLike[str] | None = None,
        project_root: str | os.PathLike[str] | None = None,
    ) -> UserDataPaths:
        """Resolve paths lexically without reading or changing filesystem state."""

        selected_environment = os.environ if environment is None else environment
        root = _select_canonical_root(selected_environment, home=home)
        selected_project_root = _select_project_root(project_root)
        derived = {
            name: _bounded_child(root, parts)
            for name, parts in _STORE_RELATIVE_PARTS.items()
        }
        return cls(
            layout_version=USER_DATA_LAYOUT_VERSION,
            root=root,
            conversation_sessions=derived["conversation_sessions"],
            memory=derived["memory"],
            profile=derived["profile"],
            ideas=derived["ideas"],
            vosk_settings=derived["vosk_settings"],
            project_root=selected_project_root,
        )


def _select_canonical_root(
    environment: Mapping[str, object],
    *,
    home: str | os.PathLike[str] | None,
) -> Path:
    override = _environment_value(
        environment,
        "JARVIS_USER_DATA_DIR",
        invalid_code="user_data_root_invalid",
    )
    if override is not _MISSING and override != "":
        return _absolute_lexical_path(
            override,
            not_absolute_code="user_data_root_not_absolute",
            invalid_code="user_data_root_invalid",
        )

    local_app_data = _environment_value(
        environment,
        "LOCALAPPDATA",
        invalid_code="local_app_data_invalid",
    )
    if local_app_data is not _MISSING and local_app_data != "":
        parent = _absolute_lexical_path(
            local_app_data,
            not_absolute_code="local_app_data_not_absolute",
            invalid_code="local_app_data_invalid",
        )
        return _lexically_normalized_path(
            parent / "JARVIS-OS" / "data" / USER_DATA_LAYOUT_VERSION,
            invalid_code="local_app_data_invalid",
        )

    try:
        selected_home = Path.home() if home is None else home
        home_path = _absolute_lexical_path(
            selected_home,
            not_absolute_code="user_data_root_unavailable",
            invalid_code="user_data_root_unavailable",
        )
        return _lexically_normalized_path(
            home_path / ".jarvis-os" / "data" / USER_DATA_LAYOUT_VERSION,
            invalid_code="user_data_root_unavailable",
        )
    except UserDataPathResolutionError:
        raise
    except Exception:
        raise UserDataPathResolutionError("user_data_root_unavailable") from None


def _select_project_root(
    explicit_root: str | os.PathLike[str] | None,
) -> Path:
    if explicit_root is None:
        return Path(__file__).resolve().parents[1]
    return _absolute_lexical_path(
        explicit_root,
        not_absolute_code="project_root_not_absolute",
        invalid_code="project_root_not_absolute",
    )


def _environment_value(
    environment: Mapping[str, object],
    name: str,
    *,
    invalid_code: str,
) -> object:
    try:
        if name not in environment:
            return _MISSING
        return environment[name]
    except Exception:
        raise UserDataPathResolutionError(invalid_code) from None


def _absolute_lexical_path(
    value: object,
    *,
    not_absolute_code: str,
    invalid_code: str,
) -> Path:
    try:
        raw = os.fspath(value)
        if not isinstance(raw, str) or "\x00" in raw:
            raise ValueError("invalid path value")
        candidate = Path(raw)
    except Exception:
        raise UserDataPathResolutionError(invalid_code) from None

    if not candidate.is_absolute():
        raise UserDataPathResolutionError(not_absolute_code)

    normalized = _lexically_normalized_path(candidate, invalid_code=invalid_code)
    if not normalized.is_absolute():
        raise UserDataPathResolutionError(not_absolute_code)
    return normalized


def _lexically_normalized_path(value: object, *, invalid_code: str) -> Path:
    try:
        raw = os.fspath(value)
        if not isinstance(raw, str) or "\x00" in raw:
            raise ValueError("invalid path value")
        return Path(os.path.normpath(raw))
    except Exception:
        raise UserDataPathResolutionError(invalid_code) from None


def _bounded_child(root: Path, parts: tuple[str, ...]) -> Path:
    try:
        candidate = _lexically_normalized_path(
            root.joinpath(*parts),
            invalid_code="user_data_path_outside_root",
        )
        candidate.relative_to(root)
    except (UserDataPathResolutionError, ValueError):
        raise UserDataPathResolutionError("user_data_path_outside_root") from None
    return candidate
