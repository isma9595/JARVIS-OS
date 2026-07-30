from pathlib import Path

from app import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from language.language_manager import ApplicationLanguageManager
from memory import LocalMemoryManager, SessionConversationContext
from users.user_profile import UserProfileManager


REMEMBER_AUDIT_KEY = "remember that audit091key is north"
RECALL_AUDIT_KEY = "what do you remember about audit091key"
FORGET_AUDIT_KEY = "forget audit091key"
SET_LANGUAGE_EN = "language English"


class TrackingProcessor:
    def __init__(self):
        self.calls = []
        self.user_profile = None
        self.memory_manager = None
        self.language_manager = None

    def process(self, text):
        self.calls.append(text)
        return {"response": f"processed: {text}"}


def make_service(tmp_path: Path):
    memory = LocalMemoryManager(tmp_path / "task091_memory.json")
    profile = UserProfileManager(tmp_path / "task091_profile.json")
    language = ApplicationLanguageManager.from_profile_manager(profile)
    processor = TrackingProcessor()
    service = JarvisAppService(
        command_processor=processor,
        memory_manager=memory,
        language_manager=language,
        conversation_context=SessionConversationContext(),
    )
    return service, processor, memory, language


def memory_entries(memory):
    return memory.list_user_facts().entries


def assert_memory_preview_recognized_and_non_mutating(
    service,
    memory,
    command,
    *,
    command_id,
    risk,
    read_only,
):
    before_entries = memory_entries(memory)
    preview = service.preview_command(command)
    after_entries = memory_entries(memory)

    assert preview.known_command is True
    assert preview.registry_match_id == command_id
    assert preview.category == "memory"
    assert preview.risk_level == risk
    assert preview.read_only is read_only
    assert preview.requires_confirmation is False
    assert preview.requires_network is False
    assert preview.operation_id is None
    assert after_entries == before_entries
    assert service.recent_execution_operations(None) == ()
    assert service._pending_memory_forget_all is None
    return preview


def assert_desktop_fields(
    diagnostics,
    *,
    command_id,
    category,
    risk,
    requires_confirmation,
    operation_status,
):
    assert "Desktop turn diagnostics:" in diagnostics
    assert "- route: execution" in diagnostics
    assert f"- command id: {command_id}" in diagnostics
    assert f"- category: {category}" in diagnostics
    assert f"- risk: {risk}" in diagnostics
    assert f"- requires confirmation: {requires_confirmation}" in diagnostics
    assert "- operation id: op-" in diagnostics
    assert f"- operation status: {operation_status}" in diagnostics


def test_characterizes_current_preview_execute_memory_remember(tmp_path):
    service, processor, memory, _language = make_service(tmp_path)

    assert_memory_preview_recognized_and_non_mutating(
        service,
        memory,
        REMEMBER_AUDIT_KEY,
        command_id="memory.remember",
        risk="local_write",
        read_only=False,
    )

    result = service.execute_command(REMEMBER_AUDIT_KEY, AppCommandSource.TEST)

    assert result.registry_match_id == "memory.remember"
    assert result.category == "memory"
    assert result.risk_level == "local_write"
    assert result.executed is True
    assert result.requires_confirmation is False
    assert result.network_may_be_used is False
    assert result.response_executed_as_command is False
    assert result.operation_id is not None
    assert result.operation_status == "succeeded"
    operation = service.recent_execution_operations(1)[0]
    assert operation["command_id"] == "memory.remember"
    assert operation["status"] == "succeeded"
    assert operation["metadata"]["risk_level"] == "local_write"
    assert memory.recall_user_fact("audit091key").value == "north"
    assert processor.calls == []


def test_characterizes_current_preview_execute_memory_recall(tmp_path):
    service, processor, memory, _language = make_service(tmp_path)
    memory.remember_user_fact("audit091key", "north")
    before_preview_entries = memory_entries(memory)

    assert_memory_preview_recognized_and_non_mutating(
        service,
        memory,
        RECALL_AUDIT_KEY,
        command_id="memory.recall",
        risk="read_only",
        read_only=True,
    )

    result = service.execute_command(RECALL_AUDIT_KEY, AppCommandSource.TEST)
    after_execute_entries = memory_entries(memory)

    assert result.registry_match_id == "memory.recall"
    assert result.category == "memory"
    assert result.risk_level == "read_only"
    assert result.executed is False
    assert result.requires_confirmation is False
    assert result.network_may_be_used is False
    assert result.response_executed_as_command is False
    assert result.operation_id is None
    assert result.operation_status == "succeeded"
    assert "north" in result.output_text
    assert after_execute_entries == before_preview_entries
    assert processor.calls == []


def test_characterizes_current_preview_execute_memory_forget(tmp_path):
    service, processor, memory, _language = make_service(tmp_path)
    memory.remember_user_fact("audit091key", "north")
    before_preview_entries = memory_entries(memory)

    assert_memory_preview_recognized_and_non_mutating(
        service,
        memory,
        FORGET_AUDIT_KEY,
        command_id="memory.forget",
        risk="local_write",
        read_only=False,
    )
    assert memory_entries(memory) == before_preview_entries
    assert memory.recall_user_fact("audit091key").found is True

    result = service.execute_command(FORGET_AUDIT_KEY, AppCommandSource.TEST)

    assert result.registry_match_id == "memory.forget"
    assert result.category == "memory"
    assert result.risk_level == "local_write"
    assert result.executed is True
    assert result.requires_confirmation is False
    assert result.network_may_be_used is False
    assert result.response_executed_as_command is False
    assert result.operation_id is not None
    assert result.operation_status == "succeeded"
    operation = service.recent_execution_operations(1)[0]
    assert operation["command_id"] == "memory.forget"
    assert operation["status"] == "succeeded"
    assert operation["metadata"]["risk_level"] == "local_write"
    assert memory.recall_user_fact("audit091key").found is False
    assert memory_entries(memory) == ()
    assert processor.calls == []


