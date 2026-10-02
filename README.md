# Yunkai AI Customer Service

A local-first AI customer-service reference service built around **source-grounded answers, explicit human handoff, bounded authority, and verifiable webhook handling**.

This is a sanitized public export of a larger private Yunkai service. The public version focuses only on customer support and intentionally excludes private companion memory, device-control authority, personal messaging, local credentials, and runtime databases.

## Highlights

- FastAPI service with a small local web demo
- OpenAI-compatible model adapter for Ollama, LM Studio, DeepSeek, or another compatible endpoint
- Markdown knowledge base with deterministic lightweight retrieval
- conversation history stored in local SQLite
- explicit human handoff for refunds, payments, fraud, account security, legal disputes, and customer-requested escalation
- Chatwoot `message_created` webhook support
- HMAC-SHA256 webhook verification with a five-minute replay window
- idempotent webhook event claims
- loopback-only bind policy
- no device-control, payment, refund-execution, or account-change authority

## Architecture

```text
Browser / Chatwoot
       |
       v
    FastAPI
       |
       +--> deterministic policy gate ------> human handoff
       |
       +--> Markdown knowledge retrieval
       |
       +--> OpenAI-compatible LLM
       |
       +--> local SQLite conversation state
```

The model is not an authority boundary. Customer text and retrieved knowledge are treated as untrusted data. Sensitive or irreversible requests are escalated instead of being executed.

## Quick start

Requirements: Python 3.10+.

```powershell
git clone https://github.com/YunkaiLim/yunkai-ai-customer-service.git
cd yunkai-ai-customer-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000.

The default configuration targets an OpenAI-compatible local endpoint on `127.0.0.1:11434/v1`. Change `LLM_BASE_URL`, `LLM_MODEL`, and optionally `LLM_API_KEY` through environment variables.

## Tests

```powershell
python -m pytest -q
```

GitHub Actions runs the public test suite on pushes and pull requests.

## Chatwoot

Configure these environment variables only on the machine running the service:

- `CHATWOOT_BASE_URL`
- `CHATWOOT_ACCOUNT_ID`
- `CHATWOOT_API_TOKEN`
- `CHATWOOT_WEBHOOK_SECRET`

The webhook rejects missing/invalid signatures and timestamps outside the allowed replay window.

## Security boundary

The public service deliberately does **not**:

- read Yunkai personal memory
- operate phones or desktops
- perform refunds, payments, account changes, or irreversible actions
- accept credentials in query strings
- bind to public network interfaces
- commit runtime databases or `.env` files

See [SECURITY.md](SECURITY.md).

## Why this exists

The project demonstrates a small but practical customer-operations pattern: combine AI assistance with deterministic policy, source grounding, local-first storage, explicit escalation, and observable boundaries instead of giving the model unrestricted business authority.

## License

MIT. See [LICENSE](LICENSE).
