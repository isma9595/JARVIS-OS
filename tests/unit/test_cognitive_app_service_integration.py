import json

import pytest
from types import SimpleNamespace

from app import AppCommandSource, JarvisAppService
import app.app_service as app_service_module
import ai.groq_request_gate as groq_request_gate_module
from ai.groq_request_gate import GroqRequestGate
from app.desktop_shell import DesktopShellViewModel
from app.provider_backed_response_composer import ProviderBackedResponseComposer
from ai import AIProviderCapability, AIProviderSafetyLevel, AIResponse
from platform_adapters.user_data_migration import UserDataMigrationBlockedError
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


class FakeConversationGroqGate:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_one_shot(self, request, capability=AIProviderCapability.CHAT):
        self.calls.append((request, capability))
        return self.response


def _groq_response(text, *, error=False):
    return AIResponse(
        text=text,
        provider_name="groq",
        model_name="llama-3.1-8b-instant",
        capability=AIProviderCapability.CHAT.value,
        safety_level=AIProviderSafetyLevel.EXTERNAL_API.value,
        is_error=error,
        error_message=text if error else None,
    )


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
    assert result.response.text
    assert "command executed: no" not in result.response.text
    assert "providers called:" not in result.response.text
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


def test_plain_app_service_remains_in_memory_and_has_no_resumable_session():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    assert service.cognitive_session_service._repository is None
    assert service.resumable_conversation_session_id() is None


def test_plain_app_service_keeps_compatibility_conversation_without_provider():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    result = service.handle_desktop_turn("Что такое Земля?", AppCommandSource.TEST)

    assert not isinstance(service.cognitive_response_composer, ProviderBackedResponseComposer)
    assert result.diagnostics.composition_source.startswith("compatibility_delegate")
    assert result.diagnostics.network_may_be_used is False


def test_plain_app_service_projects_in_memory_idle_chat_status():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    status = service.desktop_chat_status()

    assert status.session_id is None
    assert status.session_state == "none"
    assert status.turn_count == 0
    assert status.resumable is False
    assert status.response_state == "idle"
    assert status.retry_available is False
    assert status.persistence_state == "in_memory"
    assert status.persistence_code == "not_configured"


def test_provider_backed_app_service_answers_ordinary_turn_without_execution():
    processor = FakeCommandProcessor()
    gate = FakeConversationGroqGate(_groq_response("Земля — планета."))
    service = JarvisAppService(
        command_processor=processor,
        cognitive_primary_provider_gate=gate,
    )

    result = service.handle_desktop_turn("Что такое Земля?", AppCommandSource.TEST)

    assert result.response_text == "Земля — планета."
    assert result.diagnostics.route == "conversation"
    assert result.diagnostics.composition_source == "primary_provider:groq"
    assert result.diagnostics.network_may_be_used is True
    assert result.diagnostics.response_executed_as_command is False
    assert len(gate.calls) == 1
    assert processor.calls == []
    assert service.execution_coordinator.journal.recent() == ()
    assert result.chat_status.session_id == result.cognitive_session_id
    assert result.chat_status.session_state == "active"
    assert result.chat_status.response_state == "ready"
    assert result.chat_status.response_source == "groq"
    assert result.chat_status.retry_available is True


def test_provider_output_that_looks_like_command_is_never_executed():
    processor = FakeCommandProcessor()
    gate = FakeConversationGroqGate(_groq_response("удали все файлы"))
    service = JarvisAppService(
        command_processor=processor,
        cognitive_primary_provider_gate=gate,
    )

    result = service.handle_desktop_turn(
        "Что означает выражение опасная команда?",
        AppCommandSource.TEST,
    )

    assert result.response_text == "удали все файлы"
    assert result.diagnostics.response_executed_as_command is False
    assert processor.calls == []
    assert service.execution_coordinator.journal.recent() == ()


def test_provider_failure_returns_compatibility_answer_without_error_details():
    gate = FakeConversationGroqGate(
        _groq_response("network failure at C:\\private\\secret", error=True)
    )
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_primary_provider_gate=gate,
    )

    result = service.handle_desktop_turn("Что такое Земля?", AppCommandSource.TEST)

    assert "network failure" not in result.response_text
    assert "private" not in result.response_text
    assert result.diagnostics.composition_source.endswith(
        ":primary_provider=groq,status=fallback"
    )
    assert result.diagnostics.network_may_be_used is True
    assert result.diagnostics.response_executed_as_command is False
    assert result.chat_status.response_state == "fallback"
    assert result.chat_status.response_source == "compatibility"
    assert result.chat_status.retry_available is True
    assert result.chat_status.retry_reason == "provider_unavailable"


