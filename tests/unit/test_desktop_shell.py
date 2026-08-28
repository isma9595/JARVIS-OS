from dataclasses import dataclass, field, replace
from threading import Event, Thread, current_thread

import pytest

from app.app_contracts import (
    AppDesktopChatStatus,
    AppExecutionHistoryEntry,
    AppExecutionHistoryResult,
    ApplicationActivityDto,
    ApplicationActivityKind,
    ApplicationActivitySnapshotDto,
    ApplicationActivityState,
)
from app.app_service import (
    AppCommandSource,
    JarvisAppService,
    create_default_desktop_app_service,
)
from app import desktop_shell
from app.desktop_shell import DesktopShellViewModel, JarvisDesktopShell
from app.desktop_interaction_worker import DesktopInteractionWorker
from core.command_processor import CommandProcessor
from memory import LocalMemoryManager
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult
from voice.speech_synthesis_backend import SpeechSynthesisResult
from voice.voice_output_manager import VoiceOutputManager
from workflows.contracts import (
    WorkflowHistoryResult,
    WorkflowCancellationRejectionReason,
    WorkflowCancellationResult,
    WorkflowCancellationStatus,
    WorkflowResumeRejectionReason,
    WorkflowResumeResult,
    WorkflowResumeStatus,
    WorkflowRunHistory,
    WorkflowRunHistoryState,
    WorkflowStepHistory,
    WorkflowStepHistoryState,
)


