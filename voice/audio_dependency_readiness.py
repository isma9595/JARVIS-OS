"""Read-only diagnostics for local audio capture dependencies."""

from dataclasses import dataclass, field
from importlib import import_module


AUDIO_DEPENDENCY_INSTALL_COMMANDS = {
    "numpy": "python -m pip install numpy",
    "sounddevice": "python -m pip install sounddevice",
    "vosk": "python -m pip install vosk",
}


@dataclass(frozen=True)
class AudioDependencyStatus:
    name: str
    available: bool
    import_error: str | None
    manual_install_command: str

    def to_dict(self):
        return {
            "name": self.name,
            "available": self.available,
            "import_error": self.import_error,
            "manual_install_command": self.manual_install_command,
        }


@dataclass(frozen=True)
class AudioDependencyReadinessResult:
    dependencies: tuple[AudioDependencyStatus, ...]
    audio_capture_dependencies_ready: bool
    vosk_recognition_dependencies_ready: bool
    russian_summary: str
    safety_notes: tuple[str, ...] = field(
        default_factory=lambda: (
            "JARVIS ничего не устанавливает автоматически.",
            "Постоянное прослушивание не включается.",
            "Аудио не отправляется в облако.",
            "Распознанный текст не выполняется как команда.",
        )
    )

    @property
    def ready(self):
        return (
            self.audio_capture_dependencies_ready
            and self.vosk_recognition_dependencies_ready
        )

    @property
    def missing_dependencies(self):
        return tuple(
            dependency
            for dependency in self.dependencies
            if not dependency.available
        )

    def dependency(self, name):
        normalized_name = str(name).strip().lower()
        for dependency in self.dependencies:
            if dependency.name == normalized_name:
                return dependency
        return None

    def to_dict(self):
        return {
            "dependencies": [
                dependency.to_dict() for dependency in self.dependencies
            ],
            "audio_capture_dependencies_ready": (
                self.audio_capture_dependencies_ready
            ),
            "vosk_recognition_dependencies_ready": (
                self.vosk_recognition_dependencies_ready
            ),
            "ready": self.ready,
            "russian_summary": self.russian_summary,
            "safety_notes": list(self.safety_notes),
        }


class AudioDependencyReadinessChecker:
    DEPENDENCIES = ("numpy", "sounddevice", "vosk")

    def __init__(self, import_checker=None):
        self.import_checker = import_checker or self._default_import_checker

    def check(self):
        dependencies = tuple(
            self._check_dependency(dependency_name)
            for dependency_name in self.DEPENDENCIES
        )
        available = {
            dependency.name: dependency.available for dependency in dependencies
        }
        audio_capture_ready = bool(
            available.get("numpy") and available.get("sounddevice")
        )
        vosk_recognition_ready = bool(available.get("vosk"))
        return AudioDependencyReadinessResult(
            dependencies=dependencies,
            audio_capture_dependencies_ready=audio_capture_ready,
            vosk_recognition_dependencies_ready=vosk_recognition_ready,
            russian_summary=self.format_russian_dependencies(dependencies),
        )

    def _check_dependency(self, dependency_name):
        try:
            self.import_checker(dependency_name)
        except Exception as exc:
            return AudioDependencyStatus(
                name=dependency_name,
                available=False,
                import_error=str(exc),
                manual_install_command=AUDIO_DEPENDENCY_INSTALL_COMMANDS[
                    dependency_name
                ],
            )
        return AudioDependencyStatus(
            name=dependency_name,
            available=True,
            import_error=None,
            manual_install_command=AUDIO_DEPENDENCY_INSTALL_COMMANDS[
                dependency_name
            ],
        )

    @staticmethod
    def _default_import_checker(dependency_name):
        return import_module(dependency_name)

    @staticmethod
    def format_russian(result):
        if isinstance(result, AudioDependencyReadinessResult):
            return result.russian_summary
        return AudioDependencyReadinessChecker.format_russian_dependencies(result)

    @staticmethod
    def format_russian_dependencies(dependencies):
        dependencies = tuple(dependencies)
        missing = tuple(
            dependency for dependency in dependencies if not dependency.available
        )
        if not missing:
            available_lines = "\n".join(
                f"- {dependency.name}" for dependency in dependencies
            )
            return (
                "Зависимости аудиозахвата готовы.\n"
                "Доступно:\n"
                f"{available_lines}\n"
                "Можно повторить явную команду: распознай голос один раз.\n"
                "Безопасность: JARVIS ничего не устанавливает автоматически, постоянное прослушивание не включается."
            )

        lines = []
        for dependency in missing:
            lines.append(
                AudioDependencyReadinessChecker.missing_dependency_message(
                    dependency
                )
            )
        return "\n".join(lines)

    @staticmethod
    def missing_dependency_message(dependency):
        if dependency.name == "numpy":
            return (
                "Зависимость NumPy не найдена. One-shot захват микрофона может не работать.\n"
                f"Установите вручную: {dependency.manual_install_command}\n"
                "Безопасность: JARVIS ничего не устанавливает автоматически."
            )
        if dependency.name == "sounddevice":
            return (
                "Зависимость sounddevice не найдена. One-shot захват микрофона может не работать.\n"
                f"Установите вручную: {dependency.manual_install_command}\n"
                "Безопасность: JARVIS ничего не устанавливает автоматически."
            )
        if dependency.name == "vosk":
            return (
                "Пакет vosk не найден. Локальное распознавание речи Vosk не будет работать.\n"
                f"Установите вручную: {dependency.manual_install_command}\n"
                "Безопасность: JARVIS ничего не устанавливает автоматически."
            )
        return (
            f"Зависимость {dependency.name} не найдена.\n"
            f"Установите вручную: {dependency.manual_install_command}\n"
            "Безопасность: JARVIS ничего не устанавливает автоматически."
        )
