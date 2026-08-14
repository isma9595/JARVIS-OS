from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
from pathlib import Path

from core.kernel import JARVISKernel
from ideas import IdeaManager
from memory import LocalMemoryManager
from platform_adapters.user_data_migration import (
    CompositionMigrationReport,
    DeterministicLegacyRegistry,
    UserDataMigrationBlockedError,
    UserDataMigrationCoordinator,
)
from platform_adapters.user_data_paths import UserDataPaths
from users.user_profile import UserProfileManager
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognition
from voice.vosk_settings_manager import VoskSettingsManager


@dataclass(frozen=True)
class DefaultCliComposition:
    paths: UserDataPaths
    migration_report: CompositionMigrationReport
    profile_manager: UserProfileManager
    kernel: JARVISKernel


def create_default_cli_composition(
    *,
    environment: Mapping[str, object] | None = None,
    home: str | os.PathLike[str] | None = None,
    project_root: str | os.PathLike[str] | None = None,
    store_overrides: Mapping[str, str | os.PathLike[str]] | None = None,
    profile_setup: Callable[[UserProfileManager], object] | None = None,
) -> DefaultCliComposition:
    """Build the supported CLI owners after bounded migration completes."""

    selected_environment = os.environ if environment is None else environment
    paths = UserDataPaths.resolve(
        environment=selected_environment,
        home=home,
        project_root=project_root,
    )
    conversation_override = _environment_path(
        selected_environment,
        "JARVIS_COGNITIVE_SESSION_DIR",
    )
    external_overrides = {
        store_id: Path(os.fspath(path))
        for store_id, path in (store_overrides or {}).items()
    }
    if "conversation" not in external_overrides and conversation_override is not None:
        external_overrides["conversation"] = conversation_override
    registry = DeterministicLegacyRegistry.from_user_data_paths(
        paths,
        conversation_legacy=_legacy_conversation_path(
            selected_environment,
            home=home,
        ),
    )
    migration_report = UserDataMigrationCoordinator(
        paths,
        registry,
        external_overrides=external_overrides,
    ).migrate_all()
    if not migration_report.completed:
        raise UserDataMigrationBlockedError(migration_report.blocking_store_id or "unknown")

    profile_manager = UserProfileManager(
        profile_path=external_overrides.get("profile", paths.profile)
    )
    if profile_setup is not None and not profile_manager.profile_exists():
        profile_setup(profile_manager)
    user_profile = profile_manager.load_profile() if profile_manager.profile_exists() else None
    memory_manager = LocalMemoryManager(
        storage_path=external_overrides.get("memory", paths.memory)
    )
    idea_manager = IdeaManager(
        storage_path=external_overrides.get("ideas", paths.ideas)
    )
    vosk_settings_manager = VoskSettingsManager(
        settings_path=external_overrides.get("vosk_settings", paths.vosk_settings)
    )
    one_shot = OneShotVoskRealRecognition(settings_manager=vosk_settings_manager)
    kernel = JARVISKernel(
        user_profile=user_profile,
        idea_manager=idea_manager,
        memory_manager=memory_manager,
        user_profile_manager=profile_manager,
        vosk_settings_manager=vosk_settings_manager,
        one_shot_vosk_real_recognition=one_shot,
    )
    return DefaultCliComposition(
        paths=paths,
        migration_report=migration_report,
        profile_manager=profile_manager,
        kernel=kernel,
    )


def _environment_path(
    environment: Mapping[str, object],
    name: str,
) -> Path | None:
    value = environment.get(name)
    if value is None or value == "":
        return None
    try:
        return Path(os.fspath(value))
    except Exception:
        raise ValueError(f"{name.lower()}_invalid") from None


def _legacy_conversation_path(
    environment: Mapping[str, object],
    *,
    home: str | os.PathLike[str] | None,
) -> Path:
    local_app_data = _environment_path(environment, "LOCALAPPDATA")
    if local_app_data is not None and local_app_data.is_absolute():
        return local_app_data / "JARVIS-OS" / "data" / "v1" / "cognition" / "sessions"
    selected_home = Path.home() if home is None else Path(home)
    return selected_home / ".jarvis-os" / "data" / "v1" / "cognition" / "sessions"


def _ask_required(question, default=None):
    answer = input(question).strip()
    if answer:
        return answer
    return default or _ask_required(question, default)


def _ask_optional(question, default=None):
    answer = input(question).strip()
    return answer or default


def _parse_age(value):
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _parse_use_cases(value):
    if not value:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


def first_launch_setup(profile_manager):
    print("Здравствуйте. Я JARVIS.")
    print("Давайте познакомимся.")

    user_name = _ask_required("Как вас зовут? ")
    preferred_name = _ask_required("Как мне к вам обращаться? ", user_name)
    assistant_name = _ask_required("Как вы хотите назвать ассистента? ", "JARVIS")
    language = _ask_optional("Какой язык использовать? По умолчанию ru. ", "ru")
    age = _parse_age(
        _ask_optional("Хотите указать возраст? Это необязательно. ")
    )
    main_use_cases = _parse_use_cases(
        _ask_optional(
            "В каких сферах вы планируете использовать ассистента? "
        )
    )
    communication_style = _ask_optional(
        "Какой стиль общения вам удобен? ",
        "естественный, понятный, не робот",
    )

    return profile_manager.create_profile(
        user_name=user_name,
        preferred_name=preferred_name,
        assistant_name=assistant_name,
        language=language,
        age=age,
        main_use_cases=main_use_cases,
        communication_style=communication_style,
    )


def main():
    composition = create_default_cli_composition(profile_setup=first_launch_setup)
    kernel = composition.kernel
    kernel.start()

    command_processor = kernel.get_service("command_processor")
    print(
        "Введите команду для JARVIS. "
        "Для выхода напишите: выход"
    )

    while kernel.running:
        try:
            command_text = input("> ")
        except EOFError:
            command_text = "выход"

        result = command_processor.process(command_text)
        print(result["response"])

        if result["should_exit"]:
            kernel.shutdown()
            break


if __name__ == "__main__":
    main()