LOCAL_TTS_STATUS_COMMAND = (
    "\u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)
LOCAL_TTS_ENABLE_COMMAND = (
    "\u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 "
    "\u0433\u043e\u043b\u043e\u0441"
)
LOCAL_TTS_TEST_COMMAND = (
    "\u0442\u0435\u0441\u0442 "
    "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e "
    "\u0433\u043e\u043b\u043e\u0441\u0430"
)
RAW_MICROPHONE_ERROR = "Error querying device -1: PaErrorCode -9999; MME error 1"
RAW_HISTORY_ERROR = "Traceback RuntimeError backend failed at C:/Users/User/raw.log"


def history_entry(
    entry_id,
    *,
    timestamp="2026-07-22T10:00:00+00:00",
    status="succeeded",
    command_id="ai.status",
    action_id=None,
    operation_type=None,
    preview=False,
    request_summary="status ai",
    user_message="processed safely",
    safe_error_summary=None,
):
    success = (
        True
        if status == "succeeded"
        else False
        if status in {"failed", "denied", "cancelled"}
        else None
    )
    return AppExecutionHistoryEntry(
        entry_id=entry_id,
        timestamp=timestamp,
        updated_at=timestamp,
        source="desktop_ui",
        command_id=command_id,
        action_id=action_id,
        operation_type=operation_type or command_id or action_id or "operation",
        status=status,
        succeeded=success,
        preview=preview,
        awaiting_confirmation=status == "awaiting_confirmation",
        cancellable=status == "awaiting_confirmation",
        duplicate_suppressed=False,
        request_summary=request_summary,
        user_message=user_message,
        safe_error_summary=safe_error_summary,
        metadata=(("risk_level", "read_only"),),
    )


def activity(
    activity_id,
    *,
    state=ApplicationActivityState.RUNNING,
    kind=ApplicationActivityKind.COMMAND_EXECUTION,
    title="Command execution",
    error=None,
):
    return ApplicationActivityDto(
        activity_id=activity_id,
        kind=kind,
        state=state,
        title=title,
        detail="safe detail",
        started_at="2026-07-22T10:00:00+00:00",
        updated_at="2026-07-22T10:01:00+00:00",
        finished_at=None
        if state
        in {
            ApplicationActivityState.STARTING,
            ApplicationActivityState.RUNNING,
            ApplicationActivityState.WAITING_FOR_USER,
            ApplicationActivityState.CANCELLATION_REQUESTED,
        }
        else "2026-07-22T10:02:00+00:00",
        is_active=state
        in {
            ApplicationActivityState.STARTING,
            ApplicationActivityState.RUNNING,
            ApplicationActivityState.WAITING_FOR_USER,
            ApplicationActivityState.CANCELLATION_REQUESTED,
        },
        requires_user_attention=state == ApplicationActivityState.WAITING_FOR_USER,
        cancellation_requested=state == ApplicationActivityState.CANCELLATION_REQUESTED,
        can_cancel=state == ApplicationActivityState.RUNNING,
        cancel_target_id=activity_id if state == ApplicationActivityState.RUNNING else None,
        source_run_id=None,
        error_message=error,
        revision=1,
    )


def activity_snapshot(current=None, recent=(), *, available=True, error=None):
    return ApplicationActivitySnapshotDto(
        current=current,
        recent=tuple(recent),
        is_busy=current is not None and getattr(current, "is_active", False),
        requires_user_attention=(
            current is not None and getattr(current, "requires_user_attention", False)
        ),
        updated_at="2026-07-22T10:03:00+00:00",
        revision=1,
        status_available=available,
        error=error,
    )


def workflow_step(
    step_id,
    *,
    index=0,
    state=WorkflowStepHistoryState.COMPLETED,
    display_name=None,
    result="step completed safely",
    error=None,
):
    return WorkflowStepHistory(
        step_id=step_id,
        step_index=index,
        display_name=display_name or f"Step {step_id}",
        operation_type=f"operation.{step_id}",
        state=state,
        started_at=f"2026-07-22T10:0{index}:00+00:00",
        completed_at=f"2026-07-22T10:0{index}:30+00:00"
        if state == WorkflowStepHistoryState.COMPLETED
        else None,
        safe_result_summary=result if state == WorkflowStepHistoryState.COMPLETED else None,
        safe_error_summary=error,
    )


def workflow_run(
    run_id,
    *,
    state=WorkflowRunHistoryState.COMPLETED,
    steps=None,
    workflow_name="Document review",
    objective="Review document safely",
    completed_count=None,
    resume_eligible=False,
    resume_reason=WorkflowResumeRejectionReason.NONE,
    resume_step_id=None,
    resume_step_index=None,
    resumed_from_run_id=None,
    cancellation_eligible=False,
    cancellation_reason=WorkflowCancellationRejectionReason.NONE,
):
    safe_steps = tuple(steps or ())
    return WorkflowRunHistory(
        run_id=run_id,
        operation_id=run_id,
        workflow_id="document_review.local_text",
        workflow_name=workflow_name,
        objective_summary=objective,
        state=state,
        created_at="2026-07-22T10:00:00+00:00",
        started_at="2026-07-22T10:00:00+00:00",
        completed_at="2026-07-22T10:05:00+00:00"
        if state == WorkflowRunHistoryState.COMPLETED
        else None,
        total_step_count=len(safe_steps),
        completed_step_count=(
            len(safe_steps)
            if completed_count is None and state == WorkflowRunHistoryState.COMPLETED
            else int(completed_count or 0)
        ),
        active_step_id=safe_steps[-1].step_id if safe_steps else None,
        active_step_name=safe_steps[-1].display_name if safe_steps else None,
        safe_result_summary="workflow completed safely"
        if state == WorkflowRunHistoryState.COMPLETED
        else None,
        safe_failure_summary="workflow failed safely"
        if state == WorkflowRunHistoryState.FAILED
        else None,
        cancelled=state == WorkflowRunHistoryState.CANCELLED,
        waiting_for_confirmation=state == WorkflowRunHistoryState.WAITING_FOR_CONFIRMATION,
        cancellation_eligible=cancellation_eligible,
        cancellation_rejection_reason=cancellation_reason,
        resume_eligible=resume_eligible,
        resume_rejection_reason=resume_reason,
        resume_step_id=resume_step_id,
        resume_step_index=resume_step_index,
        resumed_from_run_id=resumed_from_run_id,
        steps=safe_steps,
    )


class FakeLocalTtsBackend:
    def __init__(self, *, available=True):
        self.available = available
        self.diagnostics_calls = 0
        self.synthesis_calls = []

    def get_name(self):
        return "windows_local_tts"

    def availability_diagnostics(self):
        self.diagnostics_calls += 1
        return {
            "available": self.available,
            "reason": "fake available" if self.available else "fake unavailable",
            "backend_name": self.get_name(),
            "network_used": False,
            "audio_file_saved": False,
        }

    def synthesize(self, text, mode="WINDOWS_LOCAL"):
        self.synthesis_calls.append((text, mode))
        return SpeechSynthesisResult(
            success=True,
            spoken_text=text,
            backend_name=self.get_name(),
            mode=mode,
            played_audio=False,
            backend_available=True,
        )


def make_local_tts_desktop_view_model(*, available=True):
    backend = FakeLocalTtsBackend(available=available)
    voice_output = VoiceOutputManager(windows_local_backend=backend)
    processor = CommandProcessor(voice_output_manager=voice_output)
    service = JarvisAppService(command_processor=processor)
    return DesktopShellViewModel(service), backend, processor


@dataclass
class FakeExecutionResult:
    ok: bool = True
    output_text: str = "processed safely"
    registry_match_id: str | None = "ai.status"
    category: str | None = "ai"
    risk_level: str | None = "read_only"
    requires_confirmation: bool = False
    network_may_be_used: bool = False
    operation_id: str | None = None
    operation_status: str | None = None
    awaiting_confirmation: bool = False
    error: str | None = None
    requires_clarification: bool = False
    clarification_question: str | None = None
    clarification_options: tuple = ()


@dataclass
class FakeDesktopDiagnostics:
    route: str = "execution"

    def safe_text_ru(self):
        return f"Desktop turn diagnostics:\n- route: {self.route}"


@dataclass
class FakeDesktopTurnResult:
    ok: bool = True
    response_text: str = "processed safely"
    cognitive_session_id: str | None = None
    diagnostics: FakeDesktopDiagnostics = field(default_factory=FakeDesktopDiagnostics)
    execution: object | None = None
    error: str | None = None
    chat_status: AppDesktopChatStatus | None = None


@dataclass
class FakeVoiceResult:
    ok: bool = True
    voice_capture_succeeded: bool = True
    recognition_succeeded: bool = True
    recognized_text: str | None = "СЃС‚Р°С‚СѓСЃ ai"
    text_processing_succeeded: bool = True
    result_type: str = "text_processed"
    category: str | None = "ai"
    requires_confirmation: bool = False
    error_code: str | None = None
    user_message: str = "processed through text path"
    text_result: FakeExecutionResult | None = None
    normalized_text: str | None = None
    normalization_applied: bool = False
    normalization_rules: tuple[str, ...] = ()
    desktop_turn_result: FakeDesktopTurnResult | None = None
    cognitive_session_id: str | None = None


def _operation_id_from_desktop_text(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("- operation id: "):
            return line.removeprefix("- operation id: ").strip()
    return ""


def _desktop_field(text: str, label: str) -> str:
    prefix = f"- {label}: "
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


class FakeAppService:
    def __init__(self):
        self.preview_calls = []
        self.execute_calls = []
        self.desktop_turn_calls = []
        self.voice_calls = []
        self.list_calls = []
        self.history_calls = []
        self.workflow_list_calls = []
        self.workflow_detail_calls = []
        self.workflow_resume_calls = []
        self.workflow_cancellation_calls = []
        self.history_entries = (
            history_entry(
                "op-new",
                timestamp="2026-07-22T10:02:00+00:00",
                status="failed",
                command_id="voice.test",
                request_summary="voice test",
                safe_error_summary="voice.output.local_test.failed",
            ),
            history_entry(
                "op-old",
                timestamp="2026-07-22T10:01:00+00:00",
                status="succeeded",
                command_id="ai.status",
                request_summary="status ai",
            ),
        )
        self.history_error = None
        self.workflow_runs = (
            workflow_run(
                "wf-new",
                steps=(
                    workflow_step("validate", index=0),
                    workflow_step("write", index=1),
                ),
            ),
            workflow_run(
                "wf-old",
                steps=(workflow_step("read", index=0),),
                objective="Older workflow",
            ),
        )
        self.workflow_details = {run.run_id: run for run in self.workflow_runs}
        self.workflow_list_error = None
        self.workflow_detail_error = None
        self.workflow_resume_result = None
        self.workflow_cancellation_result = None
        self.activity_calls = 0
        self.activity_snapshots = [activity_snapshot()]
        self.activity_error = None
        self.resumable_session_id = None
        self.resumable_session_calls = 0
        self.chat_status = AppDesktopChatStatus(
            session_id=None,
            session_state="none",
            turn_count=0,
            resumable=False,
            response_state="idle",
            response_source="none",
            retry_available=False,
            retry_reason="not_available",
            persistence_state="in_memory",
            persistence_code="not_configured",
        )

    def resumable_conversation_session_id(self):
        self.resumable_session_calls += 1
        return self.resumable_session_id

    def desktop_chat_status(self, session_id=None):
        return replace(
            self.chat_status,
            session_id=session_id or self.chat_status.session_id,
            response_state="idle",
            response_source="none",
            retry_available=False,
            retry_reason="not_available",
        )

    def status_text_ru(self):
        return "\n".join(
            [
                "App service status:",
                "- enabled yes",
                "- network default: no",
                "- no secrets",
            ]
        )

    def contract_status_text_ru(self):
        return "\n".join(
            [
                "AppService contracts status:",
                "- schema name: jarvis.app_service.contracts",
                "- contract version: 0.1",
                "- network default: no",
                "- secrets included: no",
            ]
        )

    def categories_text_ru(self):
        return "Command registry categories:\n- app: 8 command(s)\n- ai: 10 command(s)\n- voice: 12 command(s)"

    def list_commands(self, category=None):
        self.list_calls.append(category)
        category_text = category or "all"
        return f"Command registry: {category_text}\n- app_service.status\n- desktop_shell.status"

    def preview_text_ru(self, text):
        self.preview_calls.append(text)
        if "groq" in text:
            return "\n".join(
                [
                    "App command preview:",
                    "- does not execute command",
                    "- command id: ai_provider.groq.real_request",
                    "- risk: network_explicit",
                    "- requires_network: yes",
                    "- requires_privacy_check: yes",
                    "- no secrets",
                ]
            )
        return "\n".join(
            [
                "App command preview:",
                "- does not execute command",
                "- command id: ai.status",
                "- risk: read_only",
                "- requires_network: no",
                "- no secrets",
            ]
        )

    def execute_command(self, text, source):
        self.execute_calls.append((text, source))
        return FakeExecutionResult(output_text=f"processed: {text}")

    def handle_desktop_turn(self, text, source, *, session_id=None):
        self.desktop_turn_calls.append((text, source, session_id))
        execution = self.execute_command(text, source)
        return FakeDesktopTurnResult(
            ok=execution.ok,
            response_text=execution.output_text,
            cognitive_session_id=session_id,
            diagnostics=FakeDesktopDiagnostics(),
            execution=execution,
            error=execution.error,
            chat_status=self.chat_status,
        )

    def process_one_shot_voice_request(self, source, *, session_id=None):
        self.voice_calls.append(source)
        configured = getattr(self, "voice_result", None)
        if configured is not None:
            return configured
        turn_result = FakeDesktopTurnResult(
            response_text="processed voice command",
            cognitive_session_id=session_id,
            diagnostics=FakeDesktopDiagnostics(route="conversation"),
            execution=None,
        )
        return FakeVoiceResult(
            text_result=FakeExecutionResult(output_text="processed voice command"),
            desktop_turn_result=turn_result,
            cognitive_session_id=session_id,
        )

    def execution_history(self, limit=None):
        self.history_calls.append(limit)
        if self.history_error is not None:
            return AppExecutionHistoryResult(
                ok=False,
                entries=(),
                limit=50,
                max_limit=100,
                empty=True,
                error=self.history_error,
            )
        return AppExecutionHistoryResult(
            ok=True,
            entries=tuple(self.history_entries),
            limit=50 if limit is None else int(limit),
            max_limit=100,
            empty=not self.history_entries,
            error=None,
        )

    def application_activity(self):
        self.activity_calls += 1
        if self.activity_error is not None:
            raise RuntimeError(self.activity_error)
        if len(self.activity_snapshots) > 1:
            return self.activity_snapshots.pop(0)
        return self.activity_snapshots[0]

    def recent_workflow_runs(self, limit=None):
        self.workflow_list_calls.append(limit)
        if self.workflow_list_error is not None:
            return WorkflowHistoryResult(
                ok=False,
                runs=(),
                limit=25,
                max_limit=100,
                empty=True,
                error=self.workflow_list_error,
            )
        return WorkflowHistoryResult(
            ok=True,
            runs=tuple(self.workflow_runs),
            limit=25 if limit is None else int(limit),
            max_limit=100,
            empty=not self.workflow_runs,
            error=None,
        )

    def workflow_run_history(self, run_id):
        self.workflow_detail_calls.append(run_id)
        if self.workflow_detail_error is not None:
            return WorkflowHistoryResult(
                ok=False,
                runs=(),
                limit=1,
                max_limit=100,
                empty=True,
                error=self.workflow_detail_error,
            )
        run = self.workflow_details.get(run_id)
        return WorkflowHistoryResult(
            ok=run is not None,
            runs=(run,) if run is not None else (),
            limit=1,
            max_limit=100,
            empty=run is None,
            error=None if run is not None else "workflow_history_unavailable",
        )

    def resume_workflow_run(self, run_id):
        self.workflow_resume_calls.append(run_id)
        if self.workflow_resume_result is not None:
            return self.workflow_resume_result
        return WorkflowResumeResult(
            ok=True,
            status=WorkflowResumeStatus.STARTED,
            source_run_id=run_id,
            resumed_run_id="wf-resumed",
            resume_step_id="write",
            resume_step_index=1,
            execution_started=True,
            safe_message="Workflow resume started.",
        )

    def cancel_workflow_run(self, run_id):
        self.workflow_cancellation_calls.append(run_id)
        if self.workflow_cancellation_result is not None:
            return self.workflow_cancellation_result
        return WorkflowCancellationResult(
            ok=True,
            status=WorkflowCancellationStatus.ACCEPTED,
            run_id=run_id,
            cancellation_accepted=True,
            signal_sent=True,
            current_state=WorkflowRunHistoryState.CANCELLED,
            safe_message="Workflow cancellation accepted.",
        )


class FakeAppServiceCommandProcessor:
    def __init__(self):
        self.calls = []
        self.action_router = self.FailingActionRouter()

    class FailingActionRouter:
        def route(self, command):
            raise AssertionError("Desktop AppService test must not call ActionRouter")

    def process(self, text):
        self.calls.append(text)
        if text == "\u0441\u0442\u0430\u0442\u0443\u0441 \u043c\u0438\u043a\u0440\u043e\u0444\u043e\u043d\u0430":
            return {
                "intent": "microphone.mode.status",
                "response": "\u041c\u0438\u043a\u0440\u043e\u0444\u043e\u043d \u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d.",
            }
        if text == "task096 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430":
            return {
                "intent": "unknown",
                "requires_confirmation": False,
                "response": "\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c, \u044f \u043f\u043e\u043a\u0430 \u043d\u0435 \u0443\u043c\u0435\u044e \u0432\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u044d\u0442\u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u0443, \u043d\u043e \u043c\u043e\u0433\u0443 \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0435\u0451 \u043a\u0430\u043a \u0438\u0434\u0435\u044e \u0434\u043b\u044f \u0431\u0443\u0434\u0443\u0449\u0435\u0433\u043e.",
            }
        return {"intent": "fake.intent", "response": f"processed: {text}"}


class FakeOneShotRecognition:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def run_once(self, explicit_one_shot_requested=False):
        self.calls += 1
        assert explicit_one_shot_requested is True
        return self.result


class FakeRoot:
    def __init__(self):
        self.clipboard = ""
        self.clear_calls = 0
        self.append_calls = []
        self.raise_on_get = False
        self.raise_on_set = False

    def clipboard_clear(self):
        if self.raise_on_set:
            raise RuntimeError("raw clipboard failure")
        self.clear_calls += 1
        self.clipboard = ""

    def clipboard_append(self, text):
        if self.raise_on_set:
            raise RuntimeError("raw clipboard failure")
        self.append_calls.append(text)
        self.clipboard += text

    def clipboard_get(self):
        if self.raise_on_get:
            raise RuntimeError("raw clipboard failure")
        return self.clipboard


class FakeMenu:
    def __init__(self, _parent, tearoff=0):
        self.labels = []
        self.commands = {}
        self.popup_calls = []
        self.released = False

    def add_command(self, label, command):
        self.labels.append(label)
        self.commands[label] = command

    def add_separator(self):
        self.labels.append("---")

    def tk_popup(self, x_root, y_root):
        self.popup_calls.append((x_root, y_root))

    def grab_release(self):
        self.released = True


class FakeTk:
    Menu = FakeMenu


class FakeEntry:
    def __init__(self, text=""):
        self.text = text
        self.cursor = len(text)
        self.selection = None
        self.bindings = {}

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def selection_get(self):
        if self.selection is None:
            raise RuntimeError("no selection")
        start, end = self.selection
        return self.text[start:end]

    def selection_range(self, start, end):
        start = 0 if start == 0 else int(start)
        end = len(self.text) if end == "end" else int(end)
        self.selection = (start, end)

    def icursor(self, index):
        self.cursor = len(self.text) if index in {"end", "insert"} else int(index)

    def delete(self, start, end=None):
        if start == "sel.first" and end == "sel.last":
            if self.selection is None:
                raise RuntimeError("no selection")
            start, end = self.selection
            self.text = self.text[:start] + self.text[end:]
            self.cursor = start
            self.selection = None
            return
        if start == 0 and end == "end":
            self.text = ""
            self.cursor = 0

    def insert(self, index, text):
        if index == "insert":
            index = self.cursor
        self.text = self.text[:index] + text + self.text[index:]
        self.cursor = index + len(text)


class FakeText:
    def __init__(self, text=""):
        self.text = text
        self.bindings = {}
        self.tags = {}
        self.state = "disabled"
        self.deleted = False
        self.inserted = []

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def get(self, start, end):
        if start == "sel.first" and end == "sel.last":
            selection = self.tags.get("sel")
            if selection is None:
                raise RuntimeError("no selection")
            return self.text
        return self.text

    def tag_add(self, tag, start, end):
        self.tags[tag] = (start, end)

    def mark_set(self, *_args):
        return None

    def see(self, *_args):
        return None

    def configure(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs["state"]

    def delete(self, *_args):
        self.deleted = True

    def insert(self, *_args):
        self.inserted.append(_args)


def fake_shell(root=None):
    shell = JarvisDesktopShell.__new__(JarvisDesktopShell)
    shell.root = root or FakeRoot()
    shell.tk = FakeTk
    shell.view_model = DesktopShellViewModel(FakeAppService())
    return shell


def test_view_model_builds_initial_state_safely():
    view_model = DesktopShellViewModel(FakeAppService())

    state = view_model.state

    assert state.app_title == "JARVIS OS"
    assert state.ui_ready is True
    assert state.safe_mode is True
    assert "No command has been executed" in state.output_text
    assert "desktop_shell.status" in state.command_list_text
    assert "Execution history:" in state.history_list_text
    assert "op-new" in state.selected_history_details_text
    assert state.selected_history_id == "op-new"
    assert "Workflow History:" in state.workflow_list_text
    assert state.selected_workflow_run_id == "wf-new"
    assert "Workflow Steps:" in state.workflow_details_text
    assert "validate" in state.workflow_details_text


def test_workflow_runs_render_through_app_service_dtos():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.refresh_workflow_history()

    assert service.workflow_list_calls[-1] is None
    assert service.workflow_detail_calls[-1] == "wf-new"
    assert "wf-new | Document review | completed" in text
    assert "wf-old | Document review | completed" in text
    assert view_model.state.workflow_runs == service.workflow_runs
    assert view_model.state.selected_workflow_run_id == "wf-new"


def test_selecting_workflow_run_loads_detail_and_ordered_steps():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    details = view_model.select_workflow_run(1)

    assert service.workflow_detail_calls[-1] == "wf-old"
    assert view_model.state.selected_workflow_run_id == "wf-old"
    assert "Older workflow" in details
    assert "- 1. Step read" in details
    assert [step.step_id for step in view_model.state.selected_workflow_steps] == ["read"]
    assert "validate" not in details


def test_workflow_unknown_state_renders_safe_fallback_label():
    service = FakeAppService()
    service.workflow_runs = (
        workflow_run(
            "wf-unknown",
            state=WorkflowRunHistoryState.UNKNOWN,
            steps=(
                workflow_step(
                    "unknown-step",
                    state=WorkflowStepHistoryState.UNKNOWN,
                    index=0,
                    error="Traceback RuntimeError C:/Users/User/raw.log",
                ),
            ),
        ),
    )
    service.workflow_details = {"wf-unknown": service.workflow_runs[0]}

    view_model = DesktopShellViewModel(service)

    assert "unknown" in view_model.state.workflow_list_text
    assert "state: unknown" in view_model.state.workflow_details_text
    assert "Traceback" not in view_model.state.workflow_details_text
    assert "RuntimeError" not in view_model.state.workflow_details_text
    assert "C:/Users/User" not in view_model.state.workflow_details_text


def test_empty_workflow_run_list_shows_empty_state():
    service = FakeAppService()
    service.workflow_runs = ()
    service.workflow_details = {}

    view_model = DesktopShellViewModel(service)

    assert "No workflow runs available." in view_model.state.workflow_list_text
    assert "Select a workflow run to view its steps." in view_model.state.workflow_details_text
    assert view_model.state.selected_workflow_run_id is None
    assert view_model.selected_workflow_copy_text() == ""


def test_workflow_run_with_no_steps_shows_step_empty_state():
    service = FakeAppService()
    service.workflow_runs = (workflow_run("wf-empty", steps=()),)
    service.workflow_details = {"wf-empty": service.workflow_runs[0]}

    view_model = DesktopShellViewModel(service)

    assert "No workflow steps were recorded." in view_model.state.workflow_details_text
    assert view_model.state.selected_workflow_steps == ()


def test_workflow_list_failure_shows_safe_error_without_crash():
    service = FakeAppService()
    service.workflow_list_error = RAW_HISTORY_ERROR

    view_model = DesktopShellViewModel(service)
    text = view_model.refresh_workflow_history()

    assert "workflow_history_unavailable" in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert view_model.state.workflow_runs == ()
    assert view_model.state.selected_workflow_run_id is None


def test_workflow_detail_failure_clears_stale_details_safely():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    first_details = view_model.state.workflow_details_text
    assert "validate" in first_details
    service.workflow_detail_error = RAW_HISTORY_ERROR
    details = view_model.select_workflow_run(1)

    assert view_model.state.selected_workflow_run_id == "wf-old"
    assert "workflow_history_unavailable" in details
    assert "validate" not in details
    assert "write" not in details
    assert "Traceback" not in details
    assert "RuntimeError" not in details
    assert "C:/Users/User" not in details
    assert view_model.state.selected_workflow_steps == ()
    assert view_model.selected_workflow_copy_text() == ""


def test_workflow_refresh_preserves_selection_and_reloads_detail_without_duplicates():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    view_model.select_workflow_run(1)
    updated = workflow_run(
        "wf-old",
        state=WorkflowRunHistoryState.FAILED,
        steps=(
            workflow_step("read", index=0),
            workflow_step(
                "analyze",
                index=1,
                state=WorkflowStepHistoryState.FAILED,
                error="safe analyze failure",
            ),
        ),
        objective="Updated older workflow",
        completed_count=1,
    )
    service.workflow_runs = (updated, workflow_run("wf-newer", steps=(workflow_step("new", index=0),)))
    service.workflow_details = {run.run_id: run for run in service.workflow_runs}

    text = view_model.refresh_workflow_history()

    assert view_model.state.selected_workflow_run_id == "wf-old"
    assert service.workflow_detail_calls[-1] == "wf-old"
    assert text.count("wf-old") == 1
    assert [run.run_id for run in view_model.state.workflow_runs] == ["wf-old", "wf-newer"]
    assert [step.step_id for step in view_model.state.selected_workflow_steps] == [
        "read",
        "analyze",
    ]
    assert view_model.state.workflow_details_text.count("Step read") == 1
    assert "state: failed" in view_model.state.workflow_details_text


def test_workflow_refresh_clears_selection_when_selected_run_disappears():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    view_model.select_workflow_run(1)
    service.workflow_runs = (workflow_run("wf-newer", steps=(workflow_step("new", index=0),)),)
    service.workflow_details = {"wf-newer": service.workflow_runs[0]}

    view_model.refresh_workflow_history()

    assert view_model.state.selected_workflow_run_id == "wf-newer"
    assert "Older workflow" not in view_model.state.workflow_details_text
    assert "Step new" in view_model.state.workflow_details_text

    service.workflow_runs = ()
    service.workflow_details = {}
    view_model.refresh_workflow_history()

    assert view_model.state.selected_workflow_run_id is None
    assert "Select a workflow run to view its steps." in view_model.state.workflow_details_text
    assert view_model.state.selected_workflow_steps == ()


def test_workflow_selection_replaces_old_run_details():
    view_model = DesktopShellViewModel(FakeAppService())

    assert "validate" in view_model.state.workflow_details_text
    details = view_model.select_workflow_run(1)

    assert "Step read" in details
    assert "validate" not in details
    assert "write" not in details


def test_workflow_copy_uses_only_safe_projected_content():
    service = FakeAppService()
    service.workflow_runs = (
        workflow_run(
            "wf-copy",
            state=WorkflowRunHistoryState.FAILED,
            steps=(
                workflow_step(
                    "fail",
                    state=WorkflowStepHistoryState.FAILED,
                    error="Traceback RuntimeError C:/Users/User/raw.log sk-test-1234567890secret",
                ),
            ),
            completed_count=0,
        ),
    )
    service.workflow_details = {"wf-copy": service.workflow_runs[0]}
    view_model = DesktopShellViewModel(service)

    copied = view_model.selected_workflow_copy_text()

    assert "Workflow Run:" in copied
    assert "wf-copy" in copied
    assert "Traceback" not in copied
    assert "RuntimeError" not in copied
    assert "C:/Users/User" not in copied
    assert "sk-test" not in copied


def test_workflow_copy_is_unavailable_without_valid_selection():
    service = FakeAppService()
    service.workflow_runs = ()
    service.workflow_details = {}
    view_model = DesktopShellViewModel(service)

    assert view_model.selected_workflow_copy_text() == ""


def test_desktop_workflow_view_does_not_import_runtime_or_journal_directly():
    source = desktop_shell.__loader__.get_source(desktop_shell.__name__)

    assert "WorkflowRunner" not in source
    assert "ExecutionJournal" not in source
    assert "execution_journal" not in source
    assert ".document_review_runner" not in source


def test_workflow_resume_availability_comes_from_projected_dto():
    service = FakeAppService()
    service.workflow_runs = (
        workflow_run(
            "wf-failed",
            state=WorkflowRunHistoryState.FAILED,
            steps=(workflow_step("read", index=0), workflow_step("write", index=1)),
            completed_count=1,
            resume_eligible=True,
            resume_step_id="write",
            resume_step_index=1,
        ),
        workflow_run(
            "wf-complete",
            resume_eligible=False,
            resume_reason=WorkflowResumeRejectionReason.ALREADY_COMPLETED,
            steps=(workflow_step("done", index=0),),
        ),
    )
    service.workflow_details = {run.run_id: run for run in service.workflow_runs}
    view_model = DesktopShellViewModel(service)

    assert view_model.state.workflow_resume_available is True
    assert "resume available: yes" in view_model.state.workflow_details_text
    view_model.select_workflow_run(1)
    assert view_model.state.workflow_resume_available is False
    assert "already_completed" in view_model.state.workflow_resume_text


def test_workflow_resume_confirmation_cancellation_makes_no_appservice_call():
    service = FakeAppService()
    service.workflow_runs = (
        workflow_run(
            "wf-failed",
            state=WorkflowRunHistoryState.FAILED,
            steps=(workflow_step("write", index=0, state=WorkflowStepHistoryState.FAILED),),
            completed_count=0,
            resume_eligible=True,
            resume_step_id="write",
            resume_step_index=0,
        ),
    )
    service.workflow_details = {"wf-failed": service.workflow_runs[0]}
    view_model = DesktopShellViewModel(service)

    text = view_model.resume_selected_workflow_run(confirmed=False)

    assert text == "Workflow resume cancelled."
    assert service.workflow_resume_calls == []


def test_workflow_resume_confirmation_acceptance_calls_appservice_once_and_refreshes():
    service = FakeAppService()
    source = workflow_run(
        "wf-failed",
        state=WorkflowRunHistoryState.FAILED,
        steps=(workflow_step("write", index=0, state=WorkflowStepHistoryState.FAILED),),
        completed_count=0,
        resume_eligible=True,
        resume_step_id="write",
        resume_step_index=0,
    )
    resumed = workflow_run(
        "wf-resumed",
        steps=(workflow_step("write", index=0), workflow_step("verify", index=1)),
        resumed_from_run_id="wf-failed",
    )
    service.workflow_runs = (source,)
    service.workflow_details = {"wf-failed": source}
    view_model = DesktopShellViewModel(service)
    service.workflow_runs = (resumed, source)
    service.workflow_details = {"wf-resumed": resumed, "wf-failed": source}

    text = view_model.resume_selected_workflow_run(confirmed=True)

    assert service.workflow_resume_calls == ["wf-failed"]
    assert "- status: started" in text
    assert "- completed steps rerun: no" in text
    assert view_model.state.selected_workflow_run_id == "wf-resumed"
    assert "resumed from: wf-failed" in view_model.state.workflow_details_text
    assert "Step verify" in view_model.state.workflow_details_text


def test_workflow_resume_rejection_and_exceptions_are_safe_and_keep_view_usable():
    service = FakeAppService()
    source = workflow_run(
        "wf-failed",
        state=WorkflowRunHistoryState.FAILED,
        steps=(workflow_step("write", index=0, state=WorkflowStepHistoryState.FAILED),),
        completed_count=0,
        resume_eligible=True,
        resume_step_id="write",
        resume_step_index=0,
    )
    service.workflow_runs = (source,)
    service.workflow_details = {"wf-failed": source}
    service.workflow_resume_result = WorkflowResumeResult(
        ok=False,
        status=WorkflowResumeStatus.REJECTED,
        source_run_id="wf-failed",
        rejection_reason=WorkflowResumeRejectionReason.WORKFLOW_DEFINITION_INCOMPATIBLE,
        safe_message="Traceback RuntimeError C:/Users/User/raw.log sk-test-1234567890secret",
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.resume_selected_workflow_run(confirmed=True)

    assert service.workflow_resume_calls == ["wf-failed"]
    assert "workflow_definition_incompatible" in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert "sk-test" not in text
    assert view_model.state.selected_workflow_run_id == "wf-failed"


def test_workflow_resume_unavailable_without_selection_and_double_click_guard():
    view_model = DesktopShellViewModel(FakeAppService())
    view_model.select_workflow_run(None)

    no_selection = view_model.resume_selected_workflow_run(confirmed=True)
    view_model.state = view_model._replace(workflow_resume_in_progress=True)
    pending = view_model.resume_selected_workflow_run(confirmed=True)

    assert "no workflow run selected" in no_selection
    assert pending == "Workflow resume is already in progress."


def test_workflow_cancellation_availability_comes_from_projected_dto():
    service = FakeAppService()
    service.workflow_runs = (
        workflow_run(
            "wf-active",
            state=WorkflowRunHistoryState.RUNNING,
            steps=(workflow_step("running", index=0, state=WorkflowStepHistoryState.RUNNING),),
            completed_count=0,
            cancellation_eligible=True,
        ),
        workflow_run(
            "wf-complete",
            steps=(workflow_step("done", index=0),),
            cancellation_eligible=False,
            cancellation_reason=WorkflowCancellationRejectionReason.ALREADY_COMPLETED,
        ),
    )
    service.workflow_details = {run.run_id: run for run in service.workflow_runs}
    view_model = DesktopShellViewModel(service)

    assert view_model.state.workflow_cancellation_available is True
    assert "cancel available: yes" in view_model.state.workflow_details_text
    view_model.select_workflow_run(1)
    assert view_model.state.workflow_cancellation_available is False
    assert "already_completed" in view_model.state.workflow_cancellation_text
    assert view_model.state.workflow_resume_available is False


def test_workflow_cancellation_confirmation_cancellation_makes_no_appservice_call():
    service = FakeAppService()
    service.workflow_runs = (
        workflow_run(
            "wf-active",
            state=WorkflowRunHistoryState.RUNNING,
            steps=(workflow_step("running", index=0, state=WorkflowStepHistoryState.RUNNING),),
            completed_count=0,
            cancellation_eligible=True,
        ),
    )
    service.workflow_details = {"wf-active": service.workflow_runs[0]}
    view_model = DesktopShellViewModel(service)

    text = view_model.cancel_selected_workflow_run(confirmed=False)

    assert text == "Workflow cancellation cancelled."
    assert service.workflow_cancellation_calls == []


def test_workflow_cancellation_acceptance_calls_appservice_once_and_refreshes():
    service = FakeAppService()
    active = workflow_run(
        "wf-active",
        state=WorkflowRunHistoryState.RUNNING,
        steps=(
            workflow_step("done", index=0),
            workflow_step("running", index=1, state=WorkflowStepHistoryState.RUNNING),
            workflow_step("later", index=2, state=WorkflowStepHistoryState.PENDING),
        ),
        completed_count=1,
        cancellation_eligible=True,
    )
    cancelled = workflow_run(
        "wf-active",
        state=WorkflowRunHistoryState.CANCELLED,
        steps=(
            workflow_step("done", index=0),
            workflow_step("running", index=1, state=WorkflowStepHistoryState.CANCELLED),
            workflow_step("later", index=2, state=WorkflowStepHistoryState.PENDING),
        ),
        completed_count=1,
        cancellation_eligible=False,
        cancellation_reason=WorkflowCancellationRejectionReason.ALREADY_CANCELLED,
    )
    service.workflow_runs = (active,)
    service.workflow_details = {"wf-active": active}
    view_model = DesktopShellViewModel(service)
    service.workflow_runs = (cancelled,)
    service.workflow_details = {"wf-active": cancelled}

    text = view_model.cancel_selected_workflow_run(confirmed=True)

    assert service.workflow_cancellation_calls == ["wf-active"]
    assert "- status: accepted" in text
    assert "- cancellation accepted: yes" in text
    assert "- later steps start after accepted cancellation: no" in text
    assert view_model.state.selected_workflow_run_id == "wf-active"
    assert "state: cancelled" in view_model.state.workflow_details_text
    assert "Step later" in view_model.state.workflow_details_text
    assert view_model.state.workflow_cancellation_available is False


def test_workflow_cancellation_rejection_and_exceptions_are_safe_and_keep_view_usable():
    service = FakeAppService()
    source = workflow_run(
        "wf-active",
        state=WorkflowRunHistoryState.RUNNING,
        steps=(workflow_step("running", index=0, state=WorkflowStepHistoryState.RUNNING),),
        completed_count=0,
        cancellation_eligible=True,
    )
    service.workflow_runs = (source,)
    service.workflow_details = {"wf-active": source}
    service.workflow_cancellation_result = WorkflowCancellationResult(
        ok=False,
        status=WorkflowCancellationStatus.REJECTED,
        run_id="wf-active",
        rejection_reason=WorkflowCancellationRejectionReason.SIGNAL_FAILED,
        safe_message="Traceback RuntimeError C:/Users/User/raw.log sk-test-1234567890secret",
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.cancel_selected_workflow_run(confirmed=True)

    assert service.workflow_cancellation_calls == ["wf-active"]
    assert "signal_failed" in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert "sk-test" not in text
    assert view_model.state.selected_workflow_run_id == "wf-active"


def test_workflow_cancellation_unavailable_without_selection_and_double_click_guard():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    view_model.select_workflow_run(None)

    no_selection = view_model.cancel_selected_workflow_run(confirmed=True)
    view_model.state = view_model._replace(workflow_cancellation_in_progress=True)
    pending = view_model.cancel_selected_workflow_run(confirmed=True)

    assert "no workflow run selected" in no_selection
    assert pending == "Workflow cancellation is already in progress."
    assert service.workflow_cancellation_calls == []


def test_workflow_cancellation_non_cancellable_projection_disables_cancel():
    service = FakeAppService()
    run = workflow_run(
        "wf-active",
        state=WorkflowRunHistoryState.RUNNING,
        steps=(workflow_step("running", index=0, state=WorkflowStepHistoryState.RUNNING),),
        completed_count=0,
        cancellation_eligible=False,
        cancellation_reason=WorkflowCancellationRejectionReason.NON_CANCELLABLE_STEP,
    )
    service.workflow_runs = (run,)
    service.workflow_details = {"wf-active": run}
    view_model = DesktopShellViewModel(service)

    text = view_model.cancel_selected_workflow_run(confirmed=True)

    assert view_model.state.workflow_cancellation_available is False
    assert "non_cancellable_step" in view_model.state.workflow_cancellation_text
    assert "non_cancellable_step" in text
    assert service.workflow_cancellation_calls == []


def test_desktop_activity_renders_current_and_recent_outcome():
    service = FakeAppService()
    current = activity(
        "op-current",
        state=ApplicationActivityState.WAITING_FOR_USER,
        title="Confirmation required",
    )
    recent = activity(
        "op-recent",
        state=ApplicationActivityState.FAILED,
        title="Voice request",
        error="Traceback RuntimeError C:/Users/User/raw.log sk-test-1234567890secret",
    )
    service.activity_snapshots = [activity_snapshot(current=current, recent=(recent,))]

    view_model = DesktopShellViewModel(service)

    assert "Application Activity:" in view_model.state.activity_text
    assert "- status: busy" in view_model.state.activity_text
    assert "waiting_for_user" in view_model.state.activity_text
    assert "Voice request | failed" in view_model.state.activity_text
    assert "Traceback" not in view_model.state.activity_text
    assert "C:/Users/User" not in view_model.state.activity_text
    assert view_model.state.current_activity.activity_id == "op-current"
    assert view_model.state.recent_activities[0].activity_id == "op-recent"


def test_desktop_activity_idle_transition_clears_stale_current():
    service = FakeAppService()
    service.activity_snapshots = [
        activity_snapshot(current=activity("op-current")),
        activity_snapshot(current=None),
    ]
    view_model = DesktopShellViewModel(service)

    text = view_model.refresh_application_activity()

    assert "- status: idle" in text
    assert "- current: idle" in text
    assert view_model.state.current_activity is None
    assert "op-current" not in view_model.state.activity_text


def test_desktop_activity_refresh_failure_preserves_usability_and_recovers():
    service = FakeAppService()
    service.activity_snapshots = [activity_snapshot()]
    view_model = DesktopShellViewModel(service)
    service.activity_error = "Traceback RuntimeError backend C:/Users/User/raw.log sk-test-1234567890secret"

    failed = view_model.refresh_application_activity()
    service.activity_error = None
    service.activity_snapshots = [activity_snapshot(current=activity("op-recovered"))]
    recovered = view_model.refresh_application_activity()

    assert "unavailable" in failed
    assert "Traceback" not in failed
    assert "RuntimeError" not in failed
    assert "C:/Users/User" not in failed
    assert "sk-test" not in failed
    assert "op-recovered" in recovered
    assert view_model.state.activity_load_error is None


def test_desktop_activity_refresh_guard_prevents_overlapping_reads():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    calls_before = service.activity_calls
    view_model.state = view_model._replace(activity_refresh_in_progress=True)

    text = view_model.refresh_application_activity()

    assert text == view_model.state.activity_text
    assert service.activity_calls == calls_before
    assert view_model.state.last_error == "Application activity refresh is already in progress."


def test_desktop_activity_boundary_uses_appservice_only():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    view_model.refresh_application_activity()
    source = desktop_shell.__loader__.get_source(desktop_shell.__name__)

    assert service.activity_calls >= 2
    assert "WorkflowRunner" not in source
    assert "ExecutionCoordinator" not in source
    assert "ExecutionJournal" not in source
    assert "execution_coordinator" not in source
    assert "execution_journal" not in source
    assert ".journal" not in source


def test_desktop_workflow_cancel_uses_only_run_id_and_no_runtime_data():
    service = FakeAppService()
    service.workflow_runs = (
        workflow_run(
            "wf-active",
            state=WorkflowRunHistoryState.RUNNING,
            steps=(workflow_step("running", index=0, state=WorkflowStepHistoryState.RUNNING),),
            completed_count=0,
            cancellation_eligible=True,
        ),
    )
    service.workflow_details = {"wf-active": service.workflow_runs[0]}
    view_model = DesktopShellViewModel(service)

    view_model.cancel_selected_workflow_run(confirmed=True)
    source = desktop_shell.__loader__.get_source(desktop_shell.__name__)

    assert service.workflow_cancellation_calls == ["wf-active"]
    assert "WorkflowRunner" not in source
    assert "ExecutionCoordinator" not in source
    assert "ExecutionJournal" not in source
    assert "CancellationToken" not in source
    assert "execution_journal" not in source


def test_view_model_displays_history_entries_newest_first():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.refresh_execution_history()

    assert service.history_calls[-1] is None
    assert "1. 2026-07-22T10:02:00+00:00 | failed | voice.test" in text
    assert "2. 2026-07-22T10:01:00+00:00 | succeeded | ai.status" in text
    assert view_model.state.history_entries[0].entry_id == "op-new"
    assert view_model.state.history_entries[1].entry_id == "op-old"
    assert view_model.state.loaded_history_entries == view_model.state.history_entries
    assert view_model.state.history_result_count_text == "2 entries"


def test_view_model_refreshes_history_without_duplicates():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    service.history_entries = (history_entry("op-third", command_id="memory.remember"),)

    first = view_model.refresh_execution_history()
    second = view_model.refresh_execution_history()

    assert first.count("op-third") <= 1
    assert second.count("op-third") <= 1
    assert len(view_model.state.history_entries) == 1
    assert view_model.state.selected_history_id == "op-third"


def test_view_model_displays_empty_history_state():
    service = FakeAppService()
    service.history_entries = ()
    view_model = DesktopShellViewModel(service)

    assert "No execution history is available." in view_model.state.history_list_text
    assert "no entry selected" in view_model.state.selected_history_details_text
    assert view_model.state.loaded_history_entries == ()
    assert view_model.state.history_entries == ()


def test_view_model_displays_safe_history_loading_error():
    service = FakeAppService()
    service.history_error = RAW_HISTORY_ERROR
    view_model = DesktopShellViewModel(service)

    text = view_model.refresh_execution_history()

    assert "execution_history_unavailable" in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
    assert "C:/Users/User" not in text
    assert view_model.state.last_error == text


def test_view_model_updates_selected_history_details():
    view_model = DesktopShellViewModel(FakeAppService())

    details = view_model.select_history_entry(1)

    assert "op-old" in details
    assert "- command id: ai.status" in details
    assert view_model.state.selected_history_id == "op-old"


def test_view_model_history_copy_uses_safe_projected_content():
    service = FakeAppService()
    service.history_entries = (
        history_entry(
            "op-copy",
            status="failed",
            command_id="voice.test",
            request_summary="api key sk-test-1234567890secret",
            user_message="RuntimeError backend C:/Users/User/raw.log",
            safe_error_summary="PaErrorCode -9999 MME error 1",
        ),
    )
    view_model = DesktopShellViewModel(service)

    copied = view_model.selected_history_copy_text()

    assert "op-copy" in copied
    assert "sk-test-1234567890secret" not in copied
    assert "RuntimeError" not in copied
    assert "C:/Users/User" not in copied
    assert "PaErrorCode" not in copied
    assert "MME error" not in copied


def test_shell_history_copy_action_uses_selected_safe_text():
    root = FakeRoot()
    shell = fake_shell(root)

    shell._on_history_copy()

    assert root.clipboard
    assert "Execution history entry:" in root.clipboard
    assert "op-new" in root.clipboard
    assert "sk-test" not in root.clipboard


def test_view_model_malformed_history_entry_does_not_crash_rendering():
    class MalformedEntry:
        entry_id = "op-malformed"
        timestamp = "2026-07-22T10:03:00+00:00"
        status = "cancelled"
        command_id = None
        user_message = None
        safe_error_summary = None

    service = FakeAppService()
    service.history_entries = (MalformedEntry(),)
    view_model = DesktopShellViewModel(service)

    assert "op-malformed" in view_model.state.selected_history_details_text
    assert "cancelled" in view_model.state.history_list_text


def test_history_search_is_case_insensitive_and_matches_command_summary():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-doc", command_id="document.open", request_summary="Open Document"),
        history_entry("op-ai", command_id="ai.status", request_summary="status ai"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.update_history_search(" document ")

    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-doc"]
    assert view_model.state.loaded_history_entries[1].entry_id == "op-ai"
    assert view_model.state.history_search_query == "document"
    assert view_model.state.history_result_count_text == "1 of 2 entries"
    assert "op-ai" not in text


def test_history_search_matches_operation_action_message_and_error_fields():
    service = FakeAppService()
    service.history_entries = (
        history_entry(
            "op-action",
            command_id=None,
            action_id="workflow.review",
            operation_type="document_review",
            request_summary="review request",
        ),
        history_entry("op-message", user_message="Local microphone check failed"),
        history_entry(
            "op-error",
            status="failed",
            safe_error_summary="voice.output.local_test.failed",
        ),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_search("DOCUMENT_REVIEW")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-action"]

    view_model.update_history_search("microphone")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-message"]

    view_model.update_history_search("LOCAL_TEST")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-error"]


def test_history_search_whitespace_only_behaves_as_no_filter():
    view_model = DesktopShellViewModel(FakeAppService())

    view_model.update_history_search("   ")

    assert len(view_model.state.history_entries) == 2
    assert view_model.state.history_search_query == ""
    assert view_model.state.history_result_count_text == "2 entries"


def test_history_search_missing_optional_fields_and_unsafe_details_are_safe():
    class MinimalEntry:
        entry_id = "op-minimal"
        status = None
        preview = False

    service = FakeAppService()
    service.history_entries = (
        MinimalEntry(),
        history_entry(
            "op-safe",
            status="failed",
            command_id="voice.test",
            request_summary="microphone unavailable",
            user_message="Safe execution detail unavailable.",
            safe_error_summary="Safe execution detail unavailable.",
        ),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_search("RuntimeError")
    assert view_model.state.history_entries == ()

    view_model.update_history_search("microphone")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-safe"]


def test_history_status_filter_all_and_each_supported_status():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-success", status="succeeded"),
        history_entry("op-failed", status="FAILED"),
        history_entry("op-denied", status="denied"),
        history_entry("op-cancelled", status="cancelled"),
        history_entry("op-preview", status="succeeded", preview=True),
        history_entry("op-unknown", status="mystery"),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_status_filter("All")
    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-success",
        "op-failed",
        "op-denied",
        "op-cancelled",
        "op-preview",
        "op-unknown",
    ]

    view_model.update_history_status_filter("successful")
    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-success",
        "op-preview",
    ]

    view_model.update_history_status_filter("Failed")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-failed"]

    view_model.update_history_status_filter("Denied")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-denied"]

    view_model.update_history_status_filter("Cancelled")
    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-cancelled"
    ]

    view_model.update_history_status_filter("Preview")
    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-preview"]

    view_model.update_history_status_filter("unsupported")
    assert len(view_model.state.history_entries) == 6


def test_history_status_filter_does_not_mutate_dtos():
    service = FakeAppService()
    original_entries = service.history_entries
    view_model = DesktopShellViewModel(service)

    view_model.update_history_status_filter("Failed")

    assert service.history_entries == original_entries
    assert view_model.state.loaded_history_entries == original_entries
    assert view_model.state.loaded_history_entries is not view_model.state.history_entries


def test_history_combined_search_and_status_filter_use_and_semantics():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-success-mic", status="succeeded", request_summary="microphone status"),
        history_entry("op-failed-mic", status="failed", request_summary="microphone blocked"),
        history_entry("op-failed-doc", status="failed", request_summary="document failed"),
        history_entry("op-preview-mic", status="succeeded", preview=True, request_summary="microphone preview"),
    )
    view_model = DesktopShellViewModel(service)

    view_model.update_history_status_filter("Failed")
    view_model.update_history_search("microphone")

    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-failed-mic"
    ]
    assert view_model.state.selected_history_id == "op-failed-mic"
    assert view_model.state.history_result_count_text == "1 of 4 entries"


def test_history_no_matches_clear_filters_and_copy_state():
    view_model = DesktopShellViewModel(FakeAppService())
    view_model.select_history_entry(1)

    text = view_model.update_history_search("value-that-does-not-exist")

    assert view_model.state.history_entries == ()
    assert view_model.state.selected_history_id is None
    assert view_model.state.history_copy_text == ""
    assert view_model.selected_history_copy_text() == ""
    assert "No history entries match the current filters." in text
    assert "No execution history is available." not in text

    view_model.clear_history_filters()

    assert view_model.state.history_search_query == ""
    assert view_model.state.history_status_filter == "All"
    assert len(view_model.state.history_entries) == 2
    assert view_model.state.selected_history_id == "op-new"
    assert view_model.state.history_result_count_text == "2 entries"


def test_history_refresh_reapplies_filters_without_duplicates_and_preserves_selection():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-keep", status="failed", request_summary="microphone failed"),
        history_entry("op-drop", status="failed", request_summary="document failed"),
    )
    view_model = DesktopShellViewModel(service)
    view_model.update_history_status_filter("Failed")
    view_model.update_history_search("microphone")
    view_model.select_history_entry(0)
    service.history_entries = (
        history_entry("op-new", status="failed", request_summary="microphone failed again"),
        history_entry("op-keep", status="failed", request_summary="microphone failed"),
        history_entry("op-success", status="succeeded", request_summary="microphone ok"),
    )

    first = view_model.refresh_execution_history()
    second = view_model.refresh_execution_history()

    assert [entry.entry_id for entry in view_model.state.history_entries] == [
        "op-new",
        "op-keep",
    ]
    assert first.count("op-keep") <= 1
    assert second.count("op-keep") <= 1
    assert view_model.state.selected_history_id == "op-keep"


def test_history_refresh_selects_first_visible_when_previous_selection_no_longer_matches():
    service = FakeAppService()
    service.history_entries = (
        history_entry("op-old", status="failed", request_summary="microphone failed"),
    )
    view_model = DesktopShellViewModel(service)
    view_model.update_history_status_filter("Failed")
    view_model.update_history_search("microphone")
    service.history_entries = (
        history_entry("op-new", status="failed", request_summary="microphone failed"),
    )

    view_model.refresh_execution_history()

    assert [entry.entry_id for entry in view_model.state.history_entries] == ["op-new"]
    assert view_model.state.selected_history_id == "op-new"


def test_history_loading_failure_remains_distinct_from_filtering_state():
    service = FakeAppService()
    service.history_error = RAW_HISTORY_ERROR
    view_model = DesktopShellViewModel(service)

    view_model.update_history_search("microphone")
    view_model.clear_history_filters()

    assert "execution_history_unavailable" in view_model.state.history_list_text
    assert view_model.state.history_load_error is not None
    assert view_model.state.history_entries == ()


def test_status_text_mentions_app_service_and_no_network_default():
    view_model = DesktopShellViewModel(FakeAppService())

    text = view_model.safe_status_text_ru()

    assert "app service used: yes" in text
    assert "command registry used: yes" in text
    assert "network default: no" in text
    assert "no secrets" in text
    assert "AppService contracts status:" in text


def test_list_categories_uses_app_service_registry_text():
    view_model = DesktopShellViewModel(FakeAppService())

    text = view_model.list_categories()

    assert "Command registry categories" in text
    assert "app:" in text
    assert "ai:" in text
    assert "voice:" in text


def test_list_commands_works_for_app_ai_and_voice():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    assert "Command registry: app" in view_model.list_commands("app")
    assert "Command registry: ai" in view_model.list_commands("ai")
    assert "Command registry: voice" in view_model.list_commands("voice")
    assert service.list_calls[-3:] == ["app", "ai", "voice"]


def test_preview_command_does_not_execute_command():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("статус ai")

    assert "- does not execute command" in text
    assert service.preview_calls == ["статус ai"]
    assert service.execute_calls == []


def test_command_input_ctrl_v_pastes_cyrillic_and_windows_path_without_appservice_calls():
    root = FakeRoot()
    command = "\u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442 C:\\JARVIS-OS\\task084-sample.txt"
    root.clipboard = command
    shell = fake_shell(root)
    entry = FakeEntry()
    shell._bind_command_clipboard(entry)

    result = entry.bindings["<Control-v>"](None)

    assert result == "break"
    assert entry.text == command
    assert shell.view_model.app_service.preview_calls == []
    assert shell.view_model.app_service.execute_calls == []


def test_command_input_ctrl_a_selects_all_and_copy_cut_work_on_selection():
    root = FakeRoot()
    shell = fake_shell(root)
    entry = FakeEntry("\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt")
    shell._bind_command_clipboard(entry)

    assert entry.bindings["<Control-a>"](None) == "break"
    assert entry.selection == (0, len(entry.text))

    assert entry.bindings["<Control-c>"](None) == "break"
    assert root.clipboard == "\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt"
    assert entry.text == "\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt"

    assert entry.bindings["<Control-x>"](None) == "break"
    assert root.clipboard == "\u0441\u0442\u0430\u0442\u0443\u0441 C:\\JARVIS-OS\\file.txt"
    assert entry.text == ""


def test_command_input_right_click_menu_actions_are_safely_wired():
    shell = fake_shell()
    entry = FakeEntry("abc")
    shell._bind_command_clipboard(entry)
    menu = shell.command_entry_context_menu

    assert menu.labels == ["\u0412\u044b\u0440\u0435\u0437\u0430\u0442\u044c", "\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c", "\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c", "---", "\u0412\u044b\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u0441\u0451"]
    for label in (
        "\u0412\u044b\u0440\u0435\u0437\u0430\u0442\u044c",
        "\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c",
        "\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c",
        "\u0412\u044b\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u0441\u0451",
    ):
        assert callable(menu.commands[label])


def test_output_text_stays_read_only_but_can_select_and_copy():
    root = FakeRoot()
    shell = fake_shell(root)
    output = FakeText("\u0413\u043e\u0442\u043e\u0432\u043e\nC:\\JARVIS-OS\\task084-sample.txt")
    shell._bind_readonly_text_copy(output)

    assert output.state == "disabled"
    assert output.bindings["<Control-a>"](None) == "break"
    assert output.tags["sel"] == ("1.0", "end-1c")
    assert output.bindings["<Control-c>"](None) == "break"
    assert root.clipboard == "\u0413\u043e\u0442\u043e\u0432\u043e\nC:\\JARVIS-OS\\task084-sample.txt"
    assert output.bindings["<Key>"](None) == "break"
    assert output.state == "disabled"


def test_clipboard_errors_are_handled_without_raw_exception_or_appservice_calls():
    root = FakeRoot()
    root.raise_on_get = True
    shell = fake_shell(root)
    entry = FakeEntry()
    shell._bind_command_clipboard(entry)

    assert entry.bindings["<Control-v>"](None) == "break"
    assert entry.text == ""
    assert shell.view_model.state.last_error is None
    assert shell.view_model.app_service.preview_calls == []
    assert shell.view_model.app_service.execute_calls == []

    root.raise_on_get = False
    root.raise_on_set = True
    entry.text = "abc"
    entry.selection = (0, 3)
    assert entry.bindings["<Control-c>"](None) == "break"
    assert "raw clipboard failure" not in shell.view_model.state.output_text


def test_preview_of_status_ai_known_read_only_with_real_service():
    view_model = DesktopShellViewModel(JarvisAppService())

    text = view_model.preview_command("статус ai")

    assert "- known command: yes" in text
    assert "- command id: ai.status" in text
    assert "- risk: read_only" in text
    assert "- requires_network: no" in text


def assert_desktop_memory_preview_fields(text, *, command_id, risk):
    assert "- known command: yes" in text
    assert f"- command id: {command_id}" in text
    assert "- category: memory" in text
    assert f"- risk: {risk}" in text
    assert "- requires_network: no" in text
    assert "- requires_confirmation: no" in text
    assert "- operation id: none" in text
    assert "- executed through AppService: yes" in text


def test_desktop_shell_projects_memory_remember_preview_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_preview_remember_memory.json")
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("remember that audit091key is north")

    assert_desktop_memory_preview_fields(
        text,
        command_id="memory.remember",
        risk="local_write",
    )
    assert service.memory_manager.recall_user_fact("audit091key").found is False
    assert service.recent_execution_operations(None) == ()


def test_desktop_shell_projects_memory_recall_preview_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_preview_recall_memory.json")
    )
    service.memory_manager.remember_user_fact("audit091key", "north")
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("what do you remember about audit091key")

    assert_desktop_memory_preview_fields(
        text,
        command_id="memory.recall",
        risk="read_only",
    )
    assert service.memory_manager.recall_user_fact("audit091key").value == "north"
    assert service.recent_execution_operations(None) == ()


def test_desktop_shell_projects_memory_forget_preview_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_preview_forget_memory.json")
    )
    service.memory_manager.remember_user_fact("audit091key", "north")
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("forget audit091key")

    assert_desktop_memory_preview_fields(
        text,
        command_id="memory.forget",
        risk="local_write",
    )
    assert service.memory_manager.recall_user_fact("audit091key").value == "north"
    assert service.recent_execution_operations(None) == ()


