from dataclasses import dataclass
from pathlib import Path

from app import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from core.policy_boundary import PolicyDecision, PolicyDecisionType


CHECK_DOCUMENT = "проверить документ"
YES = "да"
CANCEL = "отмена"


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


def make_source(tmp_path: Path, name: str = "task084.txt") -> Path:
    source = tmp_path / name
    source.write_text("Name  \n\n\n\nNo final", encoding="utf-8")
    return source


def command_for(path: Path) -> str:
    return f"{CHECK_DOCUMENT} {path}"


def test_workflow_progression_same_operation_verified(tmp_path):
    source = make_source(tmp_path)
    before = source.read_bytes()
    service = JarvisAppService(command_processor=TrackingProcessor())

    review = service.execute_contract(command_for(source), AppCommandSource.TEST)

    assert review.operation_status == "awaiting_confirmation"
    assert review.workflow_status == "awaiting_confirmation"
    assert review.current_step_id == "write_output"
    assert review.awaiting_confirmation is True
    assert 0 < review.progress_percent < 100
    assert not (tmp_path / "task084.jarvis-reviewed.txt").exists()

    saved = service.execute_contract(YES, AppCommandSource.TEST)

    output = tmp_path / "task084.jarvis-reviewed.txt"
    assert saved.operation_id == review.operation_id
    assert saved.workflow_status == "succeeded"
    assert saved.progress_percent == 100
    assert saved.verified is True
    assert "verify_output" in saved.completed_steps
    assert "verify_source_unchanged" in saved.completed_steps
    assert output.exists()
    assert source.read_bytes() == before


def test_cancellation_no_write_and_no_remaining_steps(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())

    review = service.execute_contract(command_for(source), AppCommandSource.TEST)
    cancelled = service.execute_contract(CANCEL, AppCommandSource.TEST)

    assert cancelled.operation_id == review.operation_id
    assert cancelled.workflow_status == "cancelled"
    assert "write_output" not in cancelled.completed_steps
    assert not (tmp_path / "task084.jarvis-reviewed.txt").exists()


def test_duplicate_resume_and_idempotency_do_not_duplicate_write(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())

    review = service.execute_contract(
        command_for(source),
        AppCommandSource.TEST,
        idempotency_key="task-084-review",
    )
    duplicate_review = service.execute_contract(
        command_for(source),
        AppCommandSource.TEST,
        idempotency_key="task-084-review",
    )
    saved = service.execute_contract(YES, AppCommandSource.TEST)
    second_yes = service.execute_contract(YES, AppCommandSource.TEST)

    output = tmp_path / "task084.jarvis-reviewed.txt"
    assert duplicate_review.operation_id == review.operation_id
    assert duplicate_review.duplicate_suppressed is True
    assert saved.operation_id == review.operation_id
    assert output.exists()
    first_bytes = output.read_bytes()
    assert second_yes.operation_id != saved.operation_id
    assert output.read_bytes() == first_bytes


def test_policy_denial_and_failure_are_safe(tmp_path):
    source = make_source(tmp_path)
    service = JarvisAppService(command_processor=TrackingProcessor())
    service.policy_boundary = DenyingPolicy("file_read")

    denied = service.execute_contract(command_for(source), AppCommandSource.TEST)

    assert denied.operation_status == "denied"
    assert denied.workflow_status == "denied"
    assert not (tmp_path / "task084.jarvis-reviewed.txt").exists()

    failing = JarvisAppService(command_processor=TrackingProcessor())
    original = failing.document_review_workflow.verify_output_step

    def fail_verify(state):
        raise RuntimeError("raw exception sk-test-1234567890secret")

    failing.document_review_workflow.verify_output_step = fail_verify
    review = failing.execute_contract(command_for(make_source(tmp_path, "fail.txt")), AppCommandSource.TEST)
    failed = failing.execute_contract(YES, AppCommandSource.TEST)

    assert review.operation_status == "awaiting_confirmation"
    assert failed.operation_id == review.operation_id
    assert failed.workflow_status == "failed"
    assert "sk-test" not in failed.safe_text_ru()
    failing.document_review_workflow.verify_output_step = original


def test_preview_desktop_voice_and_task_080_081_082_083_compatibility(tmp_path):
    source = make_source(tmp_path)
    processor = TrackingProcessor()
    service = JarvisAppService(
        command_processor=processor,
        one_shot_voice_recognition=FakeRecognition(command_for(source)),
    )

    preview = service.preview_contract(command_for(source))
    assert preview.executed is False
    assert service.recent_execution_operations() == ()

    shell_text = DesktopShellViewModel(service).execute_command(command_for(source))
    assert "workflow id: local_text_document_review" in shell_text
    assert "progress percent:" in shell_text
    assert processor.calls == []
    service.execute_contract(CANCEL, AppCommandSource.TEST)

    voice = service.process_one_shot_voice_request(AppCommandSource.TEST)
    assert voice.text_result.workflow_status == "awaiting_confirmation"
    assert processor.action_router.calls == []

    clarification = service.execute_contract("покажи статус", AppCommandSource.TEST)
    assert clarification.requires_clarification is True
    service.execute_contract(CANCEL, AppCommandSource.TEST)

    task083 = service.execute_contract(command_for(make_source(tmp_path, "compat.txt")), AppCommandSource.TEST)
    assert task083.operation_status == "awaiting_confirmation"
    assert task083.workflow_id == "local_text_document_review"
