# Value Methodology

All values are computed on MOCK data and are demonstration metrics, not financial claims.

## Baselines

**Baseline A — traditional bank wire:** the `bankwire` record in `providers.json`, with its mock fixed fee, percentage fee, FX markup, and ETA.

**Baseline B — default choice:** `SwiftFox Student`, marked `default_choice=true`. This models the first plausible provider presented to the student; it is not a claim about consumer behavior.

## Per-transfer formulas

- `savings_send = baseline.total_cost − selected.total_cost`
- `savings_usd = savings_send × send_currency_to_usd_rate`
- `savings_percent = savings_send / baseline.total_cost × 100`
- `deadline_risk_avoided = count(route misses deadline)` when selected route meets it, else zero
- `estimated_manual_minutes = provider_count × 4 minutes`
- `comparison_seconds = measured deterministic comparison runtime`

Negative savings are preserved rather than clipped. Percent is zero when baseline cost is zero.

## Aggregate metrics

The scenario runner reports total/average savings against the bank baseline, task completion, attack block rate, false-block rate, and scenario pass count. The intent evaluator reports accuracy, slot F1, and clarification correctness.

## Limits

Prices, rates, routes and the four-minute manual estimate are synthetic. The scenario set is curated and small. Results do not establish production accuracy, fraud prevention, or user time savings.

