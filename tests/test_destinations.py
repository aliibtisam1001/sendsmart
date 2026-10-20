from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from sendsmart.core.advisory import build_corridor_plan
from sendsmart.core.destinations import find_destination, load_destinations
from sendsmart.core.fx import load_public_cache
from sendsmart.models import AmountMode


def test_top_fifty_catalog_and_currency_coverage():
    destinations = load_destinations()
    fx = load_public_cache()
    assert len(destinations) == 50
    assert [item.rank for item in destinations] == list(range(1, 51))
    assert all(item.currency in fx.rates for item in destinations)
    assert not fx.is_mock


def test_build_public_fx_advisory_plan():
    destinations = load_destinations()
    plan = build_corridor_plan(
        find_destination("CHN", destinations),
        find_destination("GBR", destinations),
        Decimal("25000"),
        AmountMode.SEND,
        "balanced",
        "tuition",
        date(2026, 10, 30),
        load_public_cache(),
        now=datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
    )
    assert plan.reference_rate > 0
    assert plan.request.currency_from == "CNY"
    assert plan.request.currency_to == "GBP"
    assert plan.priority == "balanced"
    assert "Wise" in " ".join(plan.steps)


def test_same_country_is_not_cross_border():
    china = find_destination("CHN")
    with pytest.raises(ValueError, match="different"):
        build_corridor_plan(
            china, china, Decimal("100"), AmountMode.SEND, "balanced", "tuition",
            None, load_public_cache(),
        )
