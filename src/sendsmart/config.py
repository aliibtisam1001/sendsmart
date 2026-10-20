from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
EVIDENCE_DIR = ROOT / "evidence"


@dataclass(frozen=True)
class Settings:
    hard_limit_usd: Decimal = Decimal("10000")
    confirm_limit_usd: Decimal = Decimal("500")
    quote_max_age_minutes: int = 15
    token_ttl_seconds: int = 300
    cancel_window_seconds: int = 60
    max_llm_tool_calls: int = 6
    token_secret: str = field(
        default_factory=lambda: os.getenv("SENDSMART_TOKEN_SECRET") or secrets.token_urlsafe(48)
    )
    model: str = os.getenv("SENDSMART_MODEL", "claude-sonnet-4-5")
    live_fx: bool = os.getenv("SENDSMART_LIVE_FX", "false").lower() == "true"


settings = Settings()