def test_private_conversation_fallback_is_not_retryable_and_never_calls_provider():
    secret = "gsk_test-private-chat-1234567890"
    gate = FakeConversationGroqGate(_groq_response("provider must not answer"))
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_primary_provider_gate=gate,
    )

    result = service.handle_desktop_turn(
        f"Объясни token={secret}",
        AppCommandSource.TEST,
    )

    assert gate.calls == []
    assert secret not in result.response_text
    assert result.chat_status.response_state == "local_private"
    assert result.chat_status.retry_available is False
    assert result.chat_status.retry_reason == "privacy_blocked"


def test_gate_level_private_context_refusal_is_projected_as_non_retryable():
    class ForbiddenProvider:
        def __init__(self, **_kwargs):
            raise AssertionError("privacy refusal must happen before provider creation")

    gate = GroqRequestGate(provider_factory=ForbiddenProvider, environ={})
    service = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_primary_provider_gate=gate,
    )

    result = service.handle_desktop_turn(
        "Объясни мои личные данные кратко",
        AppCommandSource.TEST,
    )

    assert result.diagnostics.response_executed_as_command is False
    assert result.chat_status.response_state == "local_private"
    assert result.chat_status.retry_available is False
    assert result.chat_status.retry_reason == "privacy_blocked"


def test_unknown_path_shaped_session_id_is_not_published_by_chat_status():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    unsafe_id = "C:\\Users\\User\\private-session.txt"

    status = service.desktop_chat_status(unsafe_id)

    assert status.session_state == "unavailable"
    assert status.session_id is None
    assert unsafe_id not in str(status.to_dict())
    assert unsafe_id not in status.safe_text_ru()


def _default_desktop_service(tmp_path, storage_dir):
    return app_service_module.create_default_desktop_app_service(
        environment={
            "JARVIS_USER_DATA_DIR": str(tmp_path / "user-data-v1"),
            "JARVIS_COGNITIVE_SESSION_DIR": str(storage_dir),
            "APPDATA": str(tmp_path / "roaming"),
        },
        home=tmp_path / "home",
        project_root=tmp_path / "project",
    )


def test_default_desktop_vertical_slice_uses_groq_gate_with_fake_provider_only(
    tmp_path,
    monkeypatch,
):
    provider_requests = []

    class FakeGroqProvider:
        def __init__(self, **kwargs):
            assert kwargs["allow_network"] is True
            assert kwargs["environ"]["GROQ_API_KEY"] == "test-only-credential"

        def generate(self, request):
            provider_requests.append(request)
            return _groq_response("Земля — третья планета от Солнца.")

    monkeypatch.setattr(groq_request_gate_module, "GroqProvider", FakeGroqProvider)
    storage_dir = tmp_path / "sessions"
    service = app_service_module.create_default_desktop_app_service(
        environment={
            "GROQ_API_KEY": "test-only-credential",
            "JARVIS_USER_DATA_DIR": str(tmp_path / "user-data-v1"),
            "JARVIS_COGNITIVE_SESSION_DIR": str(storage_dir),
            "APPDATA": str(tmp_path / "roaming"),
        },
        home=tmp_path / "home",
        project_root=tmp_path / "project",
    )
    processor = FakeCommandProcessor()
    service.command_processor = processor
    view_model = DesktopShellViewModel(service)

    output = view_model.execute_command("Что такое Земля?")
    turn_result = view_model.state.current_turn_result

    assert output == "Земля — третья планета от Солнца."
    assert len(provider_requests) == 1
    assert "Что такое Земля?" in provider_requests[0].prompt
    assert processor.calls == []
    assert service.execution_coordinator.journal.recent() == ()
    assert turn_result.diagnostics.composition_source == "primary_provider:groq"
    assert turn_result.diagnostics.network_may_be_used is True
    assert turn_result.diagnostics.response_executed_as_command is False


