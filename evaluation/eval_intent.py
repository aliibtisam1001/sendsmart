from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sendsmart.agent.intent import classify_rule_based  # noqa: E402


def normalize(value):
    return str(value) if value is not None else None


def main() -> int:
    cases = yaml.safe_load((ROOT / "data" / "intent_eval_set.yaml").read_text(encoding="utf-8"))
    intent_hits = 0
    slot_tp = slot_fp = slot_fn = 0
    clarification_hits = 0
    rows = []
    for case in cases:
        result = classify_rule_based(case["text"], now=datetime(2026, 10, 20), defaults={})
        intent_ok = result.type.value == case["intent"]
        intent_hits += int(intent_ok)
        expected_slots = case.get("slots", {})
        actual_items = {key: normalize(result.slots.get(key)) for key in expected_slots}
        expected_items = {key: normalize(value) for key, value in expected_slots.items()}
        for key, expected in expected_items.items():
            actual = actual_items.get(key)
            if actual == expected:
                slot_tp += 1
            else:
                slot_fn += 1
                if actual is not None:
                    slot_fp += 1
        expected_clarification = bool(case.get("missing") or case.get("ambiguous"))
        actual_clarification = bool(result.missing_slots or result.ambiguities)
        clarification_ok = expected_clarification == actual_clarification
        clarification_hits += int(clarification_ok)
        rows.append({
            "text": case["text"], "expected_intent": case["intent"], "actual_intent": result.type.value,
            "intent_ok": intent_ok, "slot_expected": expected_items, "slot_actual": actual_items,
            "clarification_ok": clarification_ok,
        })
    precision = slot_tp / (slot_tp + slot_fp) if slot_tp + slot_fp else 1
    recall = slot_tp / (slot_tp + slot_fn) if slot_tp + slot_fn else 1
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    report = {
        "case_count": len(cases),
        "intent_accuracy": round(intent_hits / len(cases), 4),
        "slot_f1": round(f1, 4),
        "clarification_correctness": round(clarification_hits / len(cases), 4),
        "model": "rule-based fallback",
        "rows": rows,
    }
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "intent_eval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    return 0 if report["intent_accuracy"] >= 0.9 else 1


if __name__ == "__main__":
    raise SystemExit(main())