def test_desktop_shell_displays_planner_preview_with_real_service():
    view_model = DesktopShellViewModel(JarvisAppService())

    text = view_model.preview_command(
        "\u0441\u043e\u0441\u0442\u0430\u0432\u044c \u043f\u043b\u0430\u043d: \u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b; \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u044f\u0437\u044b\u043a"
    )

    assert "- known command: yes" in text
    assert "- command id: planner.general_multi_step" in text
    assert "- category: planner" in text
    assert "- app_ready: yes" in text
    assert "- requires_network: no" in text
    assert "- requires_confirmation: no" in text


def test_desktop_shell_projects_execute_plan_confirmation_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_planner_memory.json")
    )
    service.memory_manager.remember_user_fact("marker", "survives")
    view_model = DesktopShellViewModel(service)

    create_text = view_model.execute_command("create plan: forget everything you remember about me")
    create_diagnostics = view_model.state.diagnostics_text
    preview_text = view_model.preview_command("execute plan")

    assert "status: proposed" in create_text.lower()
    assert "- plan status: proposed" in create_diagnostics.lower()
    assert "- command id: planner.general_multi_step" in preview_text
    assert "- active plan id: plan-" in preview_text
    assert "- active plan status: proposed" in preview_text
    assert "- active step id: step-1" in preview_text
    assert "- active step capability: memory.forget_all" in preview_text
    assert "- operation id: none" in preview_text
    assert "- risk: confirmation_required" in preview_text
    assert "- requires_confirmation: yes" in preview_text
    assert "- executed through AppService: yes" in preview_text
    assert "- requires_network: no" in preview_text
    assert len(service.memory_manager.list_user_facts().entries) == 1
    assert service.memory_manager.recall_user_fact("marker").found is True


