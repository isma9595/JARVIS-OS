import pytest

from app import AppCommandSource, JarvisAppService
from cognition import (
    AssistantResponseType,
    ConversationSessionClosedError,
    ConversationSessionStatus,
)


class FakeCommandProcessor:
    def __init__(self):
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        return {"response": f"processed: {text}"}


def test_app_service_conversation_session_api_works_without_execution():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    session = service.start_conversation_session()
    result = service.handle_conversation_turn(
        "hello",
        AppCommandSource.TEST,
        session.session_id,
    )
    snapshot = service.conversation_session_snapshot(session.session_id)
    turns = service.cognitive_session_service.turns_snapshot(session.session_id)

    assert snapshot.turn_count == 2
    assert result.session.session_id == session.session_id
    assert result.response.response_type is AssistantResponseType.MESSAGE
    assert "command executed: no" in result.response.text
    assert processor.calls == []
    assert [turn.sequence for turn in turns] == [1, 2]


def test_app_service_missing_session_id_creates_session():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    result = service.handle_conversation_turn("hello", AppCommandSource.TEST)

    assert result.session.session_id.startswith("cog-session-")
    assert result.session.turn_count == 2


def test_app_service_close_conversation_session_rejects_later_turns():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    session = service.start_conversation_session()

    closed = service.close_conversation_session(session.session_id)

    assert closed.status is ConversationSessionStatus.CLOSED
    with pytest.raises(ConversationSessionClosedError):
        service.handle_conversation_turn("hello", AppCommandSource.TEST, session.session_id)


def test_existing_app_service_preview_and_execute_behavior_remain_unchanged():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    preview = service.preview_command("app contracts status")
    result = service.execute_command("app contracts status", AppCommandSource.TEST)

    assert preview.known_command is True
    assert preview.registry_match_id == "app_contracts.status"
    assert processor.calls == ["app contracts status"]
    assert result.registry_match_id == "app_contracts.status"
    assert result.response_executed_as_command is False


def test_session_creation_and_snapshot_do_not_call_execution_workflow_or_provider_boundaries():
    class ForbiddenCoordinator:
        def register(self, *_, **__):
            raise AssertionError("session API must not register execution")

    class ForbiddenRunner:
        def start(self, *_, **__):
            raise AssertionError("session API must not start workflows")

        def recent_run_histories(self, *_, **__):
            raise AssertionError("session API must not inspect workflow history")

    class ForbiddenProviderRuntime:
        def all_credential_statuses(self):
            raise AssertionError("session API must not inspect providers")

    service = JarvisAppService(command_processor=FakeCommandProcessor())
    service.execution_coordinator = ForbiddenCoordinator()
    service.document_review_runner = ForbiddenRunner()
    service._provider_runtime_component = ForbiddenProviderRuntime()

    session = service.start_conversation_session()
    snapshot = service.conversation_session_snapshot(session.session_id)

    assert snapshot.session_id == session.session_id
    assert snapshot.turn_count == 0
