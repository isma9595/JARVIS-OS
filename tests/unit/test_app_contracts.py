from app.app_contracts import (
    APP_CONTRACT_SCHEMA_NAME,
    APP_CONTRACT_VERSION,
    AppCommandCard,
    AppStatusCard,
)
from app import AppCommandSource, JarvisAppService


class FakeCommandProcessor:
    def __init__(self):
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        return {"response": f"processed {text} sk-test-1234567890secret"}


def test_contract_status_has_schema_version_and_safe_flags():
    status = JarvisAppService(command_processor=FakeCommandProcessor()).contract_status()

    assert status.schema_name == APP_CONTRACT_SCHEMA_NAME
    assert status.version == APP_CONTRACT_VERSION
    assert status.network_default is False
    assert status.secrets_included is False
    assert status.responses_executed_as_commands is False


def test_dataclasses_to_dict_are_deterministic_and_safe():
    card = AppStatusCard(
        card_id="safe",
        title_ru="Safe",
        value_ru="api key=sk-test-1234567890secret",
        status="ready",
        category="app",
        safe=True,
        ui_visible=True,
        details_ru=("token=abcd1234567890",),
    )

    assert list(card.to_dict()) == [
        "card_id",
        "title_ru",
        "value_ru",
        "status",
        "category",
        "safe",
        "ui_visible",
        "details_ru",
    ]
    assert "sk-test-1234567890secret" not in str(card.to_dict())
    assert "token=abcd1234567890" not in str(card.to_dict())


def test_command_card_to_dict_safe():
    card = AppCommandCard(
        command_id="cmd",
        title_ru="Title",
        description_ru="Description",
        category="app",
        aliases=("alias",),
        risk_level="read_only",
        read_only=True,
        voice_auto_allowed=True,
        requires_confirmation=False,
        requires_network=False,
        requires_ai_key=False,
        requires_privacy_check=False,
        app_ready=True,
        ui_visible=True,
        notes_ru="api key=sk-test-1234567890secret",
    )

    data = card.to_dict()

    assert data["command_id"] == "cmd"
    assert "sk-test-1234567890secret" not in str(data)


def test_preview_contract_for_known_command_safe_and_not_executed():
    processor = FakeCommandProcessor()
    service = JarvisAppService(command_processor=processor)

    preview = service.preview_contract("app contracts status")

    assert preview.known_command is True
    assert preview.command_id == "app_contracts.status"
    assert preview.category == "app"
    assert preview.risk_level == "read_only"
    assert preview.executed is False
    assert preview.secrets_included is False
    assert processor.calls == []


def test_preview_contract_for_provider_real_request_marks_network_privacy_and_risk():
    preview = JarvisAppService(command_processor=FakeCommandProcessor()).preview_contract(
        "groq реальный запрос: test"
    )

    assert preview.command_id == "ai_provider.groq.real_request"
    assert preview.requires_network is True
    assert preview.requires_privacy_check is True
    assert preview.risk_level == "network_explicit"
    assert preview.executed is False


def test_execution_contract_wraps_output_and_never_executes_response():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    result = service.execute_contract("app contracts status", AppCommandSource.TEST)

    assert result.ok is True
    assert result.executed is True
    assert result.response_executed_as_command is False
    assert result.secrets_included is False
    assert "sk-test-1234567890secret" not in result.output_text


def test_no_raw_secret_like_strings_in_contract_outputs():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    secret = "sk-test-1234567890secret"

    text = "\n".join(
        [
            service.contract_status_text_ru(),
            service.status_cards_text_ru(),
            service.command_cards_text_ru(),
            service.contract_manifest_text_ru(),
            service.preview_contract(f"app preview: api key={secret}").safe_text_ru(),
        ]
    )

    assert secret not in text
    assert "secrets included: no" in text


def test_contract_manifest_includes_categories_and_command_count():
    manifest = JarvisAppService(command_processor=FakeCommandProcessor()).contract_manifest()

    assert manifest.schema_name == APP_CONTRACT_SCHEMA_NAME
    assert manifest.version == APP_CONTRACT_VERSION
    assert manifest.command_cards_count > 0
    assert "app" in manifest.categories
    assert manifest.status_cards
    assert any(card.card_id == "audio_lifecycle" for card in manifest.status_cards)


def test_command_cards_are_created_from_registry_metadata():
    service = JarvisAppService(command_processor=FakeCommandProcessor())

    cards = service.command_cards("app")
    ids = {card.command_id for card in cards}

    assert "app_contracts.status" in ids
    assert any(card.aliases for card in cards)


def test_audio_status_card_is_safe_no_network_no_audio_saved():
    service = JarvisAppService(command_processor=FakeCommandProcessor())
    card = service.audio_status_card()

    assert card.card_id == "audio_lifecycle"
    assert card.category == "voice"
    assert card.safe is True
    text = card.safe_text_ru()
    assert "network used: no" in text
    assert "audio saved: no" in text
