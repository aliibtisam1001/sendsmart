from __future__ import annotations

from decimal import Decimal
from typing import Any

from sendsmart.config import settings
from sendsmart.models import IntentType, PaymentRequest, PolicyDecision, Preferences, Quote, Tier
from sendsmart.security.guardrails import blocked_rules
from sendsmart.security.injection import InjectionFlag


def evaluate(
    request: PaymentRequest,
    quote: Quote,
    user: dict[str, Any],
    beneficiary: dict[str, Any],
    usd_equivalent: Decimal,
    *,
    intent_type: IntentType = IntentType.PAY_TUITION,
    injection_flags: list[InjectionFlag] | None = None,
    supplied_bank_fingerprint: str | None = None,
    sanctioned_countries: set[str] | None = None,
    quote_stale: bool = False,
    preferences: Preferences | None = None,
) -> PolicyDecision:
    if intent_type == IntentType.COMPARE_ONLY:
        return PolicyDecision(
            tier=Tier.T1_ADVISE,
            allowed=True,
            required_user_action="Review recommendation only; execution is disabled.",
            reasons=["The user requested comparison only."],
            triggered_rules=["COMPARE_ONLY"],
        )
    failures = blocked_rules(
        request,
        quote,
        user,
        beneficiary,
        usd_equivalent,
        injection_flags,
        supplied_bank_fingerprint,
        sanctioned_countries,
        quote_stale,
        preferences,
    )
    if failures:
        return PolicyDecision(
            tier=Tier.BLOCKED,
            allowed=False,
            required_user_action="Resolve the blocking conditions; no token can be issued.",
            reasons=[reason for _, reason in failures],
            triggered_rules=[rule for rule, _ in failures],
        )
    if usd_equivalent <= settings.confirm_limit_usd:
        return PolicyDecision(
            tier=Tier.T2_CONFIRM,
            allowed=True,
            required_user_action="Click Confirm to authorize this simulated payment.",
            reasons=["Verified beneficiary and amount is within the one-click confirmation tier."],
            triggered_rules=["VERIFIED_BENEFICIARY", "T2_AMOUNT"],
        )
    return PolicyDecision(
        tier=Tier.T3_APPROVE,
        allowed=True,
        required_user_action=(
            f"Type APPROVE {request.amount} {request.currency_to if request.amount_mode.value == 'RECIPIENT' else request.currency_from} "
            f"TO {beneficiary['name']}"
        ),
        reasons=["Verified beneficiary and amount requires explicit typed approval."],
        triggered_rules=["VERIFIED_BENEFICIARY", "T3_AMOUNT"],
    )

