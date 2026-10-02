import hashlib
import hmac
import time

import httpx

from .config import Settings


class ChatwootClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def ready(self) -> bool:
        return bool(
            self.settings.chatwoot_base_url
            and self.settings.chatwoot_account_id
            and self.settings.chatwoot_api_token
            and self.settings.chatwoot_webhook_secret
        )

    def _url(self, path: str) -> str:
        return self.settings.chatwoot_base_url.rstrip("/") + path

    def _headers(self) -> dict[str, str]:
        return {
            "api_access_token": self.settings.chatwoot_api_token,
            "Content-Type": "application/json",
        }

    async def send_message(self, conversation_id: int | str, content: str):
        path = (
            f"/api/v1/accounts/{self.settings.chatwoot_account_id}"
            f"/conversations/{conversation_id}/messages"
        )
        payload = {"content": content, "message_type": "outgoing", "private": False}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                self._url(path), headers=self._headers(), json=payload
            )
            response.raise_for_status()
            return response.json()

    async def handoff(self, conversation_id: int | str):
        path = (
            f"/api/v1/accounts/{self.settings.chatwoot_account_id}"
            f"/conversations/{conversation_id}/toggle_status"
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                self._url(path),
                headers=self._headers(),
                json={"status": "open"},
            )
            response.raise_for_status()
            return response.json()


def verify_chatwoot_signature(
    raw_body: bytes,
    timestamp: str | None,
    signature: str | None,
    secret: str,
    *,
    max_age_seconds: int = 300,
    now: int | None = None,
) -> bool:
    if not secret or not timestamp or not signature:
        return False

    try:
        signed_at = int(timestamp)
    except ValueError:
        return False

    current = int(time.time()) if now is None else now
    if abs(current - signed_at) > max_age_seconds:
        return False

    message = timestamp.encode("utf-8") + b"." + raw_body
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    expected = "sha256=" + digest
    return hmac.compare_digest(expected, signature)


def parse_incoming_message(payload: dict) -> tuple[str, str, str] | None:
    if payload.get("event") != "message_created":
        return None
    if payload.get("message_type") not in {"incoming", 0}:
        return None

    content = (payload.get("content") or "").strip()
    if not content:
        return None

    conversation = payload.get("conversation") or {}
    conversation_id = conversation.get("id") or payload.get("conversation_id")
    message_id = payload.get("id") or payload.get("message", {}).get("id")
    if conversation_id is None or message_id is None:
        return None

    return str(message_id), str(conversation_id), content
