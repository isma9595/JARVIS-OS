"""Read-only installation guidance for a future Vosk integration."""

import sys


class VoskInstallationGuide:
    """Provide Vosk setup information without changing the local environment."""

    OFFICIAL_PYTHON_RANGE = "3.5-3.9"
    MIN_PIP_VERSION = "20.3"
    RECOMMENDED_MODEL = "vosk-model-small-ru-0.22"

    def get_python_version_status(self):
        version = sys.version_info
        version_text = f"{version.major}.{version.minor}.{version.micro}"
        is_likely_compatible = (
            version.major == 3 and 5 <= version.minor <= 9
        )
        if is_likely_compatible:
            message = (
                f"Python {version_text} входит в диапазон 3.5-3.9, указанный "
                "в официальной инструкции Vosk."
            )
        else:
            message = (
                f"Python {version_text} находится вне диапазона 3.5-3.9, "
                "указанного в официальной инструкции Vosk. Совместимость не "
                "гарантируется; рекомендуется отдельный совместимый venv."
            )
        return {
            "python_version": version_text,
            "official_supported_range": self.OFFICIAL_PYTHON_RANGE,
            "is_likely_compatible": is_likely_compatible,
            "message": message,
        }

    def get_pip_install_command(self):
        return {
            "command": "python -m pip install vosk",
            "minimum_pip_version": self.MIN_PIP_VERSION,
            "execute_automatically": False,
            "message": (
                "Команда приведена только как текст. JARVIS не запускает её и "
                "не изменяет Python-окружение."
            ),
        }

    def get_recommended_model(self):
        return {
            "name": self.RECOMMENDED_MODEL,
            "language": "ru",
            "size": "small",
            "recommended_for": "первый локальный lightweight-прототип",
            "download_automatically": False,
        }

    def get_model_download_guidance(self):
        return {
            "model": self.RECOMMENDED_MODEL,
            "steps": [
                "Откройте официальный каталог моделей Vosk вручную.",
                f"Найдите архив {self.RECOMMENDED_MODEL}.",
                "Проверьте источник и целостность архива перед распаковкой.",
                "Распакуйте модель в отдельную локальную папку.",
                "Укажите путь к папке через настройки JARVIS.",
            ],
            "network_access_performed": False,
            "files_changed": False,
            "message": "JARVIS не скачивает и не распаковывает модель.",
        }

    def get_safe_enablement_steps(self):
        return [
            "Сверить разрядность Windows и версию Python.",
            "Создать вручную отдельный venv с совместимой версией Python.",
            f"Проверить, что pip имеет версию {self.MIN_PIP_VERSION} или новее.",
            "Установить зависимость вручную только в отдельный venv.",
            f"Скачать вручную модель {self.RECOMMENDED_MODEL} из официального источника.",
            "Настроить и проверить локальный путь к модели.",
            "Добавить отдельный безопасный runtime loader с явными ошибками.",
            "Проверить offline-режим без микрофона на тестовом аудиофайле.",
            "Подключать микрофон только отдельной задачей и после явного разрешения.",
        ]

    def get_installation_summary(self):
        python_status = self.get_python_version_status()
        return {
            "title": "Vosk: ручная безопасная установка",
            "automatic_installation": False,
            "python": python_status,
            "pip": self.get_pip_install_command(),
            "model": self.get_recommended_model(),
            "recommended_environment": "отдельный совместимый venv",
            "message": (
                "TASK-020 предоставляет только инструкцию. Зависимость, модель "
                "и runtime не подключаются автоматически."
            ),
        }

    def get_runtime_risks(self):
        return [
            "Текущая версия Python может быть вне официально указанного диапазона.",
            "Установка в основное окружение может вызвать конфликт зависимостей.",
            "Модель из непроверенного источника может быть повреждена или подменена.",
            "Ошибочный путь к модели не должен приводить к удалению или изменению файлов.",
            "Будущий доступ к микрофону требует отдельного явного разрешения.",
            "Runtime должен оставаться локальным и не отправлять аудио в интернет.",
        ]

    def get_public_status(self):
        python_status = self.get_python_version_status()
        return {
            "component": "vosk_installation_guide",
            "mode": "information_only",
            "automatic_installation": False,
            "dependency_installed_by_jarvis": False,
            "model_downloaded_by_jarvis": False,
            "runtime_enabled": False,
            "microphone_enabled": False,
            "audio_recording_enabled": False,
            "network_access_enabled": False,
            "python_version_status": python_status,
            "recommended_model": self.RECOMMENDED_MODEL,
        }
