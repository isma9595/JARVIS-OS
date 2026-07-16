"""Local UTF-8 text document review workflow for TASK-083.

The workflow is intentionally narrow: one local .txt file is reviewed with
deterministic formatting rules, a sibling copy is proposed, and the original is
never modified.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import os
from pathlib import Path
import re
import tempfile


MAX_DOCUMENT_BYTES = 1024 * 1024
WORKFLOW_ID = "local_text_document_review"


class DocumentReviewErrorCode(Enum):
    MISSING_FILE = "missing_file"
    DIRECTORY_NOT_SUPPORTED = "directory_not_supported"
    SYMLINK_NOT_SUPPORTED = "symlink_not_supported"
    UNC_PATH_NOT_SUPPORTED = "unc_path_not_supported"
    UNSUPPORTED_EXTENSION = "unsupported_extension"
    BINARY_FILE = "binary_file"
    INVALID_UTF8 = "invalid_utf8"
    FILE_TOO_LARGE = "file_too_large"
    SAME_SOURCE_AND_OUTPUT = "same_source_and_output"
    OUTPUT_ALREADY_EXISTS = "output_already_exists"
    SOURCE_CHANGED = "source_changed"
    OUTPUT_VERIFY_FAILED = "output_verify_failed"


class DocumentReviewIssueCode(Enum):
    TRAILING_WHITESPACE = "trailing_whitespace"
    REPEATED_EMPTY_LINES = "repeated_empty_lines"
    MISSING_FINAL_NEWLINE = "missing_final_newline"
    MIXED_LINE_ENDINGS = "mixed_line_endings"


@dataclass(frozen=True)
class DocumentReviewIssue:
    issue_code: str
    line_number: int
    description_ru: str
    fix_available: bool
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "issue_code": self.issue_code,
            "line_number": self.line_number,
            "description_ru": self.description_ru,
            "fix_available": self.fix_available,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DocumentReviewProposal:
    workflow_id: str
    source_path: str
    source_filename: str
    source_hash: str
    source_size_bytes: int
    output_path: str
    proposed_output_filename: str
    issue_count: int
    issues: tuple[DocumentReviewIssue, ...]
    revised_content: str
    output_encoding: str
    newline: str
    changed: bool

    def safe_metadata(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "source_filename": self.source_filename,
            "source_hash": self.source_hash,
            "source_size_bytes": self.source_size_bytes,
            "proposed_output_filename": self.proposed_output_filename,
            "issue_count": self.issue_count,
            "issue_codes": tuple(issue.issue_code for issue in self.issues),
            "output_encoding": self.output_encoding,
            "newline": _newline_name(self.newline),
            "changed": self.changed,
        }


@dataclass(frozen=True)
class DocumentReviewSaveResult:
    workflow_id: str
    source_path: str
    output_path: str
    saved: bool
    verified: bool
    source_hash_unchanged: bool
    output_hash: str
    bytes_written: int


@dataclass
class DocumentReviewRunState:
    source_path: str
    source: Path | None = None
    output: Path | None = None
    raw: bytes | None = None
    text: str | None = None
    encoding: str | None = None
    size: int = 0
    issues: tuple[DocumentReviewIssue, ...] = ()
    revised_content: str | None = None
    newline: str | None = None
    proposal: DocumentReviewProposal | None = None
    save_result: DocumentReviewSaveResult | None = None

    def safe_metadata(self) -> dict[str, object]:
        metadata: dict[str, object] = {"workflow_id": WORKFLOW_ID}
        if self.source is not None:
            metadata["source_filename"] = self.source.name
            metadata["source_size_bytes"] = self.size
        if self.output is not None:
            metadata["proposed_output_filename"] = self.output.name
        if self.proposal is not None:
            metadata.update(self.proposal.safe_metadata())
        if self.save_result is not None:
            metadata.update(
                {
                    "saved": self.save_result.saved,
                    "verified": self.save_result.verified,
                    "source_hash_unchanged": self.save_result.source_hash_unchanged,
                    "bytes_written": self.save_result.bytes_written,
                    "output_hash": self.save_result.output_hash,
                }
            )
        return metadata


class DocumentReviewWorkflowError(ValueError):
    def __init__(self, error_code: DocumentReviewErrorCode, message_ru: str):
        super().__init__(message_ru)
        self.error_code = error_code.value
        self.message_ru = message_ru


class LocalTextDocumentReviewWorkflow:
    """Validate, review, propose, and save one local UTF-8 .txt revision."""

    def __init__(self, max_bytes: int = MAX_DOCUMENT_BYTES):
        self.max_bytes = int(max_bytes)

    def review(self, source_path: str) -> DocumentReviewProposal:
        source = self._validate_source(source_path)
        size = source.stat().st_size
        if size > self.max_bytes:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.FILE_TOO_LARGE,
                f"Файл больше допустимого лимита {self.max_bytes} байт.",
            )
        raw = source.read_bytes()
        if b"\x00" in raw:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.BINARY_FILE,
                "Файл похож на бинарный: найден нулевой байт.",
            )
        try:
            text, encoding = self._decode_utf8(raw)
        except UnicodeDecodeError as exc:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.INVALID_UTF8,
                "Файл не является корректным UTF-8 текстом.",
            ) from exc

        output = self.propose_output_path(source)
        self._validate_distinct_paths(source, output)
        if output.exists():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.OUTPUT_ALREADY_EXISTS,
                "Предлагаемый выходной файл уже существует. Перезапись запрещена.",
            )

        issues, revised, newline = analyze_and_revise_text(text)
        return DocumentReviewProposal(
            workflow_id=WORKFLOW_ID,
            source_path=str(source),
            source_filename=source.name,
            source_hash=_hash_bytes(raw),
            source_size_bytes=size,
            output_path=str(output),
            proposed_output_filename=output.name,
            issue_count=len(issues),
            issues=issues,
            revised_content=revised,
            output_encoding=encoding,
            newline=newline,
            changed=revised != text,
        )

    def validate_source_step(self, state: DocumentReviewRunState) -> None:
        source = self._validate_source(state.source_path)
        size = source.stat().st_size
        if size > self.max_bytes:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.FILE_TOO_LARGE,
                f"Р¤Р°Р№Р» Р±РѕР»СЊС€Рµ РґРѕРїСѓСЃС‚РёРјРѕРіРѕ Р»РёРјРёС‚Р° {self.max_bytes} Р±Р°Р№С‚.",
            )
        output = self.propose_output_path(source)
        self._validate_distinct_paths(source, output)
        if output.exists():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.OUTPUT_ALREADY_EXISTS,
                "РџСЂРµРґР»Р°РіР°РµРјС‹Р№ РІС‹С…РѕРґРЅРѕР№ С„Р°Р№Р» СѓР¶Рµ СЃСѓС‰РµСЃС‚РІСѓРµС‚. РџРµСЂРµР·Р°РїРёСЃСЊ Р·Р°РїСЂРµС‰РµРЅР°.",
            )
        state.source = source
        state.output = output
        state.size = size

    def read_source_step(self, state: DocumentReviewRunState) -> None:
        if state.source is None:
            self.validate_source_step(state)
        assert state.source is not None
        raw = state.source.read_bytes()
        if b"\x00" in raw:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.BINARY_FILE,
                "Р¤Р°Р№Р» РїРѕС…РѕР¶ РЅР° Р±РёРЅР°СЂРЅС‹Р№: РЅР°Р№РґРµРЅ РЅСѓР»РµРІРѕР№ Р±Р°Р№С‚.",
            )
        try:
            text, encoding = self._decode_utf8(raw)
        except UnicodeDecodeError as exc:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.INVALID_UTF8,
                "Р¤Р°Р№Р» РЅРµ СЏРІР»СЏРµС‚СЃСЏ РєРѕСЂСЂРµРєС‚РЅС‹Рј UTF-8 С‚РµРєСЃС‚РѕРј.",
            ) from exc
        state.raw = raw
        state.text = text
        state.encoding = encoding

    def analyze_document_step(self, state: DocumentReviewRunState) -> None:
        if state.text is None:
            self.read_source_step(state)
        assert state.text is not None
        issues, revised, newline = analyze_and_revise_text(state.text)
        state.issues = issues
        state.revised_content = revised
        state.newline = newline

    def prepare_revision_step(self, state: DocumentReviewRunState) -> None:
        if state.revised_content is None:
            self.analyze_document_step(state)
        assert state.source is not None
        assert state.output is not None
        assert state.raw is not None
        assert state.text is not None
        assert state.encoding is not None
        assert state.revised_content is not None
        assert state.newline is not None
        state.proposal = DocumentReviewProposal(
            workflow_id=WORKFLOW_ID,
            source_path=str(state.source),
            source_filename=state.source.name,
            source_hash=_hash_bytes(state.raw),
            source_size_bytes=state.size,
            output_path=str(state.output),
            proposed_output_filename=state.output.name,
            issue_count=len(state.issues),
            issues=state.issues,
            revised_content=state.revised_content,
            output_encoding=state.encoding,
            newline=state.newline,
            changed=state.revised_content != state.text,
        )

    def save_confirmed(self, proposal: DocumentReviewProposal) -> DocumentReviewSaveResult:
        source = Path(proposal.source_path)
        output = Path(proposal.output_path)
        self._validate_source(str(source))
        self._validate_distinct_paths(source, output)
        if output.parent.resolve() != source.parent.resolve():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.SAME_SOURCE_AND_OUTPUT,
                "Выходной файл должен находиться рядом с исходным файлом.",
            )
        if output.exists():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.OUTPUT_ALREADY_EXISTS,
                "Выходной файл уже существует. Перезапись запрещена.",
            )
        current_raw = source.read_bytes()
        if _hash_bytes(current_raw) != proposal.source_hash:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.SOURCE_CHANGED,
                "Исходный файл изменился после проверки. Сохранение отменено.",
            )

        encoded = self._encode_output(proposal.revised_content, proposal.output_encoding)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(output.parent),
                prefix=f".{output.stem}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.rename(temp_name, output)
            temp_name = None
        finally:
            if temp_name and os.path.exists(temp_name):
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass

        output_raw = output.read_bytes()
        if output_raw != encoded:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.OUTPUT_VERIFY_FAILED,
                "Сохраненная копия не прошла проверку содержимого.",
            )
        source_hash_unchanged = _hash_bytes(source.read_bytes()) == proposal.source_hash
        if not source_hash_unchanged:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.SOURCE_CHANGED,
                "Исходный файл изменился при сохранении. Проверьте вручную.",
            )
        return DocumentReviewSaveResult(
            workflow_id=proposal.workflow_id,
            source_path=str(source),
            output_path=str(output),
            saved=True,
            verified=True,
            source_hash_unchanged=True,
            output_hash=_hash_bytes(output_raw),
            bytes_written=len(output_raw),
        )

    def write_output_step(self, state: DocumentReviewRunState) -> None:
        if state.proposal is None:
            self.prepare_revision_step(state)
        assert state.proposal is not None
        state.save_result = self.save_confirmed(state.proposal)

    def verify_output_step(self, state: DocumentReviewRunState) -> None:
        if state.save_result is None or not state.save_result.verified:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.OUTPUT_VERIFY_FAILED,
                "РЎРѕС…СЂР°РЅРµРЅРЅР°СЏ РєРѕРїРёСЏ РЅРµ РїСЂРѕС€Р»Р° РїСЂРѕРІРµСЂРєСѓ.",
            )

    def verify_source_unchanged_step(self, state: DocumentReviewRunState) -> None:
        if state.save_result is None or not state.save_result.source_hash_unchanged:
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.SOURCE_CHANGED,
                "РСЃС…РѕРґРЅС‹Р№ С„Р°Р№Р» РёР·РјРµРЅРёР»СЃСЏ РїСЂРё workflow.",
            )

    def propose_output_path(self, source: Path) -> Path:
        return source.with_name(f"{source.stem}.jarvis-reviewed.txt")

    def _validate_source(self, source_path: str) -> Path:
        raw = str(source_path or "").strip().strip('"')
        if raw.startswith("\\\\"):
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.UNC_PATH_NOT_SUPPORTED,
                "UNC или сетевые пути не поддерживаются.",
            )
        source = Path(raw)
        if not source.is_absolute():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.MISSING_FILE,
                "Нужен абсолютный локальный путь к .txt файлу.",
            )
        if source.is_symlink():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.SYMLINK_NOT_SUPPORTED,
                "Символические ссылки не поддерживаются.",
            )
        if not source.exists():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.MISSING_FILE,
                "Файл не найден.",
            )
        if source.is_dir():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.DIRECTORY_NOT_SUPPORTED,
                "Каталоги не поддерживаются. Нужен обычный .txt файл.",
            )
        if not source.is_file():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.MISSING_FILE,
                "Нужен обычный локальный файл.",
            )
        if source.suffix.lower() != ".txt":
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.UNSUPPORTED_EXTENSION,
                "Поддерживаются только локальные .txt файлы.",
            )
        return source

    @staticmethod
    def _validate_distinct_paths(source: Path, output: Path) -> None:
        if source.resolve() == output.resolve():
            raise DocumentReviewWorkflowError(
                DocumentReviewErrorCode.SAME_SOURCE_AND_OUTPUT,
                "Исходный и выходной пути не должны совпадать.",
            )

    @staticmethod
    def _decode_utf8(raw: bytes) -> tuple[str, str]:
        if raw.startswith(b"\xef\xbb\xbf"):
            return raw.decode("utf-8-sig"), "utf-8-sig"
        return raw.decode("utf-8"), "utf-8"

    @staticmethod
    def _encode_output(text: str, encoding: str) -> bytes:
        if encoding == "utf-8-sig":
            return text.encode("utf-8-sig")
        return text.encode("utf-8")


def analyze_and_revise_text(text: str) -> tuple[tuple[DocumentReviewIssue, ...], str, str]:
    newline = _preferred_newline(text)
    issues: list[DocumentReviewIssue] = []
    if _has_mixed_line_endings(text):
        issues.append(
            DocumentReviewIssue(
                issue_code=DocumentReviewIssueCode.MIXED_LINE_ENDINGS.value,
                line_number=1,
                description_ru="Смешанные окончания строк будут нормализованы единообразно.",
                fix_available=True,
                metadata={"target_newline": _newline_name(newline)},
            )
        )

    normalized = re.sub(r"\r\n|\r|\n", "\n", text)
    lines = normalized.split("\n")
    had_final_newline = normalized.endswith("\n")
    if had_final_newline:
        lines = lines[:-1]

    revised_lines: list[str] = []
    empty_run = 0
    for index, line in enumerate(lines, start=1):
        if line.endswith((" ", "\t")):
            issues.append(
                DocumentReviewIssue(
                    issue_code=DocumentReviewIssueCode.TRAILING_WHITESPACE.value,
                    line_number=index,
                    description_ru="В конце строки есть пробелы или табуляция; их можно безопасно удалить.",
                    fix_available=True,
                    metadata={"kind": "line_suffix"},
                )
            )
        stripped_line = line.rstrip(" \t")
        if stripped_line == "":
            empty_run += 1
            if empty_run == 3:
                issues.append(
                    DocumentReviewIssue(
                        issue_code=DocumentReviewIssueCode.REPEATED_EMPTY_LINES.value,
                        line_number=index,
                        description_ru="Три или более пустые строки подряд будут сокращены до двух.",
                        fix_available=True,
                        metadata={"max_empty_lines": 2},
                    )
                )
            if empty_run <= 2:
                revised_lines.append("")
            continue
        empty_run = 0
        revised_lines.append(stripped_line)

    revised_normalized = "\n".join(revised_lines)
    if text and not had_final_newline:
        issues.append(
            DocumentReviewIssue(
                issue_code=DocumentReviewIssueCode.MISSING_FINAL_NEWLINE.value,
                line_number=max(1, len(lines)),
                description_ru="В конце файла нет завершающего перевода строки.",
                fix_available=True,
                metadata={"final_newline": True},
            )
        )
    if text:
        revised_normalized += "\n"
    revised = revised_normalized.replace("\n", newline)
    return tuple(issues), revised, newline


def _preferred_newline(text: str) -> str:
    crlf = text.count("\r\n")
    without_crlf = text.replace("\r\n", "")
    lf = without_crlf.count("\n")
    cr = without_crlf.count("\r")
    counts = {("\r\n", 0): crlf, ("\n", 1): lf, ("\r", 2): cr}
    best = max(counts.items(), key=lambda item: (item[1], -item[0][1]))
    return best[0][0] if best[1] else os.linesep


def _has_mixed_line_endings(text: str) -> bool:
    crlf = text.count("\r\n")
    without_crlf = text.replace("\r\n", "")
    kinds = sum(1 for count in (crlf, without_crlf.count("\n"), without_crlf.count("\r")) if count)
    return kinds > 1


def _hash_bytes(raw: bytes) -> str:
    return "sha256:" + sha256(raw).hexdigest()


def _newline_name(newline: str) -> str:
    return {"\r\n": "crlf", "\n": "lf", "\r": "cr"}.get(newline, "platform")
