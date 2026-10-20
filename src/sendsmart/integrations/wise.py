from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from sendsmart.models import AmountMode


WISE_QUOTES_URL = "https://api.wise.com/2026Q4/quotes"


@dataclass(frozen=True)
class WiseQuote:
    source_amount: Decimal
    target_amount: Decimal
    source_currency: str
    target_currency: str
    fee: Decimal
    rate: Decimal
    pay_in: str
    pay_out: str
    estimated_delivery: datetime | None
    estimated_delivery_text: str
    rate_timestamp: datetime
    expires_at: datetime | None
    is_executable: bool = False


def _timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def fetch_wise_quotes(
    source_currency: str,
    target_currency: str,
    amount: Decimal,
    amount_mode: AmountMode,
    timeout: float = 6.0,
    requester: Callable[..., object] | None = None,
) -> list[WiseQuote]:
    if requester is None:
        import requests

        requester = requests.post
    body: dict[str, str | float] = {
        "sourceCurrency": source_currency.upper(),
        "targetCurrency": target_currency.upper(),
    }
    key = "sourceAmount" if amount_mode == AmountMode.SEND else "targetAmount"
    body[key] = float(amount)
    response = requester(
        WISE_QUOTES_URL,
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-External-Correlation-Id": str(uuid.uuid4()),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    rate_timestamp = _timestamp(payload.get("rateTimestamp")) or datetime.now().astimezone()
    expires_at = _timestamp(payload.get("rateExpirationTime") or payload.get("expirationTime"))
    quotes = []
    for option in payload.get("paymentOptions", []):
        if option.get("disabled"):
            continue
        quotes.append(
            WiseQuote(
                source_amount=Decimal(str(option["sourceAmount"])),
                target_amount=Decimal(str(option["targetAmount"])),
                source_currency=option["sourceCurrency"],
                target_currency=option["targetCurrency"],
                fee=Decimal(str(option["fee"]["total"])),
                rate=Decimal(str(payload["rate"])),
                pay_in=option.get("payIn", "UNKNOWN"),
                pay_out=option.get("payOut", "UNKNOWN"),
                estimated_delivery=_timestamp(option.get("estimatedDelivery")),
                estimated_delivery_text=option.get("formattedEstimatedDelivery", "Unavailable"),
                rate_timestamp=rate_timestamp,
                expires_at=expires_at,
            )
        )
    return sorted(quotes, key=lambda quote: (-quote.target_amount, quote.fee, quote.pay_in))
