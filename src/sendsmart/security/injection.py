from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InjectionFlag:
    rule_id: str
    severity: str
    evidence: str


PATTERNS = {
    "PROMPT_OVERRIDE": r"\b(ignore|disregard)\s+(all\s+)?(previous|prior|above)\b",
    "LIMIT_OVERRIDE": r"\boverride\s+(the\s+)?(limit|policy|guardrail)s?\b",
    "ACCOUNT_REDIRECT": r"\bsend\s+(it\s+|money\s+)?to\s+(this|another|my)\s+account\b",
    "CONCEALMENT": r"\b(do not|don't)\s+(tell|show|notify)\s+(the\s+)?user\b",
    "SYSTEM_MIMICRY": r"\b(system|developer)\s*(prompt|message|instruction)\b",
    "HIDDEN_TEXT": r"(font-size\s*:\s*0|display\s*:\s*none|white-on-white|hidden text)",
    "URGENCY_PRESSURE": r"\b(urgent|immediately|right now)\b.{0,40}\b(skip|bypass|ignore)\b",
}


def scan_untrusted_text(text: str | None) -> list[InjectionFlag]:
    if not text:
        return []
    flags: list[InjectionFlag] = []
    for rule_id, pattern in PATTERNS.items():
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            flags.append(InjectionFlag(rule_id, "high", match.group(0)[:120]))
    return flags

