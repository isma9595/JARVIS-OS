"""Safe tkinter desktop shell prototype for JARVIS.

The shell is a UI boundary only. It talks to JarvisAppService for status,
registry browsing, preview, and explicit execution.
"""

from dataclasses import dataclass
import re
from threading import Thread

from app.app_service import AppCommandSource, JarvisAppService


@dataclass(frozen=True)
class DesktopShellState:
    app_title: str
    status_text: str
    command_input: str
    preview_text: str
    output_text: str
    selected_category: str | None
    command_list_text: str
    history_list_text: str
    selected_history_id: str | None
    selected_history_details_text: str
    history_copy_text: str
    loaded_history_entries: tuple[object, ...]
    history_entries: tuple[object, ...]
    history_search_query: str
    history_status_filter: str
    history_result_count_text: str
    history_loading: bool
    history_load_error: str | None
    workflow_list_text: str
    selected_workflow_run_id: str | None
    workflow_details_text: str
    workflow_copy_text: str
    workflow_runs: tuple[object, ...]
    selected_workflow_run: object | None
    selected_workflow_steps: tuple[object, ...]
    workflow_loading: bool
    workflow_load_error: str | None
    workflow_resume_text: str
    workflow_resume_available: bool
    workflow_resume_in_progress: bool
    last_error: str | None
    ui_ready: bool
    safe_mode: bool