def test_desktop_shell_projects_russian_create_plan_forget_all_confirmation(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_russian_forget_all_memory.json")
    )
    service.memory_manager.remember_user_fact("marker", "survives")
    view_model = DesktopShellViewModel(service)

    preview_text = view_model.preview_command(
        "составь план: забудь всё, что ты обо мне помнишь"
    )
    create_text = view_model.execute_command(
        "составь план: забудь всё, что ты обо мне помнишь"
    )
    create_diagnostics = view_model.state.diagnostics_text
    execute_text = view_model.execute_command("execute plan")
    execute_diagnostics = view_model.state.diagnostics_text
    cancel_text = view_model.execute_command("cancel plan")
    cancel_diagnostics = view_model.state.diagnostics_text

    assert "- command id: planner.general_multi_step" in preview_text
    assert "- active step id: step-1" in preview_text
    assert "- active step capability: memory.forget_all" in preview_text
    assert "- operation id: none" in preview_text
    assert "- risk: confirmation_required" in preview_text
    assert "- requires_confirmation: yes" in preview_text
    assert "status: proposed" in create_text.lower()
    assert "- plan status: proposed" in create_diagnostics
    assert "- operation id: none" in create_diagnostics
    assert "- plan status: awaiting_confirmation" in execute_diagnostics
    assert "awaiting_confirmation" in execute_text
    assert "- operation status: awaiting_confirmation" in execute_diagnostics
    assert "- plan status: cancelled" in cancel_diagnostics
    assert "- requires confirmation: yes" not in cancel_diagnostics
    assert "Memory cleared" not in preview_text
    assert "Memory cleared" not in create_text
    assert "Memory cleared" not in execute_text
    assert "Memory cleared" not in cancel_text
    assert service.memory_manager.recall_user_fact("marker").found is True


