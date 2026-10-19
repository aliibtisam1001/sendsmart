from __future__ import annotations

from sendsmart.models import Quote, Route


def explain_route(route: Route, alternatives: list[Quote]) -> str:
    quote = route.quote
    cheaper_count = sum(1 for item in alternatives if item.total_cost < quote.total_cost)
    deadline_note = "meets the deadline" if quote.deadline_ok else "does not meet the requested deadline"
    return (
        f"{quote.provider_name} is ranked #{route.rank}. It sends {quote.send_amount} {quote.send_currency}, "
        f"the recipient gets {quote.recipient_amount} {quote.receive_currency}, and the computed fee plus FX "
        f"markup is {quote.total_cost} {quote.send_currency}. It {deadline_note}; {cheaper_count} displayed "
        "route(s) have a lower computed cost. All figures are computed from MOCK provider data."
    )


def numbers_match(explanation: str, quote: Quote) -> bool:
    required = (str(quote.send_amount), str(quote.recipient_amount), str(quote.total_cost))
    return all(number in explanation for number in required)

