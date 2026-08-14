from __future__ import annotations

from contextlib import contextmanager
from dataclasses import FrozenInstanceError
import errno
import importlib
import json
import multiprocessing
import os
from pathlib import Path
import threading
from typing import Any

import pytest

from platform_adapters.user_data_paths import UserDataPaths


STORE_IDS = ("conversation", "memory", "profile", "ideas", "vosk_settings")


@pytest.fixture(scope="module")
def migration_api():
    try:
        return importlib.import_module("platform_adapters.user_data_migration")
    except ModuleNotFoundError:
        pytest.fail("TASK-125 migration boundary is not implemented")


def _paths(tmp_path: Path) -> UserDataPaths:
    return UserDataPaths.resolve(
        environment={"JARVIS_USER_DATA_DIR": str(tmp_path / "canonical-v1")},
        home=tmp_path / "unused-home",
        project_root=tmp_path / "project",
    )


def _registry(api: Any, candidates: dict[str, tuple[Path, ...]] | None = None):
    return api.DeterministicLegacyRegistry.from_mapping(candidates or {})


def _coordinator(
    api: Any,
    paths: UserDataPaths,
    candidates: dict[str, tuple[Path, ...]] | None = None,
    **kwargs: Any,
):
    return api.UserDataMigrationCoordinator(
        paths,
        _registry(api, candidates),
        **kwargs,
    )


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _valid_payload(store_id: str) -> bytes:
    values = {
        "memory": {"version": "0.1", "items": []},
        "profile": {},
        "ideas": {"ideas": []},
        "vosk_settings": {},
    }
    return _json_bytes(values[store_id])


def _valid_session(session_id: str = "session-1", *, schema_version: int = 1) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "session_id": session_id,
        "status": "active",
        "created_at": "2026-08-05T00:00:00+00:00",
        "updated_at": "2026-08-05T00:00:00+00:00",
        "turn_count": 0,
        "last_turn_id": None,
        "turns": [],
        "revision": 1,
    }


def _valid_session_with_two_turns(session_id: str = "session-1") -> dict[str, object]:
    record = _valid_session(session_id)
    turns = [
        {
            "turn_id": "turn-1",
            "sequence": 1,
            "role": "user",
            "source_classification": "typed_input",
            "created_at": "2026-08-05T00:00:01+00:00",
            "summary_text": "hello",
            "content_classification": "bounded_redacted_summary",
            "redaction_reason": None,
        },
        {
            "turn_id": "turn-2",
            "sequence": 2,
            "role": "assistant",
            "source_classification": "assistant.response",
            "created_at": "2026-08-05T00:00:02+00:00",
            "summary_text": "world",
            "content_classification": "redacted_sensitive_content",
            "redaction_reason": "sensitive_content",
        },
    ]
    record.update(turn_count=2, last_turn_id="turn-2", turns=turns)
    return record


def _receipt_path(paths: UserDataPaths, store_id: str) -> Path:
    return paths.root / ".migration" / "v1" / f"{store_id}.json"


def _canonical_path(paths: UserDataPaths, store_id: str) -> Path:
    return {
        "conversation": paths.conversation_sessions,
        "memory": paths.memory,
        "profile": paths.profile,
        "ideas": paths.ideas,
        "vosk_settings": paths.vosk_settings,
    }[store_id]


def _write_valid_store(path: Path, store_id: str) -> None:
    if store_id == "conversation":
        path.mkdir(parents=True, exist_ok=True)
        return
    _write(path, _valid_payload(store_id))


def _process_attempt(
    root: str,
    project_root: str,
    legacy: str,
    start_event: Any,
    result_queue: Any,
) -> None:
    api = importlib.import_module("platform_adapters.user_data_migration")
    paths = UserDataPaths.resolve(
        environment={"JARVIS_USER_DATA_DIR": root},
        home=Path(root).parent / "unused-home",
        project_root=project_root,
    )
    registry = api.DeterministicLegacyRegistry.from_mapping(
        {"memory": (Path(legacy),)}
    )
    if not start_event.wait(5.0):
        result_queue.put("start_timeout")
        return
    result = api.UserDataMigrationCoordinator(
        paths,
        registry,
        lock_timeout_seconds=4.0,
    ).attempt_store("memory")
    result_queue.put(result.internal_code)