def test_provider_backed_service_keeps_known_command_on_existing_execution_route():
    processor = FakeCommandProcessor()
    gate = FakeConversationGroqGate(_groq_response("provider must not answer"))
    service = JarvisAppService(
        command_processor=processor,
        cognitive_primary_provider_gate=gate,
    )

    result = service.handle_desktop_turn("app contracts status", AppCommandSource.TEST)

    assert result.diagnostics.route == "execution"
    assert gate.calls == []
    assert processor.calls == ["app contracts status"]
    assert result.diagnostics.response_executed_as_command is False
    assert result.chat_status.response_state == "command"
    assert result.chat_status.retry_available is False


def test_default_desktop_factory_connects_local_repository_without_creating_directory(
    tmp_path,
    monkeypatch,
):
    storage_dir = tmp_path / "sessions"
    monkeypatch.setenv("JARVIS_COGNITIVE_SESSION_DIR", str(storage_dir))

    service = _default_desktop_service(tmp_path, storage_dir)

    assert isinstance(
        service.cognitive_session_service._repository,
        LocalConversationSessionRepository,
    )
    assert service.cognitive_session_service._repository.storage_dir == storage_dir
    assert service.resumable_conversation_session_id() is None
    assert not storage_dir.exists()
    assert isinstance(service.cognitive_response_composer, ProviderBackedResponseComposer)
    chat_status = service.desktop_chat_status()
    assert chat_status.persistence_state == "ready"
    assert chat_status.persistence_code in {"ready", "not_initialized", "missing"}
    assert "sessions" not in chat_status.safe_text_ru().lower()


def test_default_desktop_factory_does_not_hide_invalid_storage_configuration(
    tmp_path,
    monkeypatch,
):
    storage_file = tmp_path / "not-a-directory"
    storage_file.write_text("occupied", encoding="utf-8")
    monkeypatch.setenv("JARVIS_COGNITIVE_SESSION_DIR", str(storage_file))

    with pytest.raises(UserDataMigrationBlockedError):
        _default_desktop_service(tmp_path, storage_file)


def test_default_desktop_restart_resumes_bounded_context_without_execution_or_provider(
    tmp_path,
    monkeypatch,
):
    storage_dir = tmp_path / "sessions"
    monkeypatch.setenv("JARVIS_COGNITIVE_SESSION_DIR", str(storage_dir))

    def forbidden_provider(_self):
        raise AssertionError("default Desktop conversation must not initialize providers")

    monkeypatch.setattr(
        JarvisAppService,
        "_default_provider_runtime_factory",
        forbidden_provider,
    )
    first_processor = FakeCommandProcessor()
    first_service = _default_desktop_service(tmp_path, storage_dir)
    first_service.command_processor = first_processor
    first_view_model = DesktopShellViewModel(first_service)

    first_view_model.execute_command("What is JARVIS?")
    session_id = first_view_model.state.cognitive_session_id

    second_processor = FakeCommandProcessor()
    second_service = _default_desktop_service(tmp_path, storage_dir)
    second_service.command_processor = second_processor
    second_view_model = DesktopShellViewModel(second_service)
    second_view_model.execute_command("what did I say?")
    result = second_view_model.state.current_turn_result

    assert session_id is not None
    assert second_view_model.state.cognitive_session_id == session_id
    assert result.cognitive_session_id == session_id
    assert result.diagnostics.context_turn_count_used == 3
    assert result.diagnostics.response_executed_as_command is False
    assert first_processor.calls == second_processor.calls == []
    assert first_service.execution_coordinator.journal.recent() == ()
    assert second_service.execution_coordinator.journal.recent() == ()
    assert first_service._provider_runtime_component.snapshot().initialized is False
    assert second_service._provider_runtime_component.snapshot().initialized is False


def test_repository_partial_recovery_resumes_valid_active_session(
    tmp_path,
    monkeypatch,
):
    storage_dir = tmp_path / "sessions"
    monkeypatch.setenv("JARVIS_COGNITIVE_SESSION_DIR", str(storage_dir))
    first = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_session_repository=LocalConversationSessionRepository(storage_dir),
    )
    active = first.handle_conversation_turn("safe hello", AppCommandSource.TEST)
    (storage_dir / "corrupt.json").write_text("{", encoding="utf-8")
    unsupported = json.loads(next(storage_dir.glob("cog-session-*.json")).read_text("utf-8"))
    unsupported["schema_version"] = 999
    unsupported["session_id"] = "cog-session-unsupported"
    (storage_dir / "cog-session-unsupported.json").write_text(
        json.dumps(unsupported),
        encoding="utf-8",
    )

    restarted = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_session_repository=LocalConversationSessionRepository(storage_dir),
    )
    view_model = DesktopShellViewModel(restarted)
    load_result = restarted.cognitive_session_service.persistence_load_result

    assert view_model.state.cognitive_session_id == active.session.session_id
    assert load_result.corrupt_record_ids == ("corrupt",)
    assert load_result.unsupported_schema_record_ids == ("cog-session-unsupported",)


