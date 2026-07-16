import json

import pytest

from voice.russian_voice_normalizer import normalize_russian_voice_text


@pytest.mark.parametrize(
    "recognized",
    [
        "статус системы",
        "статус система",
        "статус систем",
        "СТАТУС СИСТЕМА",
        "  статус   система  ",
        "джарвис статус система",
        "джарвис, статус системы",
        "пожалуйста статус система",
    ],
)
def test_required_safe_status_cases_normalize_to_system_status(recognized):
    result = normalize_russian_voice_text(recognized)

    assert result.original_text == recognized
    assert result.normalized_text == "статус системы"
    assert result.safe_to_use_as_command_candidate is True


@pytest.mark.parametrize(
    "recognized",
    [
        "статус заказа",
        "система статусов",
        "расскажи про систему",
        "что такое статус системы",
        "почему система имеет статус",
        "проверь статус документа",
    ],
)
def test_negative_cases_do_not_normalize_into_system_status(recognized):
    result = normalize_russian_voice_text(recognized)

    assert result.original_text == recognized
    assert result.normalized_text != "статус системы"
    assert result.safe_to_use_as_command_candidate is False


@pytest.mark.parametrize(
    "recognized",
    [
        "удали фал",
        "отправь писмо",
        "выключи компютер",
        "перезагрузи ноутбок",
        "можно ли удалить файл",
        "как отправить письмо",
        "что будет если выключить компьютер",
    ],
)
def test_risky_misspellings_remain_unresolved(recognized):
    result = normalize_russian_voice_text(recognized)

    assert result.original_text == recognized
    assert result.normalized_text == recognized
    assert result.safe_to_use_as_command_candidate is False


def test_original_text_is_preserved_while_cyrillic_result_serializes():
    result = normalize_russian_voice_text("  СТАТУС   СИСТЕМА  ")
    payload = result.to_dict()
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert result.original_text == "  СТАТУС   СИСТЕМА  "
    assert payload["normalized_text"] == "статус системы"
    assert "статус системы" in serialized


def test_repeated_calls_are_deterministic():
    first = normalize_russian_voice_text("джарвис, статус системы")
    second = normalize_russian_voice_text("джарвис, статус системы")

    assert first == second
    assert first.to_dict() == second.to_dict()


def test_unsupported_locale_returns_text_unchanged():
    result = normalize_russian_voice_text("СТАТУС СИСТЕМА", locale="en-US")

    assert result.original_text == "СТАТУС СИСТЕМА"
    assert result.normalized_text == "СТАТУС СИСТЕМА"
    assert result.changed is False
    assert result.applied_rules == ()
    assert result.safe_to_use_as_command_candidate is False


def test_normalizer_does_not_call_execution_or_provider_boundaries(monkeypatch):
    import core.action_router
    import core.command_processor

    def fail(*_args, **_kwargs):
        raise AssertionError("normalizer must not execute or route commands")

    monkeypatch.setattr(core.command_processor.CommandProcessor, "process", fail)
    monkeypatch.setattr(core.action_router.SafeActionRouter, "route", fail)

    result = normalize_russian_voice_text("статус система")

    assert result.normalized_text == "статус системы"
    assert result.safe_to_use_as_command_candidate is True
