import pytest

from app import AppCommandSource, JarvisAppService
from cognition import (
    AssistantResponseType,
    ClarificationRequest,
    ClarificationReason,
    ClarificationStatus,
    ConversationSessionClosedError,
    ConversationSessionStatus,
    IntentCategory,
    IntentConfidence,
    IntentEvidence,
    InterpretedIntent,
    ReferenceResolutionResult,
    LocalConversationSessionRepository,
    ResponseCompositionResult,
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


def test_app_service_can_recover_sessions_through_injected_repository(tmp_path):
    repository = LocalConversationSessionRepository(tmp_path)
    first_service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_session_repository=repository,
    )
    session = first_service.start_conversation_session()
    first_service.handle_conversation_turn("hello", AppCommandSource.TEST, session.session_id)

    restarted = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_session_repository=LocalConversationSessionRepository(tmp_path),
    )
    snapshot = restarted.conversation_session_snapshot(session.session_id)

    assert snapshot.session_id == session.session_id
    assert snapshot.turn_count == 2


def test_app_service_conversation_turn_flows_through_context_and_composer():
    calls = []

    class TrackingComposer:
        def compose(self, composition_input):
            calls.append(composition_input)
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text=f"used context {composition_input.context.included_turn_count}",
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="test",
            )

    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_response_composer=TrackingComposer(),
    )

    result = service.handle_conversation_turn("hello", AppCommandSource.TEST)

    assert len(calls) == 1
    assert calls[0].context.included_turn_count == 1
    assert result.response.text == "used context 1"
    assert result.composition.context_turn_count_used == 1


def test_app_service_conversation_turn_flows_through_interpreter():
    calls = []

    class TrackingInterpreter:
        def interpret(self, interpretation_input):
            calls.append(interpretation_input)
            return InterpretedIntent(
                category=IntentCategory.QUESTION,
                confidence=IntentConfidence.MEDIUM,
                safe_user_text=interpretation_input.current_user_turn.text,
                evidence=(
                    IntentEvidence(
                        evidence_type="rule",
                        safe_excerpt=interpretation_input.current_user_turn.text,
                        rule_id="direct_question",
                    ),
                ),
                requires_reference_resolution=False,
                may_require_clarification=False,
                is_actionable_request=False,
                interpreter_id="test",
                interpreter_version="1",
                context_turn_count_used=interpretation_input.context.included_turn_count,
            )

    class TrackingComposer:
        def compose(self, composition_input):
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text=composition_input.interpreted_intent.category.value,
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="test",
            )

    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_intent_interpreter=TrackingInterpreter(),
        cognitive_response_composer=TrackingComposer(),
    )

    result = service.handle_conversation_turn("what is this?", AppCommandSource.TEST)

    assert len(calls) == 1
    assert calls[0].context.included_turn_count == 1
    assert result.intent.category is IntentCategory.QUESTION
    assert result.response.text == "question"


def test_app_service_conversation_turn_flows_through_reference_resolver():
    calls = []

    class TrackingResolver:
        def resolve(self, resolution_input):
            calls.append(resolution_input)
            return ReferenceResolutionResult(
                references=(),
                has_unresolved_references=False,
                has_ambiguous_references=False,
                context_turn_count_used=resolution_input.context.included_turn_count,
                resolver_id="test",
                resolver_version="1",
            )

    class TrackingComposer:
        def compose(self, composition_input):
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text=f"refs {len(composition_input.reference_resolution.references)}",
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="test",
            )

    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_reference_resolver=TrackingResolver(),
        cognitive_response_composer=TrackingComposer(),
    )

    result = service.handle_conversation_turn("what about it?", AppCommandSource.TEST)

    assert len(calls) == 1
    assert calls[0].interpreted_intent is result.intent
    assert result.references.references == ()
    assert result.response.text == "refs 0"


def test_app_service_constructs_and_injects_clarification_coordinator():
    calls = []

    class TrackingCoordinator:
        def coordinate(self, coordination_input):
            calls.append(coordination_input)
            return ClarificationRequest(
                status=ClarificationStatus.NEEDED,
                reason=ClarificationReason.UNCLEAR_CONFIRMATION,
                safe_question="What are you confirming?",
                options=(),
                related_reference_count=0,
                context_turn_count_used=coordination_input.context.included_turn_count,
                coordinator_id="test",
                coordinator_version="1",
                rule_id="test_rule",
            )

    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_clarification_coordinator=TrackingCoordinator(),
    )

    result = service.handle_conversation_turn("yes", AppCommandSource.TEST)

    assert len(calls) == 1
    assert result.clarification.status is ClarificationStatus.NEEDED
    assert result.response.text == "What are you confirming?"


def test_app_service_execute_routes_unresolved_russian_action_to_clarification():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.execute_command("\u0421\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e", AppCommandSource.TEST)

    assert result.requires_clarification is True
    assert result.category == "clarification"
    assert result.executed is False
    assert result.operation_status == "awaiting_clarification"
    assert "\u044d\u0442\u043e" in result.clarification_question.casefold()
    assert processor.calls == []


def test_app_service_execute_does_not_route_clarification_controls_to_legacy_voice():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)
    first = service.execute_command("\u0421\u0434\u0435\u043b\u0430\u0439 \u044d\u0442\u043e", AppCommandSource.TEST)

    confirm = service.execute_command("\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u044e", AppCommandSource.TEST)
    cancel = service.execute_command("\u043e\u0442\u043c\u0435\u043d\u0430", AppCommandSource.TEST)

    assert confirm.category == "clarification"
    assert confirm.requires_clarification is True
    assert confirm.operation_status == "awaiting_clarification"
    assert cancel.category == "clarification"
    assert cancel.requires_confirmation is False
    assert cancel.operation_status == "cancelled"
    assert first.operation_id == confirm.operation_id == cancel.operation_id
    assert "voice" not in confirm.output_text.casefold()
    assert "voice" not in cancel.output_text.casefold()
    assert processor.calls == []


def test_context_composition_does_not_call_provider_execution_workflow_or_memory():
    class ForbiddenProviderRuntime:
        def all_credential_statuses(self):
            raise AssertionError("conversation composition must not inspect providers")

    class ForbiddenCoordinator:
        def register(self, *_, **__):
            raise AssertionError("conversation composition must not register execution")

    class ForbiddenRunner:
        def start(self, *_, **__):
            raise AssertionError("conversation composition must not start workflow")

    class ForbiddenMemory:
        def remember(self, *_, **__):
            raise AssertionError("conversation composition must not write memory")

    service = JarvisAppService(command_processor=FakeCommandProcessor())
    service._provider_runtime_component = ForbiddenProviderRuntime()
    service.execution_coordinator = ForbiddenCoordinator()
    service.document_review_runner = ForbiddenRunner()
    service.memory_manager = ForbiddenMemory()

    result = service.handle_conversation_turn("hello", AppCommandSource.TEST)

    assert result.response.response_type is AssistantResponseType.MESSAGE
