import os
from pathlib import Path

import pytest

from workflows.document_review import (
    DocumentReviewWorkflowError,
    LocalTextDocumentReviewWorkflow,
    analyze_and_revise_text,
)


def write_bytes(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_valid_utf8_txt_loads_safely_and_output_path_is_deterministic(tmp_path):
    source = write_bytes(tmp_path / "sample.txt", "hello\n".encode("utf-8"))

    proposal = LocalTextDocumentReviewWorkflow().review(str(source))

    assert proposal.source_filename == "sample.txt"
    assert proposal.proposed_output_filename == "sample.jarvis-reviewed.txt"
    assert proposal.output_path == str(tmp_path / "sample.jarvis-reviewed.txt")
    assert proposal.source_hash.startswith("sha256:")


def test_utf8_bom_works_and_is_preserved_on_save(tmp_path):
    source = write_bytes(tmp_path / "bom.txt", "\ufeffline   ".encode("utf-8"))
    workflow = LocalTextDocumentReviewWorkflow()

    proposal = workflow.review(str(source))
    saved = workflow.save_confirmed(proposal)

    assert saved.verified is True
    assert (tmp_path / "bom.jarvis-reviewed.txt").read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize(
    "filename,error_code",
    [
        ("missing.txt", "missing_file"),
        ("sample.md", "unsupported_extension"),
    ],
)
def test_invalid_source_shapes_are_rejected(tmp_path, filename, error_code):
    if filename.endswith(".md"):
        write_bytes(tmp_path / filename, b"text")

    with pytest.raises(DocumentReviewWorkflowError) as exc:
        LocalTextDocumentReviewWorkflow().review(str(tmp_path / filename))

    assert exc.value.error_code == error_code


def test_directory_is_rejected(tmp_path):
    directory = tmp_path / "folder.txt"
    directory.mkdir()

    with pytest.raises(DocumentReviewWorkflowError) as exc:
        LocalTextDocumentReviewWorkflow().review(str(directory))

    assert exc.value.error_code == "directory_not_supported"


def test_symlink_is_rejected(tmp_path):
    target = write_bytes(tmp_path / "target.txt", b"text")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(DocumentReviewWorkflowError) as exc:
        LocalTextDocumentReviewWorkflow().review(str(link))

    assert exc.value.error_code == "symlink_not_supported"


def test_unc_path_is_rejected():
    with pytest.raises(DocumentReviewWorkflowError) as exc:
        LocalTextDocumentReviewWorkflow().review(r"\\server\share\sample.txt")

    assert exc.value.error_code == "unc_path_not_supported"


def test_binary_invalid_utf8_and_oversized_files_are_rejected(tmp_path):
    workflow = LocalTextDocumentReviewWorkflow(max_bytes=8)
    binary = write_bytes(tmp_path / "binary.txt", b"a\x00b")
    invalid = write_bytes(tmp_path / "invalid.txt", b"\xff\xfe")
    oversized = write_bytes(tmp_path / "big.txt", b"123456789")

    for path, code in (
        (binary, "binary_file"),
        (invalid, "invalid_utf8"),
        (oversized, "file_too_large"),
    ):
        with pytest.raises(DocumentReviewWorkflowError) as exc:
            workflow.review(str(path))
        assert exc.value.error_code == code


def test_detects_required_formatting_issues_and_fixes_are_deterministic():
    text = "Name  \r\n\r\n\r\n\r\nDate: 2026-07-16\nURL: https://example.com\rNo final"

    issues, revised, newline = analyze_and_revise_text(text)
    second = analyze_and_revise_text(text)

    assert [issue.issue_code for issue in issues] == [
        "mixed_line_endings",
        "trailing_whitespace",
        "repeated_empty_lines",
        "missing_final_newline",
    ]
    assert revised == second[1]
    assert newline == "\r\n"
    assert revised.endswith("\r\n")
    assert "\r\n\r\n\r\n\r\n" not in revised
    assert "Name  " not in revised


def test_safe_content_shapes_remain_unchanged_except_formatting():
    text = (
        "Ivan Petrov  \n"
        "Date: 2026-07-16\n"
        "Amount: 12345\n"
        "Email: user@example.com\n"
        "URL: https://example.com/a?b=1\n"
        r"Path: C:\JARVIS-OS\file.txt"
    )

    _, revised, _ = analyze_and_revise_text(text)

    assert "Ivan Petrov" in revised
    assert "2026-07-16" in revised
    assert "12345" in revised
    assert "user@example.com" in revised
    assert "https://example.com/a?b=1" in revised
    assert r"C:\JARVIS-OS\file.txt" in revised


def test_original_content_and_hash_are_unchanged_until_and_after_save(tmp_path):
    source = write_bytes(tmp_path / "source.txt", b"line   \n")
    before = source.read_bytes()
    workflow = LocalTextDocumentReviewWorkflow()

    proposal = workflow.review(str(source))
    after_review = source.read_bytes()
    saved = workflow.save_confirmed(proposal)

    assert after_review == before
    assert source.read_bytes() == before
    assert saved.source_hash_unchanged is True


def test_existing_output_is_not_overwritten_and_same_path_is_rejected(tmp_path):
    source = write_bytes(tmp_path / "source.txt", b"line\n")
    output = write_bytes(tmp_path / "source.jarvis-reviewed.txt", b"existing")

    with pytest.raises(DocumentReviewWorkflowError) as exc:
        LocalTextDocumentReviewWorkflow().review(str(source))

    assert exc.value.error_code == "output_already_exists"
    assert output.read_bytes() == b"existing"


def test_source_and_output_path_equality_is_rejected(tmp_path):
    source = write_bytes(tmp_path / "source.txt", b"line\n")

    class SamePathWorkflow(LocalTextDocumentReviewWorkflow):
        def propose_output_path(self, source_path):
            return source_path

    with pytest.raises(DocumentReviewWorkflowError) as exc:
        SamePathWorkflow().review(str(source))

    assert exc.value.error_code == "same_source_and_output"


def test_source_change_between_review_and_save_is_rejected(tmp_path):
    source = write_bytes(tmp_path / "source.txt", b"line   \n")
    workflow = LocalTextDocumentReviewWorkflow()
    proposal = workflow.review(str(source))
    source.write_bytes(b"changed\n")

    with pytest.raises(DocumentReviewWorkflowError) as exc:
        workflow.save_confirmed(proposal)

    assert exc.value.error_code == "source_changed"
    assert not (tmp_path / "source.jarvis-reviewed.txt").exists()
