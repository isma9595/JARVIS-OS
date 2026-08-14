from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib
import json
from pathlib import Path

import pytest

from platform_adapters.user_data_paths import UserDataPaths


def _api():
    try:
        return importlib.import_module("app.persistence_health")
    except ModuleNotFoundError:
        pytest.fail("TASK-125 persistence health boundary is not implemented")


def _migration_api():
    return importlib.import_module("platform_adapters.user_data_migration")


def _paths(tmp_path: Path) -> UserDataPaths:
    return UserDataPaths.resolve(
        environment={"JARVIS_USER_DATA_DIR": str(tmp_path / "canonical-v1")},
        home=tmp_path / "unused-home",
        project_root=tmp_path / "project",
    )


def _registry(paths: UserDataPaths, **candidates: tuple[Path, ...]):
    del paths
    return _migration_api().DeterministicLegacyRegistry.from_mapping(candidates)


def _service(paths: UserDataPaths, **kwargs):
    registry = kwargs.pop("registry", _registry(paths))
    return _api().PersistenceHealthService(paths, registry, **kwargs)


def _write(path: Path, value: object | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
    path.write_bytes(payload)


def _store(snapshot, store_id: str):
    return next(store for store in snapshot.stores if store.store_id == store_id)


def _receipt(paths: UserDataPaths, store_id: str) -> Path:
    return paths.root / ".migration" / "v1" / f"{store_id}.json"


def test_health_is_read_only_and_reports_uninitialized_defaults(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    before = tuple(tmp_path.rglob("*"))

    snapshot = _service(paths, secure_keys_backend_available=False).snapshot()

    assert tuple(store.store_id for store in snapshot.stores) == (
        "conversation",
        "memory",
        "profile",
        "ideas",
        "vosk_settings",
        "secure_keys",
    )
    assert tuple(store.code for store in snapshot.stores[:5]) == ("not_initialized",) * 5
    assert _store(snapshot, "secure_keys").code == "unavailable"
    assert tuple(tmp_path.rglob("*")) == before


def test_valid_legacy_changes_from_migration_required_to_ready(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(legacy, {"version": "0.1", "items": []})
    registry = _registry(paths, memory=(legacy,))
    service = _service(paths, registry=registry)

    assert _store(service.snapshot(), "memory").code == "migration_required"
    result = _migration_api().UserDataMigrationCoordinator(paths, registry).attempt_store("memory")
    assert result.internal_code == "migrated"
    assert _store(service.snapshot(), "memory").code == "ready"


def test_valid_receipt_selects_canonical_only_and_ignores_retained_legacy(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _write(paths.memory, {"version": "0.1", "items": []})
    _write(
        _receipt(paths, "memory"),
        {"layout_version": "v1", "store_id": "memory", "established": True},
    )
    unsafe_legacy = tmp_path / "unsafe-legacy"
    unsafe_legacy.mkdir()

    snapshot = _service(
        paths,
        registry=_registry(paths, memory=(unsafe_legacy,)),
    ).snapshot()

    assert _store(snapshot, "memory").code == "ready"


@pytest.mark.parametrize(
    ("receipt_payload", "expected"),
    [
        (b"not-json", "migration_state_invalid"),
        (json.dumps({"layout_version": "v1", "store_id": "memory", "established": True}).encode(), "migration_state_invalid"),
    ],
    ids=("invalid", "missing-canonical"),
)
def test_invalid_receipt_state_fails_closed(
    tmp_path: Path,
    receipt_payload: bytes,
    expected: str,
) -> None:
    paths = _paths(tmp_path)
    _write(_receipt(paths, "memory"), receipt_payload)
    if receipt_payload == b"not-json":
        _write(paths.memory, {"version": "0.1", "items": []})

    assert _store(_service(paths).snapshot(), "memory").code == expected


def test_receipt_inspection_failure_remains_unavailable_with_observation_callback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths(tmp_path)
    api = _api()
    original_entry_kind = api._entry_kind
    receipt = _receipt(paths, "memory")
    observations: list[tuple[str, bool]] = []

    def controlled_entry_kind(path: Path, *, inspect_ancestors: bool = False) -> str:
        if path == receipt:
            raise api._UnsafeFilesystemState
        return original_entry_kind(path, inspect_ancestors=inspect_ancestors)

    monkeypatch.setattr(api, "_entry_kind", controlled_entry_kind)

    snapshot = _service(
        paths,
        after_receipt_observation=lambda store_id, present: observations.append(
            (store_id, present)
        ),
    ).snapshot()

    assert _store(snapshot, "memory").code == "unavailable"
    assert ("memory", False) in observations


def test_canonical_and_differing_legacy_conflict_is_read_only(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    _write(paths.memory, b'{"version":"0.1","items":[]}')
    _write(legacy, b'{ "version": "0.1", "items": [] }')

    store = _store(
        _service(paths, registry=_registry(paths, memory=(legacy,))).snapshot(),
        "memory",
    )

    assert store.code == "canonical_legacy_conflict"
    assert not _receipt(paths, "memory").exists()


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (None, "missing"),
        (b"not-json", "corrupt"),
        (json.dumps({"version": "9", "items": []}).encode(), "unsupported_version"),
        (json.dumps({"version": "0.1", "items": []}).encode(), "ready"),
    ],
)
def test_external_override_is_the_only_health_target(
    tmp_path: Path,
    payload: bytes | None,
    code: str,
) -> None:
    paths = _paths(tmp_path)
    override = tmp_path / "override" / "memory.json"
    if payload is not None:
        _write(override, payload)
    _write(paths.memory, b"canonical-must-not-be-read")

    snapshot = _service(paths, external_overrides={"memory": override}).snapshot()

    assert _store(snapshot, "memory").code == code


@pytest.mark.parametrize(
    ("store_id", "payload", "code"),
    [
        ("memory", {"version": "0.1", "items": []}, "ready"),
        ("memory", {"version": "2", "items": []}, "unsupported_version"),
        ("profile", {}, "ready"),
        ("ideas", {"ideas": None}, "corrupt"),
        ("vosk_settings", {"language": " "}, "corrupt"),
    ],
)
def test_health_uses_the_strict_store_validation_matrix(
    tmp_path: Path,
    store_id: str,
    payload: object,
    code: str,
) -> None:
    paths = _paths(tmp_path)
    canonical = getattr(paths, {"memory": "memory", "profile": "profile", "ideas": "ideas", "vosk_settings": "vosk_settings"}[store_id])
    _write(canonical, payload)

    assert _store(_service(paths).snapshot(), store_id).code == code


def test_receipt_branch_selection_is_linearized_once(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    legacy = tmp_path / "legacy-memory.json"
    payload = b'{"version":"0.1","items":[]}'
    _write(legacy, payload)
    registry = _registry(paths, memory=(legacy,))
    calls: list[str] = []

    def after_receipt_observation(store_id: str, receipt_present: bool) -> None:
        if store_id != "memory" or receipt_present or calls:
            return
        calls.append(store_id)
        _write(paths.memory, payload)
        _write(
            _receipt(paths, "memory"),
            {"layout_version": "v1", "store_id": "memory", "established": True},
        )

    first = _service(
        paths,
        registry=registry,
        after_receipt_observation=after_receipt_observation,
    ).snapshot()
    second = _service(paths, registry=registry).snapshot()

    assert _store(first, "memory").code == "migration_required"
    assert _store(second, "memory").code == "ready"


def test_secure_keys_metadata_is_validated_without_decrypting(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    secure_path = tmp_path / "security" / "secure_keys.json"
    _write(
        secure_path,
        {
            "version": 1,
            "backend": "windows-dpapi",
            "entries": {
                "openai::api_key": {
                    "provider": "openai",
                    "secret_name": "api_key",
                    "encrypted_value": "dpapi:YQ==",
                    "masked_hint": "***abcd",
                    "source": "stored",
                    "updated_at": "2026-08-05T00:00:00+00:00",
                }
            },
        },
    )

    snapshot = _service(
        paths,
        secure_keys_path=secure_path,
        secure_keys_backend_available=True,
    ).snapshot()
    secure = _store(snapshot, "secure_keys")

    assert secure.code == "ready"
    assert secure.item_count == 1
    assert "openai" not in repr(secure)
    assert "abcd" not in repr(secure)


@pytest.mark.parametrize(
    "failure",
    [ValueError("integer limit"), RecursionError("nested input")],
    ids=("value-error", "recursion-error"),
)
def test_secure_key_json_parser_failures_are_classified_as_corrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    paths = _paths(tmp_path)
    secure_path = tmp_path / "security" / "secure_keys.json"
    _write(secure_path, b"{}")
    api = _api()

    def fail_json_loads(*args, **kwargs):
        del args, kwargs
        raise failure

    monkeypatch.setattr(api.json, "loads", fail_json_loads)

    snapshot = _service(
        paths,
        secure_keys_path=secure_path,
        secure_keys_backend_available=True,
    ).snapshot()

    assert _store(snapshot, "secure_keys").code == "corrupt"


def test_health_contracts_are_immutable_and_privacy_safe(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    private = "SECRET-ACCOUNT-PATH"
    legacy = tmp_path / private / "memory.json"
    _write(legacy, b"not-json sk-private-token")

    snapshot = _service(
        paths,
        registry=_registry(paths, memory=(legacy,)),
    ).snapshot()

    with pytest.raises(FrozenInstanceError):
        snapshot.layout_version = "v2"
    rendered = (repr(snapshot), str(snapshot), repr(_store(snapshot, "memory")), str(snapshot.to_dict()))
    assert all(private not in value for value in rendered)
    assert all(str(tmp_path) not in value for value in rendered)
    assert all("sk-private-token" not in value for value in rendered)
    assert snapshot.to_dict()["layout_version"] == "v1"
