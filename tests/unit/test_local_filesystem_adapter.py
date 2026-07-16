import ast
import builtins
import os
from pathlib import Path

import pytest

from platform_adapters.contracts import LocalFileSystemError
from platform_adapters.local_filesystem import WindowsLocalFileSystemAdapter


def test_safe_absolute_local_path_metadata_is_typed_serializable_and_content_free(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("secret document body", encoding="utf-8")
    adapter = WindowsLocalFileSystemAdapter()

    info = adapter.inspect_path(str(source))
    metadata = info.to_dict()

    assert info.exists is True
    assert info.is_file is True
    assert info.is_absolute is True
    assert info.is_local is True
    assert metadata["filename"] == "sample.txt"
    assert "secret document body" not in str(metadata)


def test_relative_and_unc_paths_are_rejected_for_bounded_read(tmp_path):
    adapter = WindowsLocalFileSystemAdapter()

    with pytest.raises(LocalFileSystemError) as relative:
        adapter.read_bounded_bytes("relative.txt", 10)
    with pytest.raises(LocalFileSystemError) as unc:
        adapter.read_bounded_bytes(r"\\server\share\sample.txt", 10)

    assert relative.value.code == "path_not_absolute"
    assert unc.value.code == "network_path_denied"


def test_missing_directory_and_symlink_are_reported_safely(tmp_path):
    adapter = WindowsLocalFileSystemAdapter()
    directory = tmp_path / "folder.txt"
    directory.mkdir()

    with pytest.raises(LocalFileSystemError) as missing:
        adapter.read_bounded_bytes(str(tmp_path / "missing.txt"), 10)
    with pytest.raises(LocalFileSystemError) as not_file:
        adapter.read_bounded_bytes(str(directory), 10)

    assert missing.value.code == "file_not_found"
    assert not_file.value.code == "not_a_file"

    target = tmp_path / "target.txt"
    target.write_text("text", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(LocalFileSystemError) as symlink:
        adapter.read_bounded_bytes(str(link), 10)
    assert symlink.value.code == "symlink_denied"


def test_bounded_read_works_and_oversized_read_is_refused(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_bytes(b"12345")
    adapter = WindowsLocalFileSystemAdapter()

    assert adapter.read_bounded_bytes(str(source), 5) == b"12345"
    with pytest.raises(LocalFileSystemError) as exc:
        adapter.read_bounded_bytes(str(source), 4)

    assert exc.value.code == "file_too_large"


def test_raw_os_exceptions_are_redacted(monkeypatch, tmp_path):
    source = tmp_path / "sample.txt"
    source.write_bytes(b"123")
    adapter = WindowsLocalFileSystemAdapter()
    real_open = builtins.open

    def failing_open(*args, **kwargs):
        if args and str(args[0]) == str(source.resolve()):
            raise OSError("raw secret CREDENTIAL=abc")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", failing_open)

    with pytest.raises(LocalFileSystemError) as exc:
        adapter.read_bounded_bytes(str(source), 10)

    assert exc.value.code == "read_failed"
    assert "CREDENTIAL" not in exc.value.safe_message
    assert "raw secret" not in str(exc.value)


def test_atomic_write_creates_new_sibling_verifies_and_preserves_source(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"original")
    target = tmp_path / "source.jarvis-reviewed.txt"
    adapter = WindowsLocalFileSystemAdapter()

    result = adapter.atomic_write_new_file(
        target_path=str(target),
        data=b"revised",
        source_path=str(source),
    )

    assert result.verified is True
    assert result.bytes_written == 7
    assert result.output_hash.startswith("sha256:")
    assert target.read_bytes() == b"revised"
    assert source.read_bytes() == b"original"


def test_atomic_write_never_overwrites_existing_output_or_source(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"original")
    target = tmp_path / "target.txt"
    target.write_bytes(b"existing")
    adapter = WindowsLocalFileSystemAdapter()

    with pytest.raises(LocalFileSystemError) as exists:
        adapter.atomic_write_new_file(target_path=str(target), data=b"new", source_path=str(source))
    with pytest.raises(LocalFileSystemError) as same:
        adapter.atomic_write_new_file(target_path=str(source), data=b"new", source_path=str(source))

    assert exists.value.code == "target_exists"
    assert same.value.code == "source_target_conflict"
    assert target.read_bytes() == b"existing"
    assert source.read_bytes() == b"original"


def test_temporary_file_is_removed_after_controlled_write_failure(monkeypatch, tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"original")
    target = tmp_path / "target.txt"
    adapter = WindowsLocalFileSystemAdapter()

    monkeypatch.setattr(os, "link", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("blocked")))
    monkeypatch.setattr(os, "open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("raw failure")))

    with pytest.raises(LocalFileSystemError) as exc:
        adapter.atomic_write_new_file(target_path=str(target), data=b"new", source_path=str(source))

    assert exc.value.code == "write_failed"
    assert not target.exists()
    assert list(tmp_path.glob(".target.*.tmp")) == []
    assert source.read_bytes() == b"original"


def test_document_workflow_has_no_direct_filesystem_write_primitives():
    tree = ast.parse(Path("workflows/document_review.py").read_text(encoding="utf-8"))
    prohibited_path_attrs = {"read_bytes", "read_text", "write_bytes", "write_text"}
    prohibited_os_attrs = {"replace", "rename", "remove", "unlink"}
    prohibited_calls = {"open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in prohibited_path_attrs:
                assert False, f"direct pathlib filesystem call: {node.func.attr}"
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr in prohibited_os_attrs
            ):
                assert False, f"direct os filesystem write call: {node.func.attr}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in prohibited_calls
