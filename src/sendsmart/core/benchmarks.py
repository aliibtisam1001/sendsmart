from __future__ import annotations

import json
from pathlib import Path

from sendsmart.config import DATA_DIR


def load_world_bank_snapshot(path: Path | None = None) -> dict:
    return json.loads((path or DATA_DIR / "world_bank_rpw_snapshot.json").read_text(encoding="utf-8"))


def find_world_bank_corridor(source_iso3: str, destination_iso3: str, path: Path | None = None) -> dict | None:
    payload = load_world_bank_snapshot(path)
    return next(
        (
            corridor
            for corridor in payload["corridors"]
            if corridor["source_iso3"] == source_iso3 and corridor["destination_iso3"] == destination_iso3
        ),
        None,
    )
