from core.kernel import JARVISKernel
from users.user_profile import UserProfileManager


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
    profile_manager = UserProfileManager()
    if not profile_manager.profile_exists():
        first_launch_setup(profile_manager)

    user_profile = None
    if profile_manager.profile_exists():
        user_profile = profile_manager.load_profile()

    kernel = JARVISKernel(user_profile=user_profile)
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
