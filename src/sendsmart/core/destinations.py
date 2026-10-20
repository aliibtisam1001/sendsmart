from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sendsmart.config import DATA_DIR


@dataclass(frozen=True)
class StudyDestination:
    rank: int
    iso3: str
    country: str
    currency: str
    year: int
    students: int

    @property
    def label(self) -> str:
        return f"#{self.rank}  {self.country}  ·  {self.currency}"


def load_destination_dataset(path: Path | None = None) -> dict:
    return json.loads((path or DATA_DIR / "study_destinations.json").read_text(encoding="utf-8"))


def load_destinations(path: Path | None = None) -> list[StudyDestination]:
    payload = load_destination_dataset(path)
    return [StudyDestination(**row) for row in payload["destinations"]]


def find_destination(iso3: str, destinations: list[StudyDestination] | None = None) -> StudyDestination:
    for destination in destinations or load_destinations():
        if destination.iso3 == iso3:
            return destination
    raise ValueError(f"Unknown study destination: {iso3}")
