from unittest.mock import Mock, patch

from voice import (
    check_vosk_model_path_status,
    check_vosk_package_status,
    evaluate_vosk_local_recognition_gate,
)


def test_package_check_reports_missing_vosk_without_importing_package():
    finder = Mock(return_value=None)

    status = check_vosk_package_status(package_finder=finder)

    assert status.available is False
    finder.assert_called_once_with("vosk")


def test_model_path_check_reports_missing_configuration():
    status = check_vosk_model_path_status(None)

    assert status.configured is False
    assert status.display_value == "не указан"
    assert status.exists is False
    assert status.is_directory is False


def test_model_path_check_reports_existing_directory_with_safe_display_value():
    status = check_vosk_model_path_status(
        " C:/models/vosk-ru ",
        path_exists=lambda path: path == "C:/models/vosk-ru",
        path_is_directory=lambda path: path == "C:/models/vosk-ru",
    )

    assert status.configured is True
    assert status.raw_value == "C:/models/vosk-ru"
    assert status.display_value == "C:/models/vosk-ru"
    assert status.exists is True
    assert status.is_directory is True


def test_gate_is_blocked_when_vosk_package_is_missing():
    result = evaluate_vosk_local_recognition_gate(
        model_path="C:/models/vosk-ru",
        package_available=False,
        path_exists=lambda _path: True,
        path_is_directory=lambda _path: True,
    )

    assert result.allowed is False
    assert result.package_available is False
    assert "Пакет vosk не установлен." in result.blockers
    assert result.message == "Локальное распознавание Vosk пока недоступно."


def test_gate_is_blocked_when_model_path_is_not_configured():
    result = evaluate_vosk_local_recognition_gate(package_available=True)

    assert result.allowed is False
    assert result.model_path_configured is False
    assert result.model_path_display_value == "не указан"
    assert "Путь к модели Vosk не указан." in result.blockers


def test_gate_is_blocked_when_model_path_does_not_exist():
    result = evaluate_vosk_local_recognition_gate(
        model_path="C:/models/missing",
        package_available=True,
        path_exists=lambda _path: False,
        path_is_directory=lambda _path: False,
    )

    assert result.allowed is False
    assert result.model_path_exists is False
    assert "Папка модели Vosk не найдена." in result.blockers


def test_gate_is_blocked_when_model_path_is_not_a_directory():
    result = evaluate_vosk_local_recognition_gate(
        model_path="C:/models/vosk.zip",
        package_available=True,
        path_exists=lambda _path: True,
        path_is_directory=lambda _path: False,
    )

    assert result.allowed is False
    assert result.model_path_exists is True
    assert result.model_path_is_directory is False
    assert "Путь к модели Vosk должен указывать на папку." in result.blockers


def test_gate_allows_when_all_fake_prerequisites_pass_and_activation_is_required():
    result = evaluate_vosk_local_recognition_gate(
        model_path="C:/models/vosk-ru",
        package_available=True,
        explicit_activation_required=True,
        microphone_capture_automatic=False,
        recognition_continuous=False,
        path_exists=lambda _path: True,
        path_is_directory=lambda _path: True,
    )

    assert result.allowed is True
    assert result.package_available is True
    assert result.model_path_configured is True
    assert result.model_path_exists is True
    assert result.model_path_is_directory is True
    assert result.explicit_activation_required is True
    assert result.blockers == []
    assert result.message.startswith("Локальное распознавание Vosk может")


def test_gate_blocks_when_explicit_activation_is_not_required():
    result = evaluate_vosk_local_recognition_gate(
        model_path="C:/models/vosk-ru",
        package_available=True,
        explicit_activation_required=False,
        path_exists=lambda _path: True,
        path_is_directory=lambda _path: True,
    )

    assert result.allowed is False
    assert (
        "Локальное распознавание может быть включено только после явного "
        "разрешения пользователя."
    ) in result.blockers


def test_gate_blocks_automatic_microphone_and_continuous_recognition():
    result = evaluate_vosk_local_recognition_gate(
        model_path="C:/models/vosk-ru",
        package_available=True,
        microphone_capture_automatic=True,
        recognition_continuous=True,
        path_exists=lambda _path: True,
        path_is_directory=lambda _path: True,
    )

    assert result.allowed is False
    assert "Автоматический запуск микрофона не выполняется." in result.blockers
    assert (
        "Постоянное прослушивание пока не связано с реальным распознаванием."
    ) in result.blockers


def test_gate_returns_russian_first_warnings_and_useful_next_steps():
    result = evaluate_vosk_local_recognition_gate(package_available=False)

    assert "Автоматический запуск микрофона не выполняется." in result.warnings
    assert (
        "Постоянное прослушивание пока не связано с реальным распознаванием."
        in result.warnings
    )
    assert "Установите пакет vosk вручную в выбранном окружении." in result.next_steps
    assert (
        "Скачайте модель Vosk вручную и укажите путь к папке модели."
        in result.next_steps
    )


def test_gate_result_can_be_returned_as_plain_dict():
    result = evaluate_vosk_local_recognition_gate(package_available=False)

    as_dict = result.to_dict()

    assert as_dict["allowed"] is False
    assert as_dict["package_available"] is False
    assert as_dict["message"] == "Локальное распознавание Vosk пока недоступно."


def test_gate_does_not_load_vosk_model_access_microphone_or_start_listeners():
    fake_vosk = Mock()
    with patch.dict("sys.modules", {"vosk": fake_vosk}):
        with patch(
            "voice.one_shot_microphone_capture.OneShotMicrophoneCapture.capture_once"
        ) as capture_once:
            with patch(
                "voice.microphone_listening_modes."
                "MicrophoneListeningModeManager.switch_to_continuous"
            ) as switch_to_continuous:
                with patch("threading.Thread.start") as thread_start:
                    result = evaluate_vosk_local_recognition_gate(
                        model_path="C:/models/vosk-ru",
                        package_available=True,
                        path_exists=lambda _path: True,
                        path_is_directory=lambda _path: True,
                    )

    assert result.allowed is True
    fake_vosk.Model.assert_not_called()
    capture_once.assert_not_called()
    switch_to_continuous.assert_not_called()
    thread_start.assert_not_called()
