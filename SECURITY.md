# Security

## Scope

This repository is a local-first customer-support reference service. It is not designed to grant an LLM independent business authority.

## Security boundaries

- The HTTP server accepts only loopback bind addresses.
- Runtime credentials belong in environment variables or an external secret store.
- `.env` files and SQLite runtime databases are ignored by Git.
- Customer text and retrieved knowledge are untrusted model context, not authorization.
- Refunds, payments, fraud, account security, legal disputes, and irreversible actions are escalated for human review.
- Chatwoot webhooks require HMAC-SHA256 verification and a bounded timestamp window.
- Replayed webhook delivery IDs are rejected by the local event store.
- The service exposes no device-control, arbitrary shell, payment, refund, or account-mutation capability.

## Reporting

Please open a GitHub issue for non-sensitive bugs. For a vulnerability, avoid posting secrets, credentials, customer data, or a working exploit against a real system in a public issue.
