"""Safe tkinter desktop shell prototype for JARVIS.

The shell is a UI boundary only. It talks to JarvisAppService for status,
registry browsing, preview, and explicit execution.
"""

from dataclasses import dataclass
import re

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
    last_error: str | None
    ui_ready: bool
    safe_mode: bool


class DesktopShellViewModel:
    """Pure app-shell logic that can be tested without opening a GUI."""

    def __init__(self, app_service: JarvisAppService):
        self.app_service = app_service
        self.state = self.build_initial_state()

    def build_initial_state(self) -> DesktopShellState:
        status_text = self.safe_status_text_ru()
        try:
            command_list_text = self._safe_text(self.app_service.list_commands(None))
        except Exception as exc:
            command_list_text = self._safe_error(exc)
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

    def clear_output(self) -> str:
        output_text = "Output cleared. No command has been executed by clear."
        self.state = self._replace(
            preview_text="Command preview cleared.",
            output_text=output_text,
            last_error=None,
        )
        return output_text

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
            "- executed through AppService: yes",
            f"- network may be used: {'yes' if getattr(result, 'network_may_be_used', False) else 'no'}",
            "- response executed as command: no",
            "- no secrets",
        ]
        error = getattr(result, "error", None)
        if error:
            lines.append(f"- error: {error}")
        output_text = getattr(result, "output_text", "")
        if output_text:
            lines.append("Output:")
            lines.append(str(output_text))
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
        main.grid_rowconfigure(3, weight=1)

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

        note = tk.Label(
            main,
            text="No auto-execution. Network/provider commands require explicit command text and Execute.",
            bg=self.COLORS["bg"],
            fg=self.COLORS["warning"],
            anchor="w",
        )
        note.grid(row=1, column=0, sticky="ew", pady=8)

        split = tk.PanedWindow(main, orient="vertical", bg=self.COLORS["bg"], sashwidth=6)
        split.grid(row=3, column=0, sticky="nsew")
        self.preview_box = self._text_box(split, height=10)
        self.output_box = self._text_box(split, height=14)
        self.command_list_box = self._text_box(split, height=10)
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

    def _render_state(self) -> None:
        state = self.view_model.state
        self._set_text(self.status_box, state.status_text)
        self._set_text(self.preview_box, state.preview_text)
        self._set_text(self.output_box, state.output_text)
        self._set_text(self.command_list_box, state.command_list_text)

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
