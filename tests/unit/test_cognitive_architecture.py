import ast
from dataclasses import fields
from pathlib import Path

from cognition import RuleBasedClarificationCoordinator


COGNITION_ROOT = Path("cognition")
DESKTOP_SHELL_PATH = Path("app/desktop_shell.py")
DESKTOP_WORKER_PATH = Path("app/desktop_interaction_worker.py")
USER_DATA_MIGRATION_PATH = Path("platform_adapters/user_data_migration.py")
PERSISTENCE_HEALTH_PATH = Path("app/persistence_health.py")


def _imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_desktop_interaction_worker_has_no_runtime_owner_or_tk_imports():
    imports = _imports_for(DESKTOP_WORKER_PATH)
    forbidden_prefixes = (
        "tkinter",
        "app.app_service",
        "cognition",
        "ai",
        "core",
        "workflows",
        "voice",
        "memory",
    )

    assert not {
        module
        for module in imports
        if module in forbidden_prefixes
        or any(module.startswith(prefix + ".") for prefix in forbidden_prefixes)
    }


def test_desktop_shell_delegates_thread_lifecycle_to_worker_only():
    imports = _imports_for(DESKTOP_SHELL_PATH)
    source = DESKTOP_SHELL_PATH.read_text(encoding="utf-8")

    assert "threading" not in imports
    assert "Thread" not in imports
    assert "daemon=True" not in source
    assert "app.desktop_interaction_worker" in imports


def test_worker_does_not_own_session_cache_history_or_repository():
    source = DESKTOP_WORKER_PATH.read_text(encoding="utf-8").lower()

    assert "repository" not in source
    assert "session_cache" not in source
    assert "conversation_history" not in source


def test_task_125_keeps_migration_and_health_out_of_desktop_and_worker():
    desktop_imports = _imports_for(DESKTOP_SHELL_PATH)
    worker_imports = _imports_for(DESKTOP_WORKER_PATH)

    assert "platform_adapters.user_data_migration" not in desktop_imports
    assert "platform_adapters.user_data_paths" not in desktop_imports
    assert "app.persistence_health" not in desktop_imports
    assert "platform_adapters.user_data_migration" not in worker_imports
    assert "platform_adapters.user_data_paths" not in worker_imports
    assert "app.persistence_health" not in worker_imports


def test_migration_and_health_do_not_take_store_or_runtime_ownership():
    migration_imports = _imports_for(USER_DATA_MIGRATION_PATH)
    health_imports = _imports_for(PERSISTENCE_HEALTH_PATH)
    forbidden = ("cognition", "core", "memory", "ideas", "users", "voice", "workflows", "ai")

    assert not {
        module
        for module in migration_imports | health_imports
        if module in forbidden or any(module.startswith(prefix + ".") for prefix in forbidden)
    }
    migration_source = USER_DATA_MIGRATION_PATH.read_text(encoding="utf-8").lower()
    health_source = PERSISTENCE_HEALTH_PATH.read_text(encoding="utf-8").lower()
    assert "commandprocessor" not in migration_source + health_source
    assert "desktopinteractionworker" not in migration_source + health_source
    assert "close_conversation_session" not in migration_source + health_source


def test_cognition_package_contains_only_approved_cognitive_modules():
    modules = {path.name for path in COGNITION_ROOT.glob("*.py")}

    assert modules == {
        "__init__.py",
        "contracts.py",
        "context.py",
        "clarification_coordinator.py",
        "intent_interpreter.py",
        "interaction_service.py",
        "memory_policy.py",
        "persistence.py",
        "reference_resolver.py",
        "response_composer.py",
        "sessions.py",
    }


def test_cognition_does_not_import_desktop_or_forbidden_runtime_owners():
    forbidden_prefixes = (
        "app.desktop_shell",
        "core.execution_coordinator",
        "core.command_processor",
        "workflows.runner",
        "ai.",
        "memory",
        "platform_adapters",
    )

    for path in COGNITION_ROOT.glob("*.py"):
        imports = _imports_for(path)
        assert not {
            module
            for module in imports
            if module in forbidden_prefixes
            or any(module.startswith(prefix) for prefix in forbidden_prefixes)
        }, path


def test_interaction_service_does_not_import_execution_or_provider_owners():
    imports = _imports_for(COGNITION_ROOT / "interaction_service.py")

    assert "core.execution_coordinator" not in imports
    assert "workflows.runner" not in imports
    assert not any(module.startswith("ai.") for module in imports)
    assert "memory" not in imports


def test_persistence_does_not_import_appservice_or_runtime_owners():
    imports = _imports_for(COGNITION_ROOT / "persistence.py")
    forbidden = {
        "app.app_service",
        "cognition.interaction_service",
        "core.execution_coordinator",
        "workflows.runner",
        "memory",
        "platform_adapters",
    }

    assert not forbidden.intersection(imports)
    assert not any(module.startswith("ai.") for module in imports)


