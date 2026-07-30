from dataclasses import dataclass
from pathlib import Path

from app import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from core.policy_boundary import PolicyDecision, PolicyDecisionType


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
    def __init__(self, deny_capability):
        self.deny_capability = deny_capability
        self.requests = []

    def evaluate(self, request):
        self.requests.append(request)
        if self.deny_capability in request.required_capabilities:
            return PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reason_codes=("test_policy_denial",),
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


@dataclass(frozen=True)
class FakeRecognition:
    recognized_text: str
    completed: bool = True
    blocked: bool = False
    allowed: bool = True
    reasons: tuple[str, ...] = ()

    def run_once(self, explicit_one_shot_requested=False):
        assert explicit_one_shot_requested is True
        return self

    def close(self):
        return None


def make_source(tmp_path: Path, name: str = "task083-sample.txt") -> Path:
    source = tmp_path / name
    source.write_text("Name  \n\n\n\nEmail: user@example.com\nNo final", encoding="utf-8")
    return source


def command_for(path: Path) -> str:
    return f"{CHECK_DOCUMENT} {path}"


def test_vertical_review_and_save_same_operation_id_verified_source_unchanged(tmp_path):
    source = make_source(tmp_path)
    before = source.read_bytes()
    service = JarvisAppService(command_processor=TrackingProcessor())

    review = service.execute_contract(command_for(source), AppCommandSource.TEST)

    assert review.command_id == "document_review.local_text"
    assert review.operation_status == "awaiting_confirmation"
    assert review.requires_confirmation is True
    assert review.workflow_id == "local_text_document_review"
    assert review.issue_count >= 3
    assert any(issue["issue_code"] == "trailing_whitespace" for issue in review.issue_summaries)
    assert not (tmp_path / "task083-sample.jarvis-reviewed.txt").exists()
    assert source.read_bytes() == before

    saved = service.execute_contract(YES, AppCommandSource.TEST)

    output = tmp_path / "task083-sample.jarvis-reviewed.txt"
    assert saved.operation_id == review.operation_id
    assert saved.operation_status == "succeeded"
    assert saved.saved is True
    assert saved.verified is True
    assert output.exists()
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert source.read_bytes() == before


def test_vertical_cancellation_continues_same_operation_and_writes_nothing(tmp_path):
    source = make_source(tmp_path)
    before = source.read_bytes()
    service = JarvisAppService(command_processor=TrackingProcessor())

    review = service.execute_contract(command_for(source), AppCommandSource.TEST)
    cancelled = service.execute_contract(CANCEL, AppCommandSource.TEST)

    assert cancelled.operation_id == review.operation_id
    assert cancelled.operation_status == "cancelled"
    assert not (tmp_path / "task083-sample.jarvis-reviewed.txt").exists()
    assert source.read_bytes() == before


def test_preview_reads_nothing_creates_no_operation_and_writes_nothing(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())

    preview = service.preview_contract(command_for(source))

    assert preview.command_id == "document_review.local_text"
    assert preview.executed is False
    assert service.recent_execution_operations() == ()
    assert not (tmp_path / "task083-sample.jarvis-reviewed.txt").exists()


def test_duplicate_idempotency_retry_returns_existing_review_without_second_write(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())

    first = service.execute_contract(
        command_for(source),
        AppCommandSource.TEST,
        idempotency_key="task-083-same",
    )
    duplicate = service.execute_contract(
        command_for(source),
        AppCommandSource.TEST,
        idempotency_key="task-083-same",
    )

    assert duplicate.operation_id == first.operation_id
    assert duplicate.duplicate_suppressed is True
    assert duplicate.operation_status == "awaiting_confirmation"
    assert not (tmp_path / "task083-sample.jarvis-reviewed.txt").exists()


def test_idempotency_conflict_writes_nothing(tmp_path):
    first_source = make_source(tmp_path, "one.txt")
    second_source = make_source(tmp_path, "two.txt")
    service = JarvisAppService(command_processor=TrackingProcessor())

    first = service.execute_contract(
        command_for(first_source),
        AppCommandSource.TEST,
        idempotency_key="task-083-conflict",
    )
    conflict = service.execute_contract(
        command_for(second_source),
        AppCommandSource.TEST,
        idempotency_key="task-083-conflict",
    )

    assert first.operation_status == "awaiting_confirmation"
    assert conflict.operation_status == "denied"
    assert conflict.error == "idempotency_conflict"
    assert not (tmp_path / "two.jarvis-reviewed.txt").exists()


