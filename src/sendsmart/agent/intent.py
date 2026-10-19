from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sendsmart.models import AmountMode, Intent, IntentType


CURRENCY_NAMES = {
    "pounds": "GBP", "pound": "GBP", "gbp": "GBP", "£": "GBP",
    "dollars": "USD", "dollar": "USD", "usd": "USD", "$": "USD",
    "ringgit": "MYR", "myr": "MYR", "pesos": "MXN", "peso": "MXN", "mxn": "MXN",
    "euros": "EUR", "euro": "EUR", "eur": "EUR", "yuan": "CNY", "cny": "CNY",
}


def _parse_amount(text: str) -> tuple[Decimal | None, str | None, bool]:
    patterns = [
        r"(?P<currency>GBP|USD|MYR|MXN|EUR|CNY|£|\$)\s*(?P<amount>\d[\d,]*(?:\.\d+)?)",
        r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<currency>GBP|USD|MYR|MXN|EUR|CNY|pounds?|dollars?|ringgit|pesos?|euros?|yuan)\b",
    ]
    matches: list[tuple[Decimal, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            try:
                amount = Decimal(match.group("amount").replace(",", ""))
            except InvalidOperation:
                continue
            currency = CURRENCY_NAMES[match.group("currency").lower()]
            pair = (amount, currency)
            if pair not in matches:
                matches.append(pair)
    if not matches:
        return None, None, False
    return matches[0][0], matches[0][1], len(matches) > 1


def _parse_pair(text: str) -> tuple[str | None, str | None]:
    pair = re.search(r"\b(?:from\s+)?(GBP|USD|MYR|MXN|EUR|CNY)\s+(?:to|into|->)\s+(GBP|USD|MYR|MXN|EUR|CNY)\b", text, re.I)
    if pair:
        return pair.group(1).upper(), pair.group(2).upper()
    source = re.search(r"\bfrom\s+(GBP|USD|MYR|MXN|EUR|CNY)\b", text, re.I)
    target = re.search(r"\b(?:to|into)\s+(GBP|USD|MYR|MXN|EUR|CNY)\b", text, re.I)
    return (source.group(1).upper() if source else None, target.group(1).upper() if target else None)


def _parse_deadline(text: str, today: date) -> date | None:
    iso = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    relative = re.search(r"\b(?:in|within)\s+(\d+)\s+days?\b", text, re.I)
    if relative:
        return today + timedelta(days=int(relative.group(1)))
    weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    weekday = re.search(r"\b(?:by\s+)?(" + "|".join(weekdays) + r")\b", text, re.I)
    if weekday:
        target = weekdays[weekday.group(1).lower()]
        delta = (target - today.weekday()) % 7
        return today + timedelta(days=delta or 7)
    named = re.search(
        r"\b(?:by\s+)?(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)(?:\s+(20\d{2}))?\b",
        text, re.I,
    )
    if named:
        months = {name.lower(): index for index, name in enumerate(
            ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
        return date(int(named.group(3) or today.year), months[named.group(2).lower()], int(named.group(1)))
    return None


def _beneficiary(text: str) -> str | None:
    known = {
        "northbridge university": "northbridge_university",
        "aisha's landlord": "aisha_landlord",
        "my landlord": "aisha_landlord",
        "pacific state university": "carlos_university",
        "new beneficiary": "new_beneficiary",
    }
    lowered = text.lower()
    return next((identifier for name, identifier in known.items() if name in lowered), None)


def classify_rule_based(text: str, now: datetime | None = None, defaults: dict[str, Any] | None = None) -> Intent:
    clean = " ".join(text.strip().split())
    lowered = clean.lower()
    defaults = defaults or {}
    current_date = (now or datetime.now()).date()
    if re.search(r"\b(buy|trade|pick)\b.*\b(stock|share|crypto|bitcoin)\b", lowered):
        return Intent(type=IntentType.OUT_OF_SCOPE, confidence=Decimal("0.98"), slots={})
    if re.search(r"\b(cancel|stop)\b.*\b(payment|transfer|remittance)\b", lowered):
        return Intent(type=IntentType.CANCEL_PAYMENT, confidence=Decimal("0.96"), slots={})
    if re.search(r"\b(status|track|where is)\b.*\b(payment|transfer|money)\b", lowered):
        return Intent(type=IntentType.CHECK_STATUS, confidence=Decimal("0.94"), slots={})
    if re.search(r"\b(prefer|preference|cheapest|fastest|balanced)\b", lowered) and not re.search(r"\bcompare|send|pay|transfer\b", lowered):
        priority = next((p for p in ("cheapest", "fastest", "balanced") if p in lowered), None)
        return Intent(type=IntentType.CHANGE_PREFERENCE, confidence=Decimal("0.91"), slots={"priority": priority})
    compare = bool(re.search(r"\b(compare|quote|options|just checking|best rate|how much would)\b", lowered))
    tuition = bool(re.search(r"\b(tuition|university|college|school fee)\b", lowered))
    transfer = bool(re.search(r"\b(send|transfer|remit|living cost|rent|money)\b", lowered))
    intent_type = IntentType.COMPARE_ONLY if compare else (IntentType.PAY_TUITION if tuition else IntentType.SEND_LIVING_COSTS if transfer else IntentType.OUT_OF_SCOPE)
    if intent_type == IntentType.OUT_OF_SCOPE:
        return Intent(type=intent_type, confidence=Decimal("0.65"), slots={})

    amount, amount_currency, ambiguous_amount = _parse_amount(clean)
    currency_from, currency_to = _parse_pair(clean)
    if not currency_from:
        currency_from = defaults.get("currency_from")
    if not currency_to:
        if amount_currency and tuition:
            currency_to = amount_currency
        elif amount_currency:
            currency_from = currency_from or amount_currency
        currency_to = currency_to or defaults.get("currency_to")
    slots: dict[str, Any] = {
        "amount": amount,
        "currency_from": currency_from,
        "currency_to": currency_to,
        "amount_mode": AmountMode.RECIPIENT if tuition and not re.search(r"\b(send|debit)\s+(exactly\s+)?", lowered) else AmountMode.SEND,
        "deadline": _parse_deadline(clean, current_date),
        "beneficiary": _beneficiary(clean),
        "purpose": "tuition" if tuition else "living costs",
        "priority": next((p for p in ("cheapest", "fastest", "balanced") if p in lowered), defaults.get("priority", "balanced")),
    }
    required = ["amount", "currency_from", "currency_to", "beneficiary"]
    if tuition:
        required.append("deadline")
    missing = [field for field in required if not slots.get(field)]
    ambiguities = ["Multiple monetary amounts were found; identify which amount should be used."] if ambiguous_amount else []
    return Intent(
        type=intent_type,
        confidence=Decimal("0.90" if not missing and not ambiguities else "0.78"),
        slots=slots,
        missing_slots=missing,
        ambiguities=ambiguities,
    )


def clarification_question(intent: Intent) -> str | None:
    if intent.ambiguities:
        return intent.ambiguities[0]
    prompts = {
        "amount": "How much should be sent or received, and in which currency?",
        "currency_from": "Which currency will you pay from?",
        "currency_to": "Which currency should the recipient receive?",
        "beneficiary": "Who is the intended beneficiary?",
        "deadline": "By what date must the tuition payment arrive?",
    }
    return prompts.get(intent.missing_slots[0]) if intent.missing_slots else None

