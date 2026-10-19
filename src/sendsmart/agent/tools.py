from __future__ import annotations

import json
from pathlib import Path

from sendsmart.config import DATA_DIR
from sendsmart.core.pricing import compute_route_cost
from sendsmart.models import PaymentRequest


def load_json(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def list_providers() -> list[dict]:
    return load_json("providers.json")


def find_record(name: str, identifier: str) -> dict:
    records = load_json(name)
    return next((record for record in records if record["id"] == identifier), {})


def compare_routes(request: PaymentRequest, fx, quoted_at=None):
    return [compute_route_cost(provider, request, fx, quoted_at=quoted_at) for provider in list_providers()]