class DesktopShellViewModel:
    """Pure app-shell logic that can be tested without opening a GUI."""

    HISTORY_STATUS_FILTERS = (
        "All",
        "Successful",
        "Failed",
        "Denied",
        "Cancelled",
        "Preview",
    )

    def __init__(self, app_service: JarvisAppService):
        self.app_service = app_service
        self.state = self.build_initial_state()

    def build_initial_state(self) -> DesktopShellState:
        status_text = self.safe_status_text_ru()
        try:
            command_list_text = self._safe_text(self.app_service.list_commands(None))
        except Exception as exc:
            command_list_text = self._safe_error(exc)
        history = self._load_history_state()
        workflow = self._load_workflow_state()
        return DesktopShellState(
            app_title="JARVIS OS",
            status_text=status_text,
            command_input="",
            preview_text=(
                "Command preview is idle.\n"
                "Preview checks registry risk metadata and does not execute."
            ),
            output_text=(
                "Desktop shell ready.\n"
                "No command has been executed.\n"
                "Risky/network commands require explicit command text."
            ),
            selected_category=None,
            command_list_text=command_list_text,
            history_list_text=history["history_list_text"],
            selected_history_id=history["selected_history_id"],
            selected_history_details_text=history["selected_history_details_text"],
            history_copy_text=history["history_copy_text"],
            loaded_history_entries=history["loaded_history_entries"],
            history_entries=history["history_entries"],
            history_search_query=history["history_search_query"],
            history_status_filter=history["history_status_filter"],
            history_result_count_text=history["history_result_count_text"],
            history_loading=history["history_loading"],
            history_load_error=history["history_load_error"],
            workflow_list_text=workflow["workflow_list_text"],
            selected_workflow_run_id=workflow["selected_workflow_run_id"],
            workflow_details_text=workflow["workflow_details_text"],
            workflow_copy_text=workflow["workflow_copy_text"],
            workflow_runs=workflow["workflow_runs"],
            selected_workflow_run=workflow["selected_workflow_run"],
            selected_workflow_steps=workflow["selected_workflow_steps"],
            workflow_loading=workflow["workflow_loading"],
            workflow_load_error=workflow["workflow_load_error"],
            workflow_resume_text=workflow["workflow_resume_text"],
            workflow_resume_available=workflow["workflow_resume_available"],
            workflow_resume_in_progress=False,
            last_error=None,
            ui_ready=True,
            safe_mode=True,
        )

    def refresh_status(self) -> str:
        status_text = self.safe_status_text_ru()
        self.state = self._replace(status_text=status_text, last_error=None)
        return status_text

    def list_categories(self) -> str:
        try:
            return self._safe_text(self.app_service.categories_text_ru())
        except Exception as exc:
            return self._safe_error(exc)

    def list_commands(self, category: str | None = None) -> str:
        try:
            text = self.app_service.list_commands(category)
            self.state = self._replace(
                selected_category=category,
                command_list_text=self._safe_text(text),
                last_error=None,
            )
            return self.state.command_list_text
        except Exception as exc:
            error = self._safe_error(exc)
            self.state = self._replace(last_error=error)
            return error

    def preview_command(self, text: str) -> str:
        try:
            preview_text = self.app_service.preview_text_ru(text)
            self.state = self._replace(
                command_input=str(text or ""),
                preview_text=self._safe_text(preview_text),
                last_error=None,
            )
            return self.state.preview_text
        except Exception as exc:
            error = self._safe_error(exc)
            self.state = self._replace(preview_text=error, last_error=error)
            return error

    def execute_command(self, text: str) -> str:
        try:
            result = self.app_service.execute_command(
                text,
                AppCommandSource.DESKTOP_UI,
            )
            output_text = self._format_execution_result(result)
            self.state = self._replace(
                command_input=str(text or ""),
                output_text=output_text,
                last_error=None if getattr(result, "ok", False) else output_text,
            )
            return output_text
        except Exception as exc:
            error = self._safe_error(exc)
            self.state = self._replace(output_text=error, last_error=error)
            return error

    def process_one_shot_voice_request(self) -> str:
        try:
            result = self.app_service.process_one_shot_voice_request(
                AppCommandSource.DESKTOP_UI,
            )
            output_text = self._format_voice_result(result)
            recognized_text = getattr(result, "recognized_text", None)
            normalized_text = getattr(result, "normalized_text", None)
            normalization_applied = getattr(result, "normalization_applied", False)
            preview_lines = [
                "Одноразовый голосовой запрос завершён.",
                f"Распознано: {recognized_text or 'нет'}",
            ]
            if normalization_applied and normalized_text:
                preview_lines.append(f"Нормализовано: {normalized_text}")
            self.state = self._replace(
                command_input=str(recognized_text or self.state.command_input),
                preview_text="\n".join(preview_lines),
                output_text=output_text,
                last_error=None if getattr(result, "ok", False) else output_text,
            )
            return output_text
        except Exception as exc:
            error = self._safe_error(exc)
            self.state = self._replace(output_text=error, last_error=error)
            return error

    def clear_output(self) -> str:
        output_text = "Output cleared. No command has been executed by clear."
        self.state = self._replace(
            preview_text="Command preview cleared.",
            output_text=output_text,
            last_error=None,
        )
        return output_text

    def refresh_execution_history(self, limit: int | None = None) -> str:
        previous_selected_id = self.state.selected_history_id
        history = self._load_history_state(limit=limit)
        if history["last_error"] is None:
            history = self._apply_history_filters(
                loaded_entries=history["loaded_history_entries"],
                search_query=self.state.history_search_query,
                status_filter=self.state.history_status_filter,
                preferred_selected_id=previous_selected_id,
                last_error=None,
                history_load_error=None,
            )
        self.state = self._replace(
            history_list_text=history["history_list_text"],
            selected_history_id=history["selected_history_id"],
            selected_history_details_text=history["selected_history_details_text"],
            history_copy_text=history["history_copy_text"],
            loaded_history_entries=history["loaded_history_entries"],
            history_entries=history["history_entries"],
            history_search_query=history["history_search_query"],
            history_status_filter=history["history_status_filter"],
            history_result_count_text=history["history_result_count_text"],
            history_loading=history["history_loading"],
            history_load_error=history["history_load_error"],
            last_error=history["last_error"],
        )
        return self.state.history_list_text

    def select_history_entry(self, index: int | str | None) -> str:
        try:
            selected_index = int(index)
        except (TypeError, ValueError):
            selected_index = -1
        entries = self.state.history_entries
        if selected_index < 0 or selected_index >= len(entries):
            details = "Execution history entry details:\n- no entry selected"
            self.state = self._replace(
                selected_history_id=None,
                selected_history_details_text=details,
                history_copy_text="",
                last_error=None,
            )
            return details
        entry = entries[selected_index]
        details = self._history_entry_details(entry)
        self.state = self._replace(
            selected_history_id=getattr(entry, "entry_id", None),
            selected_history_details_text=details,
            history_copy_text=details,
            last_error=None,
        )
        return details

    def selected_history_copy_text(self) -> str:
        if not self.state.selected_history_id:
            return ""
        text = self.state.history_copy_text or self.state.selected_history_details_text
        return self._safe_text(text)

    def refresh_workflow_history(self, limit: int | None = None) -> str:
        previous_selected_id = self.state.selected_workflow_run_id
        workflow = self._load_workflow_state(
            limit=limit,
            preferred_selected_id=previous_selected_id,
        )
        self.state = self._replace(
            workflow_list_text=workflow["workflow_list_text"],
            selected_workflow_run_id=workflow["selected_workflow_run_id"],
            workflow_details_text=workflow["workflow_details_text"],
            workflow_copy_text=workflow["workflow_copy_text"],
            workflow_runs=workflow["workflow_runs"],
            selected_workflow_run=workflow["selected_workflow_run"],
            selected_workflow_steps=workflow["selected_workflow_steps"],
            workflow_loading=workflow["workflow_loading"],
            workflow_load_error=workflow["workflow_load_error"],
            workflow_resume_text=workflow["workflow_resume_text"],
            workflow_resume_available=workflow["workflow_resume_available"],
            workflow_resume_in_progress=False,
            last_error=workflow["last_error"],
        )
        return self.state.workflow_list_text

    def select_workflow_run(self, index: int | str | None) -> str:
        try:
            selected_index = int(index)
        except (TypeError, ValueError):
            selected_index = -1
        runs = self.state.workflow_runs
        if selected_index < 0 or selected_index >= len(runs):
            details = "Workflow run details:\n- Select a workflow run to view its steps."
            self.state = self._replace(
                selected_workflow_run_id=None,
                workflow_details_text=details,
                workflow_copy_text="",
                selected_workflow_run=None,
                selected_workflow_steps=(),
                workflow_resume_text="Resume unavailable: no workflow run selected.",
                workflow_resume_available=False,
                last_error=None,
            )
            return details
        run = runs[selected_index]
        run_id = getattr(run, "run_id", None) or getattr(run, "operation_id", None)
        details = self._load_workflow_details_text(run_id)
        self.state = self._replace(
            selected_workflow_run_id=str(run_id or ""),
            workflow_details_text=details["workflow_details_text"],
            workflow_copy_text=details["workflow_copy_text"],
            selected_workflow_run=details["selected_workflow_run"],
            selected_workflow_steps=details["selected_workflow_steps"],
            workflow_load_error=details["workflow_load_error"],
            workflow_resume_text=details["workflow_resume_text"],
            workflow_resume_available=details["workflow_resume_available"],
            last_error=details["last_error"],
        )
        return self.state.workflow_details_text

    def selected_workflow_copy_text(self) -> str:
        if not self.state.selected_workflow_run_id or self.state.workflow_load_error:
            return ""
        text = self.state.workflow_copy_text or self.state.workflow_details_text
        return self._safe_text(text)

    def workflow_resume_confirmation_text(self) -> str:
        run = self.state.selected_workflow_run
        if run is None or not self.state.workflow_resume_available:
            return self.state.workflow_resume_text
        run_id = getattr(run, "run_id", None) or getattr(run, "operation_id", None) or "unknown"
        step_id = getattr(run, "resume_step_id", None) or "first unfinished step"
        return self._safe_text(
            "\n".join(
                [
                    "Resume workflow run?",
                    f"- run id: {run_id}",
                    "- completed steps will not be rerun",
                    f"- resume from: {step_id}",
                    "- a distinct resumed attempt will be created",
                ]
            )
        )

    def resume_selected_workflow_run(self, *, confirmed: bool) -> str:
        if self.state.workflow_resume_in_progress:
            text = "Workflow resume is already in progress."
            self.state = self._replace(workflow_resume_text=text, last_error=text)
            return text
        run = self.state.selected_workflow_run
        run_id = (
            getattr(run, "run_id", None) or getattr(run, "operation_id", None)
            if run is not None
            else None
        )
        if not run_id:
            text = "Resume unavailable: no workflow run selected."
            self.state = self._replace(
                workflow_resume_text=text,
                workflow_resume_available=False,
                last_error=None,
            )
            return text
        if not self.state.workflow_resume_available:
            text = self.state.workflow_resume_text or "Resume unavailable for this workflow run."
            self.state = self._replace(workflow_resume_text=text, last_error=None)
            return text
        if not confirmed:
            text = "Workflow resume cancelled."
            self.state = self._replace(workflow_resume_text=text, last_error=None)
            return text
        self.state = self._replace(workflow_resume_in_progress=True)
        try:
            result = self.app_service.resume_workflow_run(str(run_id))
            text = self._format_workflow_resume_result(result)
            preferred_id = getattr(result, "resumed_run_id", None) or str(run_id)
            workflow = self._load_workflow_state(preferred_selected_id=preferred_id)
            self.state = self._replace(
                workflow_list_text=workflow["workflow_list_text"],
                selected_workflow_run_id=workflow["selected_workflow_run_id"],
                workflow_details_text=workflow["workflow_details_text"],
                workflow_copy_text=workflow["workflow_copy_text"],
                workflow_runs=workflow["workflow_runs"],
                selected_workflow_run=workflow["selected_workflow_run"],
                selected_workflow_steps=workflow["selected_workflow_steps"],
                workflow_loading=workflow["workflow_loading"],
                workflow_load_error=workflow["workflow_load_error"],
                workflow_resume_text=text,
                workflow_resume_available=workflow["workflow_resume_available"],
                workflow_resume_in_progress=False,
                output_text=text,
                last_error=None if getattr(result, "ok", False) else text,
            )
            return text
        except Exception:
            text = "Workflow resume failed safely."
            self.state = self._replace(
                workflow_resume_text=text,
                workflow_resume_available=False,
                workflow_resume_in_progress=False,
                output_text=text,
                last_error=text,
            )
            return text

    def update_history_search(self, query: str | None) -> str:
        history = self._apply_history_filters(
            loaded_entries=self.state.loaded_history_entries,
            search_query=query,
            status_filter=self.state.history_status_filter,
            preferred_selected_id=self.state.selected_history_id,
            last_error=self.state.last_error,
            history_load_error=self.state.history_load_error,
        )
        self.state = self._replace(**history)
        return self.state.history_list_text

    def update_history_status_filter(self, status_filter: str | None) -> str:
        history = self._apply_history_filters(
            loaded_entries=self.state.loaded_history_entries,
            search_query=self.state.history_search_query,
            status_filter=status_filter,
            preferred_selected_id=self.state.selected_history_id,
            last_error=self.state.last_error,
            history_load_error=self.state.history_load_error,
        )
        self.state = self._replace(**history)
        return self.state.history_list_text

    def clear_history_filters(self) -> str:
        history = self._apply_history_filters(
            loaded_entries=self.state.loaded_history_entries,
            search_query="",
            status_filter="All",
            preferred_selected_id=self.state.selected_history_id,
            last_error=self.state.last_error,
            history_load_error=self.state.history_load_error,
        )
        self.state = self._replace(**history)
        return self.state.history_list_text

    def _load_history_state(self, limit: int | None = None) -> dict[str, object]:
        try:
            result = self.app_service.execution_history(limit)
            if not getattr(result, "ok", False):
                error_text = self._safe_history_error(getattr(result, "error", None))
                return {
                    "history_list_text": error_text,
                    "selected_history_id": None,
                    "selected_history_details_text": error_text,
                    "history_copy_text": "",
                    "loaded_history_entries": (),
                    "history_entries": (),
                    "history_search_query": "",
                    "history_status_filter": "All",
                    "history_result_count_text": "0 entries",
                    "history_loading": False,
                    "history_load_error": error_text,
                    "last_error": error_text,
                }
            entries = tuple(getattr(result, "entries", ()) or ())
            return self._apply_history_filters(
                loaded_entries=entries,
                search_query="",
                status_filter="All",
                preferred_selected_id=None,
                last_error=None,
                history_load_error=None,
            )
        except Exception:
            error_text = self._safe_history_error("execution_history_unavailable")
            return {
                "history_list_text": error_text,
                "selected_history_id": None,
                "selected_history_details_text": error_text,
                "history_copy_text": "",
                "loaded_history_entries": (),
                "history_entries": (),
                "history_search_query": "",
                "history_status_filter": "All",
                "history_result_count_text": "0 entries",
                "history_loading": False,
                "history_load_error": error_text,
                "last_error": error_text,
            }

    def _load_workflow_state(
        self,
        limit: int | None = None,
        *,
        preferred_selected_id: str | None = None,
    ) -> dict[str, object]:
        try:
            result = self.app_service.recent_workflow_runs(limit)
            if not getattr(result, "ok", False):
                error_text = self._safe_workflow_error(getattr(result, "error", None))
                return {
                    "workflow_list_text": error_text,
                    "selected_workflow_run_id": None,
                    "workflow_details_text": error_text,
                    "workflow_copy_text": "",
                    "workflow_runs": (),
                    "selected_workflow_run": None,
                    "selected_workflow_steps": (),
                    "workflow_loading": False,
                    "workflow_load_error": error_text,
                    "workflow_resume_text": "Resume unavailable: workflow history could not be loaded.",
                    "workflow_resume_available": False,
                    "last_error": error_text,
                }
            runs = tuple(getattr(result, "runs", ()) or ())
            selected_run = self._select_workflow_run(runs, preferred_selected_id)
            details = (
                self._load_workflow_details_text(
                    getattr(selected_run, "run_id", None)
                    or getattr(selected_run, "operation_id", None)
                )
                if selected_run is not None
                else self._empty_workflow_details()
            )
            return {
                "workflow_list_text": self._workflow_list_text(runs),
                "selected_workflow_run_id": (
                    getattr(selected_run, "run_id", None)
                    or getattr(selected_run, "operation_id", None)
                    if selected_run is not None
                    else None
                ),
                "workflow_details_text": details["workflow_details_text"],
                "workflow_copy_text": details["workflow_copy_text"],
                "workflow_runs": runs,
                "selected_workflow_run": details["selected_workflow_run"],
                "selected_workflow_steps": details["selected_workflow_steps"],
                "workflow_loading": False,
                "workflow_load_error": details["workflow_load_error"],
                "workflow_resume_text": details["workflow_resume_text"],
                "workflow_resume_available": details["workflow_resume_available"],
                "last_error": details["last_error"],
            }
        except Exception:
            error_text = self._safe_workflow_error("workflow_history_unavailable")
            return {
                "workflow_list_text": error_text,
                "selected_workflow_run_id": None,
                "workflow_details_text": error_text,
                "workflow_copy_text": "",
                "workflow_runs": (),
                "selected_workflow_run": None,
                "selected_workflow_steps": (),
                "workflow_loading": False,
                "workflow_load_error": error_text,
                "workflow_resume_text": "Resume unavailable: workflow history could not be loaded.",
                "workflow_resume_available": False,
                "last_error": error_text,
            }

    def _load_workflow_details_text(self, run_id: str | None) -> dict[str, object]:
        if not run_id:
            return self._empty_workflow_details()
        try:
            result = self.app_service.workflow_run_history(run_id)
            if not getattr(result, "ok", False):
                error_text = self._safe_workflow_error(getattr(result, "error", None))
                return {
                    "workflow_details_text": error_text,
                    "workflow_copy_text": "",
                    "selected_workflow_run": None,
                    "selected_workflow_steps": (),
                    "workflow_load_error": error_text,
                    "workflow_resume_text": "Resume unavailable: workflow details could not be loaded.",
                    "workflow_resume_available": False,
                    "last_error": error_text,
                }
            runs = tuple(getattr(result, "runs", ()) or ())
            run = runs[0] if runs else None
            if run is None:
                return self._empty_workflow_details()
            details = self._workflow_run_details(run)
            return {
                "workflow_details_text": details,
                "workflow_copy_text": details,
                "selected_workflow_run": run,
                "selected_workflow_steps": tuple(getattr(run, "steps", ()) or ()),
                "workflow_load_error": None,
                "workflow_resume_text": self._workflow_resume_text(run),
                "workflow_resume_available": bool(getattr(run, "resume_eligible", False)),
                "last_error": None,
            }
        except Exception:
            error_text = self._safe_workflow_error("workflow_history_unavailable")
            return {
                "workflow_details_text": error_text,
                "workflow_copy_text": "",
                "selected_workflow_run": None,
                "selected_workflow_steps": (),
                "workflow_load_error": error_text,
                "workflow_resume_text": "Resume unavailable: workflow details could not be loaded.",
                "workflow_resume_available": False,
                "last_error": error_text,
            }

    @staticmethod
    def _select_workflow_run(runs: tuple[object, ...], preferred_id: str | None):
        if preferred_id:
            for run in runs:
                run_id = getattr(run, "run_id", None) or getattr(run, "operation_id", None)
                if run_id == preferred_id:
                    return run
        return runs[0] if runs else None

    def _workflow_list_text(self, runs: tuple[object, ...]) -> str:
        if not runs:
            return "Workflow History:\n- No workflow runs available."
        lines = ["Workflow History:", "- newest first", f"- {len(runs)} workflow run(s)"]
        for index, run in enumerate(runs, start=1):
            lines.append(f"{index}. {self._workflow_run_summary(run)}")
        return self._safe_text("\n".join(lines))

    def _workflow_run_summary(self, run) -> str:
        run_id = getattr(run, "run_id", None) or getattr(run, "operation_id", None) or "unknown"
        workflow = getattr(run, "workflow_name", None) or getattr(run, "workflow_id", None) or "workflow"
        state = self._state_value(getattr(run, "state", None))
        started = getattr(run, "started_at", None) or getattr(run, "created_at", None) or "unknown"
        completed = getattr(run, "completed_at", None) or "not finished"
        completed_count = getattr(run, "completed_step_count", 0)
        total_count = getattr(run, "total_step_count", 0)
        return self._safe_text(
            f"{run_id} | {workflow} | {state} | started {started} | finished {completed} | steps {completed_count}/{total_count}"
        )

    def _workflow_run_details(self, run) -> str:
        lines = [
            "Workflow Run:",
            f"- run id: {getattr(run, 'run_id', None) or getattr(run, 'operation_id', None) or 'unknown'}",
            f"- workflow: {getattr(run, 'workflow_name', None) or getattr(run, 'workflow_id', None) or 'workflow'}",
            f"- state: {self._state_value(getattr(run, 'state', None))}",
            f"- objective: {getattr(run, 'objective_summary', None) or 'Workflow objective unavailable.'}",
            f"- started: {getattr(run, 'started_at', None) or getattr(run, 'created_at', None) or 'unknown'}",
            f"- finished: {getattr(run, 'completed_at', None) or 'not finished'}",
            f"- completed steps: {getattr(run, 'completed_step_count', 0)}/{getattr(run, 'total_step_count', 0)}",
            f"- resume available: {'yes' if getattr(run, 'resume_eligible', False) else 'no'}",
        ]
        if getattr(run, "resumed_from_run_id", None):
            lines.append(f"- resumed from: {getattr(run, 'resumed_from_run_id')}")
        resume_step = getattr(run, "resume_step_id", None)
        if resume_step:
            lines.append(f"- resume step: {resume_step}")
        reason = self._resume_reason_value(getattr(run, "resume_rejection_reason", None))
        if reason and reason != "none":
            lines.append(f"- resume reason: {reason}")
        active_step = getattr(run, "active_step_name", None) or getattr(run, "active_step_id", None)
        if active_step:
            lines.append(f"- active step: {active_step}")
        result = getattr(run, "safe_result_summary", None)
        if result:
            lines.append(f"- result: {result}")
        failure = getattr(run, "safe_failure_summary", None)
        if failure:
            lines.append(f"- error: {failure}")
        lines.append("")
        lines.append("Workflow Steps:")
        steps = tuple(getattr(run, "steps", ()) or ())
        if not steps:
            lines.append("- No workflow steps were recorded.")
        else:
            for step in steps:
                lines.extend(self._workflow_step_lines(step))
        return self._safe_text("\n".join(lines))

    def _workflow_step_lines(self, step) -> list[str]:
        index = getattr(step, "step_index", 0)
        label = getattr(step, "display_name", None) or getattr(step, "step_id", None) or "Workflow step"
        lines = [
            f"- {index + 1}. {label}",
            f"  step id: {getattr(step, 'step_id', None) or 'unknown'}",
            f"  state: {self._state_value(getattr(step, 'state', None))}",
            f"  started: {getattr(step, 'started_at', None) or 'not started'}",
            f"  finished: {getattr(step, 'completed_at', None) or 'not finished'}",
        ]
        operation_type = getattr(step, "operation_type", None)
        if operation_type:
            lines.append(f"  operation: {operation_type}")
        result = getattr(step, "safe_result_summary", None)
        if result:
            lines.append(f"  result: {result}")
        error = getattr(step, "safe_error_summary", None)
        if error:
            lines.append(f"  error: {error}")
        if getattr(step, "requires_confirmation", False):
            lines.append("  requires confirmation: yes")
        if getattr(step, "preview", False):
            lines.append("  preview: yes")
        return lines

    def _empty_workflow_details(self) -> dict[str, object]:
        details = "Workflow run details:\n- Select a workflow run to view its steps."
        return {
            "workflow_details_text": details,
            "workflow_copy_text": "",
            "selected_workflow_run": None,
            "selected_workflow_steps": (),
            "workflow_load_error": None,
            "workflow_resume_text": "Resume unavailable: no workflow run selected.",
            "workflow_resume_available": False,
            "last_error": None,
        }

    @staticmethod
    def _state_value(state) -> str:
        value = getattr(state, "value", state)
        return str(value or "unknown")

    def _workflow_resume_text(self, run) -> str:
        if getattr(run, "resume_eligible", False):
            step_id = getattr(run, "resume_step_id", None) or "first unfinished step"
            return self._safe_text(f"Resume available from {step_id}.")
        reason = self._resume_reason_value(getattr(run, "resume_rejection_reason", None))
        if reason and reason != "none":
            return self._safe_text(f"Resume unavailable: {reason}.")
        return "Resume unavailable for this workflow run."

    @staticmethod
    def _resume_reason_value(reason) -> str:
        value = getattr(reason, "value", reason)
        return str(value or "none")

    def _apply_history_filters(
        self,
        *,
        loaded_entries: tuple[object, ...],
        search_query: str | None,
        status_filter: str | None,
        preferred_selected_id: str | None,
        last_error: str | None,
        history_load_error: str | None,
    ) -> dict[str, object]:
        normalized_query = str(search_query or "").strip()
        normalized_filter = self._normalize_history_status_filter(status_filter)
        loaded = tuple(loaded_entries or ())
        if history_load_error:
            return {
                "history_list_text": history_load_error,
                "selected_history_id": None,
                "selected_history_details_text": history_load_error,
                "history_copy_text": "",
                "loaded_history_entries": loaded,
                "history_entries": (),
                "history_search_query": normalized_query,
                "history_status_filter": normalized_filter,
                "history_result_count_text": self._history_result_count_text(0, len(loaded), True),
                "history_loading": False,
                "history_load_error": history_load_error,
                "last_error": last_error,
            }
        visible = tuple(
            entry
            for entry in loaded
            if self._history_matches_status(entry, normalized_filter)
            and self._history_matches_search(entry, normalized_query)
        )
        selected_entry = self._select_visible_history_entry(visible, preferred_selected_id)
        details = (
            self._history_entry_details(selected_entry)
            if selected_entry is not None
            else "Execution history entry details:\n- no entry selected"
        )
        return {
            "history_list_text": self._history_list_text(
                visible,
                loaded_count=len(loaded),
                search_query=normalized_query,
                status_filter=normalized_filter,
            ),
            "selected_history_id": getattr(selected_entry, "entry_id", None)
            if selected_entry is not None
            else None,
            "selected_history_details_text": details,
            "history_copy_text": details if selected_entry is not None else "",
            "loaded_history_entries": loaded,
            "history_entries": visible,
            "history_search_query": normalized_query,
            "history_status_filter": normalized_filter,
            "history_result_count_text": self._history_result_count_text(
                len(visible),
                len(loaded),
                self._history_filters_active(normalized_query, normalized_filter),
            ),
            "history_loading": False,
            "history_load_error": None,
            "last_error": last_error,
        }

    def _history_list_text(
        self,
        entries: tuple[object, ...],
        *,
        loaded_count: int | None = None,
        search_query: str = "",
        status_filter: str = "All",
    ) -> str:
        total = len(entries) if loaded_count is None else loaded_count
        active = self._history_filters_active(search_query, status_filter)
        if total == 0:
            return "Execution history:\n- No execution history is available."
        if not entries:
            return "\n".join(
                [
                    "Execution history:",
                    "- No history entries match the current filters.",
                    f"- {self._history_result_count_text(0, total, True)}",
                ]
            )
        lines = [
            "Execution history:",
            "- newest first",
            f"- {self._history_result_count_text(len(entries), total, active)}",
        ]
        for index, entry in enumerate(entries, start=1):
            summary = (
                entry.summary_text()
                if hasattr(entry, "summary_text")
                else self._fallback_history_summary(entry)
            )
            lines.append(f"{index}. {summary}")
        return self._safe_text("\n".join(lines))

    @classmethod
    def _normalize_history_status_filter(cls, status_filter: str | None) -> str:
        raw = str(status_filter or "All").strip().lower()
        for option in cls.HISTORY_STATUS_FILTERS:
            if option.lower() == raw:
                return option
        return "All"

    @staticmethod
    def _history_filters_active(search_query: str, status_filter: str) -> bool:
        return bool(str(search_query or "").strip()) or status_filter != "All"

    @staticmethod
    def _history_result_count_text(visible_count: int, total_count: int, active: bool) -> str:
        noun = "entry" if visible_count == 1 else "entries"
        if active:
            total_noun = "entry" if total_count == 1 else "entries"
            return f"{visible_count} of {total_count} {total_noun}"
        return f"{visible_count} {noun}"

    @staticmethod
    def _select_visible_history_entry(entries: tuple[object, ...], preferred_id: str | None):
        if preferred_id:
            for entry in entries:
                if getattr(entry, "entry_id", None) == preferred_id:
                    return entry
        return entries[0] if entries else None

    def _history_matches_status(self, entry, status_filter: str) -> bool:
        if status_filter == "All":
            return True
        if status_filter == "Preview":
            return bool(getattr(entry, "preview", False))
        status = str(getattr(entry, "status", "") or "").strip().lower()
        if status_filter == "Successful":
            return status == "succeeded" or getattr(entry, "succeeded", None) is True
        if status_filter == "Failed":
            return status == "failed"
        if status_filter == "Denied":
            return status == "denied"
        if status_filter == "Cancelled":
            return status == "cancelled"
        return True

    def _history_matches_search(self, entry, query: str) -> bool:
        normalized = str(query or "").strip().lower()
        if not normalized:
            return True
        return normalized in self._history_search_text(entry).lower()

    def _history_search_text(self, entry) -> str:
        parts = [
            getattr(entry, "request_summary", None),
            getattr(entry, "command_id", None),
            getattr(entry, "action_id", None),
            getattr(entry, "operation_type", None),
            getattr(entry, "status", None),
            getattr(entry, "user_message", None),
            getattr(entry, "safe_error_summary", None),
        ]
        return " ".join(self._safe_text(part) for part in parts if part)

    def _history_entry_details(self, entry) -> str:
        if hasattr(entry, "details_text"):
            return self._safe_text(entry.details_text())
        return self._safe_text(self._fallback_history_summary(entry))

    def _fallback_history_summary(self, entry) -> str:
        return "\n".join(
            [
                "Execution history entry:",
                f"- id: {getattr(entry, 'entry_id', 'unknown') or 'unknown'}",
                f"- timestamp: {getattr(entry, 'timestamp', 'unknown') or 'unknown'}",
                f"- status: {getattr(entry, 'status', 'unknown') or 'unknown'}",
                f"- command id: {getattr(entry, 'command_id', None) or 'none'}",
                f"- message: {getattr(entry, 'user_message', None) or 'none'}",
                f"- error: {getattr(entry, 'safe_error_summary', None) or 'none'}",
            ]
        )

    @classmethod
    def _safe_history_error(cls, _error=None) -> str:
        return "\n".join(
            [
                "Execution history:",
                "- status: unavailable",
                "- error: execution_history_unavailable",
                "- no internal details",
            ]
        )

    @classmethod
    def _safe_workflow_error(cls, _error=None) -> str:
        return "\n".join(
            [
                "Workflow History:",
                "- status: unavailable",
                "- error: workflow_history_unavailable",
                "- no internal details",
            ]
        )

    def safe_status_text_ru(self) -> str:
        service_status = self.app_service.status_text_ru()
        contract_status = self.app_service.contract_status_text_ru()
        return self._safe_text(
            "\n".join(
                [
                    "Desktop shell status:",
                    "- desktop shell foundation: yes",
                    "- gui prototype: yes",
                    "- run command: python run_desktop.py",
                    "- app service used: yes",
                    "- command registry used: yes",
                    "- installer ready: no",
                    "- secure key storage foundation: available",
                    "- provider settings UI ready: no",
                    "- network default: no",
                    "- no secrets",
                    "- no response execution",
                    "- run.py unchanged",
                    "",
                    service_status,
                    "",
                    contract_status,
                ]
            )
        )

    def ui_capabilities_text_ru(self) -> str:
        return "\n".join(
            [
                "Desktop shell capabilities:",
                "- can show app/service status",
                "- can list command registry/categories",
                "- can preview command risk",
                "- can execute through AppService",
                "- can show recent execution history",
                "- future AI provider settings planned",
                "- secure key storage foundation available",
                "- future secure key input UI planned",
                "- future installer planned",
                "- no final design yet",
            ]
        )

    def _format_execution_result(self, result) -> str:
        lines = [
            "Desktop shell execution:",
            f"- ok: {'yes' if getattr(result, 'ok', False) else 'no'}",
            "- source: desktop_ui",
            f"- command id: {getattr(result, 'registry_match_id', None) or 'none'}",
            f"- category: {getattr(result, 'category', None) or 'unknown'}",
            f"- risk: {getattr(result, 'risk_level', None) or 'unknown'}",
            f"- requires confirmation: {'yes' if getattr(result, 'requires_confirmation', False) else 'no'}",
            f"- operation id: {getattr(result, 'operation_id', None) or 'none'}",
            f"- operation status: {getattr(result, 'operation_status', None) or 'none'}",
            f"- duplicate suppressed: {'yes' if getattr(result, 'duplicate_suppressed', False) else 'no'}",
            "- executed through AppService: yes",
            f"- network may be used: {'yes' if getattr(result, 'network_may_be_used', False) else 'no'}",
            "- response executed as command: no",
            "- no secrets",
        ]
        plan_id = getattr(result, "plan_id", None)
        if plan_id:
            lines.extend(
                [
                    f"- plan id: {plan_id}",
                    f"- plan status: {getattr(result, 'plan_status', None) or 'none'}",
                    f"- plan step count: {getattr(result, 'plan_step_count', None) if getattr(result, 'plan_step_count', None) is not None else 0}",
                ]
            )
        error = getattr(result, "error", None)
        if error:
            lines.append(f"- error: {error}")
        workflow_id = getattr(result, "workflow_id", None)
        if workflow_id:
            lines.extend(
                [
                    f"- workflow id: {workflow_id}",
                    f"- workflow status: {getattr(result, 'workflow_status', None) or 'none'}",
                    f"- current step id: {getattr(result, 'current_step_id', None) or 'none'}",
                    f"- current step name: {getattr(result, 'current_step_name', None) or 'none'}",
                    f"- completed steps: {len(getattr(result, 'completed_steps', ()) or ())}",
                    f"- total steps: {getattr(result, 'total_steps', None) if getattr(result, 'total_steps', None) is not None else 0}",
                    f"- progress percent: {getattr(result, 'progress_percent', None) if getattr(result, 'progress_percent', None) is not None else 0}",
                    f"- awaiting confirmation: {'yes' if getattr(result, 'awaiting_confirmation', False) else 'no'}",
                    f"- source filename: {getattr(result, 'source_filename', None) or 'none'}",
                    f"- issue count: {getattr(result, 'issue_count', None) if getattr(result, 'issue_count', None) is not None else 0}",
                    f"- proposed output filename: {getattr(result, 'proposed_output_filename', None) or 'none'}",
                    f"- proposed output path: {getattr(result, 'proposed_output_path', None) or 'none'}",
                    f"- saved: {'yes' if getattr(result, 'saved', False) else 'no'}",
                    f"- verified: {'yes' if getattr(result, 'verified', False) else 'no'}",
                ]
            )
            issue_summaries = getattr(result, "issue_summaries", ()) or ()
            if issue_summaries:
                lines.append("Issue summaries:")
                for issue in issue_summaries:
                    lines.append(
                        "- "
                        + str(issue.get("issue_code", "unknown"))
                        + f" line {issue.get('line_number', '?')}: "
                        + str(issue.get("description_ru", ""))
                    )
            user_message = getattr(result, "user_message", None)
            if user_message:
                lines.append(f"- message: {user_message}")
        if getattr(result, "requires_clarification", False):
            question = getattr(result, "clarification_question", None)
            options = getattr(result, "clarification_options", ())
            lines.append("Требуется уточнение:")
            if question:
                lines.append(str(question))
            if options:
                lines.append("")
                lines.append("Варианты:")
                lines.extend(f"- {getattr(option, 'label_ru', option)}" for option in options)
        else:
            output_text = getattr(result, "output_text", "")
            if output_text:
                lines.append("Output:")
                lines.append(str(output_text))
        return self._safe_text("\n".join(lines))

    def _format_voice_result(self, result) -> str:
        lines = [
            "Голосовой запрос Desktop Shell:",
            f"- успешно: {'да' if getattr(result, 'ok', False) else 'нет'}",
            "- source: desktop_ui",
            f"- захват голоса: {'да' if getattr(result, 'voice_capture_succeeded', False) else 'нет'}",
            f"- распознавание: {'да' if getattr(result, 'recognition_succeeded', False) else 'нет'}",
            f"- распознано: {getattr(result, 'recognized_text', None) or 'нет'}",
            f"- обработка текста: {'да' if getattr(result, 'text_processing_succeeded', False) else 'нет'}",
            f"- result type: {getattr(result, 'result_type', 'unknown')}",
            f"- category: {getattr(result, 'category', None) or 'unknown'}",
            f"- требуется подтверждение: {'да' if getattr(result, 'requires_confirmation', False) else 'нет'}",
            "- executed through AppService: yes",
            "- сырое аудио отправлено наружу: нет",
            "- response executed as command: no",
            "- no secrets",
        ]
        error_code = getattr(result, "error_code", None)
        if error_code:
            lines.append(f"- error code: {error_code}")
        normalized_text = getattr(result, "normalized_text", None)
        if getattr(result, "normalization_applied", False) and normalized_text:
            lines.append(f"Нормализовано: {normalized_text}")
        user_message = getattr(result, "user_message", "")
        if user_message:
            lines.append(f"- сообщение: {user_message}")
        text_result = getattr(result, "text_result", None)
        if text_result is not None:
            lines.append("Ответ:")
            lines.append(getattr(text_result, "output_text", ""))
        return self._safe_text("\n".join(lines))

    def _format_workflow_resume_result(self, result) -> str:
        status = self._state_value(getattr(result, "status", None))
        reason = self._resume_reason_value(getattr(result, "rejection_reason", None))
        lines = [
            "Workflow resume:",
            f"- ok: {'yes' if getattr(result, 'ok', False) else 'no'}",
            "- source: desktop_ui",
            f"- status: {status}",
            f"- source run id: {getattr(result, 'source_run_id', None) or 'unknown'}",
            f"- resumed run id: {getattr(result, 'resumed_run_id', None) or 'none'}",
            f"- execution started: {'yes' if getattr(result, 'execution_started', False) else 'no'}",
            f"- rejection reason: {reason}",
            "- executed through AppService: yes",
            "- completed steps rerun: no",
            "- no secrets",
        ]
        if getattr(result, "resume_step_id", None):
            lines.append(f"- resume step id: {getattr(result, 'resume_step_id')}")
        if getattr(result, "resume_step_index", None) is not None:
            lines.append(f"- resume step index: {getattr(result, 'resume_step_index')}")
        message = getattr(result, "safe_message", None)
        if message:
            lines.append(f"- message: {message}")
        return self._safe_text("\n".join(lines))

    def _replace(self, **changes) -> DesktopShellState:
        values = self.state.__dict__.copy() if hasattr(self, "state") else {}
        values.update(changes)
        return DesktopShellState(**values)

    @classmethod
    def _safe_text(cls, text: str) -> str:
        safe = str(text or "")
        safe = re.sub(
            r"(?i)(sk-[a-z0-9_-]{8,}|api[_ -]?key\s*[:=]?\s*\S+|token\s*[:=]?\s*\S+)",
            "[REDACTED]",
            safe,
        )
        return safe

    @classmethod
    def _safe_error(cls, exc: Exception) -> str:
        return "Desktop shell error: " + cls._safe_text(str(exc))


