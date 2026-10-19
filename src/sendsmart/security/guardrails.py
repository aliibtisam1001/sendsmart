from __future__ import annotations

from decimal import Decimal
from typing import Any

from sendsmart.config import settings
from sendsmart.models import PaymentRequest, Preferences, Quote
from sendsmart.security.injection import InjectionFlag


def blocked_rules(
    request: PaymentRequest,
    quote: Quote,
    user: dict[str, Any],
    beneficiary: dict[str, Any],
    usd_equivalent: Decimal,
    injection_flags: list[InjectionFlag] | None = None,
    supplied_bank_fingerprint: str | None = None,
    sanctioned_countries: set[str] | None = None,
    quote_stale: bool = False,
    preferences: Preferences | None = None,
) -> list[tuple[str, str]]:
    blocked: list[tuple[str, str]] = []
    if not beneficiary.get("verified", False):
        blocked.append(("BENEFICIARY_UNVERIFIED", "The beneficiary is new or unverified."))
    if supplied_bank_fingerprint and supplied_bank_fingerprint != beneficiary.get("bank_fingerprint"):
        blocked.append(("BANK_DETAILS_CHANGED", "The supplied bank details differ from the verified record."))
    if usd_equivalent > settings.hard_limit_usd:
        blocked.append(("HARD_LIMIT_EXCEEDED", f"The amount exceeds the USD {settings.hard_limit_usd} hard limit."))
    daily_spend = Decimal(str(user.get("daily_spend_usd", "0")))
    daily_cap = Decimal(str(user.get("daily_cap_usd", "0")))
    if daily_spend + usd_equivalent > daily_cap:
        blocked.append(("DAILY_CAP_EXCEEDED", "The transfer would exceed the user's daily cap."))
    if request.destination_country.upper() in (sanctioned_countries or set()):
        blocked.append(("SANCTIONED_DESTINATION", "The destination is on the sandbox sanctions list."))
    if injection_flags:
        blocked.append(("UNTRUSTED_INSTRUCTION_DETECTED", "Instruction-like text was detected in the source document."))
    if quote_stale:
        blocked.append(("STALE_QUOTE", "The FX quote is stale and must be refreshed."))
    if preferences and usd_equivalent > min(preferences.personal_limit_usd, settings.hard_limit_usd):
        blocked.append(("PERSONAL_LIMIT_EXCEEDED", "The amount exceeds the user's stricter personal limit."))
    if quote.send_amount <= 0 or request.amount <= 0:
        blocked.append(("INVALID_AMOUNT", "The amount must be positive."))
    return blocked

