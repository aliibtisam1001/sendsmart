from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
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
    rate_dates: dict[str, date] = field(default_factory=dict)

    def rate(self, currency_from: str, currency_to: str) -> Decimal:
        source = currency_from.upper()
        target = currency_to.upper()
        if source not in self.rates or target not in self.rates:
            raise ValueError(f"Unsupported currency pair: {source}/{target}")
        return self.rates[target] / self.rates[source]

    def rate_date(self, currency_from: str, currency_to: str) -> date:
        default = self.timestamp.date()
        return min(
            self.rate_dates.get(currency_from.upper(), default),
            self.rate_dates.get(currency_to.upper(), default),
        )


def load_fallback(path: Path | None = None) -> FXSnapshot:
    payload = json.loads((path or DATA_DIR / "fx_rates.json").read_text(encoding="utf-8"))
    timestamp = datetime.fromisoformat(payload["timestamp"])
    return FXSnapshot(
        rates={code: Decimal(value) for code, value in payload["rates"].items()},
        timestamp=timestamp,
        source="bundled mock fallback",
        is_mock=True,
    )


def load_public_cache(path: Path | None = None) -> FXSnapshot:
    payload = json.loads((path or DATA_DIR / "frankfurter_snapshot.json").read_text(encoding="utf-8"))
    timestamp = datetime.fromisoformat(payload["timestamp"])
    default_date = timestamp.date()
    return FXSnapshot(
        rates={code: Decimal(value) for code, value in payload["rates"].items()},
        timestamp=timestamp,
        source=payload.get("source", "Frankfurter public API (cached snapshot)"),
        is_mock=False,
        rate_dates={code: date.fromisoformat(value) for code, value in payload.get("rate_dates", {}).items()}
        | {"EUR": default_date},
    )


def fetch_live(
    base: str = "USD",
    timeout: float = 2.5,
    requester: Callable[..., object] | None = None,
) -> FXSnapshot:
    if requester is None:
        import requests

        requester = requests.get
    response = requester(f"https://api.frankfurter.dev/v2/rates?base={base}", timeout=timeout)
    response.raise_for_status()
    data = response.json()
    # Accept Frankfurter v2 and retain v1 compatibility for test doubles and old caches.
    if isinstance(data, list):
        rates = {row["quote"]: Decimal(str(row["rate"])) for row in data}
        dates = [row.get("date") for row in data if row.get("date")]
        timestamp = datetime.fromisoformat(max(dates)).replace(tzinfo=timezone.utc) if dates else datetime.now(timezone.utc)
        rate_dates = {row["quote"]: date.fromisoformat(row["date"]) for row in data if row.get("date")}
    else:
        rates = {code: Decimal(str(value)) for code, value in data["rates"].items()}
        timestamp = datetime.now(timezone.utc)
        rate_dates = {}
    rates[base] = Decimal("1")
    rate_dates[base] = timestamp.date()
    return FXSnapshot(
        rates=rates,
        timestamp=timestamp,
        source="Frankfurter public API (live)",
        is_mock=False,
        rate_dates=rate_dates,
    )


def get_snapshot(allow_live: bool | None = None) -> FXSnapshot:
    use_live = settings.live_fx if allow_live is None else allow_live
    if use_live:
        try:
            return fetch_live()
        except Exception:
            pass
    return load_fallback()


def get_public_snapshot(allow_live: bool = True) -> FXSnapshot:
    """Return live Frankfurter data, falling back to a bundled public snapshot."""
    if allow_live:
        try:
            return fetch_live()
        except Exception:
            pass
    return load_public_cache()


def is_stale(snapshot: FXSnapshot, now: datetime | None = None, max_age_minutes: int | None = None) -> bool:
    current = now or datetime.now(snapshot.timestamp.tzinfo or timezone.utc)
    if current.tzinfo is None and snapshot.timestamp.tzinfo is not None:
        current = current.replace(tzinfo=snapshot.timestamp.tzinfo)
    age_seconds = (current - snapshot.timestamp).total_seconds()
    return age_seconds > 60 * (max_age_minutes or settings.quote_max_age_minutes)

