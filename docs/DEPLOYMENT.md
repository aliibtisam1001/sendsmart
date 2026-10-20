# Streamlit Deployment

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open [share.streamlit.io](https://share.streamlit.io/) and create an app.
3. Select the repository and branch.
4. Set **Main file path** to `app.py`.
5. Under **Advanced settings**, use Python 3.11 and add a random secret:

```toml
SENDSMART_TOKEN_SECRET = "replace-with-a-long-random-value"
```

Generate one locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

No external API key is required. The deterministic agent and bundled public-data fallbacks remain usable if an external quote endpoint is unavailable. Do not commit `.streamlit/secrets.toml`.

## Local demo

Use Python 3.11+, create a virtual environment, install `requirements-dev.txt`, run tests/scenarios/evaluation, then start the same root entry point used in deployment:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python scenarios/run_scenarios.py
python evaluation/eval_intent.py
python -m streamlit run app.py
```

## Environment

Copy `.env.example` to `.env` without committing it. `SENDSMART_TOKEN_SECRET` should be set for stable deployments; otherwise the app generates an ephemeral cryptographic secret at startup. `SENDSMART_LIVE_FX=false` preserves offline reproducibility. `ANTHROPIC_API_KEY` is optional.

## Hosted demo considerations

- Streamlit Community Cloud supplies TLS. Add access control if the deployment should not be public.
- Store token secrets in a managed secret system.
- Replace in-memory replay/idempotency state with a transactional database.
- Persist audit events to append-only storage and externally anchor checkpoints.
- Disable filesystem uploads or scan them before parsing.
- Keep all execution adapters sandboxed; this repository contains no production payment connector.
- Audit logs are isolated per browser session and stored in ephemeral deployment storage. Do not treat them as durable production records.

## Health verification

Deployment is acceptable only when `pytest`, the 22 scenarios, and intent evaluation pass. Confirm the root `app.py` loads, the UI displays the sandbox boundary, and Attack Lab remains blocked.