def test_deterministic_registry_uses_only_explicit_known_candidates(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    conversation = tmp_path / "legacy-conversation" / "sessions"

    registry = migration_api.DeterministicLegacyRegistry.from_user_data_paths(
        paths,
        conversation_legacy=conversation,
    )

    assert registry.candidates_for("conversation") == (conversation,)
    assert registry.candidates_for("memory") == (
        paths.project_root / "memory" / "local" / "memory.json",
    )
    assert registry.candidates_for("profile") == (
        paths.project_root / "users" / "profiles" / "default_user.json",
    )
    assert registry.candidates_for("ideas") == (
        paths.project_root / "ideas" / "ideas.json",
    )
    assert registry.candidates_for("vosk_settings") == (
        paths.project_root / "config" / "local" / "vosk_settings.json",
    )
    assert "secure_keys" not in migration_api.ORDINARY_STORE_IDS
    assert str(tmp_path) not in repr(registry)


def test_registry_rejects_relative_or_unknown_candidates(
    migration_api: Any,
) -> None:
    with pytest.raises(ValueError, match="legacy_candidate_not_absolute"):
        migration_api.DeterministicLegacyRegistry.from_mapping(
            {"memory": (Path("relative-memory.json"),)}
        )
    with pytest.raises(ValueError, match="unsupported_store_id"):
        migration_api.DeterministicLegacyRegistry.from_mapping(
            {"secure_keys": (Path("C:/secure_keys.json"),)}
        )


def test_valid_legacy_file_is_copied_with_private_receipt_and_source_unchanged(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy" / "memory.json"
    original = b'{"version":"0.1","items":[],"marker":"private-marker"}\n'
    _write(legacy, original)

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
    ).attempt_store("memory")

    assert result.internal_code == "migrated"
    assert result.projection.code == "migrated"
    assert result.projection.blocking is False
    assert paths.memory.read_bytes() == original
    assert legacy.read_bytes() == original
    receipt = json.loads(_receipt_path(paths, "memory").read_text(encoding="utf-8"))
    assert receipt == {
        "layout_version": "v1",
        "store_id": "memory",
        "established": True,
    }
    receipt_text = json.dumps(receipt)
    assert "private-marker" not in receipt_text
    assert str(tmp_path) not in receipt_text


def test_valid_legacy_migrates_when_the_full_canonical_hierarchy_is_absent(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = UserDataPaths.resolve(
        environment={"LOCALAPPDATA": str(tmp_path / "fresh-local-app-data")},
        home=tmp_path / "unused-home",
        project_root=tmp_path / "project",
    )
    legacy = tmp_path / "legacy" / "memory.json"
    payload = _valid_payload("memory")
    _write(legacy, payload)
    assert not paths.root.parent.exists()

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
    ).attempt_store("memory")

    assert result.internal_code == "migrated"
    assert paths.memory.read_bytes() == payload
    assert _receipt_path(paths, "memory").is_file()


def test_valid_receipt_selects_canonical_only_and_ignores_unsafe_retained_legacy(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    _write(paths.memory, _valid_payload("memory"))
    _write(
        _receipt_path(paths, "memory"),
        _json_bytes({"layout_version": "v1", "store_id": "memory", "established": True}),
    )
    retained_legacy = tmp_path / "legacy-memory"
    retained_legacy.mkdir()

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (retained_legacy,)},
    ).attempt_store("memory")

    assert result.internal_code == "not_required"
    assert result.projection.blocking is False


@pytest.mark.parametrize(
    "receipt",
    [
        b"not-json",
        _json_bytes([]),
        _json_bytes({}),
        _json_bytes({"layout_version": "v1", "store_id": "memory", "established": 1}),
        _json_bytes({"layout_version": "v2", "store_id": "memory", "established": True}),
        _json_bytes({"layout_version": "v1", "store_id": "ideas", "established": True}),
        _json_bytes(
            {
                "layout_version": "v1",
                "store_id": "memory",
                "established": True,
                "extra": "forbidden",
            }
        ),
    ],
    ids=("json", "non-object", "missing", "bool-type", "layout", "store", "unknown"),
)
def test_invalid_regular_receipt_is_migration_state_invalid_and_never_repaired(
    migration_api: Any,
    tmp_path: Path,
    receipt: bytes,
) -> None:
    paths = _paths(tmp_path)
    _write(paths.memory, _valid_payload("memory"))
    receipt_path = _receipt_path(paths, "memory")
    _write(receipt_path, receipt)

    result = _coordinator(migration_api, paths).attempt_store("memory")

    assert result.internal_code == "migration_state_invalid"
    assert result.projection.code == "migration_state_invalid"
    assert result.projection.blocking is True
    assert receipt_path.read_bytes() == receipt


