# Technical Documentation

## System overview

SendSmart is a Python 3.11 application with a Streamlit interface, Pydantic v2 contracts, Decimal arithmetic, YAML scenario/evaluation data, and JSONL audit evidence. It runs without a network or LLM key.

The core path is: text → `Intent` → visible `Plan` → structured `PaymentRequest` → mock quotes → deadline-aware ranking → `PolicyDecision` → user checkpoint → `ExecutionToken` → sandbox receipt → `ValueReport`.

## Algorithms

### Intent and slot filling

The fallback classifier uses ordered rules for cancellation, status, preference, comparison, tuition, living-cost transfer, and out-of-scope requests. Currency and amount patterns support codes, common names, `£`, and `$`. Relative dates are resolved against an injectable clock. Tuition defaults to recipient-target mode because the institution typically must receive an exact amount. Missing required slots produce exactly one question.

The optional LLM boundary is isolated in `agent/llm.py`. Invalid or unavailable model output falls back to the deterministic classifier. Tool calls are capped conceptually at six; the current competition path needs none.

### Target-amount solving

For target amount `T`, mock mid-rate `r`, and markup fraction `m`:

`send_amount = round_money(T / (r × (1 − m)))`

Fees are `fixed_fee + send_amount × fee_percent`. FX markup cost is shown independently and total route cost is `fee + markup_cost`. All values are `Decimal`; no monetary float enters policy.

### ETA

ETA adds provider business days, skipping Saturday and Sunday. Requests after the 15:00 cutoff start on the next business day. Deadline feasibility is computed before ranking.

### Ranking

Routes that meet the deadline form the candidate set. If none meet it, all routes remain visible with warnings. Normalized cost, speed, and reliability scores are combined with `cheapest`, `fastest`, or `balanced` weights. Deterministic tie-breakers are cost and provider name.

### Planning

Plans are typed data shown before execution. Payment plans require validate → verify beneficiary → FX → compare → rank → explain → policy → checkpoint → token → sandbox → report. `validate_plan()` rejects deletion or unsafe reordering of mandatory steps.

### Security

The policy engine evaluates USD-equivalent amount, beneficiary status/fingerprint, daily and hard caps, fictional sanctions, injection flags, quote age, and personal limits. Only an allowed T2/T3 decision plus valid user action can reach token issuance. See `SECURITY_SELF_ASSESSMENT.md`.

## Data models

Pydantic models include `Intent`, `PaymentRequest`, `Plan`, `PlanStep`, `Quote`, `Route`, `PolicyDecision`, `ExecutionToken`, `AuditEvent`, `Preferences`, and `ValueReport`. Models reject unknown fields to keep boundaries explicit.

## Assumptions and trade-offs

- Provider pricing, FX and reliability are mock fixtures selected for demonstrability, not realism.
- The synthetic GBP fallback rate keeps the required GBP 9,000 scenario below the stated USD 10,000 cap. This resolves an internal scenario/cap conflict without weakening the cap.
- Weekends are modeled; public holidays and provider-specific calendars are not.
- Recipient fingerprints stand in for real account verification.
- The prototype favors transparent deterministic behavior over broad natural-language coverage.
- Execution state is in memory; evidence is durable JSONL.

