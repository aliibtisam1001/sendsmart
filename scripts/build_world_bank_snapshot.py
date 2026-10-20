"""Build a compact, reviewable snapshot from the World Bank RPW workbook."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

import openpyxl


def period_key(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})_(\d)Q", value or "")
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def compact_number(value):
    return round(float(value), 4) if isinstance(value, (int, float)) else value


def build(input_path: Path, output_path: Path) -> None:
    workbook = openpyxl.load_workbook(input_path, read_only=True, data_only=True)
    sheet = workbook["Dataset (from Q2 2016)"]
    rows = sheet.iter_rows(values_only=True)
    headers = list(next(rows))
    index = {name: position for position, name in enumerate(headers) if name}
    required = {
        "period", "source_code", "source_name", "destination_code", "destination_name",
        "firm", "firm_type", "payment instrument", "access point", "speed actual",
        "cc1 lcu amount", "cc1 lcu code", "cc1 lcu fee", "cc1 total cost %",
        "cc2 lcu amount", "cc2 lcu fee", "cc2 total cost %", "transparent",
    }
    missing = required - index.keys()
    if missing:
        raise ValueError(f"Missing workbook columns: {sorted(missing)}")

    latest_period = ""
    collected: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        period = row[index["period"]]
        if not isinstance(period, str):
            continue
        if period_key(period) > period_key(latest_period):
            latest_period = period
            collected.clear()
        if period != latest_period:
            continue
        source = row[index["source_code"]]
        destination = row[index["destination_code"]]
        if not source or not destination:
            continue
        collected[(source, destination)].append(
            {
                "source_name": row[index["source_name"]],
                "destination_name": row[index["destination_name"]],
                "firm": row[index["firm"]],
                "firm_type": row[index["firm_type"]],
                "payment_instrument": row[index["payment instrument"]],
                "access_point": row[index["access point"]],
                "speed": row[index["speed actual"]],
                "source_currency": row[index["cc1 lcu code"]],
                "amount_200_local": compact_number(row[index["cc1 lcu amount"]]),
                "fee_200_local": compact_number(row[index["cc1 lcu fee"]]),
                "cost_200_pct": compact_number(row[index["cc1 total cost %"]]),
                "amount_500_local": compact_number(row[index["cc2 lcu amount"]]),
                "fee_500_local": compact_number(row[index["cc2 lcu fee"]]),
                "cost_500_pct": compact_number(row[index["cc2 total cost %"]]),
                "transparent": str(row[index["transparent"]]).lower() == "yes",
            }
        )

    corridors = []
    for (source, destination), observations in sorted(collected.items()):
        transparent = [row for row in observations if row["transparent"]]
        usable = transparent or observations
        cost_200 = [row["cost_200_pct"] for row in usable if isinstance(row["cost_200_pct"], float)]
        cost_500 = [row["cost_500_pct"] for row in usable if isinstance(row["cost_500_pct"], float)]
        cheapest = sorted(
            usable,
            key=lambda row: row["cost_200_pct"] if isinstance(row["cost_200_pct"], float) else float("inf"),
        )[:3]
        corridors.append(
            {
                "source_iso3": source,
                "source": observations[0]["source_name"],
                "destination_iso3": destination,
                "destination": observations[0]["destination_name"],
                "observations": len(observations),
                "transparent_observations": len(transparent),
                "median_cost_200_pct": round(statistics.median(cost_200), 4) if cost_200 else None,
                "minimum_cost_200_pct": round(min(cost_200), 4) if cost_200 else None,
                "median_cost_500_pct": round(statistics.median(cost_500), 4) if cost_500 else None,
                "minimum_cost_500_pct": round(min(cost_500), 4) if cost_500 else None,
                "lowest_observed_services": cheapest,
            }
        )

    payload = {
        "source": "World Bank Remittance Prices Worldwide",
        "source_url": "https://datacatalog.worldbank.org/search/dataset/0037898/remittance-prices-worldwide",
        "license": "CC BY 4.0",
        "attribution": "The World Bank, Remittance Prices Worldwide, available at http://remittanceprices.worldbank.org",
        "period": latest_period,
        "method": "Corridor medians and minimums from transparent observations when available; services are historical observations, not live offers.",
        "corridors": corridors,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(corridors)} corridors for {latest_period} to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.input, args.output)
