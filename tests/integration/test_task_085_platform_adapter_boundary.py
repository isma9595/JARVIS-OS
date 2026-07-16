from dataclasses import replace
from pathlib import Path

from app import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from core.policy_boundary import PolicyDecision, PolicyDecisionType
from platform_adapters.contracts import AtomicWriteResult, LocalFileSystemError, LocalFileSystemErrorCode
from platform_adapters.local_filesystem import WindowsLocalFileSystemAdapter
from workflows.document_review import LocalTextDocumentReviewWorkflow


CHECK_DOCUMENT = "\u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442"
YES = "\u0434\u0430"
CANCEL = "\u043e\u0442\u043c\u0435\u043d\u0430"


class TrackingProcessor:
    def __init__(self):
        self.calls = []
        self.action_router = CountingActionRouter()
        self.user_profile = None

    def process(self, text):
        self.calls.append(text)
        return {"response": f"processed: {text}"}


class CountingActionRouter:
    def __init__(self):
        self.calls = []

    def route(self, command_text, intent=None):
        self.calls.append(command_text)
        return {"response": "router called"}


class DenyingPolicy:
    def __init__(self, capability):
        self.capability = capability

    def evaluate(self, request):
        if self.capability in request.required_capabilities:
            return PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reason_codes=("test_deny",),
                required_capabilities=request.required_capabilities,
                requires_confirmation=False,
                user_message="denied by test policy",
                safe_to_execute=False,
            )
        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reason_codes=("test_allow",),
            required_capabilities=request.required_capabilities,
            requires_confirmation=False,
            user_message="allowed",
            safe_to_execute=True,
        )


class CountingFilesystem:
    def __init__(self):
        self.inner = WindowsLocalFileSystemAdapter()
        self.inspect_count = 0
        self.read_count = 0
        self.write_count = 0

    def inspect_path(self, requested_path):
        self.inspect_count += 1
        return self.inner.inspect_path(requested_path)

    def same_path(self, first_path, second_path):
        return self.inner.same_path(first_path, second_path)

    def sibling_path(self, source_path, sibling_filename):
        return self.inner.sibling_path(source_path, sibling_filename)

    def read_bounded_bytes(self, path, max_bytes):
        self.read_count += 1
        return self.inner.read_bounded_bytes(path, max_bytes)

    def atomic_write_new_file(self, *, target_path, data, source_path=None):
        self.write_count += 1
        return self.inner.atomic_write_new_file(
            target_path=target_path,
            data=data,
            source_path=source_path,
        )


class FailingWriteFilesystem(CountingFilesystem):
    def atomic_write_new_file(self, *, target_path, data, source_path=None):
        self.write_count += 1
        raise LocalFileSystemError(
            LocalFileSystemErrorCode.VERIFICATION_FAILED,
            "safe verification failure",
        )


class MemoryFilesystem:
    def __init__(self, source_path: str, raw: bytes):
        self.source_path = source_path
        self.output_path = source_path.replace(".txt", ".jarvis-reviewed.txt")
        self.files = {self.source_path: raw}
        self.write_count = 0
        self.read_count = 0
        self.inner = WindowsLocalFileSystemAdapter()

    def inspect_path(self, requested_path):
        path = str(requested_path)
        if path == self.source_path:
            return replace(
                self.inner.inspect_path(str(Path.cwd() / "memory-source.txt")),
                requested_path=path,
                resolved_path=self.source_path,
                exists=True,
                is_file=True,
                size_bytes=len(self.files[path]),
                filename="memory-source.txt",
                suffix=".txt",
                stem="memory-source",
                parent_path="memory:",
            )
        exists = path in self.files
        return replace(
            self.inner.inspect_path(str(Path.cwd() / "memory-output.txt")),
            requested_path=path,
            resolved_path=path,
            exists=exists,
            is_file=exists,
            size_bytes=len(self.files[path]) if exists else None,
            filename=Path(path).name,
            suffix=".txt",
            stem=Path(path).stem,
            parent_path="memory:",
        )

    def same_path(self, first_path, second_path):
        return first_path == second_path

    def sibling_path(self, source_path, sibling_filename):
        return self.output_path

    def read_bounded_bytes(self, path, max_bytes):
        self.read_count += 1
        data = self.files[path]
        if len(data) > max_bytes:
            raise LocalFileSystemError(LocalFileSystemErrorCode.FILE_TOO_LARGE, "too large")
        return data

    def atomic_write_new_file(self, *, target_path, data, source_path=None):
        self.write_count += 1
        if target_path in self.files:
            raise LocalFileSystemError(LocalFileSystemErrorCode.TARGET_EXISTS, "exists")
        self.files[target_path] = data
        return AtomicWriteResult(
            target_path=target_path,
            bytes_written=len(data),
            verified=True,
            output_hash="sha256:memory",
        )


def make_source(tmp_path: Path, name: str = "task085.txt") -> Path:
    source = tmp_path / name
    source.write_text("Name  \n\n\n\nNo final", encoding="utf-8")
    return source


def command_for(path) -> str:
    return f"{CHECK_DOCUMENT} {path}"


def test_production_appservice_injects_concrete_adapter():
    service = JarvisAppService(command_processor=TrackingProcessor())

    assert isinstance(service._local_filesystem, WindowsLocalFileSystemAdapter)
    assert service.document_review_workflow.filesystem is service._local_filesystem


