from datetime import datetime
from decimal import Decimal

import pytest

from sendsmart.agent.intent import clarification_question, classify_rule_based
from sendsmart.agent.planner import build_plan, validate_plan
from sendsmart.control.user_control import apply_preferences, approve, expected_approval_phrase
from sendsmart.models import IntentType, PaymentRequest, Plan, PolicyDecision, Preferences, Tier


def test_intent_and_relative_date():
    intent = classify_rule_based(
        "Pay GBP 9,000 tuition to Northbridge University from MYR in 5 days",
        now=datetime(2026, 10, 20),
    )
    assert intent.type == IntentType.PAY_TUITION
    assert intent.slots["amount"] == Decimal("9000")
    assert str(intent.slots["deadline"]) == "2026-10-25"
    assert not intent.missing_slots


def test_missing_amount_gets_one_question():
    intent = classify_rule_based("send some money to my landlord", defaults={"currency_from": "MYR", "currency_to": "GBP"})
    assert intent.missing_slots == ["amount"]
    assert clarification_question(intent) == "How much should be sent or received, and in which currency?"


def test_compare_plan_stops_before_execution():
    intent = classify_rule_based("Compare GBP 500 options from MYR to GBP for my landlord")
    plan = build_plan(intent, "r1")
    assert plan.intent_type == IntentType.COMPARE_ONLY
    assert "execute_sandbox" not in [s.tool for s in plan.steps]


def test_planner_guardrails_cannot_be_removed():
    intent = classify_rule_based(
        "Pay GBP 9000 tuition to Northbridge University from MYR by 27 October 2026"
    )
    plan = build_plan(intent, "r1")
    plan.steps = [step for step in plan.steps if step.tool != "check_policy"]
    with pytest.raises(ValueError, match="guardrail"):
        validate_plan(plan)


def test_preferences_cannot_loosen_limits():
    prefs = Preferences(personal_limit_usd=Decimal("2000"))
    changed = apply_preferences(prefs, {"personal_limit_usd": "50000", "priority": "fastest"})
    assert changed.personal_limit_usd == Decimal("2000")
    assert changed.priority == "fastest"


def test_t3_requires_exact_phrase():
    intent = classify_rule_based("Pay GBP 9000 tuition to Northbridge University from MYR by 27 October 2026")
    plan = build_plan(intent, "r1")
    request = PaymentRequest(
        request_id="r1", user_id="aisha", amount=Decimal("9000"), currency_from="MYR", currency_to="GBP",
        amount_mode="RECIPIENT", beneficiary_id="northbridge_university", purpose="tuition",
        destination_country="GB", deadline="2026-10-27",
    )
    decision = PolicyDecision(tier=Tier.T3_APPROVE, allowed=True, required_user_action="typed")
    phrase = expected_approval_phrase(request, "Northbridge University")
    assert approve(plan, decision, phrase, request, "Northbridge University").approved

