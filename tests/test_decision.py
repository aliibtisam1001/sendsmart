from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from sendsmart.core.advisory import build_corridor_plan
from sendsmart.core.decision import assess_quote, build_decision_report, decision_status, reference_amounts
from sendsmart.core.destinations import find_destination
from sendsmart.core.fx import load_public_cache
from sendsmart.integrations.wise import WiseQuote
from sendsmart.models import AmountMode


def quote(delivery_day: int = 22) -> WiseQuote:
    return WiseQuote(
        source_amount=Decimal("1000"),
        target_amount=Decimal("110"),
        source_currency="CNY",
        target_currency="GBP",
        fee=Decimal("10"),
        rate=Decimal("0.112"),
        pay_in="BANK_TRANSFER",
        pay_out="BANK_TRANSFER",
        estimated_delivery=datetime(2026, 10, delivery_day, 12, tzinfo=timezone.utc),
        estimated_delivery_text="in two days",
        rate_timestamp=datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
        expires_at=None,
    )


def test_quote_assessment_uses_reference_rate_and_deadline():
    result = assess_quote(quote(), Decimal("0.115"), date(2026, 10, 23))
    assert result.fee_percent == Decimal("1.00")
    assert result.rate_difference_percent < 0
    assert result.effective_cost_percent > 4
    assert result.deadline_ok is True


def test_quote_assessment_rejects_invalid_reference():
    with pytest.raises(ValueError, match="positive"):
        assess_quote(quote(), Decimal("0"), None)


def test_decision_status_is_fail_closed():
    assessment = assess_quote(quote(24), Decimal("0.115"), date(2026, 10, 23))
    assert decision_status(quote(), "Example University", [object()], assessment)[0].startswith("STOP")
    assert decision_status(quote(), "", [], assessment)[0] == "INCOMPLETE"
    assert decision_status(None, "Example University", [], None)[0] == "REFERENCE ESTIMATE"
    assert decision_status(quote(24), "Example University", [], assessment)[0] == "DEADLINE RISK"


def test_decision_report_is_explicitly_non_executable():
    fx = load_public_cache()
    plan = build_corridor_plan(
        find_destination("CHN"), find_destination("GBR"), Decimal("1000"),
        AmountMode.SEND, "balanced", "tuition", date(2026, 10, 23), fx,
    )
    assessment = assess_quote(quote(), plan.reference_rate, plan.request.deadline)
    report = build_decision_report(plan, quote(), assessment, None, "Example University", [])
    assert report["execution_enabled"] is False
    assert report["status"] == "READY FOR USER REVIEW"
    assert report["provider_preview"]["provider"] == "Wise"


def test_reference_amounts_are_available_without_provider_quote():
    plan = build_corridor_plan(
        find_destination("CHN"), find_destination("GBR"), Decimal("25000"),
        AmountMode.SEND, "balanced", "tuition", None, load_public_cache(),
    )
    source, target = reference_amounts(plan)
    assert source == Decimal("25000.00")
    assert target > Decimal("0")

    recipient_plan = build_corridor_plan(
        find_destination("CHN"), find_destination("GBR"), Decimal("1000"),
        AmountMode.RECIPIENT, "balanced", "tuition", None, load_public_cache(),
    )
    needed, recipient = reference_amounts(recipient_plan)
    assert needed > Decimal("0")
    assert recipient == Decimal("1000.00")