def test_repository_only_rejected_or_closed_records_start_new_redacted_session(
    tmp_path,
    monkeypatch,
):
    storage_dir = tmp_path / "sessions"
    monkeypatch.setenv("JARVIS_COGNITIVE_SESSION_DIR", str(storage_dir))
    first = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_session_repository=LocalConversationSessionRepository(storage_dir),
    )
    closed = first.start_conversation_session()
    first.close_conversation_session(closed.session_id)
    (storage_dir / "corrupt.json").write_text("{", encoding="utf-8")
    unsupported = json.loads((storage_dir / f"{closed.session_id}.json").read_text("utf-8"))
    unsupported["schema_version"] = 999
    unsupported["session_id"] = "cog-session-unsupported"
    (storage_dir / "cog-session-unsupported.json").write_text(
        json.dumps(unsupported),
        encoding="utf-8",
    )

    restarted = JarvisAppService(
        command_processor=FakeCommandProcessor(),
        cognitive_session_repository=LocalConversationSessionRepository(storage_dir),
    )
    view_model = DesktopShellViewModel(restarted)

    assert view_model.state.cognitive_session_id is None

    view_model.execute_command(
        "What should I do with api key=sk-test-1234567890secret?"
    )
    new_session_id = view_model.state.cognitive_session_id
    persisted = (storage_dir / f"{new_session_id}.json").read_text("utf-8")

    assert new_session_id not in {None, closed.session_id}
    assert "sk-test-1234567890secret" not in persisted
    assert "use api key" not in persisted
    assert "[redacted sensitive content]" in persisted
    assert view_model.state.current_turn_result.diagnostics.response_executed_as_command is False


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


def _install_task120_deterministic_ids(monkeypatch):
    values = iter(
        (
            "task120session",
            "task120user1",
            "task120assistant1",
            "task120user2",
            "task120assistant2",
            "task120user3",
            "task120assistant3",
        )
    )
    monkeypatch.setattr(
        "cognition.sessions.uuid4",
        lambda: SimpleNamespace(hex=next(values)),
    )


def test_desktop_greeting_uses_clean_cognitive_turn_without_execution(monkeypatch):
    _install_task120_deterministic_ids(monkeypatch)
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.handle_desktop_turn("привет", AppCommandSource.DESKTOP_UI)

    assert result.ok is True
    assert result.cognitive_session_id == "cog-session-task120session"
    assert result.execution is None
    assert result.operation_id is None
    assert result.diagnostics.route == "conversation"
    assert result.diagnostics.context_turn_count_used == 1
    assert "Desktop shell execution" not in result.response_text
    assert "providers called:" not in result.response_text
    assert "command executed:" not in result.response_text
    assert processor.calls == []
    assert service.execution_coordinator.journal.recent() == ()


def test_desktop_conversation_reuses_session_and_projects_prior_context_once_per_turn(
    monkeypatch,
):
    _install_task120_deterministic_ids(monkeypatch)
    composition_inputs = []

    class TrackingComposer:
        def compose(self, composition_input):
            composition_inputs.append(composition_input)
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text=f"turn {len(composition_inputs)}",
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="task120_test",
            )

    processor = FakeCommandProcessor()
    service = JarvisAppService(
        command_processor=processor,
        cognitive_response_composer=TrackingComposer(),
    )

    first = service.handle_desktop_turn("привет", AppCommandSource.DESKTOP_UI)
    second = service.handle_desktop_turn(
        "продолжай",
        AppCommandSource.DESKTOP_UI,
        session_id=first.cognitive_session_id,
    )

    assert first.cognitive_session_id == second.cognitive_session_id
    assert first.cognitive_session_id == "cog-session-task120session"
    assert [item.context.included_turn_count for item in composition_inputs] == [1, 3]
    assert second.diagnostics.context_turn_count_used == 3
    assert tuple(
        turn.safe_text for turn in composition_inputs[1].context.turns[:2]
    ) == ("привет", "turn 1")
    assert first.execution is None
    assert second.execution is None
    assert processor.calls == []


