import configparser
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements-ci.txt"
PYTEST_CONFIG_PATH = PROJECT_ROOT / "pytest.ini"
CI_WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"

EXPECTED_TEST_DEPENDENCIES = (
    "colorama==0.4.6",
    "iniconfig==2.3.0",
    "packaging==26.2",
    "pluggy==1.6.0",
    "Pygments==2.20.0",
    "pytest==9.1.1",
)

CHECKOUT_ACTION = "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0"
SETUP_PYTHON_ACTION = (
    "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
)


def _configuration_lines(path: Path) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_ci_dependency_manifest_is_complete_and_exactly_pinned():
    lines = _configuration_lines(REQUIREMENTS_PATH)

    assert lines == EXPECTED_TEST_DEPENDENCIES
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.-]+", line) for line in lines)
    assert not any("http" in line.lower() or "@" in line for line in lines)


def test_optional_runtime_dependencies_are_not_made_mandatory_for_ci():
    manifest = REQUIREMENTS_PATH.read_text(encoding="utf-8").lower()

    assert "numpy" not in manifest
    assert "sounddevice" not in manifest
    assert "vosk" not in manifest


def test_pytest_configuration_keeps_the_supported_suite_explicit():
    parser = configparser.ConfigParser()
    parser.read(PYTEST_CONFIG_PATH, encoding="utf-8")

    pytest_config = parser["pytest"]
    assert pytest_config["minversion"] == "9.1.1"
    assert pytest_config["testpaths"].split() == ["tests"]
    assert pytest_config["python_files"].split() == ["test_*.py"]
    assert pytest_config["addopts"] == "-ra"


def test_ci_uses_one_pinned_windows_and_python_baseline():
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "runs-on: windows-2025" in workflow
    assert "python-version: '3.14.6'" in workflow
    assert "pip-version: '26.1.2'" in workflow
    assert CHECKOUT_ACTION in workflow
    assert SETUP_PYTHON_ACTION in workflow
    assert "matrix:" not in workflow
    assert "windows-latest" not in workflow


def test_ci_is_read_only_bounded_and_runs_the_local_test_contract():
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    lowered = workflow.lower()

    assert "permissions:\n  contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "timeout-minutes: 15" in workflow
    assert "cache: 'pip'" in workflow
    assert "cache-dependency-path: requirements-ci.txt" in workflow
    assert "python -m pip install --requirement requirements-ci.txt" in workflow
    assert workflow.count("python -m pytest -q") == 1
    assert "secrets." not in lowered
    assert "continue-on-error" not in lowered
    assert "provider" not in lowered
    assert "microphone" not in lowered
    assert "tts" not in lowered


def test_ci_action_references_are_immutable_commit_shas():
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    action_references = re.findall(r"uses:\s+(actions/[^@\s]+)@([^\s#]+)", workflow)

    assert action_references == [
        ("actions/checkout", CHECKOUT_ACTION.rsplit("@", 1)[1]),
        ("actions/setup-python", SETUP_PYTHON_ACTION.rsplit("@", 1)[1]),
    ]
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for _, revision in action_references)
