import re
import shutil
import warnings
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from core.time_utils import utc_now_iso_z
from ideas import IdeaManager
from memory import LocalMemoryManager


TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@contextmanager
def workspace_storage_dir():
    root = Path(__file__).resolve().parents[2]
    storage_dir = root / "workspace" / "warning-audit-tests" / str(uuid4())
    storage_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield storage_dir
    finally:
        shutil.rmtree(storage_dir, ignore_errors=True)


def test_utc_timestamp_helper_returns_z_suffix():
    timestamp = utc_now_iso_z()

    assert timestamp.endswith("Z")


def test_utc_timestamp_helper_does_not_include_offset():
    timestamp = utc_now_iso_z()

    assert "+00:00" not in timestamp


def test_utc_timestamp_helper_has_no_microseconds():
    timestamp = utc_now_iso_z()

    assert TIMESTAMP_RE.match(timestamp)


def test_idea_manager_timestamp_creation_does_not_emit_deprecation_warning():
    with workspace_storage_dir() as storage_dir:
        manager = IdeaManager(storage_dir / "ideas.json")

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            idea = manager.add_idea("warning audit idea")

    assert TIMESTAMP_RE.match(idea["created_at"])
    assert idea["created_at"] == idea["updated_at"]


def test_memory_manager_timestamp_creation_does_not_emit_deprecation_warning():
    with workspace_storage_dir() as storage_dir:
        manager = LocalMemoryManager(storage_dir / "memory.json")

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            memory = manager.add_memory("warning audit memory")

    assert TIMESTAMP_RE.match(memory["created_at"])
    assert memory["created_at"] == memory["updated_at"]


def test_no_project_owned_datetime_utcnow_usage_remains_in_production_code():
    root = Path(__file__).resolve().parents[2]
    excluded_dirs = {
        ".ai",
        ".git",
        ".pytest_cache",
        "__pycache__",
        "docs",
        "tests",
    }
    production_roots = [
        "ai",
        "app",
        "automation",
        "brain",
        "config",
        "core",
        "database",
        "dialogue",
        "ideas",
        "integrations",
        "interface",
        "language",
        "memory",
        "models",
        "plugins",
        "scheduler",
        "security",
        "services",
        "tools",
        "users",
        "vision",
        "voice",
    ]
    offenders = []

    for production_root in production_roots:
        search_root = root / production_root
        if not search_root.exists():
            continue
        for path in search_root.rglob("*.py"):
            if any(part in excluded_dirs for part in path.relative_to(root).parts):
                continue
            if "datetime.utcnow" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(root)))

    assert offenders == []


def test_warning_audit_doc_exists_and_mentions_datetime_utcnow():
    root = Path(__file__).resolve().parents[2]
    doc_path = root / "docs" / "WARNINGS_AUDIT.md"

    assert doc_path.exists()
    assert "datetime.utcnow" in doc_path.read_text(encoding="utf-8")
