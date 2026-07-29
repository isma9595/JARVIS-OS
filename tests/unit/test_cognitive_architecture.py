import ast
from pathlib import Path


COGNITION_ROOT = Path("cognition")


def _imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_cognition_package_contains_only_approved_cognitive_modules():
    modules = {path.name for path in COGNITION_ROOT.glob("*.py")}

    assert modules == {
        "__init__.py",
        "contracts.py",
        "context.py",
        "intent_interpreter.py",
        "interaction_service.py",
        "persistence.py",
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
    for module_name in ("context.py", "intent_interpreter.py", "response_composer.py"):
        imports = _imports_for(COGNITION_ROOT / module_name)
        assert not forbidden.intersection(imports)
        assert not any(module.startswith("ai.") for module in imports)


def test_session_state_has_one_authoritative_owner():
    session_source = (COGNITION_ROOT / "sessions.py").read_text(encoding="utf-8")
    interaction_source = (COGNITION_ROOT / "interaction_service.py").read_text(encoding="utf-8")
    context_source = (COGNITION_ROOT / "context.py").read_text(encoding="utf-8")
    interpreter_source = (COGNITION_ROOT / "intent_interpreter.py").read_text(encoding="utf-8")
    composer_source = (COGNITION_ROOT / "response_composer.py").read_text(encoding="utf-8")

    assert "self._sessions" in session_source
    assert "self._sessions" not in interaction_source
    assert "self._sessions" not in context_source
    assert "self._sessions" not in interpreter_source
    assert "self._sessions" not in composer_source


def test_interaction_service_owns_no_repository_or_session_cache():
    source = (COGNITION_ROOT / "interaction_service.py").read_text(encoding="utf-8")

    assert "repository" not in source
    assert "_sessions" not in source


def test_context_projector_and_response_composer_own_no_durable_state_or_token_counter():
    context_source = (COGNITION_ROOT / "context.py").read_text(encoding="utf-8")
    interpreter_source = (COGNITION_ROOT / "intent_interpreter.py").read_text(encoding="utf-8")
    composer_source = (COGNITION_ROOT / "response_composer.py").read_text(encoding="utf-8")

    assert "repository" not in context_source
    assert "save_record" not in context_source
    assert "load_records" not in context_source
    assert "token" not in context_source.lower()
    assert "repository" not in interpreter_source
    assert "save_record" not in interpreter_source
    assert "load_records" not in interpreter_source
    assert "token" not in interpreter_source.lower()
    assert "repository" not in composer_source
    assert "save_record" not in composer_source
    assert "load_records" not in composer_source
    assert "token" not in composer_source.lower()


def test_no_future_placeholder_cognitive_services_are_added():
    modules = {path.name for path in COGNITION_ROOT.glob("*.py")}

    assert "reference_resolver.py" not in modules
    assert "clarification.py" not in modules
    assert "goals.py" not in modules
    assert "planning.py" not in modules
    assert "memory_policy.py" not in modules
    assert "knowledge_service.py" not in modules
