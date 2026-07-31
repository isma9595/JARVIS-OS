import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import AppCommandSource, JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from language.language_manager import (
    ApplicationLanguageManager,
    LanguagePreferenceSnapshot,
    SupportedLanguage,
)
from users.user_profile import UserProfileManager
from voice.one_shot_vosk_real_recognition import OneShotVoskRealRecognitionResult


def manager(tmp_path):
    return UserProfileManager(Path(tmp_path) / "profile.json")


class CountingProcessor:
    user_profile = {}

    def __init__(self):
        self.calls = []
        self.action_router = type("Router", (), {"calls": []})()
        self.language_manager = None

    def process(self, text):
        self.calls.append(text)
        return {"intent": "test", "response": "processed"}


class FailingRecognizer:
    def __init__(self):
        self.calls = []

    def run_once(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return OneShotVoskRealRecognitionResult(
            allowed=False,
            completed=False,
            blocked=True,
            recognized_text=None,
            capture_seconds=0,
            reasons=["model unavailable"],
            runtime_language=kwargs.get("language_code", "ru-RU"),
        )

    def close(self):
        pass


def test_supported_language_enum_is_typed():
    assert SupportedLanguage.RU_RU.value == "ru-RU"
    assert SupportedLanguage.EN_US.value == "en-US"


def test_default_missing_legacy_invalid_and_corrupt_fall_back_to_ru_ru(tmp_path):
    service = ApplicationLanguageManager.from_profile_manager(manager(tmp_path))
    assert service.get_preference().language_code == "ru-RU"

    profile = manager(tmp_path)
    profile.save_profile({"assistant_name": "JARVIS"})
    assert ApplicationLanguageManager.from_profile_manager(profile).get_preference().language_code == "ru-RU"

    profile.save_profile({"language": "de-DE"})
    assert ApplicationLanguageManager.from_profile_manager(profile).get_preference().language_code == "ru-RU"

    profile.profile_path.write_text("{bad json", encoding="utf-8")
    snapshot = ApplicationLanguageManager.from_profile_manager(profile).get_preference()
    assert snapshot.language_code == "ru-RU"
    assert "Traceback" not in snapshot.safe_message


@pytest.mark.parametrize(
    "alias",
    [" русский ", "русский язык", "RU", "ru-ru", "Russian"],
)
def test_ru_aliases_normalize(alias):
    assert ApplicationLanguageManager.normalize_language(alias) == SupportedLanguage.RU_RU


@pytest.mark.parametrize(
    "alias",
    [" английский ", "английский язык", "English", "EN", "en-us"],
)
def test_en_aliases_normalize(alias):
    assert ApplicationLanguageManager.normalize_language(alias) == SupportedLanguage.EN_US


def test_unsupported_language_rejected_and_does_not_change(tmp_path):
    service = ApplicationLanguageManager.from_profile_manager(manager(tmp_path))
    before = service.get_preference()
    change = service.set_preference("немецкий")

    assert change.changed is False
    assert change.language_code == before.language_code == "ru-RU"
    assert service.get_preference().language_code == "ru-RU"


def test_valid_preference_persists_and_survives_new_instance(tmp_path):
    profile = manager(tmp_path)
    service = ApplicationLanguageManager.from_profile_manager(profile)

    change = service.set_preference("english")

    assert change.language_code == "en-US"
    assert change.persisted is True
    assert ApplicationLanguageManager.from_profile_manager(profile).get_preference().language_code == "en-US"


def test_persistence_exception_is_redacted(tmp_path):
    class BrokenProfile(UserProfileManager):
        def set_language_preference(self, language_code):
            raise RuntimeError("secret token abc")

    service = ApplicationLanguageManager.from_profile_manager(BrokenProfile(Path(tmp_path) / "p.json"))
    change = service.set_preference("en-US")

    assert change.persisted is False
    assert "secret token" not in change.safe_message
    assert "RuntimeError" not in change.safe_message


def test_setting_current_language_is_idempotent_and_reset_restores_default(tmp_path):
    service = ApplicationLanguageManager.from_profile_manager(manager(tmp_path))
    first = service.set_preference("ru")
    service.set_preference("en")
    reset = service.reset_to_default()

    assert first.changed is False
    assert reset.language_code == "ru-RU"
    assert service.get_preference().language_code == "ru-RU"


def test_snapshot_is_immutable_serializable_and_redacted():
    snapshot = LanguagePreferenceSnapshot(
        language_code="ru-RU",
        display_name="Russian",
        is_default=True,
        source="default",
        persisted=False,
        safe_message="Текущий язык: русский (ru-RU).",
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.language_code = "en-US"
    dumped = json.dumps(snapshot.to_dict(), ensure_ascii=False)
    assert "sk-" not in dumped
    assert "ru-RU" in dumped


def test_appservice_exposes_and_changes_preference_safely(tmp_path):
    profile = manager(tmp_path)
    processor = CountingProcessor()
    service = JarvisAppService(
        command_processor=processor,
        language_manager=ApplicationLanguageManager.from_profile_manager(profile),
    )

    assert service.get_language_preference().language_code == "ru-RU"
    changed = service.set_language_preference("en")

    assert changed.language_code == "en-US"
    assert service.get_language_preference().language_code == "en-US"
    assert processor.calls == []


def test_desktop_shell_uses_appservice_only_for_language():
    class FakeService:
        def __init__(self):
            self.executed = []

        def status_text_ru(self):
            return "status"

        def contract_status_text_ru(self):
            return "contracts"

        def list_commands(self, category=None):
            return "commands"

        def resumable_conversation_session_id(self):
            return None

        def handle_desktop_turn(
            self,
            text,
            source,
            *,
            session_id=None,
            idempotency_key=None,
        ):
            self.executed.append((text, source))
            return SimpleNamespace(
                ok=True,
                response_text="Language preference changed to English.",
                cognitive_session_id=session_id,
                diagnostics=SimpleNamespace(
                    safe_text_ru=lambda: "Desktop turn diagnostics:\n- route: execution"
                ),
                execution=SimpleNamespace(
                    ok=True,
                    command_id="profile.language.set",
                    registry_match_id="profile.language.set",
                    category="profile",
                    risk_level="local_write",
                    requires_confirmation=False,
                    requires_clarification=False,
                    operation_id="op-language-test",
                    operation_status="succeeded",
                    executed=True,
                    duplicate_suppressed=False,
                    network_may_be_used=False,
                    plan_id=None,
                    workflow_id=None,
                    error=None,
                ),
                error=None,
            )

    fake = FakeService()
    text = DesktopShellViewModel(fake).execute_command("язык английский")

    assert fake.executed == [("язык английский", AppCommandSource.DESKTOP_UI)]
    assert "Language preference changed to English." in text


def test_language_commands_are_local_and_localized(tmp_path):
    processor = CountingProcessor()
    service = JarvisAppService(
        command_processor=processor,
        language_manager=ApplicationLanguageManager.from_profile_manager(manager(tmp_path)),
    )

    ru_status = service.execute_contract("текущий язык", AppCommandSource.TEST)
    en_set = service.execute_contract("язык английский", AppCommandSource.TEST)
    en_status = service.execute_contract("current language", AppCommandSource.TEST)
    ru_set = service.execute_contract("language Russian", AppCommandSource.TEST)

    assert "русский" in ru_status.output_text
    assert "English" in en_set.output_text
    assert "English" in en_status.output_text
    assert "русский" in ru_set.output_text
    assert processor.calls == []
    assert all(result.network_may_be_used is False for result in (ru_status, en_set, en_status, ru_set))


def test_vague_language_command_requires_bounded_clarification(tmp_path):
    service = JarvisAppService(
        command_processor=CountingProcessor(),
        language_manager=ApplicationLanguageManager.from_profile_manager(manager(tmp_path)),
    )

    result = service.execute_contract("поменяй язык", AppCommandSource.TEST)

    assert result.requires_clarification is True
    assert result.executed is False
    assert service.get_language_preference().language_code == "ru-RU"
    assert {option.command_text for option in result.clarification_options} == {
        "язык русский",
        "язык английский",
    }


def test_unsupported_language_command_uses_active_language(tmp_path):
    service = JarvisAppService(
        command_processor=CountingProcessor(),
        language_manager=ApplicationLanguageManager.from_profile_manager(manager(tmp_path)),
    )
    service.execute_contract("язык английский", AppCommandSource.TEST)
    result = service.execute_contract("язык немецкий", AppCommandSource.TEST)

    assert "Unsupported language" in result.output_text
    assert service.get_language_preference().language_code == "en-US"


def test_voice_runtime_receives_language_without_real_microphone(tmp_path):
    recognizer = FailingRecognizer()
    service = JarvisAppService(
        command_processor=CountingProcessor(),
        language_manager=ApplicationLanguageManager.from_profile_manager(manager(tmp_path)),
        one_shot_voice_recognition=recognizer,
    )
    service.set_language_preference("en")

    result = service.process_one_shot_voice_request(AppCommandSource.TEST)

    assert result.ok is False
    assert recognizer.calls[0][1]["language_code"] == "en-US"
