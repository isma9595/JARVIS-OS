from core.command_processor import CommandProcessor
from ideas import IdeaManager
from pathlib import Path
from tempfile import TemporaryDirectory


def sample_profile():
    return {
        "user_name": "Исмаил",
        "preferred_name": "Исмаил",
        "assistant_name": "JARVIS",
        "language": "ru",
        "communication_style": "естественный, понятный, не робот",
        "main_use_cases": ["работа", "обучение"],
    }


def test_creation_without_profile():
    processor = CommandProcessor()

    assert processor.user_profile == {}


def test_creation_with_profile():
    processor = CommandProcessor(sample_profile())

    assert processor.user_profile["preferred_name"] == "Исмаил"


def test_user_identity_command():
    result = CommandProcessor(sample_profile()).process("кто я")

    assert result["intent"] == "user.identity"
    assert result["should_exit"] is False
    assert "Исмаил" in result["response"]


def test_assistant_identity_command():
    result = CommandProcessor(sample_profile()).process("как тебя зовут")

    assert result["intent"] == "assistant.identity"
    assert result["should_exit"] is False
    assert "JARVIS" in result["response"]


def test_profile_command():
    result = CommandProcessor(sample_profile()).process("покажи профиль")

    assert result["intent"] == "user.profile"
    assert result["should_exit"] is False
    assert "Имя пользователя: Исмаил" in result["response"]
    assert "Имя ассистента: JARVIS" in result["response"]
    assert "Язык: ru" in result["response"]
    assert "Стиль общения: естественный, понятный, не робот" in result["response"]
    assert "работа, обучение" in result["response"]


def test_capabilities_command():
    result = CommandProcessor(sample_profile()).process("что ты умеешь")

    assert result["intent"] == "assistant.capabilities"
    assert result["should_exit"] is False
    assert "простые текстовые команды" in result["response"]
    assert "Голос, зрение экрана и автоматизация" in result["response"]


def test_exit_command():
    result = CommandProcessor(sample_profile()).process("выход")

    assert result["intent"] == "system.exit"
    assert result["should_exit"] is True
    assert result["response"] == "Хорошо, Исмаил. Завершаю работу."


def test_unknown_command():
    result = CommandProcessor(sample_profile()).process("запусти космический режим")

    assert result["intent"] == "unknown"
    assert result["should_exit"] is False
    assert result["category"] == "idea"
    assert result["risk_level"] == "unknown"
    assert "идею для будущего" in result["response"]


def test_empty_command():
    result = CommandProcessor(sample_profile()).process("   ")

    assert result["intent"] == "empty"
    assert result["should_exit"] is False
    assert result["response"] == (
        "Исмаил, я не услышал команду. Повторите, пожалуйста."
    )


def test_exit_command_should_exit():
    result = CommandProcessor(sample_profile()).process("стоп")

    assert result["should_exit"] is True


def test_normalizes_command():
    result = CommandProcessor(sample_profile()).process("  Кто Я  ")

    assert result["intent"] == "user.identity"


def test_send_email_requires_confirmation():
    result = CommandProcessor(sample_profile()).process("отправь письмо")

    assert result["intent"] == "action.confirmation_required"
    assert result["category"] == "confirmation_required"
    assert result["requires_confirmation"] is True
    assert result["risk_level"] == "medium"
    assert "требует подтверждения" in result["response"]


def test_delete_file_requires_confirmation():
    result = CommandProcessor(sample_profile()).process("удали файл")

    assert result["intent"] == "action.confirmation_required"
    assert result["category"] == "confirmation_required"
    assert result["requires_confirmation"] is True
    assert result["risk_level"] == "medium"


def test_delete_system32_is_forbidden():
    result = CommandProcessor(sample_profile()).process("удали system32")

    assert result["intent"] == "action.forbidden"
    assert result["category"] == "forbidden"
    assert result["allowed"] is False
    assert result["risk_level"] == "high"
    assert "не могу выполнить" in result["response"]


def test_unknown_action_is_future_idea_without_execution():
    result = CommandProcessor(sample_profile()).process("настрой утренний сценарий")

    assert result["intent"] == "unknown"
    assert result["category"] == "idea"
    assert result["allowed"] is False
    assert result["requires_confirmation"] is False
    assert result["risk_level"] == "unknown"


def test_add_idea_command():
    with TemporaryDirectory() as tmp_dir:
        idea_manager = IdeaManager(Path(tmp_dir) / "ideas.json")
        processor = CommandProcessor(sample_profile(), idea_manager=idea_manager)

        result = processor.process("добавь идею научиться видеть экран")

        assert result["intent"] == "idea.add"
        assert result["should_exit"] is False
        assert idea_manager.count_ideas() == 1
        assert idea_manager.list_ideas()[0]["title"] == "научиться видеть экран"
        assert "я сохранил идею: научиться видеть экран" in result["response"]


def test_remember_idea_command():
    with TemporaryDirectory() as tmp_dir:
        idea_manager = IdeaManager(Path(tmp_dir) / "ideas.json")
        processor = CommandProcessor(sample_profile(), idea_manager=idea_manager)

        result = processor.process("запомни идею сделать голосовое управление")

        assert result["intent"] == "idea.add"
        assert result["should_exit"] is False
        assert idea_manager.list_ideas()[0]["title"] == "сделать голосовое управление"


def test_list_ideas_command():
    with TemporaryDirectory() as tmp_dir:
        idea_manager = IdeaManager(Path(tmp_dir) / "ideas.json")
        idea_manager.add_idea("научиться видеть экран")
        processor = CommandProcessor(sample_profile(), idea_manager=idea_manager)

        result = processor.process("покажи идеи")

        assert result["intent"] == "idea.list"
        assert result["should_exit"] is False
        assert "1. научиться видеть экран" in result["response"]


def run_tests():
    test_creation_without_profile()
    test_creation_with_profile()
    test_user_identity_command()
    test_assistant_identity_command()
    test_profile_command()
    test_capabilities_command()
    test_exit_command()
    test_unknown_command()
    test_empty_command()
    test_exit_command_should_exit()
    test_normalizes_command()
    test_send_email_requires_confirmation()
    test_delete_file_requires_confirmation()
    test_delete_system32_is_forbidden()
    test_unknown_action_is_future_idea_without_execution()
    test_add_idea_command()
    test_remember_idea_command()
    test_list_ideas_command()


if __name__ == "__main__":
    run_tests()
