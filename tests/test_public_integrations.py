import json
from datetime import datetime, timezone
from decimal import Decimal

from sendsmart.core.benchmarks import find_world_bank_corridor, load_world_bank_snapshot
from sendsmart.integrations.sanctions import screen_un_name
from sendsmart.integrations.wise import fetch_wise_quotes
from sendsmart.models import AmountMode


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "rate": 0.112145,
            "rateTimestamp": "2026-10-20T07:00:00Z",
            "rateExpirationTime": "2026-10-20T08:00:00Z",
            "paymentOptions": [
                {
                    "disabled": False,
                    "sourceAmount": 25000,
                    "targetAmount": 2783.86,
                    "sourceCurrency": "CNY",
                    "targetCurrency": "GBP",
                    "fee": {"total": 176.21},
                    "payIn": "BANK_TRANSFER",
                    "payOut": "BANK_TRANSFER",
                    "estimatedDelivery": "2026-10-20T13:00:00Z",
                    "formattedEstimatedDelivery": "in 6 hours",
                },
                {
                    "disabled": True,
                    "sourceAmount": 25000,
                    "targetAmount": 2790,
                    "sourceCurrency": "CNY",
                    "targetCurrency": "GBP",
                    "fee": {"total": 100},
                    "payIn": "BALANCE",
                    "payOut": "BANK_TRANSFER",
                },
            ],
        }


def test_wise_preview_parses_enabled_options_only():
    called = {}

    def requester(url, **kwargs):
        called["url"] = url
        called["body"] = kwargs["json"]
        return FakeResponse()

    quotes = fetch_wise_quotes("CNY", "GBP", Decimal("25000"), AmountMode.SEND, requester=requester)
    assert len(quotes) == 1
    assert quotes[0].fee == Decimal("176.21")
    assert quotes[0].estimated_delivery == datetime(2026, 10, 20, 13, tzinfo=timezone.utc)
    assert quotes[0].is_executable is False
    assert called["body"]["sourceAmount"] == 25000.0


def test_world_bank_snapshot_is_real_and_queryable():
    snapshot = load_world_bank_snapshot()
    assert snapshot["source"] == "World Bank Remittance Prices Worldwide"
    assert snapshot["license"] == "CC BY 4.0"
    assert len(snapshot["corridors"]) == 348
    corridor = snapshot["corridors"][0]
    assert find_world_bank_corridor(corridor["source_iso3"], corridor["destination_iso3"]) == corridor
    assert find_world_bank_corridor("CHN", "GBR") is None


def test_un_name_screen_uses_snapshot_and_requires_human_review(tmp_path):
    fixture = {
        "entries": [
            {"reference": "TEST.1", "kind": "entity", "names": ["Example Restricted Entity"]}
        ]
    }
    path = tmp_path / "un.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    matches = screen_un_name("Example Restricted Entity", path=path)
    assert matches[0].reference == "TEST.1"
    assert matches[0].score == 1.0
    assert screen_un_name("Ordinary University", path=path) == []
