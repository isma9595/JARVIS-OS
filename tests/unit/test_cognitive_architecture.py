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


def test_cognition_package_contains_only_task_113_skeleton_modules():
    modules = {path.name for path in COGNITION_ROOT.glob("*.py")}

    assert modules == {
        "__init__.py",
        "contracts.py",
        "interaction_service.py",
        "sessions.py",
    }


def test_cognition_does_not_import_desktop_or_forbidden_runtime_owners():
    forbidden_prefixes = (
        "app.desktop_shell",
        "core.execution_coordinator",
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


def test_session_state_has_one_authoritative_owner():
    session_source = (COGNITION_ROOT / "sessions.py").read_text(encoding="utf-8")
    interaction_source = (COGNITION_ROOT / "interaction_service.py").read_text(encoding="utf-8")

    assert "self._sessions" in session_source
    assert "self._sessions" not in interaction_source
