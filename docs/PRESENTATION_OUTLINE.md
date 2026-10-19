# Presentation Outline — 10 Minutes

## Slide 1 — SendSmart (0:40)

Problem: cross-border student payments are opaque, deadline-sensitive, and high consequence. Promise: an agent that understands and plans while code retains authority.

## Slide 2 — User journey (0:55)

Clarify → compare → explain → approve → simulated receipt → cancel/audit. Use Aisha’s Malaysia-to-UK tuition story.

## Slide 3 — Task completion, 40% (1:15)

Show seven intents, slot filling, explicit plans, deadline-aware ranking, offline fallback, and 22 executable scenarios. Emphasize one-question clarification rather than guessing.

## Slide 4 — Architecture (1:10)

Show the three trust zones and narrow authorization boundary. Speaker note: the LLM is never a payment principal.

## Slide 5 — Security and compliance, 30% (1:30)

Explain tiers, fingerprints, caps, sanctions fixture, stale quote, injection blocking, HMAC token, replay protection, kill switch, and audit chain. Demo an injection block.

## Slide 6 — User control (1:00)

Plan visibility, confirm/typed approval, preference edit, rejection, cancellation, STOP AGENT, and downloadable audit entries.

## Slide 7 — Innovation and interaction, 30% (1:00)

Policy-minted execution capability, plan integrity validation, number post-check, Attack Lab, and resilient zero-key operation.

## Slide 8 — Measurable value (1:05)

Show two documented baselines, savings formula, deadline risk avoided, time estimate, intent metrics, block rate, and false-block rate. Label every number MOCK.

## Slide 9 — Evidence and engineering quality (0:50)

Tests, coverage, intent benchmark, scenario JSON, audit JSONL, reproducible commands, MIT license, third-party list.

## Slide 10 — Limitations and next steps (0:35)

No real rail/KYC/AML; regex injection defense and local audit are not production grade. Next: regulated provider adapters, durable authorization store, holiday calendars, external audit anchoring, and red-team evaluation.