def test_desktop_shell_awaiting_confirmation_plan_text_does_not_show_pending_step(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_awaiting_message_memory.json")
    )
    service.set_language_preference("english")
    service.memory_manager.remember_user_fact("marker", "survives")
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("create plan: forget everything you remember about me")
    text = view_model.execute_command("execute plan")
    diagnostics = view_model.state.diagnostics_text

    assert "- plan status: awaiting_confirmation" in diagnostics
    assert "- requires confirmation: yes" in diagnostics
    assert "awaiting_confirmation: awaiting_confirmation" in text
    assert "awaiting_confirmation: Step is pending." not in text
    assert service.memory_manager.recall_user_fact("marker").found is True


def test_desktop_shell_projects_local_write_execute_plan_with_real_service(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_planner_local_write_memory.json")
    )
    service.set_language_preference("english")
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("create plan: remember test word north")
    preview_text = view_model.preview_command("execute plan")

    assert "- command id: planner.general_multi_step" in preview_text
    assert "- active plan id: plan-" in preview_text
    assert "- active plan status: proposed" in preview_text
    assert "- active step id: step-1" in preview_text
    assert "- active step capability: memory.remember" in preview_text
    assert "- active step name: Remember fact" in preview_text
    assert "- operation id: none" in preview_text
    assert "- risk: local_write" in preview_text
    assert "- requires_confirmation: no" in preview_text
    assert "- executed through AppService: yes" in preview_text
    assert service.memory_manager.recall_user_fact("test word").found is False


