"""Build a compact name-screening snapshot from the official UN XML list."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def text(element: ET.Element, name: str) -> str:
    child = element.find(name)
    return (child.text or "").strip() if child is not None else ""


def names_for(record: ET.Element, kind: str) -> list[str]:
    if kind == "individual":
        primary = " ".join(
            part for part in (text(record, "FIRST_NAME"), text(record, "SECOND_NAME"), text(record, "THIRD_NAME"), text(record, "FOURTH_NAME")) if part
        )
        alias_tag = "INDIVIDUAL_ALIAS"
    else:
        primary = text(record, "FIRST_NAME")
        alias_tag = "ENTITY_ALIAS"
    names = [primary] if primary else []
    for alias in record.findall(alias_tag):
        value = text(alias, "ALIAS_NAME")
        if value and value not in names:
            names.append(value)
    return names


def build(input_path: Path, output_path: Path) -> None:
    root = ET.parse(input_path).getroot()
    entries = []
    for container_name, record_name, kind in (
        ("INDIVIDUALS", "INDIVIDUAL", "individual"),
        ("ENTITIES", "ENTITY", "entity"),
    ):
        container = root.find(container_name)
        if container is None:
            continue
        for record in container.findall(record_name):
            entries.append(
                {
                    "reference": text(record, "REFERENCE_NUMBER"),
                    "kind": kind,
                    "listed_on": text(record, "LISTED_ON"),
                    "names": names_for(record, kind),
                }
            )
    payload = {
        "source": "United Nations Security Council Consolidated List",
        "source_url": "https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list",
        "generated_at": root.attrib.get("dateGenerated"),
        "disclosure": "Preliminary name screening only. A possible match requires human compliance review and additional identifiers.",
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} UN sanctions entries to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.input, args.output)
