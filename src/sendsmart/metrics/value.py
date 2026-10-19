from __future__ import annotations

from decimal import Decimal

from sendsmart.models import Quote, ValueReport


def _savings(selected: Quote, baseline: Quote) -> tuple[Decimal, Decimal]:
    amount = baseline.total_cost - selected.total_cost
    percent = Decimal("0") if baseline.total_cost == 0 else amount / baseline.total_cost * Decimal("100")
    return amount.quantize(Decimal("0.01")), percent.quantize(Decimal("0.01"))


def build_value_report(
    request_id: str,
    selected: Quote,
    bank: Quote,
    default: Quote,
    send_to_usd_rate: Decimal,
    all_quotes: list[Quote],
    comparison_seconds: Decimal,
    risks_blocked: list[str] | None = None,
) -> ValueReport:
    bank_savings, bank_percent = _savings(selected, bank)
    default_savings, default_percent = _savings(selected, default)
    missed = sum(1 for quote in all_quotes if not quote.deadline_ok) if selected.deadline_ok else 0
    return ValueReport(
        request_id=request_id,
        selected_provider=selected.provider_name,
        savings_vs_bank_send=bank_savings,
        savings_vs_bank_usd=(bank_savings * send_to_usd_rate).quantize(Decimal("0.01")),
        savings_vs_bank_percent=bank_percent,
        savings_vs_default_send=default_savings,
        savings_vs_default_usd=(default_savings * send_to_usd_rate).quantize(Decimal("0.01")),
        savings_vs_default_percent=default_percent,
        deadline_risk_avoided=missed,
        comparison_seconds=comparison_seconds.quantize(Decimal("0.001")),
        estimated_manual_minutes=(Decimal(len(all_quotes)) * Decimal("4")),
        risk_events_blocked=risks_blocked or [],
    )