def test_desktop_shell_projects_state_changing_execution_confirmation_and_operation(tmp_path):
    service = JarvisAppService(
        memory_manager=LocalMemoryManager(tmp_path / "desktop_task096_memory.json")
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("remember that task096marker is west")
    diagnostics = view_model.state.diagnostics_text

    assert "task096marker" in text
    assert "- command id: memory.remember" in diagnostics
    assert "- category: memory" in diagnostics
    assert "- risk: local_write" in diagnostics
    assert "- requires confirmation: no" in diagnostics
    assert "- operation id: op-" in diagnostics
    assert "- operation status: succeeded" in diagnostics
    assert service.memory_manager.recall_user_fact("task096marker").value == "west"


def test_desktop_shell_projects_microphone_status_confirmation_from_app_service(tmp_path):
    service = JarvisAppService(
        command_processor=FakeAppServiceCommandProcessor(),
        memory_manager=LocalMemoryManager(tmp_path / "desktop_microphone_status_memory.json"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command(
        "\u0441\u0442\u0430\u0442\u0443\u0441 \u043c\u0438\u043a\u0440\u043e\u0444\u043e\u043d\u0430"
    )
    diagnostics = view_model.state.diagnostics_text

    assert text
    assert "- command id: none" in diagnostics
    assert "- category: unknown" in diagnostics
    assert "- risk: unknown" in diagnostics
    assert "- requires confirmation: no" in diagnostics
    assert "- operation status: succeeded" in diagnostics
    assert service.memory_manager.recall_user_fact("task096marker").found is False


def test_desktop_shell_projects_unknown_fallback_confirmation_from_app_service(tmp_path):
    service = JarvisAppService(
        command_processor=FakeAppServiceCommandProcessor(),
        memory_manager=LocalMemoryManager(tmp_path / "desktop_unknown_fallback_memory.json"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command(
        "task096 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430"
    )
    diagnostics = view_model.state.diagnostics_text

    assert text
    assert "- command id: none" in diagnostics
    assert "- category: unknown" in diagnostics
    assert "- risk: unknown" in diagnostics
    assert "- requires confirmation: no" in diagnostics
    assert "- operation status: succeeded" in diagnostics
    assert service.memory_manager.recall_user_fact("task096marker").found is False


def test_desktop_shell_routes_russian_do_it_to_clarification_without_voice_fallback():
    service = JarvisAppService(command_processor=FakeAppServiceCommandProcessor())
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("\u0421\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e")
    diagnostics = view_model.state.diagnostics_text

    assert "- category: clarification" in diagnostics
    assert "- requires confirmation: no" in diagnostics
    assert "- operation status: awaiting_clarification" in diagnostics
    assert "\u044d\u0442\u043e" in text.casefold()
    assert "unsupported" not in text.casefold()
    assert "voice.confirmation" not in text.casefold()


def test_desktop_shell_clarification_confirmation_and_cancel_avoid_voice_fallback():
    service = JarvisAppService(command_processor=FakeAppServiceCommandProcessor())
    view_model = DesktopShellViewModel(service)
    first = view_model.execute_command("\u0421\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e")
    first_diagnostics = view_model.state.diagnostics_text

    confirm = view_model.execute_command("\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u044e")
    confirm_diagnostics = view_model.state.diagnostics_text
    cancel = view_model.execute_command("\u043e\u0442\u043c\u0435\u043d\u0430")
    cancel_diagnostics = view_model.state.diagnostics_text

    assert "- category: clarification" in confirm_diagnostics
    assert "- operation status: awaiting_clarification" in confirm_diagnostics
    assert "- category: clarification" in cancel_diagnostics
    assert "- operation status: cancelled" in cancel_diagnostics
    assert "voice.confirmation" not in confirm.casefold()
    assert "voice.confirmation" not in cancel.casefold()
    assert _operation_id_from_desktop_text(first_diagnostics) == _operation_id_from_desktop_text(confirm_diagnostics)
    assert _operation_id_from_desktop_text(confirm_diagnostics) == _operation_id_from_desktop_text(cancel_diagnostics)


def test_desktop_shell_atomically_replaces_multiturn_execution_projection():
    processor = FakeAppServiceCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)

    def submit(text):
        output = view_model.execute_command(text)
        view_model.refresh_application_activity()
        view_model.refresh_execution_history()
        view_model.refresh_workflow_history()
        return output, view_model.state

    _status_output, status_state = submit(
        "\u0441\u0442\u0430\u0442\u0443\u0441 app service"
    )
    status_operation_id = status_state.execution_metadata.operation_id

    assert status_state.execution_metadata.command_id == "app_service.status"
    assert status_state.execution_metadata.operation_status == "succeeded"
    assert status_state.execution_metadata.executed is True
    assert status_state.selected_history_id == status_operation_id

    clarification_output, clarification_state = submit(
        "\u0441\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e"
    )
    clarification_operation_id = (
        clarification_state.execution_metadata.operation_id
    )

    assert clarification_state.output_text == clarification_output
    assert clarification_state.current_turn_result.execution is (
        clarification_state.execution_metadata
    )
    assert clarification_state.execution_metadata.category == "clarification"
    assert (
        clarification_state.execution_metadata.operation_status
        == "awaiting_clarification"
    )
    assert clarification_state.execution_metadata.executed is False
    assert clarification_state.requires_clarification is True
    assert clarification_state.requires_confirmation is False
    assert clarification_state.clarification_question == clarification_output
    assert clarification_state.confirmation_prompt is None
    assert clarification_operation_id != status_operation_id
    assert "app_service.status" not in clarification_state.diagnostics_text
    assert status_operation_id not in clarification_state.diagnostics_text
    assert "- category: clarification" in clarification_state.diagnostics_text
    assert "- requires clarification: yes" in clarification_state.diagnostics_text
    assert (
        "- operation status: awaiting_clarification"
        in clarification_state.diagnostics_text
    )
    assert "- executed: no" in clarification_state.diagnostics_text
    assert clarification_state.selected_history_id == clarification_operation_id
    assert (
        "\u0441\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e"
        in clarification_state.selected_history_details_text
    )

    _confirm_output, confirm_state = submit("\u0434\u0430")

    assert confirm_state.execution_metadata.operation_id == clarification_operation_id
    assert (
        confirm_state.execution_metadata.operation_status
        == "awaiting_clarification"
    )
    assert confirm_state.execution_metadata.executed is False
    assert confirm_state.requires_clarification is True
    assert confirm_state.requires_confirmation is False
    assert confirm_state.selected_history_id == clarification_operation_id

    _cancel_output, cancel_state = submit("\u043e\u0442\u043c\u0435\u043d\u0430")

    assert cancel_state.execution_metadata.operation_id == clarification_operation_id
    assert cancel_state.execution_metadata.operation_status == "cancelled"
    assert cancel_state.execution_metadata.executed is False
    assert cancel_state.requires_clarification is False
    assert cancel_state.requires_confirmation is False
    assert cancel_state.clarification_question is None
    assert cancel_state.clarification_options == ()
    assert cancel_state.confirmation_prompt is None
    assert cancel_state.selected_history_id == clarification_operation_id

    _unsupported_output, unsupported_state = submit(
        "\u0443\u0434\u0430\u043b\u0438 \u044d\u0442\u043e"
    )
    unsupported_operation_id = unsupported_state.execution_metadata.operation_id

    assert unsupported_state.execution_metadata.category == "unsupported"
    assert unsupported_state.execution_metadata.executed is False
    assert unsupported_state.requires_clarification is False
    assert unsupported_state.requires_confirmation is False
    assert unsupported_state.clarification_question is None
    assert unsupported_state.confirmation_prompt is None
    assert unsupported_operation_id != clarification_operation_id
    assert clarification_operation_id not in unsupported_state.diagnostics_text
    assert unsupported_state.selected_history_id == unsupported_operation_id

    _targetless_confirm_output, targetless_confirm_state = submit("\u0434\u0430")
    targetless_operation_id = (
        targetless_confirm_state.execution_metadata.operation_id
    )

    assert targetless_operation_id != unsupported_operation_id
    assert targetless_confirm_state.execution_metadata.category == "clarification"
    assert (
        targetless_confirm_state.execution_metadata.operation_status
        == "awaiting_clarification"
    )
    assert targetless_confirm_state.execution_metadata.executed is False
    assert targetless_confirm_state.requires_clarification is True
    assert targetless_confirm_state.requires_confirmation is False
    assert targetless_confirm_state.confirmation_prompt is None
    assert "unsupported" not in targetless_confirm_state.diagnostics_text
    assert targetless_confirm_state.selected_history_id == targetless_operation_id
    assert processor.calls == [
        "\u0441\u0442\u0430\u0442\u0443\u0441 app service"
    ]


def test_desktop_shell_clears_execution_projection_for_conversation_turn():
    processor = FakeAppServiceCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("\u0441\u0442\u0430\u0442\u0443\u0441 app service")
    execution_state = view_model.state
    execution_operation_id = execution_state.execution_metadata.operation_id

    response = view_model.execute_command("\u043f\u0440\u0438\u0432\u0435\u0442")
    conversation_state = view_model.state

    assert conversation_state.output_text == response
    assert conversation_state.current_turn_result.execution is None
    assert conversation_state.execution_metadata is None
    assert conversation_state.requires_clarification is False
    assert conversation_state.requires_confirmation is False
    assert conversation_state.clarification_question is None
    assert conversation_state.clarification_options == ()
    assert conversation_state.confirmation_prompt is None
    assert conversation_state.cognitive_session_id is not None
    assert "- route: conversation" in conversation_state.diagnostics_text
    assert "app_service.status" not in conversation_state.diagnostics_text
    assert execution_operation_id not in conversation_state.diagnostics_text

    view_model.execute_command(
        "\u0441\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e"
    )
    clarification_state = view_model.state

    assert (
        clarification_state.cognitive_session_id
        == conversation_state.cognitive_session_id
    )
    assert clarification_state.execution_metadata.category == "clarification"
    assert clarification_state.requires_clarification is True
    assert "app_service.status" not in clarification_state.diagnostics_text
    assert execution_operation_id not in clarification_state.diagnostics_text
    assert processor.calls == [
        "\u0441\u0442\u0430\u0442\u0443\u0441 app service"
    ]


def test_chat_first_state_projects_injected_session_and_persistence_status():
    service = FakeAppService()
    service.chat_status = AppDesktopChatStatus(
        session_id="cog-session-resumed",
        session_state="active",
        turn_count=6,
        resumable=True,
        response_state="idle",
        response_source="none",
        retry_available=False,
        retry_reason="not_available",
        persistence_state="ready",
        persistence_code="ready",
    )

    view_model = DesktopShellViewModel(
        service,
        cognitive_session_id="cog-session-resumed",
        initial_chat_status=service.chat_status,
    )

    assert view_model.state.cognitive_session_id == "cog-session-resumed"
    assert view_model.state.chat_response_state == "idle"
    assert view_model.state.chat_retry_available is False
    assert "cog-session-resumed" in view_model.state.chat_status_text
    assert "ready" in view_model.state.chat_status_text


def test_chat_retry_is_explicit_reuses_same_session_and_does_not_create_backlog():
    service = FakeAppService()
    service.resumable_session_id = "cog-session-active"
    service.chat_status = AppDesktopChatStatus(
        session_id="cog-session-active",
        session_state="active",
        turn_count=2,
        resumable=True,
        response_state="fallback",
        response_source="compatibility",
        retry_available=True,
        retry_reason="provider_unavailable",
        persistence_state="ready",
        persistence_code="ready",
    )
    view_model = DesktopShellViewModel(service)

    view_model.execute_command("Что такое Земля?")
    first_state = view_model.state
    output = view_model.retry_last_chat_turn()

    assert first_state.chat_retry_available is True
    assert output == "processed: Что такое Земля?"
    assert service.desktop_turn_calls == [
        ("Что такое Земля?", AppCommandSource.DESKTOP_UI, "cog-session-active"),
        ("Что такое Земля?", AppCommandSource.DESKTOP_UI, "cog-session-active"),
    ]


def test_clear_output_resets_visible_chat_status_with_retry_projection():
    service = FakeAppService()
    service.chat_status = AppDesktopChatStatus(
        session_id="cog-session-active",
        session_state="active",
        turn_count=2,
        resumable=True,
        response_state="ready",
        response_source="groq",
        retry_available=True,
        retry_reason="user_requested",
        persistence_state="ready",
        persistence_code="ready",
    )
    view_model = DesktopShellViewModel(
        service,
        cognitive_session_id="cog-session-active",
        initial_chat_status=service.chat_status,
    )
    view_model.execute_command("Что такое Земля?")

    view_model.clear_output()

    assert view_model.state.chat_response_state == "idle"
    assert view_model.state.chat_retry_available is False
    assert "response state: idle" in view_model.state.chat_status_text
    assert "retry available: no" in view_model.state.chat_status_text


def test_desktop_shell_non_gui_clarification_control_smoke_matches_app_service():
    processor = FakeAppServiceCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    view_model = DesktopShellViewModel(service)
    commands = (
        "\u0421\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e.",
        "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u044e.",
        "\u043e\u0442\u043c\u0435\u043d\u0430",
        "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u044e.",
        "\u0421\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e.",
        "\u043e\u0442\u043c\u0435\u043d\u0430",
        "\u0443\u0434\u0430\u043b\u0438 \u044d\u0442\u043e",
    )

    desktop_records = []
    for command in commands:
        output = view_model.execute_command(command)
        desktop_records.append((output, view_model.state.diagnostics_text))
    desktop_outputs = tuple(output for output, _diagnostics in desktop_records)
    desktop_diagnostics = tuple(
        diagnostics for _output, diagnostics in desktop_records
    )

    assert [_desktop_field(text, "category") for text in desktop_diagnostics] == [
        "clarification",
        "clarification",
        "clarification",
        "clarification",
        "clarification",
        "clarification",
        "unsupported",
    ]
    assert [_desktop_field(text, "operation status") for text in desktop_diagnostics] == [
        "awaiting_clarification",
        "awaiting_clarification",
        "cancelled",
        "awaiting_clarification",
        "awaiting_clarification",
        "cancelled",
        "succeeded",
    ]
    assert _operation_id_from_desktop_text(desktop_diagnostics[0]) == _operation_id_from_desktop_text(desktop_diagnostics[1])
    assert _operation_id_from_desktop_text(desktop_diagnostics[1]) == _operation_id_from_desktop_text(desktop_diagnostics[2])
    assert _operation_id_from_desktop_text(desktop_diagnostics[3]) != _operation_id_from_desktop_text(desktop_diagnostics[0])
    assert _operation_id_from_desktop_text(desktop_diagnostics[4]) != _operation_id_from_desktop_text(desktop_diagnostics[3])
    for text in desktop_diagnostics:
        assert "- executed: yes" not in text
        assert "- response executed as command: no" in text
        assert "voice.confirmation" not in text.casefold()
        assert "legacy_commandprocessor_fallback" not in text
    assert processor.calls == []

    app_processor = FakeAppServiceCommandProcessor()
    app_service = JarvisAppService(command_processor=app_processor)
    app_results = tuple(
        app_service.execute_contract(command, AppCommandSource.TEST)
        for command in commands
    )

    assert [result.category for result in app_results] == [
        _desktop_field(text, "category") for text in desktop_diagnostics
    ]
    assert [result.operation_status for result in app_results] == [
        _desktop_field(text, "operation status") for text in desktop_diagnostics
    ]
    assert all(result.executed is False for result in app_results)
    assert all(result.response_executed_as_command is False for result in app_results)
    assert all(result.requires_confirmation is False for result in app_results)
    assert app_processor.calls == []


def test_desktop_shell_renders_local_tts_diagnostics_without_confirmation():
    view_model, backend, _processor = make_local_tts_desktop_view_model(available=True)

    text = view_model.execute_command(LOCAL_TTS_STATUS_COMMAND)
    diagnostics = view_model.state.diagnostics_text

    assert text
    assert "- ok: yes" in diagnostics
    assert "- command id: voice.output.local.status" in diagnostics
    assert "- category: voice" in diagnostics
    assert "- risk: read_only" in diagnostics
    assert "- requires confirmation: no" in diagnostics
    assert "- operation status: succeeded" in diagnostics
    assert "- network may be used: no" in diagnostics
    assert "confirmation_required" not in diagnostics
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_desktop_shell_renders_local_tts_enable_failure_as_failed_not_pending():
    view_model, backend, processor = make_local_tts_desktop_view_model(available=False)

    text = view_model.execute_command(LOCAL_TTS_ENABLE_COMMAND)
    diagnostics = view_model.state.diagnostics_text

    assert text
    assert "- ok: no" in diagnostics
    assert "- command id: voice.output.windows_local.enable" in diagnostics
    assert "- category: voice" in diagnostics
    assert "- risk: local_runtime" in diagnostics
    assert "- requires confirmation: no" in diagnostics
    assert "- operation status: failed" in diagnostics
    assert "- error: voice.output.windows_local.unavailable" in diagnostics
    assert "confirmation_required" not in diagnostics
    assert processor.voice_output_manager.mode == "OFF"
    assert backend.diagnostics_calls == 1
    assert backend.synthesis_calls == []


def test_desktop_shell_renders_local_tts_test_success_without_raw_audio_text_metadata():
    view_model, backend, _processor = make_local_tts_desktop_view_model(available=True)
    view_model.execute_command(LOCAL_TTS_ENABLE_COMMAND)

    text = view_model.execute_command(LOCAL_TTS_TEST_COMMAND)
    diagnostics = view_model.state.diagnostics_text

    assert text
    assert "- ok: yes" in diagnostics
    assert "- command id: voice.output.spoken" in diagnostics
    assert "- category: voice" in diagnostics
    assert "- risk: local_runtime" in diagnostics
    assert "- requires confirmation: no" in diagnostics
    assert "- operation status: succeeded" in diagnostics
    assert len(backend.synthesis_calls) == 1
    spoken_text, _mode = backend.synthesis_calls[0]
    metadata_lines = [
        line
        for line in diagnostics.splitlines()
        if line.startswith(("- command id:", "- category:", "- risk:", "- operation"))
    ]
    assert spoken_text not in "\n".join(metadata_lines)


def test_desktop_shell_renders_positive_awaiting_confirmation_result_without_execution():
    class AwaitingConfirmationService(FakeAppService):
        def execute_command(self, text, source):
            self.execute_calls.append((text, source))
            return FakeExecutionResult(
                output_text="confirmation required",
                registry_match_id="memory.forget_all",
                category="memory",
                risk_level="confirmation_required",
                requires_confirmation=True,
                operation_id="op-awaiting",
                operation_status="awaiting_confirmation",
                awaiting_confirmation=True,
            )

    service = AwaitingConfirmationService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("forget all memory")
    diagnostics = view_model.state.diagnostics_text

    assert text == "confirmation required"
    assert "- command id: memory.forget_all" in diagnostics
    assert "- risk: confirmation_required" in diagnostics
    assert "- requires confirmation: yes" in diagnostics
    assert "- operation id: op-awaiting" in diagnostics
    assert "- operation status: awaiting_confirmation" in diagnostics
    assert view_model.state.execution_metadata.operation_id == "op-awaiting"
    assert view_model.state.requires_confirmation is True
    assert view_model.state.requires_clarification is False
    assert view_model.state.confirmation_prompt == text
    assert view_model.state.clarification_question is None
    assert view_model.state.clarification_options == ()
    assert service.execute_calls == [("forget all memory", AppCommandSource.DESKTOP_UI)]


def test_preview_of_groq_real_request_marks_network_risk_privacy_without_execution():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.preview_command("groq реальный запрос: test")

    assert "- command id: ai_provider.groq.real_request" in text
    assert "- risk: network_explicit" in text
    assert "- requires_network: yes" in text
    assert "- requires_privacy_check: yes" in text
    assert service.execute_calls == []


def test_execute_command_calls_app_service_execute_only():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("статус ai")

    assert service.execute_calls == [("статус ai", AppCommandSource.DESKTOP_UI)]
    assert text == "processed: статус ai"
    assert "Desktop shell execution:" not in text
    assert "- requires confirmation: no" in view_model.state.diagnostics_text


def test_execute_command_displays_clarification_options():
    @dataclass(frozen=True)
    class Option:
        label_ru: str

    class ClarifyingService(FakeAppService):
        def execute_command(self, text, source):
            self.execute_calls.append((text, source))
            return FakeExecutionResult(
                ok=True,
                output_text="Требуется уточнение:\nКакой статус проверить?\n- системы\n- AI",
                registry_match_id=None,
                category="clarification",
                risk_level="read_only",
                requires_clarification=True,
                clarification_question="Какой статус проверить?",
                clarification_options=(Option("системы"), Option("AI")),
            )

    service = ClarifyingService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("покажи статус")

    assert "Требуется уточнение:" in text
    assert "Какой статус проверить?" in text
    assert "- системы" in text
    assert "- AI" in text
    assert view_model.state.requires_clarification is True
    assert view_model.state.requires_confirmation is False
    assert (
        view_model.state.clarification_question
        == view_model.state.execution_metadata.clarification_question
    )
    assert len(view_model.state.clarification_options) == 2
    assert tuple(
        option.label_ru for option in view_model.state.clarification_options
    ) == tuple(
        option.label_ru
        for option in view_model.state.execution_metadata.clarification_options
    )
    assert view_model.state.confirmation_prompt is None


def test_execute_command_wraps_output_safely():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.execute_command("api key sk-test-1234567890secret")

    assert "sk-test-1234567890secret" not in text
    assert "[REDACTED]" in text
    assert "Desktop shell execution:" not in text


def test_view_model_uses_app_service_resumable_session_when_id_is_not_explicit():
    service = FakeAppService()
    service.resumable_session_id = "cog-session-resumed"

    view_model = DesktopShellViewModel(service)

    assert view_model.state.cognitive_session_id == "cog-session-resumed"
    assert service.resumable_session_calls == 1


def test_view_model_explicit_session_id_has_priority_without_resume_lookup():
    service = FakeAppService()
    service.resumable_session_id = "cog-session-resumed"

    view_model = DesktopShellViewModel(
        service,
        cognitive_session_id="cog-session-explicit",
    )

    assert view_model.state.cognitive_session_id == "cog-session-explicit"
    assert service.resumable_session_calls == 0


def test_process_one_shot_voice_request_uses_app_service_only():
    service = FakeAppService()
    view_model = DesktopShellViewModel(
        service,
        cognitive_session_id="cog-session-desktop-test",
    )

    text = view_model.process_one_shot_voice_request()

    assert service.voice_calls == [AppCommandSource.DESKTOP_UI]
    assert service.execute_calls == []
    assert text == "processed voice command"
    assert "Голосовой запрос Desktop Shell:" in view_model.state.diagnostics_text
    assert "- распознавание: да" in view_model.state.diagnostics_text
    assert "- распознано:" in view_model.state.diagnostics_text
    assert "- сырое аудио отправлено наружу: нет" in view_model.state.diagnostics_text
    assert "- route: conversation" in view_model.state.diagnostics_text
    assert (
        "- cognitive session id: cog-session-desktop-test"
        in view_model.state.diagnostics_text
    )


def test_process_one_shot_voice_request_wraps_failure_safely():
    class FailingVoiceService(FakeAppService):
        def process_one_shot_voice_request(self, source, *, session_id=None):
            self.voice_calls.append(source)
            return FakeVoiceResult(
                ok=False,
                voice_capture_succeeded=False,
                recognition_succeeded=False,
                recognized_text=None,
                text_processing_succeeded=False,
                result_type="voice_recognition_failed",
                category=None,
                error_code="vosk_runtime_unavailable",
                user_message="api key sk-test-1234567890secret failed",
                text_result=None,
            )

    view_model = DesktopShellViewModel(FailingVoiceService())

    text = view_model.process_one_shot_voice_request()

    assert "vosk_runtime_unavailable" in view_model.state.diagnostics_text
    assert "sk-test-1234567890secret" not in text
    assert "[REDACTED]" in text
    assert view_model.state.last_error == text


def test_process_one_shot_voice_request_renders_sanitized_microphone_failure():
    recognizer = FakeOneShotRecognition(
        OneShotVoskRealRecognitionResult(
            allowed=False,
            completed=False,
            blocked=True,
            recognized_text=None,
            capture_seconds=0,
            reasons=[RAW_MICROPHONE_ERROR],
            next_steps=["Проверьте микрофон."],
        )
    )
    service = JarvisAppService(one_shot_voice_recognition=recognizer)
    view_model = DesktopShellViewModel(service)

    text = view_model.process_one_shot_voice_request()

    assert "- result type: voice_recognition_blocked" in view_model.state.diagnostics_text
    assert "- требуется подтверждение: нет" in view_model.state.diagnostics_text
    assert "Не удалось получить доступ к микрофону." in text
    assert "PaErrorCode" not in text
    assert "MME error" not in text
    assert "Error querying device" not in text
    assert view_model.state.last_error == text


def test_process_one_shot_voice_request_formats_cyrillic_recognition():
    service = FakeAppService()
    service.voice_result = FakeVoiceResult(
        recognized_text="статус app service",
        text_result=FakeExecutionResult(output_text="Статус готов."),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.process_one_shot_voice_request()

    assert "- распознано: статус app service" in view_model.state.diagnostics_text
    assert text == "Статус готов."
    assert "Recognized text" not in text


def test_process_one_shot_voice_request_displays_safe_normalization():
    service = FakeAppService()
    service.voice_result = FakeVoiceResult(
        recognized_text="статус система",
        normalized_text="статус системы",
        normalization_applied=True,
        normalization_rules=("normalize_system_status_phrase",),
        text_result=FakeExecutionResult(output_text="JARVIS status: ready"),
    )
    view_model = DesktopShellViewModel(service)

    text = view_model.process_one_shot_voice_request()

    assert "Распознано: статус система" in view_model.state.preview_text
    assert "Нормализовано: статус системы" in view_model.state.preview_text
    assert text == "JARVIS status: ready"


def test_execute_dialog_greeting_with_real_service_is_safe():
    view_model = DesktopShellViewModel(JarvisAppService())

    text = view_model.execute_command("диалог: привет")

    assert "Desktop shell execution:" not in text
    assert "Привет, Исмаил" in text
    assert "providers called:" not in text
    assert "network used:" not in text
    assert "command executed:" not in text
    assert "microphone/TTS started:" not in text
    assert "- route: conversation" in view_model.state.diagnostics_text
    assert view_model.state.cognitive_session_id is not None


def test_clear_output_works_without_execution():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)

    text = view_model.clear_output()

    assert "Output cleared" in text
    assert view_model.state.preview_text == "Command preview cleared."
    assert service.execute_calls == []


def test_launch_function_handles_unavailable_tkinter_gracefully(monkeypatch):
    def unavailable_shell(_view_model):
        raise ImportError("tkinter unavailable")

    monkeypatch.setattr(desktop_shell, "JarvisDesktopShell", unavailable_shell)
    monkeypatch.setattr(
        desktop_shell,
        "create_default_desktop_app_service",
        lambda: FakeAppService(),
    )

    assert desktop_shell.launch_desktop_shell() is False


def test_launch_function_uses_default_desktop_app_service_factory(monkeypatch):
    created_service = FakeAppService()
    calls = []

    def create_service():
        calls.append("factory")
        return created_service

    def unavailable_shell(view_model):
        assert view_model.app_service is created_service
        raise ImportError("tkinter unavailable")

    monkeypatch.setattr(
        desktop_shell,
        "create_default_desktop_app_service",
        create_service,
        raising=False,
    )
    monkeypatch.setattr(desktop_shell, "JarvisDesktopShell", unavailable_shell)

    assert desktop_shell.launch_desktop_shell() is False
    assert calls == ["factory"]


def test_no_secrets_in_view_model_outputs():
    service = FakeAppService()
    view_model = DesktopShellViewModel(service)
    secret = "sk-test-1234567890secret"

    preview = view_model.preview_command(f"статус ai api_key={secret}")
    execute = view_model.execute_command(f"статус ai token={secret}")

    assert secret not in preview
    assert secret not in execute


def test_status_and_capabilities_mention_secure_key_storage_safely():
    view_model = DesktopShellViewModel(JarvisAppService())
    secret = "dummy-test-key-for-storage-only"

    status = view_model.safe_status_text_ru()
    capabilities = view_model.ui_capabilities_text_ru()

    assert "secure key storage foundation: available" in status
    assert "secure key storage foundation available" in capabilities
    assert "future secure key input UI planned" in capabilities
    assert secret not in status
    assert secret not in capabilities


class InteractionTestRoot(FakeRoot):
    def __init__(self):
        super().__init__()
        self.main_thread_id = current_thread().ident
        self.after_callbacks = []
        self.after_calls = []
        self.protocol_calls = []
        self.destroy_calls = 0
        self.destroyed = False

    def after(self, delay, callback):
        assert current_thread().ident == self.main_thread_id
        assert not self.destroyed
        callback_id = f"after-{len(self.after_calls) + 1}"
        self.after_calls.append((callback_id, delay, current_thread().ident))
        self.after_callbacks.append((callback_id, callback))
        return callback_id

    def after_cancel(self, callback_id):
        assert current_thread().ident == self.main_thread_id
        self.after_callbacks = [item for item in self.after_callbacks if item[0] != callback_id]

    def protocol(self, name, callback):
        self.protocol_calls.append((name, callback))

    def destroy(self):
        assert current_thread().ident == self.main_thread_id
        self.destroy_calls += 1
        self.destroyed = True

    def run_next(self):
        _callback_id, callback = self.after_callbacks.pop(0)
        callback()


class FakeButton:
    def __init__(self):
        self.state = "normal"
        self.configure_threads = []

    def configure(self, **kwargs):
        self.configure_threads.append(current_thread().ident)
        if "state" in kwargs:
            self.state = kwargs["state"]


_INTERACTION_TEST_WORKERS = []


@pytest.fixture(autouse=True)
def _stop_interaction_test_workers():
    yield
    while _INTERACTION_TEST_WORKERS:
        worker = _INTERACTION_TEST_WORKERS.pop()
        worker.request_cancel()
        worker.request_shutdown()
        if not worker.join(0.05) and worker.wait_for_completion(2.0):
            worker.take_completion()
        assert worker.join(2.0)


def interaction_shell(service=None):
    service = service or FakeAppService()
    shell = JarvisDesktopShell.__new__(JarvisDesktopShell)
    shell.view_model = DesktopShellViewModel(service)
    shell.root = InteractionTestRoot()
    shell.tk = FakeTk
    shell.interaction_worker = DesktopInteractionWorker()
    _INTERACTION_TEST_WORKERS.append(shell.interaction_worker)
    shell._main_thread_id = current_thread().ident
    shell._interaction_after_id = None
    shell._close_requested = False
    shell._destroyed = False
    shell.execute_button = FakeButton()
    shell.voice_button = FakeButton()
    shell.workflow_resume_button = FakeButton()
    shell.interaction_cancel_button = FakeButton()
    shell.chat_retry_button = FakeButton()
    shell._render_threads = []
    def render_state():
        shell._render_threads.append(current_thread().ident)
        shell._render_interaction_controls(shell.view_model.state)
    shell._render_state = render_state
    shell._command_input = lambda: "typed secret"
    shell._confirm_workflow_resume = lambda _text: True
    return shell, service


def test_chat_retry_control_is_disabled_while_worker_busy_or_retry_is_unavailable():
    shell, _service = interaction_shell()
    shell.view_model.state = shell.view_model._replace(chat_retry_available=True)

    shell._render_interaction_controls(shell.view_model.state)
    assert shell.chat_retry_button.state == "normal"

    shell.view_model.state = shell.view_model._replace(interaction_busy=True)
    shell._render_interaction_controls(shell.view_model.state)
    assert shell.chat_retry_button.state == "disabled"

    shell.view_model.state = shell.view_model._replace(
        interaction_busy=False,
        chat_retry_available=False,
    )
    shell._render_interaction_controls(shell.view_model.state)
    assert shell.chat_retry_button.state == "disabled"


def test_chat_retry_gui_uses_same_worker_and_rejects_duplicate_submission():
    service = FakeAppService()
    service.resumable_session_id = "cog-session-active"
    service.chat_status = AppDesktopChatStatus(
        session_id="cog-session-active",
        session_state="active",
        turn_count=2,
        resumable=True,
        response_state="fallback",
        response_source="compatibility",
        retry_available=True,
        retry_reason="provider_unavailable",
        persistence_state="ready",
        persistence_code="ready",
    )
    shell, _service = interaction_shell(service)
    shell.view_model.execute_command("Что такое Земля?")
    service.desktop_turn_calls.clear()
    service.execute_calls.clear()

    shell._on_chat_retry()
    shell._on_chat_retry()
    _drive_shell_until_idle(shell)

    assert service.desktop_turn_calls == [
        ("Что такое Земля?", AppCommandSource.DESKTOP_UI, "cog-session-active")
    ]
    assert len(service.execute_calls) == 1
    assert shell.view_model.state.interaction_busy is False


def _drive_shell_until_idle(shell, limit=50):
    for _index in range(limit):
        if shell.root.after_callbacks:
            shell.root.run_next()
        if not shell.view_model.state.interaction_busy:
            return
        shell.interaction_worker.wait_for_completion(0.05)
    raise AssertionError("interaction did not become idle")


def test_typed_gui_handler_returns_while_appservice_is_blocked_and_runs_off_main_thread():
    entered = Event()
    release = Event()
    call_threads = []

    class BlockingService(FakeAppService):
        def handle_desktop_turn(self, text, source, *, session_id=None):
            call_threads.append(current_thread().ident)
            entered.set()
            release.wait(2.0)
            return super().handle_desktop_turn(text, source, session_id=session_id)

    shell, _service = interaction_shell(BlockingService())
    main_thread_id = current_thread().ident

    shell._on_execute()

    assert entered.wait(2.0)
    assert shell.view_model.state.interaction_busy is True
    assert call_threads[0] != main_thread_id
    assert shell.execute_button.state == "disabled"
    assert shell.voice_button.state == "disabled"
    assert shell.workflow_resume_button.state == "disabled"
    assert shell.interaction_cancel_button.state == "normal"
    release.set()
    _drive_shell_until_idle(shell)
    assert shell._render_threads and set(shell._render_threads) == {main_thread_id}
    shell._on_close()
    _drive_shell_until_idle(shell)


def test_unrelated_main_thread_callback_runs_while_operation_is_blocked():
    entered = Event()
    release = Event()
    unrelated = []

    class BlockingService(FakeAppService):
        def handle_desktop_turn(self, text, source, *, session_id=None):
            entered.set()
            release.wait(2.0)
            return super().handle_desktop_turn(text, source, session_id=session_id)

    shell, _service = interaction_shell(BlockingService())
    shell._on_execute()
    assert entered.wait(2.0)
    shell.root.after(0, lambda: unrelated.append(current_thread().ident))

    shell.root.run_next()
    shell.root.run_next()

    assert unrelated == [shell.root.main_thread_id]
    assert shell.view_model.state.interaction_busy is True
    release.set()
    _drive_shell_until_idle(shell)
    shell._on_close()


def test_voice_and_workflow_resume_share_injected_worker_and_busy_rejects_duplicate():
    shell, service = interaction_shell()
    worker = shell.interaction_worker

    shell._on_voice_once()
    duplicate = shell._submit_interaction("typed_turn", lambda _token: "duplicate")
    _drive_shell_until_idle(shell)
    assert duplicate.accepted is False
    assert service.voice_calls == [AppCommandSource.DESKTOP_UI]
    assert shell.interaction_worker is worker

    shell.view_model.state = shell.view_model._replace(
        selected_workflow_run=workflow_run(run_id="wf-one", resume_eligible=True),
        selected_workflow_run_id="wf-one",
        workflow_resume_available=True,
    )
    shell._on_workflow_resume()
    _drive_shell_until_idle(shell)
    assert service.workflow_resume_calls == ["wf-one"]
    assert shell.interaction_worker is worker
    shell._on_close()
    _drive_shell_until_idle(shell)


def test_interaction_cancel_projects_request_and_late_result_is_applied_once():
    entered = Event()
    release = Event()

    class BlockingService(FakeAppService):
        def handle_desktop_turn(self, text, source, *, session_id=None):
            entered.set()
            release.wait(2.0)
            return super().handle_desktop_turn(text, source, session_id=session_id)

    shell, service = interaction_shell(BlockingService())
    shell._on_execute()
    assert entered.wait(2.0)
    shell._on_interaction_cancel()

    assert shell.view_model.state.interaction_cancellation_requested is True
    release.set()
    _drive_shell_until_idle(shell)
    assert len(service.execute_calls) == 1
    assert shell.view_model.state.interaction_busy is False
    assert "успела завершиться" in shell.view_model.state.interaction_status_text
    shell._poll_interaction_completion()
    assert len(service.execute_calls) == 1
    shell._on_close()
    _drive_shell_until_idle(shell)


def test_cancel_after_published_completion_is_rejected_without_false_ui_projection():
    entered = Event()
    release = Event()

    class BlockingService(FakeAppService):
        def handle_desktop_turn(self, text, source, *, session_id=None):
            entered.set()
            assert release.wait(2.0)
            return super().handle_desktop_turn(text, source, session_id=session_id)

    shell, service = interaction_shell(BlockingService())
    shell._on_execute()
    try:
        assert entered.wait(2.0)
        release.set()
        assert shell.interaction_worker.wait_for_completion(2.0)

        published = shell.interaction_worker.snapshot()
        assert published.completion_pending is True
        assert published.cancellation_requested is False
        status_before_cancel = shell.view_model.state.interaction_status_text
        assert shell.interaction_cancel_button.state == "normal"

        shell._on_interaction_cancel()

        assert shell.view_model.state.interaction_cancellation_requested is False
        assert shell.view_model.state.interaction_status_text == status_before_cancel
        assert shell.interaction_cancel_button.state == "disabled"
        assert shell.view_model.state.interaction_busy is True
        assert len(service.execute_calls) == 1

        shell.root.run_next()

        assert shell.view_model.state.interaction_busy is False
        assert shell.view_model.state.interaction_cancellation_requested is False
        assert len(service.execute_calls) == 1
        output_after_poll = shell.view_model.state.output_text

        shell._poll_interaction_completion()

        assert shell.view_model.state.output_text == output_after_poll
        assert len(service.execute_calls) == 1
    finally:
        release.set()


def test_stale_completion_is_not_applied_and_failures_are_sanitized():
    shell, _service = interaction_shell()
    initial_output = shell.view_model.state.output_text
    shell.view_model.state = shell.view_model._replace(
        interaction_busy=True,
        active_interaction_id="desktop-interaction-current",
        active_interaction_kind="typed_turn",
    )

    assert shell._apply_interaction_completion(
        type("Completion", (), {"interaction_id": "desktop-interaction-stale"})()
    ) is False
    assert shell.view_model.state.output_text == initial_output

    shell.view_model.state = shell.view_model._replace(
        interaction_busy=False,
        active_interaction_id=None,
        active_interaction_kind=None,
    )
    submission = shell._submit_interaction(
        "typed_turn",
        lambda _token: (_ for _ in ()).throw(RuntimeError("C:\\private\\secret.txt token=abc")),
    )
    assert submission.accepted
    _drive_shell_until_idle(shell)
    safe = shell.view_model.state.output_text.lower()
    assert "secret.txt" not in safe
    assert "token=abc" not in safe
    assert "traceback" not in safe
    shell._on_close()
    _drive_shell_until_idle(shell)


def test_busy_close_waits_for_safe_stop_then_destroys_once_without_applying_result():
    entered = Event()
    release = Event()

    class BlockingService(FakeAppService):
        def handle_desktop_turn(self, text, source, *, session_id=None):
            entered.set()
            release.wait(2.0)
            return super().handle_desktop_turn(text, source, session_id=session_id)

    shell, _service = interaction_shell(BlockingService())
    original_output = shell.view_model.state.output_text
    shell._on_execute()
    assert entered.wait(2.0)
    try:
        shell._on_close()

        assert shell.root.destroy_calls == 0
        assert shell.view_model.state.shutdown_in_progress is True
        assert shell.view_model.state.interaction_cancellation_requested is True
        assert shell.interaction_cancel_button.state == "disabled"
        shell._on_close()
        assert len(_service.execute_calls) == 0
        assert shell.root.destroy_calls == 0
    finally:
        release.set()
    for _index in range(50):
        if shell.root.after_callbacks:
            shell.root.run_next()
        if shell.root.destroy_calls:
            break
        shell.interaction_worker.wait_for_completion(0.05)
    assert shell.root.destroy_calls == 1
    assert shell.view_model.state.output_text == original_output
    shell._on_close()
    assert shell.root.destroy_calls == 1


def test_idle_close_and_run_finally_stop_worker_without_closing_conversation():
    shell, service = interaction_shell()
    service.close_conversation_session = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("Desktop close must not close the conversation")
    )

    shell._on_close()
    for _index in range(10):
        if shell.root.after_callbacks:
            shell.root.run_next()
        if shell.root.destroy_calls:
            break
    assert shell.root.destroy_calls == 1
    assert shell.interaction_worker.snapshot().thread_alive is False


def test_mainloop_finally_stops_the_non_daemon_worker():
    shell, _service = interaction_shell()
    shell.root.mainloop = lambda: None

    shell.run()

    assert shell.interaction_worker.snapshot().lifecycle.value == "stopped"
    assert shell.interaction_worker.snapshot().thread_alive is False


def test_mainloop_finally_stops_with_pending_completion_and_discards_without_tk_apply():
    shell, service = interaction_shell()
    shell.root.mainloop = lambda: None
    shell._on_execute()
    assert shell.interaction_worker.wait_for_completion(2.0)
    output_before = shell.view_model.state.output_text
    render_count = len(shell._render_threads)
    after_count = len(shell.root.after_calls)
    runner = Thread(target=shell.run, name="task124-pending-fallback-test", daemon=False)

    runner.start()
    try:
        runner.join(2.0)
        assert runner.is_alive() is False
        assert shell.interaction_worker.snapshot().thread_alive is False
        assert shell.interaction_worker.take_completion() is None
        assert shell.view_model.state.output_text == output_before
        assert len(shell._render_threads) == render_count
        assert len(shell.root.after_calls) == after_count
        assert shell.root.destroy_calls == 0
        assert len(service.execute_calls) == 1
    finally:
        if runner.is_alive():
            shell.interaction_worker.take_completion()
            runner.join(2.0)
        assert runner.is_alive() is False


def test_mainloop_finally_waits_for_active_opaque_operation_then_discards_completion():
    entered = Event()
    release = Event()
    shutdown_requested = Event()

    class BlockingService(FakeAppService):
        def handle_desktop_turn(self, text, source, *, session_id=None):
            entered.set()
            release.wait(2.0)
            return super().handle_desktop_turn(text, source, session_id=session_id)

    shell, service = interaction_shell(BlockingService())
    shell.root.mainloop = lambda: None
    original_request_shutdown = shell.interaction_worker.request_shutdown

    def request_shutdown():
        snapshot = original_request_shutdown()
        shutdown_requested.set()
        return snapshot

    shell.interaction_worker.request_shutdown = request_shutdown
    shell._on_execute()
    assert entered.wait(2.0)
    output_before = shell.view_model.state.output_text
    render_count = len(shell._render_threads)
    after_count = len(shell.root.after_calls)
    runner = Thread(target=shell.run, name="task124-active-fallback-test", daemon=False)

    runner.start()
    try:
        assert shutdown_requested.wait(2.0)
        assert runner.is_alive() is True
        release.set()
        runner.join(2.0)
        assert runner.is_alive() is False
        assert shell.interaction_worker.snapshot().thread_alive is False
        assert shell.interaction_worker.take_completion() is None
        assert shell.view_model.state.output_text == output_before
        assert len(shell._render_threads) == render_count
        assert len(shell.root.after_calls) == after_count
        assert shell.root.destroy_calls == 0
        assert len(service.execute_calls) == 1
    finally:
        release.set()
        if runner.is_alive():
            assert shell.interaction_worker.wait_for_completion(2.0)
            shell.interaction_worker.take_completion()
            runner.join(2.0)
        assert runner.is_alive() is False


def test_shell_build_keeps_preview_and_execute_buttons_distinct():
    class Widget:
        created = []

        def __init__(self, *_args, **kwargs):
            self.text = kwargs.get("text")
            self.state = kwargs.get("state", "normal")
            self.value = kwargs.get("value", "")
            self.created.append(self)

        def __getattr__(self, _name):
            return lambda *_args, **_kwargs: None

        def get(self, *_args):
            return self.value

        def set(self, value):
            self.value = value

        def configure(self, **kwargs):
            self.state = kwargs.get("state", self.state)

    class Root(Widget):
        def protocol(self, name, callback):
            self.protocol_registration = (name, callback)

        def destroy(self):
            self.destroyed = True

    class TkModule:
        Tk = Root
        Frame = Label = Entry = Text = Listbox = Button = OptionMenu = PanedWindow = Menu = Widget
        StringVar = Widget

    shell = JarvisDesktopShell(DesktopShellViewModel(FakeAppService()), tk_module=TkModule)

    preview_buttons = [widget for widget in Widget.created if widget.text == "Preview"]
    assert len(preview_buttons) == 1
    assert shell.execute_button.text == "Отправить"
    assert shell.chat_retry_button.text == "Повторить запрос"
    assert shell.execute_button is not preview_buttons[0]
    assert shell.root.protocol_registration[0] == "WM_DELETE_WINDOW"
    shell._on_close()


def test_simulated_desktop_close_keeps_repository_backed_session_resumable(
    monkeypatch, tmp_path
):
    session_dir = tmp_path / "sessions"
    monkeypatch.setenv("JARVIS_COGNITIVE_SESSION_DIR", str(session_dir))
    factory_kwargs = {
        "environment": {
            "JARVIS_USER_DATA_DIR": str(tmp_path / "user-data-v1"),
            "JARVIS_COGNITIVE_SESSION_DIR": str(session_dir),
            "APPDATA": str(tmp_path / "roaming"),
        },
        "home": tmp_path / "home",
        "project_root": tmp_path / "project",
    }
    service = create_default_desktop_app_service(**factory_kwargs)
    shell, _ignored_service = interaction_shell(service)

    shell.view_model.execute_command("диалог: привет")
    session_id = shell.view_model.state.cognitive_session_id
    assert session_id is not None
    shell._on_close()
    assert shell.root.destroy_calls == 1

    restarted = DesktopShellViewModel(create_default_desktop_app_service(**factory_kwargs))
    assert restarted.state.cognitive_session_id == session_id
