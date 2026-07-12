from voice import (
    AudioDependencyReadinessChecker,
    AudioDependencyReadinessResult,
    AudioDependencyStatus,
)


def create_checker(missing=()):
    missing = set(missing)

    def fake_import_checker(dependency_name):
        if dependency_name in missing:
            raise ImportError(f"missing {dependency_name}")
        return object()

    return AudioDependencyReadinessChecker(import_checker=fake_import_checker)


def dependency(result, name):
    return result.dependency(name)


def test_all_dependencies_available():
    result = create_checker().check()

    assert result.ready is True
    assert result.audio_capture_dependencies_ready is True
    assert result.vosk_recognition_dependencies_ready is True
    assert dependency(result, "numpy").available is True
    assert dependency(result, "sounddevice").available is True
    assert dependency(result, "vosk").available is True


def test_numpy_missing():
    result = create_checker(missing={"numpy"}).check()

    assert result.ready is False
    assert dependency(result, "numpy").available is False
    assert dependency(result, "numpy").import_error == "missing numpy"
    assert dependency(result, "numpy").manual_install_command == (
        "python -m pip install numpy"
    )


def test_sounddevice_missing():
    result = create_checker(missing={"sounddevice"}).check()

    assert result.ready is False
    assert dependency(result, "sounddevice").available is False
    assert dependency(result, "sounddevice").manual_install_command == (
        "python -m pip install sounddevice"
    )


def test_vosk_missing():
    result = create_checker(missing={"vosk"}).check()

    assert result.ready is False
    assert dependency(result, "vosk").available is False
    assert dependency(result, "vosk").manual_install_command == (
        "python -m pip install vosk"
    )


def test_multiple_dependencies_missing():
    result = create_checker(missing={"numpy", "sounddevice", "vosk"}).check()

    assert result.ready is False
    assert [item.name for item in result.missing_dependencies] == [
        "numpy",
        "sounddevice",
        "vosk",
    ]


def test_manual_install_commands_are_included():
    result = create_checker(missing={"numpy", "sounddevice", "vosk"}).check()

    commands = [
        dependency.manual_install_command
        for dependency in result.missing_dependencies
    ]
    assert "python -m pip install numpy" in commands
    assert "python -m pip install sounddevice" in commands
    assert "python -m pip install vosk" in commands


def test_response_says_jarvis_does_not_install_automatically():
    result = create_checker(missing={"numpy"}).check()

    assert "JARVIS ничего не устанавливает автоматически" in result.russian_summary
    assert "JARVIS ничего не устанавливает автоматически." in result.safety_notes


def test_audio_capture_readiness_is_false_if_numpy_missing():
    result = create_checker(missing={"numpy"}).check()

    assert result.audio_capture_dependencies_ready is False
    assert result.vosk_recognition_dependencies_ready is True


def test_audio_capture_readiness_is_false_if_sounddevice_missing():
    result = create_checker(missing={"sounddevice"}).check()

    assert result.audio_capture_dependencies_ready is False
    assert result.vosk_recognition_dependencies_ready is True


def test_vosk_recognition_readiness_is_false_if_vosk_missing():
    result = create_checker(missing={"vosk"}).check()

    assert result.audio_capture_dependencies_ready is True
    assert result.vosk_recognition_dependencies_ready is False


def test_formatter_returns_russian_success_message():
    result = create_checker().check()

    formatted = AudioDependencyReadinessChecker.format_russian(result)

    assert "Зависимости аудиозахвата готовы." in formatted
    assert "- numpy" in formatted
    assert "- sounddevice" in formatted
    assert "- vosk" in formatted
    assert "распознай голос один раз" in formatted


def test_formatter_returns_russian_missing_dependency_message():
    result = create_checker(missing={"vosk"}).check()

    formatted = AudioDependencyReadinessChecker.format_russian(result)

    assert "Пакет vosk не найден." in formatted
    assert "python -m pip install vosk" in formatted
    assert "JARVIS ничего не устанавливает автоматически" in formatted


def test_result_to_dict_contains_dependency_readiness_flags():
    result = AudioDependencyReadinessResult(
        dependencies=(
            AudioDependencyStatus(
                name="numpy",
                available=True,
                import_error=None,
                manual_install_command="python -m pip install numpy",
            ),
        ),
        audio_capture_dependencies_ready=False,
        vosk_recognition_dependencies_ready=True,
        russian_summary="summary",
    )

    data = result.to_dict()

    assert data["audio_capture_dependencies_ready"] is False
    assert data["vosk_recognition_dependencies_ready"] is True
    assert data["dependencies"][0]["name"] == "numpy"
