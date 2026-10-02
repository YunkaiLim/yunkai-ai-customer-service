import hashlib
import hmac
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.chatwoot import parse_incoming_message, verify_chatwoot_signature
from app.config import Settings
from app.knowledge import KnowledgeBase
from app.main import app
from app.policy import explicit_handoff_reason
from app.storage import Storage


def test_kb_search_chinese():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "faq.md").write_text(
            "人工客服时间是周一到周五。客服不会索取验证码。",
            encoding="utf-8",
        )
        kb = KnowledgeBase(root)
        hits = kb.search("人工客服什么时候上班")
        assert hits
        assert hits[0].score > 0


def test_policy_handoff():
    assert explicit_handoff_reason("我要真人客服")
    assert explicit_handoff_reason("I need a refund")
    assert explicit_handoff_reason("我的 OTP 是什么")
    assert explicit_handoff_reason("hello") is None


def test_chatwoot_parser():
    payload = {
        "event": "message_created",
        "message_type": "incoming",
        "id": 99,
        "content": "hello",
        "conversation": {"id": 12},
    }
    assert parse_incoming_message(payload) == ("99", "12", "hello")
    payload["message_type"] = "outgoing"
    assert parse_incoming_message(payload) is None


def test_dedupe():
    with TemporaryDirectory() as directory:
        storage = Storage(Path(directory) / "db.sqlite")
        assert storage.claim_event("x") is True
        assert storage.claim_event("x") is False
        storage.release_event("x")
        assert storage.claim_event("x") is True


def test_chatwoot_signature_and_replay_window():
    body = b'{"event":"message_created"}'
    timestamp = "1000"
    secret = "test-secret"
    digest = hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("utf-8") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    signature = "sha256=" + digest

    assert verify_chatwoot_signature(body, timestamp, signature, secret, now=1200)
    assert not verify_chatwoot_signature(body, timestamp, signature, secret, now=1401)
    assert not verify_chatwoot_signature(body + b"x", timestamp, signature, secret, now=1200)


def test_bind_is_loopback_only():
    assert Settings(service_host="127.0.0.1").service_host == "127.0.0.1"
    assert Settings(service_host="::1").service_host == "::1"
    with pytest.raises(ValidationError):
        Settings(service_host="0.0.0.0")


def test_manifest_denies_sensitive_authority():
    client = TestClient(app)
    response = client.get("/yunkai/manifest")
    assert response.status_code == 200
    authority = response.json()["authority"]
    assert authority["read_personal_memory"] is False
    assert authority["device_actions"] is False
    assert authority["payments"] is False
    assert authority["refund_execution"] is False
    assert authority["account_changes"] is False


def test_admin_reindex_disabled_without_token():
    client = TestClient(app)
    response = client.post("/admin/reindex")
    assert response.status_code == 503


def test_chatwoot_webhook_disabled_without_secret():
    client = TestClient(app)
    response = client.post(
        "/webhooks/chatwoot",
        content=b'{"event":"message_created"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 503
