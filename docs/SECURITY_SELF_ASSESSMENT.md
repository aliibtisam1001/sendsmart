# Security Self-Assessment

## Threat model

Protected assets are authorization integrity, beneficiary integrity, amount correctness, user control, and audit evidence. Adversaries include malicious invoice content, a compromised language model, a user attempting to exceed limits, token forgery/replay, altered beneficiary details, stale prices, and local audit tampering.

## Permission tiers

| Tier | Deterministic condition | Enforcement |
|---|---|---|
| T1 | comparison only | planner omits token/executor steps |
| T2 | verified, ≤ USD 500, all caps pass | click confirmation required |
| T3 | verified, > USD 500 and ≤ USD 10,000, all caps pass | exact typed phrase required |
| BLOCKED | any hard rule fires | policy returns `allowed=false`; token path is unavailable |

## Controls mapped to code and tests

| Control | Implementation | Evidence/test |
|---|---|---|
| Decimal money math | `core/pricing.py` | `tests/test_core.py` |
| Beneficiary/fingerprint | `security/guardrails.py` | parametrized policy tests; scenarios 8–9 |
| Injection detection | `security/injection.py` | scenario 10 |
| Caps and sanctions | `security/policy.py` | scenarios 11–13 |
| Freshness | `core/fx.py`, policy | scenario 14 |
| Deadline feasibility | ETA + policy | scenarios 6–7 |
| Bound HMAC token | `security/tokens.py` | forged/replay test; scenario 15 |
| Tamper evidence | `security/audit.py` | audit mutation test; scenario 16 |
| Plan checkpoint | `agent/planner.py`, `control/user_control.py` | plan test; scenario 18 |
| Cancel window | `execution/sandbox.py` | scenario 19 |
| Kill switch | executor first check | unit test; scenario 20 |
| Limits cannot loosen | preference clamp + policy | unit test; scenario 21 |

## Prompt-injection defense

Documents are always data. The parser extracts a fixed schema while a separate scanner flags instruction-like phrases such as prior-instruction overrides, limit bypasses, account redirection, concealment, system-prompt mimicry, hidden-text markers, and urgency plus bypass language. Any flag blocks execution. The LLM never receives an execution capability.

## Token design

The SHA-256 request binding covers the normalized request, selected route/quote, and verified beneficiary fingerprint. A token contains a random ID, issue and expiry timestamps, binding, and HMAC-SHA256 signature. The sandbox independently verifies binding, signature and expiry, and records token IDs to reject replay.

## Audit design

Each JSONL event includes timestamp, event type, actor, request ID, summary, decision, previous hash, and SHA-256 hash. The first event points to a zero genesis hash. Editing, deleting, inserting, or reordering a line breaks verification. This is tamper-evident, not tamper-proof; production would anchor hashes externally.

## Known risk list

- **Mock data and simulated execution:** no evidence of production payment correctness. Mitigation: sandbox label and no live rail.
- **Regex injection detection is bypassable:** semantic attacks may evade it. Mitigation: keep documents non-authoritative, add classifiers and adversarial evaluation later.
- **HMAC secret in environment:** not hardware-backed or rotated. Mitigation: use a managed KMS/HSM in production.
- **No real KYC/AML/sanctions:** fictional controls only. Mitigation: integrate regulated providers and case management.
- **Single-user in-memory executor:** no concurrency or durable replay store. Mitigation: transactional database with unique constraints.
- **LLM extraction errors:** optional future LLM output may be wrong. Mitigation: strict schema, fallback, clarification, and policy independence.
- **FX trend hint is not a forecast:** historical mock data has no predictive validity. Mitigation: label it and avoid recommendations based on it.
- **Time saved is an estimate:** manual baseline is not experimentally measured. Mitigation: disclose formula and run user studies.
- **Hash chain can be replaced wholesale:** local attacker can rewrite all lines. Mitigation: remote append-only storage and signed checkpoints.

