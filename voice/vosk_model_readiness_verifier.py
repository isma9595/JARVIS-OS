"""Safe filesystem-only readiness checks for a configured Vosk model folder."""

from dataclasses import dataclass, field
from pathlib import Path


MODEL_MARKER_NAMES = {
    "am",
    "conf",
    "graph",
    "ivector",
    "README",
    "README.md",
    "README.txt",
    "final.mdl",
    "mfcc.conf",
    "model.conf",
}


@dataclass(frozen=True)
class VoskModelReadinessResult:
    configured_path: str | None
    path_exists: bool
    is_directory: bool
    is_empty: bool
    looks_like_model: bool
    ready_for_future_recognition: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "configured_path": self.configured_path,
            "path_exists": self.path_exists,
            "is_directory": self.is_directory,
            "is_empty": self.is_empty,
            "looks_like_model": self.looks_like_model,
            "ready_for_future_recognition": self.ready_for_future_recognition,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "safety_notes": list(self.safety_notes),
            "next_steps": list(self.next_steps),
        }


class VoskModelReadinessVerifier:
    """Verify model-folder shape without importing Vosk or touching audio."""

    DEFAULT_SAFETY_NOTES = [
        "Модель Vosk не загружалась.",
        "Микрофон не запускался.",
        "Распознавание не выполнялось.",
        "Автоматическая загрузка и установка не выполнялись.",
    ]

    INSTALLATION_GUIDANCE = (
        "Модель Vosk нужно скачать и распаковать вручную.\n"
        "Рекомендуемая локальная папка: C:\\JARVIS-OS\\models\\<model-folder>\n"
        "Можно использовать, например, русскую small-модель Vosk, не считая её последней версией.\n"
        "После распаковки укажите путь командой: установи путь модели vosk C:\\JARVIS-OS\\models\\<model-folder>\n"
        "Затем проверьте: проверить модель vosk\n"
        "Дополнительно: статус vosk\n"
        "Безопасность: JARVIS ничего не скачивает автоматически, ничего не устанавливает автоматически, модель не загружает, микрофон не запускает."
    )

    def verify(self, configured_path=None):
        path_text = self._normalize_optional_text(configured_path)
        safety_notes = list(self.DEFAULT_SAFETY_NOTES)

        if path_text is None:
            return VoskModelReadinessResult(
                configured_path=None,
                path_exists=False,
                is_directory=False,
                is_empty=False,
                looks_like_model=False,
                ready_for_future_recognition=False,
                reasons=["Путь к модели Vosk не указан."],
                warnings=["Реальное распознавание Vosk в TASK-035 не включается."],
                safety_notes=safety_notes,
                next_steps=[
                    "Скачайте и распакуйте модель вручную.",
                    "Укажите путь командой: установи путь модели vosk <путь>.",
                ],
            )

        try:
            path = Path(path_text)
            path_exists = path.exists()
            is_directory = path.is_dir() if path_exists else False
        except (OSError, TypeError, ValueError):
            path_exists = False
            is_directory = False

        if not path_exists:
            return VoskModelReadinessResult(
                configured_path=path_text,
                path_exists=False,
                is_directory=False,
                is_empty=False,
                looks_like_model=False,
                ready_for_future_recognition=False,
                reasons=["Путь к модели Vosk указан, но папка не найдена."],
                warnings=["Проверьте, что архив модели распакован и путь указан к папке модели."],
                safety_notes=safety_notes,
                next_steps=["Проверьте путь или задайте новый командой: установи путь модели vosk <путь>."],
            )

        if not is_directory:
            return VoskModelReadinessResult(
                configured_path=path_text,
                path_exists=True,
                is_directory=False,
                is_empty=False,
                looks_like_model=False,
                ready_for_future_recognition=False,
                reasons=["Путь к модели Vosk указывает не на папку."],
                warnings=["Нужна папка распакованной модели, а не архив или файл."],
                safety_notes=safety_notes,
                next_steps=["Укажите путь к распакованной папке модели Vosk."],
            )

        entries = self._safe_list_entries(path)
        is_empty = len(entries) == 0
        marker_count = self._count_model_markers(entries)
        looks_like_model = marker_count >= 2 or self._has_named_model_file(entries)

        if is_empty:
            reasons = ["Папка модели Vosk найдена, но она пустая."]
            warnings = ["Пустая папка не похожа на распакованную модель Vosk."]
            next_steps = ["Распакуйте модель Vosk в эту папку или укажите другую папку."]
        elif looks_like_model:
            reasons = ["Папка модели Vosk найдена и похожа на распакованную модель."]
            warnings = ["Это проверка структуры папки, а не загрузка реальной модели."]
            next_steps = ["Можно переходить к следующему этапу проверки локального распознавания в отдельной задаче."]
        else:
            reasons = ["Папка найдена, но она не похожа на распакованную модель Vosk."]
            warnings = ["Найдена папка, но в ней мало типичных маркеров модели Vosk."]
            next_steps = ["Проверьте, что вы указали внутреннюю папку распакованной модели, а не родительский каталог."]

        return VoskModelReadinessResult(
            configured_path=path_text,
            path_exists=True,
            is_directory=True,
            is_empty=is_empty,
            looks_like_model=looks_like_model,
            ready_for_future_recognition=looks_like_model,
            reasons=reasons,
            warnings=warnings,
            safety_notes=safety_notes,
            next_steps=next_steps,
        )

    @classmethod
    def format_russian(cls, result):
        if result.configured_path is None:
            return (
                "Путь к модели Vosk пока не указан.\n"
                "Статус: путь к модели не задан.\n"
                "Следующий шаг: скачайте и распакуйте модель вручную, затем укажите путь командой: установи путь модели vosk <путь>.\n"
                "Безопасность: модель не загружалась, микрофон не запускался, распознавание не выполнялось."
            )

        if not result.path_exists:
            return (
                f"Путь к модели Vosk указан, но папка не найдена: {result.configured_path}.\n"
                "Безопасность: модель не загружалась, микрофон не запускался, распознавание не выполнялось."
            )

        if not result.is_directory:
            return (
                f"Путь к модели Vosk указан, но это не папка: {result.configured_path}.\n"
                "Следующий шаг: укажите путь к распакованной папке модели Vosk."
            )

        if result.is_empty:
            return (
                f"Папка модели Vosk найдена, но она пустая: {result.configured_path}.\n"
                "Следующий шаг: распакуйте модель вручную или укажите другую папку.\n"
                "Безопасность: модель не загружалась, микрофон не запускался, распознавание не выполнялось."
            )

        if result.looks_like_model:
            return (
                "Папка модели Vosk найдена и похожа на распакованную модель.\n"
                "Готовность: можно переходить к следующему этапу проверки локального распознавания.\n"
                "Безопасность: модель не загружалась, микрофон не запускался, распознавание не выполнялось."
            )

        return (
            f"Папка найдена, но она не похожа на распакованную модель Vosk: {result.configured_path}.\n"
            "Следующий шаг: проверьте, что указан путь к внутренней папке распакованной модели.\n"
            "Безопасность: модель не загружалась, микрофон не запускался, распознавание не выполнялось."
        )

    @staticmethod
    def _normalize_optional_text(value):
        if value is None:
            return None
        normalized = str(value).strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1]:
            if normalized[0] in {'"', "'"}:
                normalized = normalized[1:-1].strip()
        return normalized or None

    @staticmethod
    def _safe_list_entries(path):
        try:
            return list(path.iterdir())
        except (OSError, TypeError, ValueError):
            return []

    @staticmethod
    def _count_model_markers(entries):
        names = {entry.name for entry in entries}
        lower_names = {name.lower() for name in names}
        count = 0
        for marker in MODEL_MARKER_NAMES:
            if marker in names or marker.lower() in lower_names:
                count += 1
        return count

    @staticmethod
    def _has_named_model_file(entries):
        common_suffixes = (".mdl", ".conf", ".fst", ".carpa")
        for entry in entries:
            if entry.name.lower().endswith(common_suffixes):
                return True
        return False
