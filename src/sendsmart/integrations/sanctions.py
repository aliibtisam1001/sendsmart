from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from sendsmart.config import DATA_DIR


@dataclass(frozen=True)
class SanctionsMatch:
    reference: str
    kind: str
    matched_name: str
    score: float


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", normalized.upper()).strip()


def load_un_snapshot(path: Path | None = None) -> dict:
    return json.loads((path or DATA_DIR / "un_sanctions_snapshot.json").read_text(encoding="utf-8"))


def screen_un_name(name: str, threshold: float = 0.92, path: Path | None = None) -> list[SanctionsMatch]:
    query = normalize_name(name)
    if len(query) < 4:
        return []
    matches: list[SanctionsMatch] = []
    for entry in load_un_snapshot(path)["entries"]:
        for candidate in entry["names"]:
            normalized = normalize_name(candidate)
            if not normalized:
                continue
            score = 1.0 if query == normalized else SequenceMatcher(None, query, normalized).ratio()
            if score >= threshold:
                matches.append(SanctionsMatch(entry["reference"], entry["kind"], candidate, score))
    return sorted(matches, key=lambda match: -match.score)