def test_characterizes_current_state_changing_metadata_for_memory_and_language(tmp_path):
    service, _processor, memory, language = make_service(tmp_path)

    memory_preview = service.preview_command(REMEMBER_AUDIT_KEY)
    remember = service.execute_command(REMEMBER_AUDIT_KEY, AppCommandSource.TEST)
    forget = service.execute_command(FORGET_AUDIT_KEY, AppCommandSource.TEST)

    language_before_preview = language.get_preference().language_code
    language_preview = service.preview_command(SET_LANGUAGE_EN)
    language_after_preview = language.get_preference().language_code
    language_result = service.execute_command(SET_LANGUAGE_EN, AppCommandSource.TEST)
    language_after_execute = language.get_preference().language_code
    desktop_service, _desktop_processor, _desktop_memory, _desktop_language = make_service(
        tmp_path / "desktop_route"
    )
    desktop = DesktopShellViewModel(desktop_service)
    desktop_text = desktop.execute_command(SET_LANGUAGE_EN)

    # TASK-096 CONTRACT: state-changing routes preserve local-write metadata
    # and operation journal identity when they mutate isolated state.
    assert (memory_preview.known_command, memory_preview.registry_match_id) == (
        True,
        "memory.remember",
    )
    assert memory_preview.category == "memory"
    assert memory_preview.risk_level == "local_write"
    assert memory_preview.requires_confirmation is False
    assert (remember.registry_match_id, remember.category, remember.risk_level) == (
        "memory.remember",
        "memory",
        "local_write",
    )
    assert remember.executed is True
    assert remember.requires_confirmation is False
    assert remember.operation_id is not None
    assert remember.operation_status == "succeeded"

    assert (forget.registry_match_id, forget.category, forget.risk_level) == (
        "memory.forget",
        "memory",
        "local_write",
    )
    assert forget.executed is True
    assert forget.requires_confirmation is False
    assert forget.operation_id is not None
    assert forget.operation_status == "succeeded"
    assert memory.list_user_facts().entries == ()

    assert (language_preview.known_command, language_preview.registry_match_id) == (
        True,
        "profile.language.set",
    )
    assert language_preview.category == "profile"
    assert language_preview.risk_level == "read_only"
    assert language_preview.read_only is False
    assert language_preview.requires_confirmation is False
    assert language_after_preview == language_before_preview

    assert language_result.registry_match_id == "profile.language.set"
    assert language_result.category == "profile"
    assert language_result.risk_level == "local_write"
    assert language_result.executed is True
    assert language_result.requires_confirmation is False
    assert language_result.network_may_be_used is False
    assert language_result.response_executed_as_command is False
    assert language_result.operation_id is not None
    assert language_result.operation_status == "succeeded"
    operation = service.recent_execution_operations(1)[0]
    assert operation["command_id"] == "profile.language.set"
    assert operation["status"] == "succeeded"
    assert operation["metadata"]["risk_level"] == "local_write"
    assert language_after_execute == "en-US"

    assert desktop_text == "Language preference changed to English."
    assert "command id: profile.language.set" not in desktop_text
    assert "command id: profile.language.set" in desktop.state.diagnostics_text
    assert "risk: local_write" in desktop.state.diagnostics_text
    assert "requires confirmation: no" in desktop.state.diagnostics_text


def test_characterizes_current_desktop_memory_and_language_execution_fields(tmp_path):
    remember_service, remember_processor, remember_memory, _remember_language = make_service(
        tmp_path / "desktop_remember"
    )
    remember_desktop = DesktopShellViewModel(remember_service)
    remember_text = remember_desktop.execute_command(REMEMBER_AUDIT_KEY)

    forget_service, forget_processor, forget_memory, _forget_language = make_service(
        tmp_path / "desktop_forget"
    )
    forget_memory.remember_user_fact("audit091key", "north")
    forget_desktop = DesktopShellViewModel(forget_service)
    forget_text = forget_desktop.execute_command(FORGET_AUDIT_KEY)

    language_service, language_processor, _language_memory, language = make_service(
        tmp_path / "desktop_language"
    )
    language_desktop = DesktopShellViewModel(language_service)
    language_text = language_desktop.execute_command(SET_LANGUAGE_EN)

    # TASK-096 metadata remains available through the TASK-120 diagnostics
    # projection while the primary Desktop output stays user-facing.
    assert_desktop_fields(
        remember_desktop.state.diagnostics_text,
        command_id="memory.remember",
        category="memory",
        risk="local_write",
        requires_confirmation="no",
        operation_status="succeeded",
    )
    assert remember_memory.recall_user_fact("audit091key").value == "north"

    assert_desktop_fields(
        forget_desktop.state.diagnostics_text,
        command_id="memory.forget",
        category="memory",
        risk="local_write",
        requires_confirmation="no",
        operation_status="succeeded",
    )
    assert forget_memory.recall_user_fact("audit091key").found is False

    assert_desktop_fields(
        language_desktop.state.diagnostics_text,
        command_id="profile.language.set",
        category="profile",
        risk="local_write",
        requires_confirmation="no",
        operation_status="succeeded",
    )
    assert language.get_preference().language_code == "en-US"
    assert "command id:" not in remember_text
    assert "command id:" not in forget_text
    assert "command id:" not in language_text
    assert remember_processor.calls == []
    assert forget_processor.calls == []
    assert language_processor.calls == []
