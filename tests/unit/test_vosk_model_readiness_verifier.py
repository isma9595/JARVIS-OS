import sys
import shutil
from pathlib import Path

import pytest

from voice import VoskModelReadinessVerifier


@pytest.fixture
def model_test_dir(request):
    base = Path("models") / "task035_readiness_tests" / request.node.name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    try:
        yield base
    finally:
        if base.exists():
            shutil.rmtree(base)


def test_no_path_configured_returns_next_steps_and_safety_notes():
    result = VoskModelReadinessVerifier().verify(None)

    assert result.configured_path is None
    assert result.path_exists is False
    assert result.ready_for_future_recognition is False
    assert "Путь к модели Vosk не указан." in result.reasons
    assert "Модель Vosk не загружалась." in result.safety_notes
    assert "Микрофон не запускался." in result.safety_notes


def test_path_missing(model_test_dir):
    missing_path = model_test_dir / "missing-model"

    result = VoskModelReadinessVerifier().verify(str(missing_path))

    assert result.configured_path == str(missing_path)
    assert result.path_exists is False
    assert result.is_directory is False
    assert result.looks_like_model is False
    assert result.ready_for_future_recognition is False


def test_path_exists_but_is_file(model_test_dir):
    model_file = model_test_dir / "vosk-model.zip"
    model_file.write_text("archive placeholder", encoding="utf-8")

    result = VoskModelReadinessVerifier().verify(str(model_file))

    assert result.path_exists is True
    assert result.is_directory is False
    assert "Путь к модели Vosk указывает не на папку." in result.reasons


def test_path_is_empty_directory(model_test_dir):
    model_dir = model_test_dir / "vosk-model-small-ru"
    model_dir.mkdir()

    result = VoskModelReadinessVerifier().verify(str(model_dir))

    assert result.path_exists is True
    assert result.is_directory is True
    assert result.is_empty is True
    assert result.looks_like_model is False
    assert result.ready_for_future_recognition is False


def test_partial_model_like_structure_is_not_too_strict(model_test_dir):
    model_dir = model_test_dir / "vosk-model-partial"
    model_dir.mkdir()
    (model_dir / "conf").mkdir()
    (model_dir / "README").write_text("model notes", encoding="utf-8")

    result = VoskModelReadinessVerifier().verify(str(model_dir))

    assert result.is_empty is False
    assert result.looks_like_model is True
    assert result.ready_for_future_recognition is True


def test_model_like_directories_and_files_are_considered_ready_for_future(model_test_dir):
    model_dir = model_test_dir / "vosk-model-small-ru"
    model_dir.mkdir()
    for child in ("am", "conf", "graph", "ivector"):
        (model_dir / child).mkdir()
    (model_dir / "README.md").write_text("model notes", encoding="utf-8")

    result = VoskModelReadinessVerifier().verify(str(model_dir))

    assert result.looks_like_model is True
    assert result.ready_for_future_recognition is True
    assert "Папка модели Vosk найдена и похожа на распакованную модель." in result.reasons


def test_formatter_returns_russian_no_path_message():
    result = VoskModelReadinessVerifier().verify(None)

    formatted = VoskModelReadinessVerifier.format_russian(result)

    assert formatted.startswith("Путь к модели Vosk пока не указан.")
    assert "установи путь модели vosk <путь>" in formatted


def test_formatter_returns_russian_missing_path_message(model_test_dir):
    missing_path = model_test_dir / "missing-model"
    result = VoskModelReadinessVerifier().verify(str(missing_path))

    formatted = VoskModelReadinessVerifier.format_russian(result)

    assert f"Путь к модели Vosk указан, но папка не найдена: {missing_path}." in formatted


def test_formatter_returns_russian_model_like_message(model_test_dir):
    model_dir = model_test_dir / "vosk-model"
    model_dir.mkdir()
    (model_dir / "am").mkdir()
    (model_dir / "conf").mkdir()

    formatted = VoskModelReadinessVerifier.format_russian(
        VoskModelReadinessVerifier().verify(str(model_dir))
    )

    assert "Папка модели Vosk найдена и похожа на распакованную модель." in formatted
    assert "модель не загружалась" in formatted
    assert "микрофон не запускался" in formatted


def test_no_real_vosk_import_required():
    sys.modules.pop("vosk", None)

    result = VoskModelReadinessVerifier().verify(None)

    assert result.ready_for_future_recognition is False
    assert "vosk" not in sys.modules