def test_context_interpreter_and_response_composer_do_not_import_runtime_owners():
    forbidden = {
        "app.app_service",
        "app.desktop_shell",
        "core.command_processor",
        "core.execution_coordinator",
        "workflows.runner",
        "memory",
        "platform_adapters",
    }
    for module_name in (
        "context.py",
        "intent_interpreter.py",
        "reference_resolver.py",
        "clarification_coordinator.py",
        "response_composer.py",
    ):
        imports = _imports_for(COGNITION_ROOT / module_name)
        assert not forbidden.intersection(imports)
        assert not any(module.startswith("ai.") for module in imports)


def test_memory_policy_has_no_runtime_owner_or_storage_dependencies():
    imports = _imports_for(COGNITION_ROOT / "memory_policy.py")
    forbidden_prefixes = (
        "ai",
        "app",
        "core.execution",
        "datetime",
        "http",
        "memory",
        "os",
        "pathlib",
        "platform_adapters",
        "requests",
        "socket",
        "subprocess",
        "time",
        "urllib",
        "workflows",
    )

    assert not {
        module
        for module in imports
        if any(
            module == prefix or module.startswith(f"{prefix}.")
            for prefix in forbidden_prefixes
        )
    }


def test_session_state_has_one_authoritative_owner():
    session_source = (COGNITION_ROOT / "sessions.py").read_text(encoding="utf-8")
    interaction_source = (COGNITION_ROOT / "interaction_service.py").read_text(encoding="utf-8")
    context_source = (COGNITION_ROOT / "context.py").read_text(encoding="utf-8")
    interpreter_source = (COGNITION_ROOT / "intent_interpreter.py").read_text(encoding="utf-8")
    resolver_source = (COGNITION_ROOT / "reference_resolver.py").read_text(encoding="utf-8")
    composer_source = (COGNITION_ROOT / "response_composer.py").read_text(encoding="utf-8")

    assert "self._sessions" in session_source
    assert "self._sessions" not in interaction_source
    assert "self._sessions" not in context_source
    assert "self._sessions" not in interpreter_source
    assert "self._sessions" not in resolver_source
    assert "self._sessions" not in composer_source


def test_interaction_service_owns_no_repository_or_session_cache():
    source = (COGNITION_ROOT / "interaction_service.py").read_text(encoding="utf-8")

    assert "repository" not in source
    assert "_sessions" not in source


def test_desktop_shell_has_no_cognition_or_repository_imports():
    imports = _imports_for(DESKTOP_SHELL_PATH)

    assert not any(module == "cognition" or module.startswith("cognition.") for module in imports)
    assert "LocalConversationSessionRepository" not in DESKTOP_SHELL_PATH.read_text(
        encoding="utf-8"
    )


def test_desktop_shell_owns_no_parallel_cognitive_session_cache_or_history():
    source = DESKTOP_SHELL_PATH.read_text(encoding="utf-8")

    assert "_cognitive_sessions" not in source
    assert "_conversation_history" not in source
    assert "_session_repository" not in source


def test_context_projector_and_response_composer_own_no_durable_state_or_token_counter():
    context_source = (COGNITION_ROOT / "context.py").read_text(encoding="utf-8")
    interpreter_source = (COGNITION_ROOT / "intent_interpreter.py").read_text(encoding="utf-8")
    resolver_source = (COGNITION_ROOT / "reference_resolver.py").read_text(encoding="utf-8")
    composer_source = (COGNITION_ROOT / "response_composer.py").read_text(encoding="utf-8")

    assert "repository" not in context_source
    assert "save_record" not in context_source
    assert "load_records" not in context_source
    assert "token" not in context_source.lower()
    assert "repository" not in interpreter_source
    assert "save_record" not in interpreter_source
    assert "load_records" not in interpreter_source
    assert "token" not in interpreter_source.lower()
    assert "repository" not in resolver_source
    assert "save_record" not in resolver_source
    assert "load_records" not in resolver_source
    assert "token" not in resolver_source.lower()
    assert "repository" not in composer_source
    assert "save_record" not in composer_source
    assert "load_records" not in composer_source
    assert "token" not in composer_source.lower()


def test_clarification_coordinator_owns_no_pending_state_behaviorally():
    coordinator = RuleBasedClarificationCoordinator()
    field_names = {field.name for field in fields(RuleBasedClarificationCoordinator)}
    forbidden_fields = {
        "sessions",
        "_sessions",
        "cache",
        "pending",
        "pending_clarification",
        "awaiting_response",
        "correlation_token",
        "retry_count",
        "expires_at",
        "state_machine",
    }

    assert field_names == {"coordinator_id", "coordinator_version"}
    assert not field_names.intersection(forbidden_fields)
    assert coordinator.__dict__ == {
        "coordinator_id": "rule_based_clarification_coordinator",
        "coordinator_version": "1",
    }


def test_no_future_placeholder_cognitive_services_are_added():
    modules = {path.name for path in COGNITION_ROOT.glob("*.py")}

    assert "clarification.py" not in modules
    assert "goals.py" not in modules
    assert "planning.py" not in modules
    assert "knowledge_service.py" not in modules