def test_valid_receipt_without_canonical_is_migration_state_invalid(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    _write(
        _receipt_path(paths, "memory"),
        _json_bytes({"layout_version": "v1", "store_id": "memory", "established": True}),
    )

    result = _coordinator(migration_api, paths).attempt_store("memory")

    assert result.internal_code == "migration_state_invalid"
    assert result.projection.blocking is True


def test_receipt_wrong_physical_type_is_unavailable(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    _write(paths.memory, _valid_payload("memory"))
    _receipt_path(paths, "memory").mkdir(parents=True)

    result = _coordinator(migration_api, paths).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"
    assert result.projection.blocking is True


def test_absent_canonical_and_legacy_is_not_required_and_creates_nothing(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    before = tuple(tmp_path.rglob("*"))

    result = _coordinator(migration_api, paths).attempt_store("memory")

    assert result.internal_code == "not_required"
    assert result.projection.code == "not_required"
    assert result.projection.blocking is False
    assert tuple(tmp_path.rglob("*")) == before
    assert not _receipt_path(paths, "memory").exists()


def test_valid_canonical_without_legacy_establishes_provenance(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    canonical = _valid_payload("memory")
    _write(paths.memory, canonical)

    result = _coordinator(migration_api, paths).attempt_store("memory")

    assert result.internal_code == "provenance_established"
    assert result.projection.code == "provenance_established"
    assert result.projection.blocking is False
    assert paths.memory.read_bytes() == canonical
    assert _receipt_path(paths, "memory").is_file()


@pytest.mark.parametrize(
    ("legacy_payload", "expected"),
    [
        (_valid_payload("memory"), "provenance_established"),
        (b'{ "version": "0.1", "items": [] }\n', "canonical_legacy_conflict"),
    ],
    ids=("byte-identical", "semantic-only-equality"),
)
def test_canonical_legacy_comparison_is_exact_bytes(
    migration_api: Any,
    tmp_path: Path,
    legacy_payload: bytes,
    expected: str,
) -> None:
    paths = _paths(tmp_path)
    canonical = _valid_payload("memory")
    legacy = tmp_path / "legacy" / "memory.json"
    _write(paths.memory, canonical)
    _write(legacy, legacy_payload)

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
    ).attempt_store("memory")

    assert result.internal_code == expected
    assert paths.memory.read_bytes() == canonical
    assert legacy.read_bytes() == legacy_payload
    assert _receipt_path(paths, "memory").exists() is (expected == "provenance_established")


def test_multiple_safe_legacy_candidates_are_not_selected(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    first = tmp_path / "legacy-a.json"
    second = tmp_path / "legacy-b.json"
    _write(first, _valid_payload("memory"))
    _write(second, _valid_payload("memory"))

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (first, second)},
    ).attempt_store("memory")

    assert result.internal_code == "multiple_legacy_sources"
    assert result.projection.blocking is True
    assert not paths.memory.exists()
    assert first.exists() and second.exists()


def test_unsafe_candidate_precedes_multiple_sources(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    safe = tmp_path / "safe-memory.json"
    unsafe = tmp_path / "wrong-type-memory"
    _write(safe, _valid_payload("memory"))
    unsafe.mkdir()

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (safe, unsafe)},
    ).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"
    assert not paths.memory.exists()


@pytest.mark.parametrize(
    ("location", "payload", "expected", "projected"),
    [
        ("legacy", b"not-json", "legacy_corrupt", "corrupt"),
        ("legacy", _json_bytes({"version": "0.2", "items": []}), "legacy_unsupported_version", "unsupported_version"),
        ("canonical", b"not-json", "corrupt", "corrupt"),
        ("canonical", _json_bytes({"version": "0.2", "items": []}), "unsupported_version", "unsupported_version"),
    ],
)
def test_corrupt_and_unsupported_sources_have_exact_codes(
    migration_api: Any,
    tmp_path: Path,
    location: str,
    payload: bytes,
    expected: str,
    projected: str,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    candidates: dict[str, tuple[Path, ...]] = {}
    if location == "legacy":
        _write(legacy, payload)
        candidates = {"memory": (legacy,)}
    else:
        _write(paths.memory, payload)
        _write(legacy, _valid_payload("memory"))
        candidates = {"memory": (legacy,)}

    result = _coordinator(migration_api, paths, candidates).attempt_store("memory")

    assert result.internal_code == expected
    assert result.projection.code == projected
    assert result.projection.blocking is True
    assert not _receipt_path(paths, "memory").exists()


@pytest.mark.parametrize(
    ("store_id", "payload", "expected"),
    [
        ("memory", _json_bytes({"version": "0.1", "items": [], "unknown": {}}), "provenance_established"),
        ("memory", _json_bytes({"items": []}), "corrupt"),
        ("memory", _json_bytes({"version": True, "items": []}), "corrupt"),
        ("memory", _json_bytes({"version": "0.1", "items": {}}), "corrupt"),
        ("memory", _json_bytes({"version": "9", "items": "ignored"}), "unsupported_version"),
        ("profile", _json_bytes({}), "provenance_established"),
        ("profile", _json_bytes({"version": 999, "anything": [None, True]}), "provenance_established"),
        ("profile", _json_bytes([]), "corrupt"),
        ("ideas", _json_bytes({}), "provenance_established"),
        ("ideas", _json_bytes({"ideas": [1, None, {"free": "shape"}], "unknown": True}), "provenance_established"),
        ("ideas", _json_bytes({"ideas": None}), "corrupt"),
        ("vosk_settings", _json_bytes({}), "provenance_established"),
        ("vosk_settings", _json_bytes({"model_path": None, "language": "ru", "unknown": 1}), "provenance_established"),
        ("vosk_settings", _json_bytes({"model_path": " relative/model ", "language": " en "}), "provenance_established"),
        ("vosk_settings", _json_bytes({"model_path": "   "}), "corrupt"),
        ("vosk_settings", _json_bytes({"language": None}), "corrupt"),
        ("vosk_settings", _json_bytes({"language": 1}), "corrupt"),
    ],
)
def test_file_store_validation_matrix(
    migration_api: Any,
    tmp_path: Path,
    store_id: str,
    payload: bytes,
    expected: str,
) -> None:
    paths = _paths(tmp_path)
    _write(_canonical_path(paths, store_id), payload)

    result = _coordinator(migration_api, paths).attempt_store(store_id)

    assert result.internal_code == expected
    assert result.projection.blocking is (expected != "provenance_established")


@pytest.mark.parametrize("payload", [b"", b"\xff", b"{", b"[]", b"null", b'"text"'])
@pytest.mark.parametrize("store_id", ["memory", "profile", "ideas", "vosk_settings"])
def test_global_json_file_corruption_rules(
    migration_api: Any,
    tmp_path: Path,
    store_id: str,
    payload: bytes,
) -> None:
    paths = _paths(tmp_path)
    _write(_canonical_path(paths, store_id), payload)

    result = _coordinator(migration_api, paths).attempt_store(store_id)

    assert result.internal_code == "corrupt"
    assert result.projection.code == "corrupt"


@pytest.mark.parametrize(
    ("store_id", "failure"),
    [
        pytest.param("memory", ValueError("integer limit"), id="file-value-error"),
        pytest.param("conversation", RecursionError("nested input"), id="conversation-recursion"),
    ],
)
def test_additional_json_parser_failures_are_classified_as_corrupt(
    migration_api: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    store_id: str,
    failure: BaseException,
) -> None:
    paths = _paths(tmp_path)
    if store_id == "conversation":
        _write(paths.conversation_sessions / "session-1.json", b"{}")
    else:
        _write(paths.memory, b"{}")

    def fail_json_loads(*args: Any, **kwargs: Any) -> object:
        del args, kwargs
        raise failure

    monkeypatch.setattr(migration_api.json, "loads", fail_json_loads)

    result = _coordinator(migration_api, paths).attempt_store(store_id)

    assert result.internal_code == "corrupt"
    assert result.projection.code == "corrupt"


def test_additional_receipt_json_parser_failure_is_migration_state_invalid(
    migration_api: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    _write(paths.memory, _valid_payload("memory"))
    _write(_receipt_path(paths, "memory"), b"{}")

    def fail_json_loads(*args: Any, **kwargs: Any) -> object:
        del args, kwargs
        raise ValueError("integer limit")

    monkeypatch.setattr(migration_api.json, "loads", fail_json_loads)

    result = _coordinator(migration_api, paths).attempt_store("memory")

    assert result.internal_code == "migration_state_invalid"
    assert result.projection.code == "migration_state_invalid"


@pytest.mark.parametrize("store_id", ["memory", "profile", "ideas", "vosk_settings"])
def test_file_store_wrong_physical_type_is_unavailable(
    migration_api: Any,
    tmp_path: Path,
    store_id: str,
) -> None:
    paths = _paths(tmp_path)
    _canonical_path(paths, store_id).mkdir(parents=True)

    result = _coordinator(migration_api, paths).attempt_store(store_id)

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"


def test_empty_conversation_directory_is_valid_and_receipted(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    paths.conversation_sessions.mkdir(parents=True)

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == "provenance_established"
    assert _receipt_path(paths, "conversation").is_file()


def test_valid_conversation_record_and_turns_are_accepted(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    record = _valid_session_with_two_turns()
    _write(paths.conversation_sessions / "session-1.json", _json_bytes(record))

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == "provenance_established"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda record: record.pop("revision"),
        lambda record: record.update(extra=True),
        lambda record: record.update(schema_version=True),
        lambda record: record.update(status="unknown"),
        lambda record: record.update(created_at=""),
        lambda record: record.update(turn_count=True),
        lambda record: record.update(last_turn_id="orphan"),
        lambda record: record.update(revision=0),
        lambda record: record.update(turns={}),
    ],
    ids=("missing", "unknown", "bool-version", "status", "timestamp", "bool-count", "last-id", "revision", "turns"),
)
def test_invalid_conversation_session_contract_is_corrupt(
    migration_api: Any,
    tmp_path: Path,
    mutator: Any,
) -> None:
    paths = _paths(tmp_path)
    record = _valid_session()
    mutator(record)
    _write(paths.conversation_sessions / "session-1.json", _json_bytes(record))

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == "corrupt"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda turn: turn.pop("role"),
        lambda turn: turn.update(extra=True),
        lambda turn: turn.update(sequence=2),
        lambda turn: turn.update(role="system"),
        lambda turn: turn.update(source_classification="Upper Case"),
        lambda turn: turn.update(created_at=""),
        lambda turn: turn.update(summary_text=""),
        lambda turn: turn.update(summary_text="x" * 161),
        lambda turn: turn.update(content_classification="plain"),
        lambda turn: turn.update(redaction_reason=""),
    ],
    ids=("missing", "unknown", "sequence", "role", "source", "created", "summary-empty", "summary-long", "classification", "reason"),
)
def test_invalid_conversation_turn_contract_is_corrupt(
    migration_api: Any,
    tmp_path: Path,
    mutator: Any,
) -> None:
    paths = _paths(tmp_path)
    record = _valid_session_with_two_turns()
    mutator(record["turns"][0])
    _write(paths.conversation_sessions / "session-1.json", _json_bytes(record))

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == "corrupt"


@pytest.mark.parametrize(
    ("entry_name", "payload", "expected"),
    [
        ("wrong.json", _json_bytes(_valid_session("session-1")), "corrupt"),
        ("session-1.tmp", _json_bytes(_valid_session()), "corrupt"),
        ("notes.txt", b"text", "corrupt"),
        ("session-1.json", _json_bytes(_valid_session(schema_version=2)), "unsupported_version"),
    ],
)
def test_conversation_entry_and_version_matrix(
    migration_api: Any,
    tmp_path: Path,
    entry_name: str,
    payload: bytes,
    expected: str,
) -> None:
    paths = _paths(tmp_path)
    _write(paths.conversation_sessions / entry_name, payload)

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == expected


def test_conversation_corrupt_precedes_unsupported_independent_of_name_order(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    _write(
        paths.conversation_sessions / "a-unsupported.json",
        _json_bytes(_valid_session("a-unsupported", schema_version=2)),
    )
    _write(paths.conversation_sessions / "z-corrupt.json", b"not-json")

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == "corrupt"


def test_regular_nested_conversation_directory_is_content_corruption(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    (paths.conversation_sessions / "nested").mkdir(parents=True)

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == "corrupt"


def test_file_instead_of_conversation_directory_is_unavailable(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    _write(paths.conversation_sessions, b"not-a-directory")

    result = _coordinator(migration_api, paths).attempt_store("conversation")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"


def test_conversation_directory_identity_is_names_and_exact_bytes(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-sessions"
    canonical_payload = _json_bytes(_valid_session())
    legacy_payload = json.dumps(_valid_session(), indent=2).encode("utf-8")
    _write(paths.conversation_sessions / "session-1.json", canonical_payload)
    _write(legacy / "session-1.json", legacy_payload)

    result = _coordinator(
        migration_api,
        paths,
        {"conversation": (legacy,)},
    ).attempt_store("conversation")

    assert result.internal_code == "canonical_legacy_conflict"
    assert not _receipt_path(paths, "conversation").exists()


def test_file_publication_uses_the_single_validated_immutable_snapshot(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    original = b'{"version":"0.1","items":[],"spacing":"original"}\n'
    changed = b'{"version":"0.1","items":[],"spacing":"changed"}\n'
    _write(legacy, original)
    delegate = migration_api.LocalMigrationPublicationAdapter(paths.root)

    class MutatingPublisher:
        def publish_file(self, target: Path, payload: bytes) -> bool:
            if target == paths.memory:
                legacy.write_bytes(changed)
            return delegate.publish_file(target, payload)

        def publish_directory(self, target: Path, entries: tuple[tuple[str, bytes], ...]) -> bool:
            return delegate.publish_directory(target, entries)

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
        publication_adapter=MutatingPublisher(),
    ).attempt_store("memory")

    assert result.internal_code == "migrated"
    assert paths.memory.read_bytes() == original
    assert legacy.read_bytes() == changed


def test_conversation_publication_uses_validated_staged_snapshot(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-sessions"
    source = legacy / "session-1.json"
    original = _json_bytes(_valid_session())
    changed = _json_bytes(_valid_session(schema_version=2))
    _write(source, original)
    delegate = migration_api.LocalMigrationPublicationAdapter(paths.root)

    class MutatingPublisher:
        def publish_file(self, target: Path, payload: bytes) -> bool:
            return delegate.publish_file(target, payload)

        def publish_directory(self, target: Path, entries: tuple[tuple[str, bytes], ...]) -> bool:
            source.write_bytes(changed)
            return delegate.publish_directory(target, entries)

    result = _coordinator(
        migration_api,
        paths,
        {"conversation": (legacy,)},
        publication_adapter=MutatingPublisher(),
    ).attempt_store("conversation")

    assert result.internal_code == "migrated"
    assert (paths.conversation_sessions / "session-1.json").read_bytes() == original
    assert source.read_bytes() == changed


@pytest.mark.parametrize(
    "failure",
    [PermissionError("denied"), OSError(errno.ENOSPC, "disk full"), NotImplementedError("no no-clobber")],
    ids=("permission", "disk-full", "unsupported-primitive"),
)
def test_publication_failure_is_safe_and_leaves_no_partial_canonical(
    migration_api: Any,
    tmp_path: Path,
    failure: BaseException,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(legacy, _valid_payload("memory"))

    class FailingPublisher:
        def publish_file(self, target: Path, payload: bytes) -> bool:
            raise failure

        def publish_directory(self, target: Path, entries: tuple[tuple[str, bytes], ...]) -> bool:
            raise failure

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
        publication_adapter=FailingPublisher(),
    ).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"
    assert result.projection.blocking is True
    assert not paths.memory.exists()
    assert legacy.exists()


def test_receipt_publication_failure_keeps_canonical_for_recovery(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    original = _valid_payload("memory")
    _write(legacy, original)
    delegate = migration_api.LocalMigrationPublicationAdapter(paths.root)

    class ReceiptFailingPublisher:
        def publish_file(self, target: Path, payload: bytes) -> bool:
            if target == _receipt_path(paths, "memory"):
                raise PermissionError("receipt denied")
            return delegate.publish_file(target, payload)

        def publish_directory(self, target: Path, entries: tuple[tuple[str, bytes], ...]) -> bool:
            return delegate.publish_directory(target, entries)

    first = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
        publication_adapter=ReceiptFailingPublisher(),
    ).attempt_store("memory")

    assert first.internal_code == "migration_unavailable"
    assert paths.memory.read_bytes() == original
    assert not _receipt_path(paths, "memory").exists()

    recovered = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
    ).attempt_store("memory")

    assert recovered.internal_code == "provenance_established"
    assert _receipt_path(paths, "memory").is_file()


def test_no_clobber_collision_re_evaluates_winner_state(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    payload = _valid_payload("memory")
    _write(legacy, payload)
    delegate = migration_api.LocalMigrationPublicationAdapter(paths.root)

    class WinningPublisher:
        def __init__(self) -> None:
            self.injected = False

        def publish_file(self, target: Path, snapshot: bytes) -> bool:
            if target == paths.memory and not self.injected:
                self.injected = True
                assert delegate.publish_file(target, snapshot) is True
                receipt = _json_bytes(
                    {"layout_version": "v1", "store_id": "memory", "established": True}
                )
                assert delegate.publish_file(_receipt_path(paths, "memory"), receipt) is True
                return False
            return delegate.publish_file(target, snapshot)

        def publish_directory(self, target: Path, entries: tuple[tuple[str, bytes], ...]) -> bool:
            return delegate.publish_directory(target, entries)

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
        publication_adapter=WinningPublisher(),
    ).attempt_store("memory")

    assert result.internal_code == "not_required"
    assert paths.memory.read_bytes() == payload


def test_spurious_no_clobber_loss_is_bounded_and_unavailable(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(legacy, _valid_payload("memory"))

    class NoWinnerPublisher:
        def publish_file(self, target: Path, snapshot: bytes) -> bool:
            return False

        def publish_directory(self, target: Path, entries: tuple[tuple[str, bytes], ...]) -> bool:
            return False

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
        publication_adapter=NoWinnerPublisher(),
    ).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert not paths.memory.exists()


def test_lock_timeout_is_bounded_unavailable_and_publishes_nothing(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(legacy, _valid_payload("memory"))

    class TimeoutLock:
        @contextmanager
        def acquire(self, canonical_root: Path, store_id: str, timeout_seconds: float):
            raise TimeoutError("controlled timeout")
            yield

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
        lock_adapter=TimeoutLock(),
        lock_timeout_seconds=0.01,
    ).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"
    assert not paths.memory.exists()
    assert legacy.exists()


def test_two_thread_attempts_publish_once_and_cleanup_workers(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(legacy, _valid_payload("memory"))
    start = threading.Event()
    ready = [threading.Event(), threading.Event()]
    results: list[str] = []
    failures: list[BaseException] = []

    def run(index: int) -> None:
        try:
            ready[index].set()
            if not start.wait(3.0):
                raise AssertionError("start gate timed out")
            result = _coordinator(
                migration_api,
                paths,
                {"memory": (legacy,)},
                lock_timeout_seconds=3.0,
            ).attempt_store("memory")
            results.append(result.internal_code)
        except BaseException as exc:
            failures.append(exc)

    threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    try:
        assert all(event.wait(2.0) for event in ready)
        start.set()
        for thread in threads:
            thread.join(5.0)
        assert all(not thread.is_alive() for thread in threads)
        assert failures == []
        assert sorted(results) == ["migrated", "not_required"]
    finally:
        start.set()
        for thread in threads:
            thread.join(5.0)


def test_two_process_attempts_publish_once_and_exit_cleanly(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(legacy, _valid_payload("memory"))
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    queue = context.Queue()
    processes = [
        context.Process(
            target=_process_attempt,
            args=(str(paths.root), str(paths.project_root), str(legacy), start, queue),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    try:
        start.set()
        for process in processes:
            process.join(8.0)
        assert all(not process.is_alive() for process in processes)
        assert all(process.exitcode == 0 for process in processes)
        results = sorted(queue.get(timeout=1.0) for _ in processes)
        assert results == ["migrated", "not_required"]
    finally:
        start.set()
        for process in processes:
            process.join(8.0)
        queue.close()
        queue.join_thread()


def test_external_override_is_authoritative_and_skips_default_state(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    override = tmp_path / "override" / "memory.json"
    unsafe_default_legacy = tmp_path / "legacy-wrong-type"
    unsafe_default_legacy.mkdir()
    coordinator = _coordinator(
        migration_api,
        paths,
        {"memory": (unsafe_default_legacy,)},
        external_overrides={"memory": override},
    )

    absent = coordinator.attempt_store("memory")
    assert absent.internal_code == "skipped_external_override"
    assert absent.projection.code == "skipped_external_override"
    assert absent.projection.blocking is False
    assert not paths.root.exists()

    _write(override, _valid_payload("memory"))
    valid = coordinator.attempt_store("memory")
    assert valid.internal_code == "skipped_external_override"
    assert valid.projection.blocking is False


@pytest.mark.parametrize(
    ("payload", "expected_projection"),
    [
        (b"not-json", "skipped_external_override"),
        (_json_bytes({"version": "0.2", "items": []}), "skipped_external_override"),
    ],
)
def test_corrupt_or_unsupported_external_override_blocks_owner_construction(
    migration_api: Any,
    tmp_path: Path,
    payload: bytes,
    expected_projection: str,
) -> None:
    paths = _paths(tmp_path)
    override = tmp_path / "override-memory.json"
    _write(override, payload)

    result = _coordinator(
        migration_api,
        paths,
        external_overrides={"memory": override},
    ).attempt_store("memory")

    assert result.internal_code == "skipped_external_override"
    assert result.projection.code == expected_projection
    assert result.projection.blocking is True
    assert not _receipt_path(paths, "memory").exists()


def test_unsafe_external_override_is_unavailable_before_owner_creation(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    override = tmp_path / "override-memory"
    override.mkdir()

    result = _coordinator(
        migration_api,
        paths,
        external_overrides={"memory": override},
    ).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"
    assert result.projection.blocking is True


def test_internal_canonical_injection_does_not_disable_migration(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(legacy, _valid_payload("memory"))

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
        external_overrides={},
    ).attempt_store("memory")

    assert result.internal_code == "migrated"


def test_symlink_legacy_fails_closed_without_following(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    target = tmp_path / "private-target.json"
    link = tmp_path / "legacy-link.json"
    _write(target, _valid_payload("memory"))
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink fixture unavailable: {type(exc).__name__}")

    result = _coordinator(
        migration_api,
        paths,
        {"memory": (link,)},
    ).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"
    assert not paths.memory.exists()


def test_absent_leaf_below_unsafe_ancestor_fails_closed_before_owner_construction(
    migration_api: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    inspected: list[bool] = []

    def unsafe_absent_entry(path: Path, *, inspect_ancestors: bool = False) -> str:
        del path
        inspected.append(inspect_ancestors)
        if inspect_ancestors:
            raise migration_api._UnsafeFilesystemState
        return "absent"

    monkeypatch.setattr(migration_api, "_entry_kind", unsafe_absent_entry)

    result = _coordinator(migration_api, paths).attempt_store("memory")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"
    assert result.projection.blocking is True
    assert inspected == [True]


def test_nested_conversation_symlink_is_unavailable_not_corrupt(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-sessions"
    target = tmp_path / "private-target.json"
    link = legacy / "session-1.json"
    _write(target, _json_bytes(_valid_session()))
    legacy.mkdir()
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink fixture unavailable: {type(exc).__name__}")

    result = _coordinator(
        migration_api,
        paths,
        {"conversation": (legacy,)},
    ).attempt_store("conversation")

    assert result.internal_code == "migration_unavailable"
    assert result.projection.code == "unavailable"


def test_attempt_projection_and_internal_objects_are_immutable_and_privacy_safe(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    private_marker = "private-candidate-marker"
    legacy = tmp_path / private_marker / "memory.json"
    _write(legacy, b"not-json")
    coordinator = _coordinator(
        migration_api,
        paths,
        {"memory": (legacy,)},
    )

    result = coordinator.attempt_store("memory")

    assert result.internal_code == "legacy_corrupt"
    assert result.projection == migration_api.MigrationAttemptProjection(
        layout_version="v1",
        store_id="memory",
        code="corrupt",
        blocking=True,
    )
    with pytest.raises(FrozenInstanceError):
        result.projection.code = "ready"
    for rendered in (repr(result), str(result), repr(coordinator), str(coordinator), repr(result.projection)):
        assert private_marker not in rendered
        assert str(tmp_path) not in rendered
        assert "not-json" not in rendered


def test_fixed_five_store_report_is_fail_fast_and_does_not_roll_back(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    conversation_legacy = tmp_path / "legacy-conversation"
    memory_legacy = tmp_path / "legacy-memory.json"
    profile_legacy = tmp_path / "legacy-profile.json"
    conversation_legacy.mkdir()
    _write(memory_legacy, b"not-json")
    _write(profile_legacy, _valid_payload("profile"))
    coordinator = _coordinator(
        migration_api,
        paths,
        {
            "conversation": (conversation_legacy,),
            "memory": (memory_legacy,),
            "profile": (profile_legacy,),
        },
    )

    report = coordinator.migrate_all()

    assert report.layout_version == "v1"
    assert tuple(attempt.store_id for attempt in report.attempts) == ("conversation", "memory")
    assert tuple(attempt.code for attempt in report.attempts) == ("migrated", "corrupt")
    assert report.completed is False
    assert report.blocking_store_id == "memory"
    assert paths.conversation_sessions.is_dir()
    assert _receipt_path(paths, "conversation").is_file()
    assert not paths.profile.exists()
    assert profile_legacy.exists()
    with pytest.raises(FrozenInstanceError):
        report.completed = True


def test_fixed_five_store_report_completes_in_stable_order(
    migration_api: Any,
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)

    report = _coordinator(migration_api, paths).migrate_all()

    assert isinstance(report, migration_api.CompositionMigrationReport)
    assert tuple(attempt.store_id for attempt in report.attempts) == STORE_IDS
    assert tuple(attempt.code for attempt in report.attempts) == ("not_required",) * 5
    assert report.completed is True
    assert report.blocking_store_id is None
    assert str(tmp_path) not in repr(report)
