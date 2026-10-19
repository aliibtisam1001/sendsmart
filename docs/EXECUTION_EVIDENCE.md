# Execution Evidence

## Files

- `scenario_results.json` — inputs, intent, plan, quotes, recommendation, policy, user actions, outcome, expected/actual result, and value report where applicable.
- `audit_log.jsonl` — hash-chained plan, policy, approval, execution, cancellation and kill-switch events.
- `metrics.json` — aggregate scenario and mock value metrics.
- `intent_eval.json` — per-utterance results plus intent accuracy, slot F1, and clarification correctness.
- `summary.md` — human-readable 22-scenario table.

## Regeneration

```bash
python scenarios/run_scenarios.py
python evaluation/eval_intent.py
python -m pytest
```

Each runner returns exit status 1 when its acceptance target fails. Scenario generation recreates the main audit log to keep evidence reproducible.

## Audit verification

```python
from sendsmart.security.audit import AuditLog
assert AuditLog("evidence/audit_log.jsonl").verify_chain()
```

Scenario 16 creates a separate tamper probe, edits a logged event, and confirms verification fails.

