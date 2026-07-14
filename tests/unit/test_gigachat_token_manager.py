import json
import time
import urllib.error
import uuid

from ai import GigaChatTokenManager


class FakeOAuthClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post_form(self, url, headers, body, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def token_response(token="fake-access-token", seconds=1800):
    return json.dumps(
        {"access_token": token, "expires_at": int(time.time()) + seconds}
    )


def test_missing_auth_key_no_network():
    client = FakeOAuthClient(response=token_response())
    manager = GigaChatTokenManager(environ={}, http_client=client)

    result = manager.get_access_token()

    assert result.ok is False
    assert result.error_message == "GIGACHAT_AUTH_KEY is missing."
    assert client.calls == []


def test_auth_key_present_status_safe_without_value():
    secret = "fake-gigachat-auth-key"
    manager = GigaChatTokenManager(environ={"GIGACHAT_AUTH_KEY": secret})

    text = manager.status_text_ru()

    assert "PRESENT" in text
    assert secret not in text


def test_scope_default_invalid_and_valid_override():
    assert GigaChatTokenManager(environ={}).scope() == "GIGACHAT_API_PERS"
    assert (
        GigaChatTokenManager(environ={"GIGACHAT_SCOPE": "GIGACHAT_API_B2B"}).scope()
        == "GIGACHAT_API_B2B"
    )
    client = FakeOAuthClient(response=token_response())
    result = GigaChatTokenManager(
        environ={"GIGACHAT_AUTH_KEY": "fake-key", "GIGACHAT_SCOPE": "BAD_SCOPE"},
        http_client=client,
    ).get_access_token()

    assert result.ok is False
    assert "scope" in result.error_message
    assert client.calls == []


def test_token_request_shape_and_response_parsed():
    client = FakeOAuthClient(response=token_response("token-value"))
    manager = GigaChatTokenManager(
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
        http_client=client,
    )

    result = manager.get_access_token()

    assert result.ok is True
    assert result.access_token == "token-value"
    call = client.calls[0]
    assert call["url"] == "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    assert call["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert call["headers"]["Accept"] == "application/json"
    uuid.UUID(call["headers"]["RqUID"])
    assert call["headers"]["Authorization"] == "Basic fake-key"
    assert call["body"] == b"scope=GIGACHAT_API_PERS"


def test_token_cached_in_memory_only_and_expired_refreshed():
    client = FakeOAuthClient(response=token_response("token-1"))
    manager = GigaChatTokenManager(
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
        http_client=client,
    )

    assert manager.get_access_token().access_token == "token-1"
    assert manager.get_access_token().access_token == "token-1"
    assert len(client.calls) == 1

    manager._expires_at = int(time.time()) + 30
    client.response = token_response("token-2")
    assert manager.get_access_token().access_token == "token-2"
    assert len(client.calls) == 2


def test_token_status_never_prints_key_or_token():
    secret = "fake-gigachat-auth-key"
    token = "fake-access-token-that-must-not-leak"
    manager = GigaChatTokenManager(
        environ={"GIGACHAT_AUTH_KEY": secret},
        http_client=FakeOAuthClient(response=token_response(token)),
    )
    manager.get_access_token()

    text = manager.status_text_ru()

    assert "token cached in memory: yes" in text
    assert secret not in text
    assert token not in text


def test_http_and_malformed_errors_safe():
    for status in (401, 403):
        error = urllib.error.HTTPError(
            url="https://ngw.devices.sberbank.ru",
            code=status,
            msg="fake-key",
            hdrs=None,
            fp=None,
        )
        result = GigaChatTokenManager(
            environ={"GIGACHAT_AUTH_KEY": "fake-key"},
            http_client=FakeOAuthClient(error=error),
        ).get_access_token()
        assert result.ok is False
        assert str(status) in result.error_message
        assert "fake-key" not in result.error_message

    for response in ("{bad", "{}", json.dumps({"access_token": "x"})):
        result = GigaChatTokenManager(
            environ={"GIGACHAT_AUTH_KEY": "fake-key"},
            http_client=FakeOAuthClient(response=response),
        ).get_access_token()
        assert result.ok is False
        assert "fake-key" not in result.error_message


def test_network_exception_safe_error_no_secret():
    result = GigaChatTokenManager(
        environ={"GIGACHAT_AUTH_KEY": "fake-key"},
        http_client=FakeOAuthClient(error=OSError("boom fake-key")),
    ).get_access_token()

    assert result.ok is False
    assert "network error" in result.error_message
    assert "fake-key" not in result.error_message