def test_normal_workflow_reads_after_policy_and_writes_once_after_confirmation(tmp_path):
    source = make_source(tmp_path)
    before = source.read_bytes()
    filesystem = CountingFilesystem()
    service = JarvisAppService(command_processor=TrackingProcessor(), local_filesystem=filesystem)

    review = service.execute_contract(command_for(source), AppCommandSource.TEST)

    assert review.operation_status == "awaiting_confirmation"
    assert review.workflow_status == "awaiting_confirmation"
    assert filesystem.read_count >= 1
    assert filesystem.write_count == 0
    assert not (tmp_path / "task085.jarvis-reviewed.txt").exists()

    saved = service.execute_contract(YES, AppCommandSource.TEST)

    output = tmp_path / "task085.jarvis-reviewed.txt"
    assert saved.operation_id == review.operation_id
    assert saved.operation_status == "succeeded"
    assert saved.verified is True
    assert filesystem.write_count == 1
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert source.read_bytes() == before

    second = service.execute_contract(YES, AppCommandSource.TEST)
    assert second.operation_id != saved.operation_id
    assert filesystem.write_count == 1


def test_preview_policy_denial_and_cancellation_perform_no_adapter_write(tmp_path):
    source = make_source(tmp_path)
    filesystem = CountingFilesystem()
    service = JarvisAppService(command_processor=TrackingProcessor(), local_filesystem=filesystem)

    preview = service.preview_contract(command_for(source))
    assert preview.executed is False
    assert filesystem.read_count == 0
    assert filesystem.write_count == 0

    service.policy_boundary = DenyingPolicy("file_read")
    denied = service.execute_contract(command_for(source), AppCommandSource.TEST)
    assert denied.operation_status == "denied"
    assert filesystem.write_count == 0

    service = JarvisAppService(command_processor=TrackingProcessor(), local_filesystem=filesystem)
    review = service.execute_contract(command_for(source), AppCommandSource.TEST)
    cancelled = service.execute_contract(CANCEL, AppCommandSource.TEST)
    assert cancelled.operation_id == review.operation_id
    assert cancelled.operation_status == "cancelled"
    assert filesystem.write_count == 0
    assert not (tmp_path / "task085.jarvis-reviewed.txt").exists()


def test_output_conflict_and_idempotency_retry_do_not_overwrite_or_write_twice(tmp_path):
    source = make_source(tmp_path)
    output = tmp_path / "task085.jarvis-reviewed.txt"
    output.write_bytes(b"existing")
    filesystem = CountingFilesystem()
    service = JarvisAppService(command_processor=TrackingProcessor(), local_filesystem=filesystem)

    conflict = service.execute_contract(command_for(source), AppCommandSource.TEST)
    assert conflict.operation_status == "failed"
    assert conflict.error == "output_already_exists"
    assert output.read_bytes() == b"existing"
    assert filesystem.write_count == 0

    source2 = make_source(tmp_path, "idempotent.txt")
    review = service.execute_contract(
        command_for(source2),
        AppCommandSource.TEST,
        idempotency_key="task-085-idempotent",
    )
    duplicate = service.execute_contract(
        command_for(source2),
        AppCommandSource.TEST,
        idempotency_key="task-085-idempotent",
    )
    saved = service.execute_contract(YES, AppCommandSource.TEST)

    assert duplicate.operation_id == review.operation_id
    assert duplicate.duplicate_suppressed is True
    assert saved.operation_id == review.operation_id
    assert filesystem.write_count == 1


def test_controlled_platform_failure_fails_safely_and_original_unchanged(tmp_path):
    source = make_source(tmp_path)
    before = source.read_bytes()
    filesystem = FailingWriteFilesystem()
    service = JarvisAppService(command_processor=TrackingProcessor(), local_filesystem=filesystem)

    review = service.execute_contract(command_for(source), AppCommandSource.TEST)
    failed = service.execute_contract(YES, AppCommandSource.TEST)

    assert review.operation_status == "awaiting_confirmation"
    assert failed.operation_id == review.operation_id
    assert failed.workflow_status == "failed"
    assert failed.error == "output_verify_failed"
    assert "safe verification failure" not in failed.safe_text_ru()
    assert not (tmp_path / "task085.jarvis-reviewed.txt").exists()
    assert source.read_bytes() == before
    assert filesystem.write_count == 1


def test_adapter_substitution_keeps_business_behavior_deterministic():
    filesystem = MemoryFilesystem("memory:/memory-source.txt", b"Line   \nNo final")
    workflow = LocalTextDocumentReviewWorkflow(filesystem=filesystem)

    proposal = workflow.review("memory:/memory-source.txt")
    saved = workflow.save_confirmed(proposal)

    assert proposal.issue_count == 2
    assert proposal.proposed_output_filename == "memory-source.jarvis-reviewed.txt"
    assert saved.verified is True
    assert filesystem.write_count == 1
    assert filesystem.files["memory:/memory-source.txt"] == b"Line   \nNo final"


def test_desktop_shell_and_voice_have_no_direct_adapter_access(tmp_path):
    source = make_source(tmp_path)
    processor = TrackingProcessor()
    filesystem = CountingFilesystem()
    service = JarvisAppService(command_processor=processor, local_filesystem=filesystem)
    shell = DesktopShellViewModel(service)

    shell_text = shell.execute_command(command_for(source))

    assert "workflow id: local_text_document_review" in shell_text
    assert not hasattr(shell, "local_filesystem")
    assert processor.calls == []
    assert processor.action_router.calls == []
