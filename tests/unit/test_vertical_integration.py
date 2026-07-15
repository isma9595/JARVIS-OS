from app import JarvisAppService
from app.desktop_shell import DesktopShellViewModel
from app.vertical_integration import VerticalIntegrationService
from core.command_registry import CommandCategory, CommandRiskLevel, CommandRegistry
from voice import SafeVoiceCommandAllowlist


SECRET = "sk-test-1234567890secret"
REQUIRED_CHECKS = {
    "command_registry_available",
    "command_registry_has_required_categories",
    "app_contracts_available",
    "app_contract_manifest_safe",
    "app_service_status_safe",
    "app_service_preview_safe",
    "desktop_viewmodel_safe",
    "secure_keys_safe",
    "audio_lifecycle_safe",
    "voice_allowlist_safe",
    "ai_safety_safe",
    "no_network_no_secret_integration",
    "command_processor_smoke_safe",
}


def test_report_exists_and_overall_passed_true():
    report = VerticalIntegrationService().run_report()

    assert report.report_id == "vertical_integration"
    assert report.overall_passed is True
    assert report.checks_count == len(REQUIRED_CHECKS)
    assert report.passed_count == report.checks_count
    assert report.failed_count == 0
    assert {check.check_id for check in report.checks} == REQUIRED_CHECKS


def test_report_has_no_network_secrets_audio_mic_tts_or_providers():
    report = VerticalIntegrationService().run_report()

    assert report.network_used is False
    assert report.secrets_included is False
    assert report.audio_started is False
    assert report.microphone_started is False
    assert report.tts_started is False
    assert report.providers_called is False
    assert report.command_execution_used is False


def test_registry_categories_include_required_layers():
    categories = set(CommandRegistry().categories())

    for category in (
        CommandCategory.APP,
        CommandCategory.AI,
        CommandCategory.AI_PROVIDER,
        CommandCategory.SECURE_KEYS,
        CommandCategory.AUDIO,
        CommandCategory.VOICE,
        CommandCategory.SAFETY,
        CommandCategory.INTEGRATION,
    ):
        assert category in categories


def test_app_contract_manifest_safe_and_has_command_cards():
    service = JarvisAppService()
    manifest = service.contract_manifest()

    assert manifest.command_cards_count > 0
    assert manifest.status.secrets_included is False
    assert manifest.status.network_default is False
    assert manifest.status.responses_executed_as_commands is False


def test_app_service_preview_known_and_provider_commands_are_safe():
    service = JarvisAppService()

    status_preview = service.preview_command("статус ai")
    provider_preview = service.preview_contract("groq реальный запрос: test")

    assert status_preview.known_command is True
    assert status_preview.registry_match_id == "ai.status"
    assert status_preview.read_only is True
    assert status_preview.requires_network is False
    assert provider_preview.command_id == "ai_provider.groq.real_request"
    assert provider_preview.risk_level == "network_explicit"
    assert provider_preview.requires_network is True
    assert provider_preview.requires_privacy_check is True
    assert provider_preview.executed is False


def test_desktop_viewmodel_builds_without_gui_and_previews_status():
    view_model = DesktopShellViewModel(JarvisAppService())

    text = view_model.preview_command("статус ai")

    assert view_model.state.ui_ready is True
    assert view_model.state.safe_mode is True
    assert "- does not execute command" in text
    assert "- command id: ai.status" in text
    assert "- requires_network: no" in text


def test_secure_key_status_and_list_metadata_have_no_secrets():
    cards = JarvisAppService().command_cards("secure_keys")
    text = "\n".join(card.safe_text_ru() for card in cards)

    assert cards
    assert SECRET not in text
    assert all(card.requires_network is False for card in cards)
    assert any(card.command_id == "secure_keys.status" for card in cards)
    assert any(card.command_id == "secure_keys.list" for card in cards)


def test_audio_lifecycle_status_safe():
    status = JarvisAppService().audio_lifecycle_status()

    assert status.microphone_active is False
    assert status.speaking_active is False
    assert status.continuous_listening_allowed is False
    assert status.audio_saved is False
    assert status.network_used is False


def test_voice_allowlist_allows_integration_read_only_and_rejects_risky():
    allowlist = SafeVoiceCommandAllowlist()

    for command in VerticalIntegrationService.SAFE_VOICE_COMMANDS:
        assert allowlist.decide(command).allowed is True

    for command in VerticalIntegrationService.RISKY_VOICE_COMMANDS:
        assert allowlist.decide(command).allowed is False


def test_ai_provider_real_requests_are_explicit_only():
    registry = CommandRegistry()
    provider_requests = [
        command
        for command in registry.commands
        if command.category == CommandCategory.AI_PROVIDER
        and command.risk_level == CommandRiskLevel.NETWORK_EXPLICIT
    ]

    assert provider_requests
    assert all(command.requires_network for command in provider_requests)
    assert all(command.requires_privacy_check for command in provider_requests)
    assert all(command.requires_confirmation for command in provider_requests)
    assert all(command.voice_auto_allowed is False for command in provider_requests)


def test_report_text_and_checklist_have_no_secret_like_strings():
    service = VerticalIntegrationService()

    report_text = service.report_text_ru() + f"\napi key={SECRET}"
    checklist_text = service.checklist_text_ru()

    assert SECRET not in service._safe_text(report_text)
    assert "Vertical integration checklist:" in checklist_text
    assert "no secrets" in checklist_text
    assert "no network" in checklist_text


def test_no_command_execution_except_metadata_only_report():
    report = VerticalIntegrationService().run_report()
    smoke = next(
        check for check in report.checks if check.check_id == "command_processor_smoke_safe"
    )

    assert report.command_execution_used is False
    assert smoke.passed is True
    assert "not used" in " ".join(smoke.details_ru)
