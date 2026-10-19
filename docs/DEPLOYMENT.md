# Deployment

## Local demo

Use Python 3.11+, create a virtual environment, install `.[ui,llm,dev]`, run tests/scenarios/evaluation, then start Streamlit. No API key is needed.

## Environment

Copy `.env.example` to `.env` without committing it. `SENDSMART_TOKEN_SECRET` must be changed outside a disposable demo. `SENDSMART_LIVE_FX=false` preserves offline reproducibility. `ANTHROPIC_API_KEY` is optional.

## Hosted demo considerations

- Run behind authentication and TLS.
- Store token secrets in a managed secret system.
- Replace in-memory replay/idempotency state with a transactional database.
- Persist audit events to append-only storage and externally anchor checkpoints.
- Disable filesystem uploads or scan them before parsing.
- Keep all execution adapters sandboxed; this repository contains no production payment connector.

## Health verification

Deployment is acceptable only when `pytest`, the 22 scenarios, and intent evaluation pass. Confirm the UI displays the sandbox banner and that Attack Lab remains blocked.

