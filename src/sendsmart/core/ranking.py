from __future__ import annotations

from decimal import Decimal

from sendsmart.models import Preferences, Quote, Route


def _weights(preferences: Preferences) -> tuple[Decimal, Decimal, Decimal]:
    presets = {
        "cheapest": (Decimal("0.75"), Decimal("0.15"), Decimal("0.10")),
        "fastest": (Decimal("0.20"), Decimal("0.65"), Decimal("0.15")),
        "balanced": (
            preferences.cost_weight,
            preferences.speed_weight,
            preferences.reliability_weight,
        ),
    }
    cost, speed, reliability = presets.get(preferences.priority, presets["balanced"])
    total = cost + speed + reliability
    if total <= 0:
        raise ValueError("Ranking weights must sum to a positive number")
    return cost / total, speed / total, reliability / total


def rank_routes(quotes: list[Quote], preferences: Preferences) -> list[Route]:
    if not quotes:
        return []
    feasible = [q for q in quotes if q.deadline_ok]
    candidates = feasible or quotes
    max_cost = max(q.total_cost for q in candidates) or Decimal("1")
    max_days = max(q.eta_business_days for q in candidates) or 1
    cost_w, speed_w, reliability_w = _weights(preferences)
    scored: list[tuple[Quote, Decimal]] = []
    for quote in candidates:
        cost_score = Decimal("1") - quote.total_cost / max_cost
        speed_score = Decimal("1") - Decimal(quote.eta_business_days) / Decimal(max_days + 1)
        score = cost_w * cost_score + speed_w * speed_score + reliability_w * quote.reliability
        scored.append((quote, score))
    scored.sort(key=lambda item: (-item[1], item[0].total_cost, item[0].provider_name))
    return [
        Route(
            quote=quote,
            score=score.quantize(Decimal("0.0001")),
            rank=index,
            rationale=[
                "Meets the requested deadline" if quote.deadline_ok else "No available route meets the deadline",
                f"Ranked for {preferences.priority} preference",
            ],
        )
        for index, (quote, score) in enumerate(scored, start=1)
    ]

