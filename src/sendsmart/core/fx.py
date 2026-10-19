from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

from sendsmart.config import DATA_DIR, settings


@dataclass(frozen=True)
class FXSnapshot:
    rates: dict[str, Decimal]
    timestamp: datetime
    source: str
    is_mock: bool

    def rate(self, currency_from: str, currency_to: str) -> Decimal:
        source = currency_from.upper()
        target = currency_to.upper()
        if source not in self.rates or target not in self.rates:
            raise ValueError(f"Unsupported currency pair: {source}/{target}")
        return self.rates[target] / self.rates[source]


def load_fallback(path: Path | None = None) -> FXSnapshot:
    payload = json.loads((path or DATA_DIR / "fx_rates.json").read_text(encoding="utf-8"))
    timestamp = datetime.fromisoformat(payload["timestamp"])
    return FXSnapshot(
        rates={code: Decimal(value) for code, value in payload["rates"].items()},
        timestamp=timestamp,
        source="bundled mock fallback",
        is_mock=True,
    )


def fetch_live(
    base: str = "USD",
    timeout: float = 2.5,
    requester: Callable[..., object] | None = None,
) -> FXSnapshot:
    if requester is None:
        import requests

        requester = requests.get
    response = requester(f"https://api.frankfurter.app/latest?from={base}", timeout=timeout)
    response.raise_for_status()
    data = response.json()
    rates = {code: Decimal(str(value)) for code, value in data["rates"].items()}
    rates[base] = Decimal("1")
    return FXSnapshot(rates=rates, timestamp=datetime.now(timezone.utc), source="Frankfurter", is_mock=False)


def get_snapshot(allow_live: bool | None = None) -> FXSnapshot:
    use_live = settings.live_fx if allow_live is None else allow_live
    if use_live:
        try:
            return fetch_live()
        except Exception:
            pass
    return load_fallback()


def is_stale(snapshot: FXSnapshot, now: datetime | None = None, max_age_minutes: int | None = None) -> bool:
    current = now or datetime.now(snapshot.timestamp.tzinfo or timezone.utc)
    if current.tzinfo is None and snapshot.timestamp.tzinfo is not None:
        current = current.replace(tzinfo=snapshot.timestamp.tzinfo)
    age_seconds = (current - snapshot.timestamp).total_seconds()
    return age_seconds > 60 * (max_age_minutes or settings.quote_max_age_minutes)