class JarvisDesktopShell:
    """Tkinter wrapper for the safe desktop shell ViewModel."""

    COLORS = {
        "bg": "#101318",
        "panel": "#171c23",
        "panel_alt": "#1f2630",
        "text": "#e7edf5",
        "muted": "#9aa7b5",
        "accent": "#3aa7ff",
        "accent_alt": "#3ddc97",
        "warning": "#f5b84b",
        "border": "#2b3440",
    }

    def __init__(self, view_model: DesktopShellViewModel, tk_module=None):
        self.view_model = view_model
        self.tk = tk_module or self._import_tkinter()
        self.root = self.tk.Tk()
        self.root.title("JARVIS OS")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=self.COLORS["bg"])
        self._voice_worker_active = False
        self._build()
        self._render_state()

    @staticmethod
    def _import_tkinter():
        import tkinter as tk

        return tk

    def run(self) -> None:
        self.root.mainloop()

    def _build(self) -> None:
        tk = self.tk
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self.root, bg=self.COLORS["bg"], padx=16, pady=14)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        title = tk.Label(
            header,
            text="JARVIS OS",
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 20, "bold"),
        )
        title.pack(side="left")
        subtitle = tk.Label(
            header,
            text="App Shell Prototype",
            bg=self.COLORS["bg"],
            fg=self.COLORS["muted"],
            font=("Segoe UI", 11),
            padx=14,
        )
        subtitle.pack(side="left")

        left = tk.Frame(self.root, bg=self.COLORS["panel"], padx=12, pady=12)
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        left.grid_rowconfigure(2, weight=1)

        tk.Label(
            left,
            text="Status",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.status_box = tk.Text(
            left,
            width=34,
            height=11,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief="flat",
            wrap="word",
        )
        self.status_box.grid(row=1, column=0, sticky="ew", pady=(8, 12))

        tk.Label(
            left,
            text="Categories",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=2, column=0, sticky="nw")
        self.category_list = tk.Listbox(
            left,
            height=9,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            selectbackground=self.COLORS["accent"],
            relief="flat",
            exportselection=False,
        )
        self.category_list.grid(row=3, column=0, sticky="nsew", pady=(8, 12))
        for category in ("app", "ai", "ai_provider", "voice", "safety", "ollama", "system"):
            self.category_list.insert("end", category)
        self.category_list.bind("<<ListboxSelect>>", self._on_category_selected)

        quick = tk.Frame(left, bg=self.COLORS["panel"])
        quick.grid(row=4, column=0, sticky="ew")
        for index, (label, command) in enumerate(
            (
                ("Status", self._on_status),
                ("Command Registry", self._on_registry),
                ("AI Status", self._on_ai_status),
                ("App Service", self._on_app_service),
            )
        ):
            button = tk.Button(
                quick,
                text=label,
                command=command,
                bg=self.COLORS["panel_alt"],
                fg=self.COLORS["text"],
                activebackground=self.COLORS["accent"],
                activeforeground=self.COLORS["text"],
                relief="flat",
                padx=8,
                pady=7,
            )
            button.grid(row=index, column=0, sticky="ew", pady=3)
        quick.grid_columnconfigure(0, weight=1)

        main = tk.Frame(self.root, bg=self.COLORS["bg"], padx=8, pady=0)
        main.grid(row=1, column=1, sticky="nsew", padx=(0, 16), pady=(0, 16))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(4, weight=1)

        input_panel = tk.Frame(main, bg=self.COLORS["panel"], padx=12, pady=12)
        input_panel.grid(row=0, column=0, sticky="ew")
        input_panel.grid_columnconfigure(0, weight=1)
        tk.Label(
            input_panel,
            text="Command",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.command_entry = tk.Entry(
            input_panel,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief="flat",
            font=("Segoe UI", 12),
        )
        self.command_entry.grid(row=1, column=0, sticky="ew", pady=(8, 0), ipady=8)
        self._bind_command_clipboard(self.command_entry)
        tk.Button(
            input_panel,
            text="Preview",
            command=self._on_preview,
            bg=self.COLORS["accent"],
            fg="#071018",
            relief="flat",
            padx=12,
            pady=8,
        ).grid(row=1, column=1, padx=(10, 4), pady=(8, 0))
        tk.Button(
            input_panel,
            text="Execute",
            command=self._on_execute,
            bg=self.COLORS["accent_alt"],
            fg="#071018",
            relief="flat",
            padx=12,
            pady=8,
        ).grid(row=1, column=2, padx=(4, 0), pady=(8, 0))
        self.voice_button = tk.Button(
            input_panel,
            text="Микрофон",
            command=self._on_voice_once,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            padx=12,
            pady=8,
        )
        self.voice_button.grid(row=1, column=3, padx=(8, 0), pady=(8, 0))

        note = tk.Label(
            main,
            text="No auto-execution. Network/provider commands require explicit command text and Execute.",
            bg=self.COLORS["bg"],
            fg=self.COLORS["warning"],
            anchor="w",
        )
        note.grid(row=1, column=0, sticky="ew", pady=8)

        history_panel = tk.Frame(main, bg=self.COLORS["panel"], padx=10, pady=10)
        history_panel.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        history_panel.grid_columnconfigure(0, weight=1)
        history_panel.grid_columnconfigure(1, weight=1)
        tk.Label(
            history_panel,
            text="Execution History",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.history_count_label = tk.Label(
            history_panel,
            text="",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="e",
        )
        self.history_count_label.grid(row=0, column=1, sticky="e", padx=(8, 4))
        tk.Button(
            history_panel,
            text="Refresh",
            command=self._on_history_refresh,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            padx=10,
            pady=6,
        ).grid(row=0, column=2, sticky="e", padx=(8, 4))
        self.history_copy_button = tk.Button(
            history_panel,
            text="Copy Selected",
            command=self._on_history_copy,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            padx=10,
            pady=6,
        )
        self.history_copy_button.grid(row=0, column=3, sticky="e")
        history_filter_bar = tk.Frame(history_panel, bg=self.COLORS["panel"])
        history_filter_bar.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        history_filter_bar.grid_columnconfigure(1, weight=1)
        tk.Label(
            history_filter_bar,
            text="Search",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.history_search_var = tk.StringVar(value=self.view_model.state.history_search_query)
        self.history_search_entry = tk.Entry(
            history_filter_bar,
            textvariable=self.history_search_var,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief="flat",
        )
        self.history_search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.history_search_entry.bind("<KeyRelease>", self._on_history_search_changed)
        tk.Label(
            history_filter_bar,
            text="Status",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
        ).grid(row=0, column=2, sticky="e", padx=(0, 6))
        self.history_status_var = tk.StringVar(
            value=self.view_model.state.history_status_filter
        )
        self.history_status_menu = tk.OptionMenu(
            history_filter_bar,
            self.history_status_var,
            *self.view_model.HISTORY_STATUS_FILTERS,
            command=self._on_history_status_changed,
        )
        self.history_status_menu.configure(
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            highlightthickness=0,
        )
        self.history_status_menu.grid(row=0, column=3, sticky="e", padx=(0, 8))
        tk.Button(
            history_filter_bar,
            text="Clear Filters",
            command=self._on_history_clear_filters,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            padx=10,
            pady=4,
        ).grid(row=0, column=4, sticky="e")
        history_content = tk.Frame(history_panel, bg=self.COLORS["panel"])
        history_content.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        history_content.grid_columnconfigure(0, weight=1)
        history_content.grid_columnconfigure(1, weight=1)
        self.history_list = tk.Listbox(
            history_content,
            height=5,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            selectbackground=self.COLORS["accent"],
            relief="flat",
            exportselection=False,
        )
        self.history_list.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.history_list.bind("<<ListboxSelect>>", self._on_history_selected)
        self.history_details_box = self._text_box(history_content, height=5)
        self.history_details_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._bind_readonly_text_copy(self.history_details_box)

        workflow_panel = tk.Frame(main, bg=self.COLORS["panel"], padx=10, pady=10)
        workflow_panel.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        workflow_panel.grid_columnconfigure(0, weight=1)
        workflow_panel.grid_columnconfigure(1, weight=1)
        tk.Label(
            workflow_panel,
            text="Workflow History",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Button(
            workflow_panel,
            text="Refresh",
            command=self._on_workflow_refresh,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            padx=10,
            pady=6,
        ).grid(row=0, column=2, sticky="e", padx=(8, 4))
        self.workflow_resume_button = tk.Button(
            workflow_panel,
            text="Resume",
            command=self._on_workflow_resume,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            padx=10,
            pady=6,
        )
        self.workflow_resume_button.grid(row=0, column=3, sticky="e", padx=(0, 4))
        self.workflow_copy_button = tk.Button(
            workflow_panel,
            text="Copy Selected",
            command=self._on_workflow_copy,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            activebackground=self.COLORS["accent"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            padx=10,
            pady=6,
        )
        self.workflow_copy_button.grid(row=0, column=4, sticky="e")
        workflow_content = tk.Frame(workflow_panel, bg=self.COLORS["panel"])
        workflow_content.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(8, 0))
        workflow_content.grid_columnconfigure(0, weight=1)
        workflow_content.grid_columnconfigure(1, weight=1)
        self.workflow_list = tk.Listbox(
            workflow_content,
            height=4,
            bg=self.COLORS["panel_alt"],
            fg=self.COLORS["text"],
            selectbackground=self.COLORS["accent"],
            relief="flat",
            exportselection=False,
        )
        self.workflow_list.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.workflow_list.bind("<<ListboxSelect>>", self._on_workflow_selected)
        self.workflow_details_box = self._text_box(workflow_content, height=4)
        self.workflow_details_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._bind_readonly_text_copy(self.workflow_details_box)

        split = tk.PanedWindow(main, orient="vertical", bg=self.COLORS["bg"], sashwidth=6)
        split.grid(row=4, column=0, sticky="nsew")
        self.preview_box = self._text_box(split, height=10)
        self.output_box = self._text_box(split, height=14)
        self.command_list_box = self._text_box(split, height=10)
        for text_widget in (self.preview_box, self.output_box, self.command_list_box):
            self._bind_readonly_text_copy(text_widget)
        split.add(self.preview_box)
        split.add(self.output_box)
        split.add(self.command_list_box)

    def _text_box(self, parent, height):
        box = self.tk.Text(
            parent,
            height=height,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief="flat",
            wrap="word",
            padx=10,
            pady=10,
        )
        return box

    def _bind_command_clipboard(self, entry) -> None:
        menu = self.tk.Menu(entry, tearoff=0)
        menu.add_command(label="Вырезать", command=lambda: self._entry_cut(entry))
        menu.add_command(label="Копировать", command=lambda: self._entry_copy(entry))
        menu.add_command(label="Вставить", command=lambda: self._entry_paste(entry))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: self._entry_select_all(entry))
        self.command_entry_context_menu = menu

        entry.bind("<Control-c>", lambda _event: self._entry_copy(entry))
        entry.bind("<Control-C>", lambda _event: self._entry_copy(entry))
        entry.bind("<Control-v>", lambda _event: self._entry_paste(entry))
        entry.bind("<Control-V>", lambda _event: self._entry_paste(entry))
        entry.bind("<Control-x>", lambda _event: self._entry_cut(entry))
        entry.bind("<Control-X>", lambda _event: self._entry_cut(entry))
        entry.bind("<Control-a>", lambda _event: self._entry_select_all(entry))
        entry.bind("<Control-A>", lambda _event: self._entry_select_all(entry))
        entry.bind("<Shift-Insert>", lambda _event: self._entry_paste(entry))
        entry.bind("<Button-3>", lambda event: self._show_context_menu(menu, event))

    def _bind_readonly_text_copy(self, widget) -> None:
        menu = self.tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self._text_copy(widget))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: self._text_select_all(widget))
        widget.readonly_context_menu = menu
        widget.bind("<Control-c>", lambda _event: self._text_copy(widget))
        widget.bind("<Control-C>", lambda _event: self._text_copy(widget))
        widget.bind("<Control-a>", lambda _event: self._text_select_all(widget))
        widget.bind("<Control-A>", lambda _event: self._text_select_all(widget))
        widget.bind("<Button-3>", lambda event: self._show_context_menu(menu, event))
        for sequence in ("<Key>", "<Control-v>", "<Control-V>", "<Control-x>", "<Control-X>"):
            widget.bind(sequence, lambda _event: "break")

    def _entry_copy(self, entry):
        try:
            selected = entry.selection_get()
            self._clipboard_set(selected)
        except Exception:
            pass
        return "break"

    def _entry_cut(self, entry):
        try:
            selected = entry.selection_get()
            self._clipboard_set(selected)
            entry.delete("sel.first", "sel.last")
        except Exception:
            pass
        return "break"

    def _entry_paste(self, entry):
        try:
            text = self.root.clipboard_get()
            try:
                entry.delete("sel.first", "sel.last")
            except Exception:
                pass
            entry.insert("insert", text)
        except Exception:
            pass
        return "break"

    @staticmethod
    def _entry_select_all(entry):
        try:
            entry.selection_range(0, "end")
            entry.icursor("end")
        except Exception:
            pass
        return "break"

    def _text_copy(self, widget):
        try:
            selected = widget.get("sel.first", "sel.last")
            self._clipboard_set(selected)
        except Exception:
            pass
        return "break"

    @staticmethod
    def _text_select_all(widget):
        try:
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
        except Exception:
            pass
        return "break"

    def _clipboard_set(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(str(text))

    @staticmethod
    def _show_context_menu(menu, event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
        return "break"

    def _render_state(self) -> None:
        state = self.view_model.state
        self._set_text(self.status_box, state.status_text)
        self._set_text(self.preview_box, state.preview_text)
        self._set_text(self.output_box, state.output_text)
        self._set_text(self.command_list_box, state.command_list_text)
        self._render_history_state(state)
        self._render_workflow_state(state)

    def _render_history_state(self, state) -> None:
        if self.history_search_var.get() != state.history_search_query:
            self.history_search_var.set(state.history_search_query)
        if self.history_status_var.get() != state.history_status_filter:
            self.history_status_var.set(state.history_status_filter)
        self.history_count_label.configure(text=state.history_result_count_text)
        self.history_list.delete(0, "end")
        entries = tuple(getattr(state, "history_entries", ()) or ())
        if entries:
            for entry in entries:
                summary = (
                    entry.summary_text()
                    if hasattr(entry, "summary_text")
                    else self.view_model._fallback_history_summary(entry)
                )
                self.history_list.insert("end", self.view_model._safe_text(summary))
            selected_id = getattr(state, "selected_history_id", None)
            selected_index = 0
            for index, entry in enumerate(entries):
                if getattr(entry, "entry_id", None) == selected_id:
                    selected_index = index
                    break
            self.history_list.selection_set(selected_index)
            self.history_list.see(selected_index)
        else:
            if getattr(state, "history_load_error", None):
                self.history_list.insert("end", "History unavailable")
            elif getattr(state, "loaded_history_entries", ()):
                self.history_list.insert("end", "No history entries match the current filters.")
            else:
                self.history_list.insert("end", "No execution history is available.")
        copy_state = "normal" if getattr(state, "selected_history_id", None) else "disabled"
        self.history_copy_button.configure(state=copy_state)
        self._set_text(self.history_details_box, state.selected_history_details_text)

    def _render_workflow_state(self, state) -> None:
        self.workflow_list.delete(0, "end")
        runs = tuple(getattr(state, "workflow_runs", ()) or ())
        if runs:
            for run in runs:
                self.workflow_list.insert("end", self.view_model._workflow_run_summary(run))
            selected_id = getattr(state, "selected_workflow_run_id", None)
            selected_index = 0
            for index, run in enumerate(runs):
                run_id = getattr(run, "run_id", None) or getattr(run, "operation_id", None)
                if run_id == selected_id:
                    selected_index = index
                    break
            self.workflow_list.selection_set(selected_index)
            self.workflow_list.see(selected_index)
        else:
            if getattr(state, "workflow_load_error", None):
                self.workflow_list.insert("end", "Workflow history unavailable")
            else:
                self.workflow_list.insert("end", "No workflow runs available.")
        copy_state = "normal" if getattr(state, "selected_workflow_run_id", None) else "disabled"
        self.workflow_copy_button.configure(state=copy_state)
        resume_state = (
            "normal"
            if getattr(state, "workflow_resume_available", False)
            and not getattr(state, "workflow_resume_in_progress", False)
            else "disabled"
        )
        self.workflow_resume_button.configure(state=resume_state)
        self._set_text(self.workflow_details_box, state.workflow_details_text)

    @staticmethod
    def _set_text(widget, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _command_input(self) -> str:
        return self.command_entry.get().strip()

    def _on_preview(self) -> None:
        self.view_model.preview_command(self._command_input())
        self._render_state()

    def _on_execute(self) -> None:
        self.view_model.execute_command(self._command_input())
        self.view_model.refresh_execution_history()
        self.view_model.refresh_workflow_history()
        self._render_state()

    def _on_voice_once(self) -> None:
        if self._voice_worker_active:
            return
        self._voice_worker_active = True
        self.voice_button.configure(state="disabled")
        self.view_model.state = self.view_model._replace(
            output_text=(
                "Одноразовый голосовой запрос активен.\n"
                "Запись и локальное распознавание запущены после явного нажатия кнопки."
            ),
            last_error=None,
        )
        self._render_state()

        def worker():
            try:
                self.view_model.process_one_shot_voice_request()
            finally:
                self.root.after(0, self._finish_voice_once)

        Thread(target=worker, daemon=True).start()

    def _finish_voice_once(self) -> None:
        self._voice_worker_active = False
        self.voice_button.configure(state="normal")
        self.view_model.refresh_execution_history()
        self.view_model.refresh_workflow_history()
        self._render_state()

    def _on_status(self) -> None:
        self.view_model.refresh_status()
        self._render_state()

    def _on_registry(self) -> None:
        self.view_model.list_commands(None)
        self._render_state()

    def _on_ai_status(self) -> None:
        self.command_entry.delete(0, "end")
        self.command_entry.insert(0, "статус ai")
        self.view_model.preview_command("статус ai")
        self._render_state()

    def _on_app_service(self) -> None:
        self.command_entry.delete(0, "end")
        self.command_entry.insert(0, "статус app service")
        self.view_model.preview_command("статус app service")
        self._render_state()

    def _on_category_selected(self, _event) -> None:
        selection = self.category_list.curselection()
        if not selection:
            return
        category = self.category_list.get(selection[0])
        self.view_model.list_commands(category)
        self._render_state()

    def _on_history_refresh(self) -> None:
        self.view_model.refresh_execution_history()
        self._render_state()

    def _on_history_search_changed(self, _event) -> None:
        self.view_model.update_history_search(self.history_search_var.get())
        self._render_history_state(self.view_model.state)

    def _on_history_status_changed(self, value) -> None:
        self.view_model.update_history_status_filter(value)
        self._render_history_state(self.view_model.state)

    def _on_history_clear_filters(self) -> None:
        self.view_model.clear_history_filters()
        self._render_history_state(self.view_model.state)

    def _on_history_selected(self, _event) -> None:
        selection = self.history_list.curselection()
        if not selection:
            self.view_model.select_history_entry(None)
        else:
            self.view_model.select_history_entry(selection[0])
        self._render_state()

    def _on_history_copy(self) -> None:
        text = self.view_model.selected_history_copy_text()
        if text:
            self._clipboard_set(text)

    def _on_workflow_refresh(self) -> None:
        self.view_model.refresh_workflow_history()
        self._render_state()

    def _on_workflow_selected(self, _event) -> None:
        selection = self.workflow_list.curselection()
        if not selection:
            self.view_model.select_workflow_run(None)
        else:
            self.view_model.select_workflow_run(selection[0])
        self._render_state()

    def _on_workflow_copy(self) -> None:
        text = self.view_model.selected_workflow_copy_text()
        if text:
            self._clipboard_set(text)

    def _on_workflow_resume(self) -> None:
        confirmation_text = self.view_model.workflow_resume_confirmation_text()
        if not self._confirm_workflow_resume(confirmation_text):
            self.view_model.resume_selected_workflow_run(confirmed=False)
            self._render_state()
            return
        self.view_model.resume_selected_workflow_run(confirmed=True)
        self._render_state()

    def _confirm_workflow_resume(self, text: str) -> bool:
        try:
            from tkinter import messagebox

            return bool(messagebox.askyesno("Workflow Resume", self.view_model._safe_text(text)))
        except Exception:
            return False


def launch_desktop_shell() -> bool:
    """Launch the tkinter desktop shell, returning False if GUI is unavailable."""

    try:
        app_service = JarvisAppService()
        view_model = DesktopShellViewModel(app_service)
        shell = JarvisDesktopShell(view_model)
        shell.run()
        return True
    except ImportError:
        print("JARVIS desktop shell: tkinter is unavailable. Run CLI with python run.py.")
        return False
    except Exception as exc:
        exc_name = exc.__class__.__name__.lower()
        if "tcl" in exc_name or "display" in str(exc).lower():
            print(
                "JARVIS desktop shell: GUI cannot initialize in this environment. "
                "Run on Windows with tkinter available."
            )
            return False
        raise