def test_duplicate_confirmation_does_not_write_twice(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())

    service.execute_contract(command_for(source), AppCommandSource.TEST)
    saved = service.execute_contract(YES, AppCommandSource.TEST)
    output = tmp_path / "task083-sample.jarvis-reviewed.txt"
    first_bytes = output.read_bytes()
    second = service.execute_contract(YES, AppCommandSource.TEST)

    assert saved.operation_status == "succeeded"
    assert output.read_bytes() == first_bytes
    assert second.operation_id != saved.operation_id


def test_unsafe_inputs_fail_safely_without_provider_or_action_router(tmp_path):
    processor = TrackingProcessor()
    service = JarvisAppService(command_processor=processor)
    unsupported = tmp_path / "bad.md"
    unsupported.write_text("bad", encoding="utf-8")
    oversized = tmp_path / "big.txt"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))

    for text in (
        f"{CHECK_DOCUMENT} \\\\server\\share\\a.txt",
        f"{CHECK_DOCUMENT} {unsupported}",
        f"{CHECK_DOCUMENT} {oversized}",
    ):
        result = service.execute_contract(text, AppCommandSource.TEST)
        assert result.operation_status == "failed"
        assert result.saved is False

    assert processor.calls == []
    assert processor.action_router.calls == []


def test_policy_denial_writes_nothing(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())
    service.policy_boundary = DenyingPolicy("file_read")

    result = service.execute_contract(command_for(source), AppCommandSource.TEST)

    assert result.operation_status == "denied"
    assert not (tmp_path / "task083-sample.jarvis-reviewed.txt").exists()


def test_write_policy_denial_after_review_writes_nothing(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())
    service.policy_boundary = DenyingPolicy("file_write")

    result = service.execute_contract(command_for(source), AppCommandSource.TEST)

    assert result.operation_status == "denied"
    assert not (tmp_path / "task083-sample.jarvis-reviewed.txt").exists()


def test_journal_contains_no_full_document_text_or_secrets(tmp_path):
    source = tmp_path / "secret.txt"
    source.write_text("token: sk-test-1234567890secret   \n\n\n\n", encoding="utf-8")
    service = JarvisAppService(command_processor=TrackingProcessor())

    service.execute_contract(command_for(source), AppCommandSource.TEST)
    text = str(service.recent_execution_operations())

    assert "sk-test-1234567890secret" not in text
    assert "token:" not in text
    assert "file_contents" not in text
    assert "revised_content" not in text


def test_desktop_shell_displays_workflow_metadata_without_bypass(tmp_path):
    source = make_source(tmp_path)
    processor = TrackingProcessor()
    shell = DesktopShellViewModel(JarvisAppService(command_processor=processor))

    text = shell.execute_command(command_for(source))

    assert "workflow id: local_text_document_review" in text
    assert "operation status:" not in text
    assert "operation status: awaiting_confirmation" in shell.state.diagnostics_text
    assert "issue count:" in shell.state.diagnostics_text
    assert "proposed output path:" in shell.state.diagnostics_text
    assert processor.calls == []


def test_voice_path_uses_appservice_policy_and_no_provider_output_command(tmp_path):
    source = make_source(tmp_path)
    processor = TrackingProcessor()
    service = JarvisAppService(
        command_processor=processor,
        one_shot_voice_recognition=FakeRecognition(command_for(source)),
    )

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.text_result.operation_status == "awaiting_confirmation"
    assert result.text_result.workflow_id == "local_text_document_review"
    assert result.requires_confirmation is True
    assert processor.calls == []
    assert processor.action_router.calls == []


def test_task_080_081_082_compatibility_smoke(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())

    clarification = service.execute_contract(
        "\u043f\u043e\u043a\u0430\u0436\u0438 \u0441\u0442\u0430\u0442\u0443\u0441",
        AppCommandSource.TEST,
    )
    assert clarification.requires_clarification is True
    service.execute_contract(CANCEL, AppCommandSource.TEST)

    review = service.execute_contract(command_for(source), AppCommandSource.TEST)
    assert review.policy_decision["decision"] == "require_confirmation"
    assert review.operation_status == "awaiting_confirmation"
