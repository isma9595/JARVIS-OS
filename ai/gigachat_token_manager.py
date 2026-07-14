"""In-memory OAuth token manager for explicit GigaChat one-shot requests."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


@dataclass(frozen=True)
class GigaChatTokenResult:
    ok: bool
    access_token: str | None = None
    expires_at: int | None = None
    error_message: str | None = None


class UrllibGigaChatOAuthClient:
    def post_form(self, url: str, headers: dict[str, str], body: bytes, timeout: int):
        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")


class GigaChatTokenManager:
    DEFAULT_AUTH_ENV_VAR = "GIGACHAT_AUTH_KEY"
    DEFAULT_SCOPE = "GIGACHAT_API_PERS"
    ALLOWED_SCOPES = {
        "GIGACHAT_API_PERS",
        "GIGACHAT_API_B2B",
        "GIGACHAT_API_CORP",
    }
    OAUTH_ENDPOINT = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    def __init__(
        self,
        environ=None,
        http_client=None,
        oauth_endpoint: str | None = None,
        timeout_seconds: int = 30,
    ):
        self.environ = os.environ if environ is None else environ
        self.http_client = http_client or UrllibGigaChatOAuthClient()
        self.oauth_endpoint = oauth_endpoint or self.OAUTH_ENDPOINT
        self.timeout_seconds = timeout_seconds
        self._access_token: str | None = None
        self._expires_at: int | None = None

    def get_access_token(self) -> GigaChatTokenResult:
        if self._cached_token_valid():
            return GigaChatTokenResult(
                ok=True,
                access_token=self._access_token,
                expires_at=self._expires_at,
            )

        auth_key = self._auth_key()
        if auth_key is None:
            return GigaChatTokenResult(
                ok=False,
                error_message="GIGACHAT_AUTH_KEY is missing.",
            )

        scope = self.scope()
        if scope not in self.ALLOWED_SCOPES:
            return GigaChatTokenResult(
                ok=False,
                error_message="GigaChat scope is invalid or unsupported.",
            )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {auth_key}",
        }
        body = urllib.parse.urlencode({"scope": scope}).encode("utf-8")

        try:
            raw_response = self.http_client.post_form(
                self.oauth_endpoint,
                headers=headers,
                body=body,
                timeout=self.timeout_seconds,
            )
        except urllib.error.HTTPError as error:
            return self._http_error(error.code)
        except TimeoutError:
            return GigaChatTokenResult(ok=False, error_message="GigaChat OAuth timeout.")
        except (socket.timeout, urllib.error.URLError, OSError) as error:
            status = getattr(error, "status", None) or getattr(error, "code", None)
            if status is not None:
                return self._http_error(status)
            return GigaChatTokenResult(
                ok=False,
                error_message="GigaChat OAuth network error.",
            )

        try:
            data = json.loads(raw_response)
        except (TypeError, json.JSONDecodeError):
            return GigaChatTokenResult(
                ok=False,
                error_message="GigaChat OAuth response was not valid JSON.",
            )
        if not isinstance(data, dict):
            return GigaChatTokenResult(
                ok=False,
                error_message="GigaChat OAuth response was malformed.",
            )

        access_token = data.get("access_token")
        expires_at = self._parse_expires_at(data.get("expires_at"))
        if not isinstance(access_token, str) or not access_token.strip():
            return GigaChatTokenResult(
                ok=False,
                error_message="GigaChat OAuth response did not include access_token.",
            )
        if expires_at is None:
            return GigaChatTokenResult(
                ok=False,
                error_message="GigaChat OAuth response did not include valid expires_at.",
            )

        self._access_token = access_token.strip()
        self._expires_at = expires_at
        return GigaChatTokenResult(
            ok=True,
            access_token=self._access_token,
            expires_at=self._expires_at,
        )

    def safe_status(self) -> dict[str, str]:
        return {
            "auth_key_status": "PRESENT" if self._auth_key() else "MISSING",
            "token_cached": "yes" if bool(self._access_token) else "no",
            "expires_at_known": "yes" if self._expires_at is not None else "no",
            "scope": self.scope(),
        }

    def status_text_ru(self) -> str:
        status = self.safe_status()
        return "\n".join(
            [
                "GigaChat token status:",
                f"- auth key status: {status['auth_key_status']}",
                f"- token cached in memory: {status['token_cached']}",
                f"- expires_at known: {status['expires_at_known']}",
                f"- scope: {status['scope']}",
                "- token value is never printed",
                "- auth key value is never printed",
                "- network: not called",
            ]
        )

    def scope(self) -> str:
        value = self.environ.get("GIGACHAT_SCOPE")
        if value is None or not str(value).strip():
            return self.DEFAULT_SCOPE
        return str(value).strip()

    def _auth_key(self) -> str | None:
        value = self.environ.get(self.DEFAULT_AUTH_ENV_VAR)
        if value is None:
            return None
        stripped = str(value).strip()
        if not stripped:
            return None
        return stripped

    def _cached_token_valid(self) -> bool:
        if not self._access_token or self._expires_at is None:
            return False
        return (self._expires_at - int(time.time())) >= 60

    @classmethod
    def _parse_expires_at(cls, value) -> int | None:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return None
        if numeric > 10_000_000_000:
            numeric = numeric // 1000
        return numeric

    @staticmethod
    def _http_error(status) -> GigaChatTokenResult:
        try:
            status_int = int(status)
        except (TypeError, ValueError):
            status_int = 0
        if status_int in (401, 403):
            return GigaChatTokenResult(
                ok=False,
                error_message=(
                    f"GigaChat OAuth authentication/permission failed: status {status_int}."
                ),
            )
        return GigaChatTokenResult(
            ok=False,
            error_message=f"GigaChat OAuth HTTP error: status {status_int}.",
        )
