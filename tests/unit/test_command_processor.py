from core.command_processor import CommandProcessor


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
    result = CommandProcessor(sample_profile()).process("открой браузер")

    assert result["intent"] == "unknown"
    assert result["should_exit"] is False
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


if __name__ == "__main__":
    run_tests()
