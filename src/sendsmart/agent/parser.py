from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from sendsmart.security.injection import InjectionFlag, scan_untrusted_text


@dataclass(frozen=True)
class ParsedDocument:
    fields: dict[str, object]
    injection_flags: list[InjectionFlag]


def parse_document(text: str) -> ParsedDocument:
    fields: dict[str, object] = {}
    amount = re.search(r"Amount due:\s*([A-Z]{3})\s*([\d,]+(?:\.\d+)?)", text, re.I)
    if amount:
        fields["currency_to"] = amount.group(1).upper()
        fields["amount"] = Decimal(amount.group(2).replace(",", ""))
    for label, key in (("Deadline", "deadline"), ("Beneficiary ID", "beneficiary_id"), ("Bank fingerprint", "bank_fingerprint")):
        match = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, re.I | re.M)
        if match:
            fields[key] = match.group(1).strip()
    return ParsedDocument(fields=fields, injection_flags=scan_untrusted_text(text))

