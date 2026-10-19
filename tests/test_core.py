from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sendsmart.core.eta import estimated_arrival
from sendsmart.core.fx import load_fallback
from sendsmart.core.pricing import compute_route_cost
from sendsmart.core.ranking import rank_routes
from sendsmart.models import AmountMode, PaymentRequest, Preferences


def request(amount="1000", mode=AmountMode.SEND):
    return PaymentRequest(
        request_id="r1",
        user_id="aisha",
        amount=Decimal(amount),
        currency_from="MYR",
        currency_to="GBP",
        amount_mode=mode,
        beneficiary_id="northbridge_university",
        purpose="tuition",
        destination_country="GB",
        deadline=date(2026, 10, 30),
    )


def provider(fee="3.00", markup="0.20", days=1):
    return {
        "id": "p1",
        "name": "Mock P1",
        "fee_fixed": fee,
        "fee_percent": "0.35",
        "fx_markup_percent": markup,
        "eta_business_days": days,
        "reliability": "0.96",
    }


def test_pricing_is_nonnegative_and_monotonic():
    fx = load_fallback()
    low = compute_route_cost(provider(), request("1000"), fx)
    high = compute_route_cost(provider(), request("2000"), fx)
    assert low.total_cost >= 0
    assert high.recipient_amount > low.recipient_amount


def test_recipient_target_solver_reaches_target():
    quote = compute_route_cost(provider(), request("9000", AmountMode.RECIPIENT), load_fallback())
    assert quote.recipient_amount == Decimal("9000.00")
    assert quote.send_amount > 0


def test_eta_skips_weekend():
    friday_after_cutoff = datetime(2026, 10, 23, 16, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    assert estimated_arrival(1, now=friday_after_cutoff) == date(2026, 10, 27)


def test_ranking_respects_deadline_feasibility():
    fx = load_fallback()
    fast = compute_route_cost(provider(fee="10", days=1), request(), fx)
    slow = compute_route_cost({**provider(fee="0", days=4), "id": "p2", "name": "Mock P2"}, request(), fx)
    fast.deadline_ok = True
    slow.deadline_ok = False
    routes = rank_routes([slow, fast], Preferences(priority="cheapest"))
    assert [r.quote.provider_id for r in routes] == ["p1"]

