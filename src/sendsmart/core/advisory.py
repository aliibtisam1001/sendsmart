from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sendsmart.core.destinations import StudyDestination
from sendsmart.core.fx import FXSnapshot
from sendsmart.models import AmountMode, PaymentRequest


@dataclass(frozen=True)
class CorridorPlan:
    """Verified inputs for an advisory corridor plan.

    Provider quotes stay outside this model because live previews can fail or
    expire independently of the public reference-rate snapshot.
    """

    origin: StudyDestination
    destination: StudyDestination
    request: PaymentRequest
    fx: FXSnapshot
    purpose: str
    priority: str

    @property
    def reference_rate(self) -> Decimal:
        return self.fx.rate(self.origin.currency, self.destination.currency)

    @property
    def steps(self) -> list[str]:
        return [
            "Validate the selected countries, currencies, amount and purpose",
            "Verify the independent Frankfurter public reference rate",
            "Request real Wise fee, FX and delivery previews for this corridor",
            "Attach a World Bank remittance-cost benchmark when the corridor is covered",
            "Run optional preliminary recipient-name screening against the UN public list",
            "Explain the result and stop; this prototype cannot create or fund a transfer",
        ]


def build_corridor_plan(
    origin: StudyDestination,
    destination: StudyDestination,
    amount: Decimal,
    amount_mode: AmountMode,
    priority: str,
    purpose: str,
    deadline: date | None,
    fx: FXSnapshot,
    now: object | None = None,
) -> CorridorPlan:
    # Kept for compatibility with callers of the earlier simulated planner.
    # Provider timestamps now come from the provider response.
    del now
    if origin.iso3 == destination.iso3:
        raise ValueError("Choose two different countries.")
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    if priority not in {"balanced", "cheapest", "fastest"}:
        raise ValueError("Unknown optimisation preference.")
    request = PaymentRequest(
        request_id=str(uuid.uuid4()),
        user_id="corridor_explorer",
        amount=amount,
        currency_from=origin.currency,
        currency_to=destination.currency,
        amount_mode=amount_mode,
        beneficiary_id="unverified_education_beneficiary",
        purpose=purpose,
        destination_country=destination.iso3,
        deadline=deadline,
    )
    return CorridorPlan(origin, destination, request, fx, purpose, priority)
