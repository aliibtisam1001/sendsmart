from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sendsmart.core.advisory import CorridorPlan
from sendsmart.integrations.wise import WiseQuote
from sendsmart.models import AmountMode


HUNDRED = Decimal("100")
MONEY = Decimal("0.01")


@dataclass(frozen=True)
class QuoteAssessment:
    fee_percent: Decimal
    rate_difference_percent: Decimal
    effective_cost_percent: Decimal
    deadline_ok: bool | None


def reference_amounts(plan: CorridorPlan) -> tuple[Decimal, Decimal]:
    """Return source and target amounts at the independent rate, before fees."""

    if plan.request.amount_mode == AmountMode.SEND:
        source = plan.request.amount
        target = source * plan.reference_rate
    else:
        target = plan.request.amount
        source = target / plan.reference_rate
    return source.quantize(MONEY, rounding=ROUND_HALF_UP), target.quantize(MONEY, rounding=ROUND_HALF_UP)


def assess_quote(quote: WiseQuote, reference_rate: Decimal, deadline: date | None) -> QuoteAssessment:
    """Compare a live preview with independent reference data.

    ``effective_cost_percent`` compares the quoted recipient amount with the
    amount produced by converting the full source amount at the independent
    reference rate. It is explanatory, not a provider accounting definition.
    """

    if quote.source_amount <= 0 or reference_rate <= 0:
        raise ValueError("Source amount and reference rate must be positive.")
    ideal_target = quote.source_amount * reference_rate
    deadline_ok = None
    if deadline and quote.estimated_delivery:
        deadline_ok = quote.estimated_delivery.date() <= deadline
    return QuoteAssessment(
        fee_percent=quote.fee / quote.source_amount * HUNDRED,
        rate_difference_percent=(quote.rate / reference_rate - Decimal("1")) * HUNDRED,
        effective_cost_percent=(Decimal("1") - quote.target_amount / ideal_target) * HUNDRED,
        deadline_ok=deadline_ok,
    )


def decision_status(
    quote: WiseQuote | None,
    screened_name: str,
    sanctions_matches: list[Any],
    assessment: QuoteAssessment | None,
) -> tuple[str, str]:
    if sanctions_matches:
        return "STOP — HUMAN REVIEW", "A possible public-list name match requires trained compliance review."
    if not screened_name:
        return "INCOMPLETE", "Add the recipient or institution name before provider handoff."
    if quote is None:
        return "REFERENCE ESTIMATE", "A live provider preview is unavailable. Amounts use the independent rate before fees."
    if assessment and assessment.deadline_ok is False:
        return "DEADLINE RISK", "The provider ETA is later than the requested date."
    return "READY FOR USER REVIEW", "Evidence checks passed, but the preview is not locked or executable."


def build_decision_report(
    plan: CorridorPlan,
    quote: WiseQuote | None,
    assessment: QuoteAssessment | None,
    benchmark: dict[str, Any] | None,
    screened_name: str,
    sanctions_matches: list[Any],
) -> dict[str, Any]:
    status, rationale = decision_status(quote, screened_name, sanctions_matches, assessment)
    reference_source, reference_target = reference_amounts(plan)
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "status_rationale": rationale,
        "execution_enabled": False,
        "corridor": {
            "origin": plan.origin.country,
            "origin_iso3": plan.origin.iso3,
            "source_currency": plan.origin.currency,
            "destination": plan.destination.country,
            "destination_iso3": plan.destination.iso3,
            "target_currency": plan.destination.currency,
        },
        "request": {
            "amount": str(plan.request.amount),
            "amount_mode": plan.request.amount_mode.value,
            "purpose": plan.purpose,
            "deadline": plan.request.deadline.isoformat() if plan.request.deadline else None,
            "priority": plan.priority,
        },
        "reference_fx": {
            "rate": str(plan.reference_rate),
            "source": plan.fx.source,
            "date": plan.fx.rate_date(plan.origin.currency, plan.destination.currency).isoformat(),
        },
        "reference_conversion_before_fees": {
            "source_amount": str(reference_source),
            "source_currency": plan.origin.currency,
            "target_amount": str(reference_target),
            "target_currency": plan.destination.currency,
            "provider_fee": None,
            "provider_eta": None,
        },
        "provider_preview": None,
        "assessment": None,
        "world_bank_benchmark": benchmark,
        "preliminary_un_name_screen": {
            "name": screened_name or None,
            "possible_match_count": len(sanctions_matches),
            "requires_human_review": bool(sanctions_matches),
        },
        "restrictions": [
            "This report cannot execute or fund a transfer.",
            "The provider preview is unauthenticated and not rate-locked.",
            "The name screen is not KYC, AML clearance, or legal advice.",
        ],
    }
    if quote:
        report["provider_preview"] = {
            "provider": "Wise",
            "source_amount": str(quote.source_amount),
            "target_amount": str(quote.target_amount),
            "fee": str(quote.fee),
            "rate": str(quote.rate),
            "pay_in": quote.pay_in,
            "pay_out": quote.pay_out,
            "estimated_delivery": quote.estimated_delivery.isoformat() if quote.estimated_delivery else None,
            "estimated_delivery_text": quote.estimated_delivery_text,
            "rate_timestamp": quote.rate_timestamp.isoformat(),
            "expires_at": quote.expires_at.isoformat() if quote.expires_at else None,
        }
    if assessment:
        report["assessment"] = {
            **{key: str(value) for key, value in asdict(assessment).items() if key != "deadline_ok"},
            "deadline_ok": assessment.deadline_ok,
        }
    return report