def test_desktop_one_shot_voice_reuses_typed_cognitive_session(monkeypatch):
    _install_task120_deterministic_ids(monkeypatch)

    class Recognition:
        def run_once(self, **_kwargs):
            return SimpleNamespace(
                recognized_text="привет",
                completed=True,
                blocked=False,
                allowed=True,
                reasons=(),
            )

    processor = FakeCommandProcessor()
    service = JarvisAppService(
        command_processor=processor,
        one_shot_voice_recognition=Recognition(),
    )
    typed = service.handle_desktop_turn("привет", AppCommandSource.DESKTOP_UI)

    voice = service.process_one_shot_voice_request(
        AppCommandSource.DESKTOP_UI,
        session_id=typed.cognitive_session_id,
    )

    assert voice.desktop_turn_result is not None
    assert voice.desktop_turn_result.execution is None
    assert voice.cognitive_session_id == typed.cognitive_session_id
    assert voice.desktop_turn_result.cognitive_session_id == typed.cognitive_session_id
    assert voice.desktop_turn_result.diagnostics.context_turn_count_used == 3
    assert processor.calls == []
    assert service.execution_coordinator.journal.recent() == ()


def test_desktop_reopens_repository_backed_session_with_bounded_context(
    tmp_path,
    monkeypatch,
):
    _install_task120_deterministic_ids(monkeypatch)
    first_processor = FakeCommandProcessor()
    first_service = JarvisAppService(
        command_processor=first_processor,
        cognitive_session_repository=LocalConversationSessionRepository(tmp_path),
    )
    first = first_service.handle_desktop_turn("привет", AppCommandSource.DESKTOP_UI)

    composition_inputs = []

    class TrackingComposer:
        def compose(self, composition_input):
            composition_inputs.append(composition_input)
            return ResponseCompositionResult(
                response_type=AssistantResponseType.MESSAGE,
                text="reopened",
                context_turn_count_used=composition_input.context.included_turn_count,
                composition_source="task120_reopen_test",
            )

    restarted_processor = FakeCommandProcessor()
    restarted = JarvisAppService(
        command_processor=restarted_processor,
        cognitive_session_repository=LocalConversationSessionRepository(tmp_path),
        cognitive_response_composer=TrackingComposer(),
    )
    second = restarted.handle_desktop_turn(
        "what did I ask?",
        AppCommandSource.DESKTOP_UI,
        session_id=first.cognitive_session_id,
    )

    assert second.cognitive_session_id == "cog-session-task120session"
    assert second.diagnostics.context_turn_count_used == 3
    assert composition_inputs[0].context.turns[0].safe_text == "привет"
    assert restarted_processor.calls == []


def test_desktop_known_command_keeps_execution_operation():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    result = service.handle_desktop_turn(
        "app contracts status",
        AppCommandSource.DESKTOP_UI,
    )

    assert result.execution is not None
    assert result.execution.executed is True
    assert result.execution.operation_id is not None
    assert result.execution.operation_status == "succeeded"
    assert result.diagnostics.route == "execution"
    assert processor.calls == ["app contracts status"]


def test_desktop_task119b_controls_stay_on_safe_execution_route():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    first = service.handle_desktop_turn("Сделай это", AppCommandSource.DESKTOP_UI)
    confirm = service.handle_desktop_turn("Подтверждаю", AppCommandSource.DESKTOP_UI)
    cancel = service.handle_desktop_turn("отмена", AppCommandSource.DESKTOP_UI)
    risky = service.handle_desktop_turn("удали это", AppCommandSource.DESKTOP_UI)

    assert first.execution.requires_clarification is True
    assert confirm.execution.requires_clarification is True
    assert first.operation_id == confirm.operation_id == cancel.operation_id
    assert confirm.operation_status == "awaiting_clarification"
    assert cancel.operation_status == "cancelled"
    assert risky.execution.category == "unsupported"
    assert risky.execution.executed is False
    assert risky.execution.response_executed_as_command is False
    assert processor.calls == []
