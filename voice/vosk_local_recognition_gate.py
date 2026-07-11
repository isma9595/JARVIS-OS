"""Side-effect-free readiness gate for future local Vosk recognition."""

from dataclasses import dataclass, field
import importlib.util
from pathlib import Path


MODEL_PATH_NOT_CONFIGURED_DISPLAY = "не указан"


@dataclass(frozen=True)
class VoskPackageStatus:
    available: bool
    package_name: str = "vosk"

    def to_dict(self):
        return {
            "available": self.available,
            "package_name": self.package_name,
        }


@dataclass(frozen=True)
class VoskModelPathStatus:
    configured: bool
    raw_value: str | None
    display_value: str
    exists: bool
    is_directory: bool

    def to_dict(self):
        return {
            "configured": self.configured,
            "raw_value": self.raw_value,
            "display_value": self.display_value,
            "exists": self.exists,
            "is_directory": self.is_directory,
        }


@dataclass(frozen=True)
class VoskLocalRecognitionGateResult:
    allowed: bool
    package_available: bool
    model_path_configured: bool
    model_path_display_value: str
    model_path_exists: bool
    model_path_is_directory: bool
    explicit_activation_required: bool
    microphone_capture_automatic: bool
    recognition_continuous: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = "Локальное распознавание Vosk пока недоступно."
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "package_available": self.package_available,
            "model_path_configured": self.model_path_configured,
            "model_path_display_value": self.model_path_display_value,
            "model_path_exists": self.model_path_exists,
            "model_path_is_directory": self.model_path_is_directory,
            "explicit_activation_required": self.explicit_activation_required,
            "microphone_capture_automatic": self.microphone_capture_automatic,
            "recognition_continuous": self.recognition_continuous,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "message": self.message,
            "next_steps": list(self.next_steps),
        }


def check_vosk_package_status(package_finder=None):
    """Check Vosk package metadata without importing Vosk."""
    finder = package_finder or importlib.util.find_spec
    try:
        available = finder("vosk") is not None
    except (ImportError, AttributeError, ValueError):
        available = False
    return VoskPackageStatus(available=bool(available))


def check_vosk_model_path_status(
    model_path,
    path_exists=None,
    path_is_directory=None,
):
    """Inspect only the configured path value and filesystem shape."""
    raw_value = _normalize_optional_text(model_path)
    configured = raw_value is not None
    display_value = raw_value if configured else MODEL_PATH_NOT_CONFIGURED_DISPLAY

    if not configured:
        return VoskModelPathStatus(
            configured=False,
            raw_value=None,
            display_value=display_value,
            exists=False,
            is_directory=False,
        )

    exists_checker = path_exists or (lambda value: Path(value).exists())
    directory_checker = path_is_directory or (lambda value: Path(value).is_dir())

    try:
        exists = bool(exists_checker(raw_value))
    except (OSError, TypeError, ValueError):
        exists = False

    try:
        is_directory = bool(directory_checker(raw_value)) if exists else False
    except (OSError, TypeError, ValueError):
        is_directory = False

    return VoskModelPathStatus(
        configured=True,
        raw_value=raw_value,
        display_value=display_value,
        exists=exists,
        is_directory=is_directory,
    )


def evaluate_vosk_local_recognition_gate(
    model_path=None,
    package_available=None,
    explicit_activation_required=True,
    microphone_capture_automatic=False,
    recognition_continuous=False,
    package_finder=None,
    path_exists=None,
    path_is_directory=None,
):
    """Return a safe decision for whether local Vosk recognition may proceed."""
    package_status = (
        VoskPackageStatus(available=bool(package_available))
        if package_available is not None
        else check_vosk_package_status(package_finder=package_finder)
    )
    model_status = check_vosk_model_path_status(
        model_path,
        path_exists=path_exists,
        path_is_directory=path_is_directory,
    )

    blockers = []
    warnings = [
        "Автоматический запуск микрофона не выполняется.",
        "Постоянное прослушивание пока не связано с реальным распознаванием.",
    ]
    next_steps = []

    if not package_status.available:
        blockers.append("Пакет vosk не установлен.")
        next_steps.append("Установите пакет vosk вручную в выбранном окружении.")

    if not model_status.configured:
        blockers.append("Путь к модели Vosk не указан.")
        next_steps.append("Скачайте модель Vosk вручную и укажите путь к папке модели.")
    elif not model_status.exists:
        blockers.append("Папка модели Vosk не найдена.")
        next_steps.append("Проверьте, что указанная папка модели Vosk существует.")
    elif not model_status.is_directory:
        blockers.append("Путь к модели Vosk должен указывать на папку.")
        next_steps.append("Укажите путь к распакованной папке модели Vosk.")

    if not explicit_activation_required:
        blockers.append(
            "Локальное распознавание может быть включено только после явного "
            "разрешения пользователя."
        )
        next_steps.append("Запрашивайте явное разрешение пользователя перед включением.")

    if microphone_capture_automatic:
        blockers.append("Автоматический запуск микрофона не выполняется.")
        next_steps.append("Отключите автоматический запуск микрофона.")

    if recognition_continuous:
        blockers.append(
            "Постоянное прослушивание пока не связано с реальным распознаванием."
        )
        next_steps.append("Не подключайте режим CONTINUOUS к реальному распознаванию.")

    if not next_steps:
        next_steps.append(
            "После отдельного одобрения можно будет связать one-shot захват "
            "с локальным Vosk распознаванием."
        )

    allowed = not blockers
    message = (
        "Локальное распознавание Vosk может пройти безопасную проверку готовности."
        if allowed
        else "Локальное распознавание Vosk пока недоступно."
    )

    return VoskLocalRecognitionGateResult(
        allowed=allowed,
        package_available=package_status.available,
        model_path_configured=model_status.configured,
        model_path_display_value=model_status.display_value,
        model_path_exists=model_status.exists,
        model_path_is_directory=model_status.is_directory,
        explicit_activation_required=bool(explicit_activation_required),
        microphone_capture_automatic=bool(microphone_capture_automatic),
        recognition_continuous=bool(recognition_continuous),
        blockers=blockers,
        warnings=warnings,
        message=message,
        next_steps=next_steps,
    )


def _normalize_optional_text(value):
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
