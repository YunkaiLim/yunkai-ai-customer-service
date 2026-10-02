import json
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .chatwoot import ChatwootClient, parse_incoming_message, verify_chatwoot_signature
from .config import settings
from .models import ChatRequest, ChatResponse
from .service import SupportService

ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title=settings.service_name, version="1.0.0")
service = SupportService(settings)
chatwoot = ChatwootClient(settings)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.get("/")
def root():
    return FileResponse(str(ROOT / "static" / "index.html"))


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": settings.service_name,
        "version": "1.0.0",
        "bind_policy": "loopback_only",
        "knowledge_chunks": len(service.kb.chunks),
        "chatwoot_ready": chatwoot.ready,
        "llm_endpoint_configured": bool(settings.llm_base_url),
        "llm_key_present": bool(settings.llm_api_key),
    }


@app.get("/yunkai/manifest")
def yunkai_manifest():
    return {
        "id": "customer-service",
        "name": settings.service_name,
        "version": "1.0.0",
        "local_first": True,
        "bind": f"{settings.service_host}:{settings.service_port}",
        "capabilities": [
            "support_chat",
            "local_markdown_knowledge",
            "conversation_history",
            "chatwoot_webhook",
            "human_handoff",
        ],
        "authority": {
            "read_personal_memory": False,
            "device_actions": False,
            "payments": False,
            "refund_execution": False,
            "account_changes": False,
        },
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "chatwoot": "/webhooks/chatwoot",
            "manifest": "/yunkai/manifest",
        },
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return await service.answer(req.message, req.conversation_id)


@app.post("/admin/reindex")
def reindex(x_admin_token: str | None = Header(default=None)):
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="Admin endpoint disabled")
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return {"knowledge_chunks": service.kb.reload()}


@app.post("/webhooks/chatwoot")
async def chatwoot_webhook(
    request: Request,
    x_chatwoot_signature: str | None = Header(default=None),
    x_chatwoot_timestamp: str | None = Header(default=None),
    x_chatwoot_delivery: str | None = Header(default=None),
):
    secret = settings.chatwoot_webhook_secret
    if not secret:
        raise HTTPException(status_code=503, detail="Chatwoot webhook disabled")

    raw_body = await request.body()
    if not verify_chatwoot_signature(
        raw_body,
        x_chatwoot_timestamp,
        x_chatwoot_signature,
        secret,
    ):
        raise HTTPException(status_code=401, detail="Invalid Chatwoot webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    parsed = parse_incoming_message(payload)
    if not parsed:
        return {"ignored": True}

    message_id, conversation_id, content = parsed
    event_id = x_chatwoot_delivery or message_id
    if not service.storage.claim_event(event_id):
        return {"duplicate": True}

    try:
        result = await service.answer(content, f"chatwoot:{conversation_id}")
        if not chatwoot.ready:
            service.storage.complete_event(event_id)
            return {
                "processed": True,
                "chatwoot_ready": False,
                "result": result.model_dump(),
            }

        if result.handoff:
            await chatwoot.handoff(conversation_id)
        await chatwoot.send_message(conversation_id, result.reply)
        service.storage.complete_event(event_id)
        return {"processed": True, "handoff": result.handoff}
    except Exception:
        service.storage.release_event(event_id)
        raise
