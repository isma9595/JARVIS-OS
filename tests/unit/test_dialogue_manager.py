from dialogue import DialogueManager


def sample_profile():
    return {
        "user_name": "Исмаил",
        "preferred_name": "Исмаил",
        "assistant_name": "JARVIS",
        "language": "ru",
        "communication_style": "естественный, понятный, не робот",
    }


def test_creation_without_profile():
    dialogue = DialogueManager()

    assert dialogue.get_user_name() == "Пользователь"
    assert dialogue.get_preferred_name() == "Пользователь"


def test_creation_with_profile():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_preferred_name() == "Исмаил"


def test_get_user_name():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_user_name() == "Исмаил"


def test_get_assistant_name():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_assistant_name() == "JARVIS"


def test_get_language():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_language() == "ru"


def test_get_communication_style():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.get_communication_style() == "естественный, понятный, не робот"


def test_greeting():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.greeting() == "Добро пожаловать, Исмаил."


def test_startup_complete():
    dialogue = DialogueManager()

    assert dialogue.startup_complete() == "Система успешно запущена."


def test_shutdown_message():
    dialogue = DialogueManager()

    assert dialogue.shutdown_message() == "Система остановлена."


def test_already_stopped_message():
    dialogue = DialogueManager()

    assert dialogue.already_stopped_message() == "Ядро уже остановлено."


def test_confirmation_request():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.confirmation_request("отправить письмо") == (
        "Исмаил, я могу выполнить действие: отправить письмо. Подтвердить?"
    )


def test_action_requires_confirmation_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.action_requires_confirmation_response("отправить письмо") == (
        "Исмаил, это действие требует подтверждения: отправить письмо. "
        "Я не буду выполнять его без вашего разрешения."
    )


def test_forbidden_action_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.forbidden_action_response("удали system32") == (
        "Исмаил, я не могу выполнить это действие, потому что оно может быть опасным."
    )


def test_future_idea_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.future_idea_response("новая команда") == (
        "Исмаил, я пока не умею выполнять эту команду, "
        "но могу сохранить её как идею для будущего."
    )


def test_safe_action_response():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.safe_action_response("подготовь черновик") == (
        "Исмаил, это безопасная команда: подготовь черновик. "
        "На этом этапе я только определяю действие и не выполняю его."
    )


def test_acknowledgement():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.acknowledgement("подготовить письмо") == (
        "Понял, Исмаил. Подготовлю: подготовить письмо."
    )


def test_error_message():
    dialogue = DialogueManager(sample_profile())

    assert dialogue.error_message("файл не найден") == (
        "Исмаил, возникла ошибка: файл не найден."
    )


def run_tests():
    test_creation_without_profile()
    test_creation_with_profile()
    test_get_user_name()
    test_get_assistant_name()
    test_get_language()
    test_get_communication_style()
    test_greeting()
    test_startup_complete()
    test_shutdown_message()
    test_already_stopped_message()
    test_confirmation_request()
    test_action_requires_confirmation_response()
    test_forbidden_action_response()
    test_future_idea_response()
    test_safe_action_response()
    test_acknowledgement()
    test_error_message()


if __name__ == "__main__":
    run_tests()
