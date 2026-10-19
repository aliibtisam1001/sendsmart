from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sendsmart.core.fx import FXSnapshot
from sendsmart.models import AmountMode, PaymentRequest, Quote


CENT = Decimal("0.01")
RATE_PRECISION = Decimal("0.000001")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def compute_route_cost(
    provider: dict[str, Any],
    request: PaymentRequest,
    fx: FXSnapshot,
    quoted_at: datetime | None = None,
) -> Quote:
    mid_rate = fx.rate(request.currency_from, request.currency_to)
    markup = Decimal(provider["fx_markup_percent"]) / Decimal("100")
    effective_rate = mid_rate * (Decimal("1") - markup)
    if effective_rate <= 0:
        raise ValueError("Effective FX rate must be positive")

    if request.amount_mode == AmountMode.RECIPIENT:
        recipient_amount = money(request.amount)
        send_amount = money(recipient_amount / effective_rate)
    else:
        send_amount = money(request.amount)
        recipient_amount = money(send_amount * effective_rate)

    fee = money(
        Decimal(provider["fee_fixed"])
        + send_amount * Decimal(provider["fee_percent"]) / Decimal("100")
    )
    markup_cost = money(send_amount * markup)
    return Quote(
        provider_id=provider["id"],
        provider_name=provider["name"],
        send_amount=send_amount,
        send_currency=request.currency_from,
        recipient_amount=recipient_amount,
        receive_currency=request.currency_to,
        fee=fee,
        fx_markup_cost=markup_cost,
        total_cost=money(fee + markup_cost),
        rate=effective_rate.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP),
        eta_business_days=int(provider["eta_business_days"]),
        reliability=Decimal(provider["reliability"]),
        quoted_at=quoted_at or fx.timestamp,
    )

