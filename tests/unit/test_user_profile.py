from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from users.user_profile import UserProfileManager


def create_manager():
    temp_dir = TemporaryDirectory()
    profile_path = Path(temp_dir.name) / "profiles" / "default_user.json"
    return temp_dir, UserProfileManager(profile_path)


def sample_profile():
    return {
        "user_name": "Исмаил",
        "preferred_name": "Исмаил",
        "assistant_name": "JARVIS",
        "language": "ru",
        "age": None,
        "main_use_cases": ["документы", "помощь в проектах"],
        "communication_style": "естественный, понятный, не робот",
    }


def test_manager_creation():
    temp_dir, manager = create_manager()
    try:
        assert isinstance(manager, UserProfileManager)
        assert manager.profile_path.name == "default_user.json"
    finally:
        temp_dir.cleanup()


def test_profile_absence():
    temp_dir, manager = create_manager()
    try:
        assert manager.profile_exists() is False
    finally:
        temp_dir.cleanup()


def test_profile_save():
    temp_dir, manager = create_manager()
    try:
        saved_profile = manager.save_profile(sample_profile())

        assert manager.profile_exists() is True
        assert saved_profile["created_at"]
        assert saved_profile["updated_at"]
    finally:
        temp_dir.cleanup()


def test_profile_load():
    temp_dir, manager = create_manager()
    try:
        manager.save_profile(sample_profile())
        loaded_profile = manager.load_profile()

        assert loaded_profile["user_name"] == "Исмаил"
        assert loaded_profile["preferred_name"] == "Исмаил"
    finally:
        temp_dir.cleanup()


def test_get_user_name():
    temp_dir, manager = create_manager()
    try:
        profile = manager.save_profile(sample_profile())

        assert manager.get_user_name(profile) == "Исмаил"
    finally:
        temp_dir.cleanup()


def test_get_assistant_name():
    temp_dir, manager = create_manager()
    try:
        profile = manager.save_profile(sample_profile())

        assert manager.get_assistant_name(profile) == "JARVIS"
    finally:
        temp_dir.cleanup()


def test_default_assistant_name_returns_jarvis():
    temp_dir, manager = create_manager()
    try:
        profile = sample_profile()
        profile.pop("assistant_name")

        assert manager.get_assistant_name(profile) == "JARVIS"
    finally:
        temp_dir.cleanup()


def test_set_assistant_name():
    temp_dir, manager = create_manager()
    try:
        manager.save_profile(sample_profile())
        manager.set_assistant_name("ВанДам")

        assert manager.get_assistant_name() == "ВанДам"
    finally:
        temp_dir.cleanup()


def test_reset_assistant_name_returns_default():
    temp_dir, manager = create_manager()
    try:
        manager.save_profile(sample_profile())
        manager.set_assistant_name("Али")
        manager.reset_assistant_name()

        assert manager.get_assistant_name() == "JARVIS"
    finally:
        temp_dir.cleanup()


def test_empty_assistant_name_is_rejected():
    temp_dir, manager = create_manager()
    try:
        manager.save_profile(sample_profile())

        with pytest.raises(ValueError):
            manager.set_assistant_name("   ")

        assert manager.get_assistant_name() == "JARVIS"
    finally:
        temp_dir.cleanup()


def test_too_long_assistant_name_is_rejected():
    temp_dir, manager = create_manager()
    try:
        manager.save_profile(sample_profile())

        with pytest.raises(ValueError):
            manager.set_assistant_name("А" * 41)

        assert manager.get_assistant_name() == "JARVIS"
    finally:
        temp_dir.cleanup()


def test_multiline_or_control_assistant_name_is_rejected():
    temp_dir, manager = create_manager()
    try:
        manager.save_profile(sample_profile())

        for name in ("Али\nБот", "Али\tБот", "Али\x1fБот"):
            with pytest.raises(ValueError):
                manager.set_assistant_name(name)

        assert manager.get_assistant_name() == "JARVIS"
    finally:
        temp_dir.cleanup()


def test_get_language():
    temp_dir, manager = create_manager()
    try:
        profile = manager.save_profile(sample_profile())

        assert manager.get_language(profile) == "ru"
    finally:
        temp_dir.cleanup()


def test_get_communication_style():
    temp_dir, manager = create_manager()
    try:
        profile = manager.save_profile(sample_profile())

        assert manager.get_communication_style(profile) == (
            "естественный, понятный, не робот"
        )
    finally:
        temp_dir.cleanup()


def test_optional_age():
    temp_dir, manager = create_manager()
    try:
        profile = manager.create_profile(
            user_name="Исмаил",
            preferred_name="Исмаил",
            assistant_name="JARVIS",
            language="ru",
            age=None,
            main_use_cases=[],
            communication_style="естественный, понятный, не робот",
        )

        assert profile["age"] is None
    finally:
        temp_dir.cleanup()


def test_standard_library_only_behavior():
    temp_dir, manager = create_manager()
    try:
        manager.create_profile(
            user_name="User",
            preferred_name="User",
            assistant_name="JARVIS",
            language="ru",
            age=None,
            main_use_cases=[],
            communication_style="natural",
        )

        assert manager.load_profile()["assistant_name"] == "JARVIS"
    finally:
        temp_dir.cleanup()


def run_tests():
    test_manager_creation()
    test_profile_absence()
    test_profile_save()
    test_profile_load()
    test_get_user_name()
    test_get_assistant_name()
    test_default_assistant_name_returns_jarvis()
    test_set_assistant_name()
    test_reset_assistant_name_returns_default()
    test_empty_assistant_name_is_rejected()
    test_too_long_assistant_name_is_rejected()
    test_multiline_or_control_assistant_name_is_rejected()
    test_get_language()
    test_get_communication_style()
    test_optional_age()
    test_standard_library_only_behavior()


if __name__ == "__main__":
    run_tests()
