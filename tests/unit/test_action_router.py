from core.action_router import SafeActionRouter


def sample_profile():
    return {
        "user_name": "Исмаил",
        "preferred_name": "Исмаил",
        "assistant_name": "JARVIS",
        "language": "ru",
        "communication_style": "естественный, понятный, не робот",
    }


def test_creation_without_profile():
    router = SafeActionRouter()

    assert router.user_profile == {}


def test_creation_with_profile():
    router = SafeActionRouter(sample_profile())

    assert router.user_profile["preferred_name"] == "Исмаил"


def test_informational_command():
    result = SafeActionRouter(sample_profile()).route("кто я")

    assert result["category"] == "informational"
    assert result["risk_level"] == "low"
    assert result["allowed"] is True
    assert result["requires_confirmation"] is False
    assert "безопасная команда" in result["response"]


def test_safe_action_command():
    result = SafeActionRouter(sample_profile()).route("подготовь черновик")

    assert result["category"] == "safe_action"
    assert result["risk_level"] == "low"
    assert result["allowed"] is True
    assert result["requires_confirmation"] is False
    assert "не выполняю" in result["response"]


def test_confirmation_required_command():
    result = SafeActionRouter(sample_profile()).route("отправь письмо")

    assert result["category"] == "confirmation_required"
    assert result["risk_level"] == "medium"
    assert result["allowed"] is True
    assert result["requires_confirmation"] is True
    assert "требует подтверждения" in result["response"]


def test_forbidden_command():
    result = SafeActionRouter(sample_profile()).route("удали system32")

    assert result["category"] == "forbidden"
    assert result["risk_level"] == "high"
    assert result["allowed"] is False
    assert result["requires_confirmation"] is False
    assert "не могу выполнить" in result["response"]


def test_idea_command():
    result = SafeActionRouter(sample_profile()).route("запусти космический режим")

    assert result["category"] == "idea"
    assert result["risk_level"] == "unknown"
    assert result["allowed"] is False
    assert result["requires_confirmation"] is False
    assert "идею для будущего" in result["response"]


def test_empty_command():
    result = SafeActionRouter(sample_profile()).route("   ")

    assert result["category"] == "empty"
    assert result["risk_level"] == "low"
    assert result["allowed"] is False
    assert result["requires_confirmation"] is False
    assert "не услышал команду" in result["response"]


def test_normalizes_command():
    result = SafeActionRouter(sample_profile()).route("  УДАЛИ SYSTEM32  ")

    assert result["category"] == "forbidden"


def run_tests():
    test_creation_without_profile()
    test_creation_with_profile()
    test_informational_command()
    test_safe_action_command()
    test_confirmation_required_command()
    test_forbidden_command()
    test_idea_command()
    test_empty_command()
    test_normalizes_command()


if __name__ == "__main__":
    run_tests()
