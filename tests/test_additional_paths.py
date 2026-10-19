from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from sendsmart.agent.intent import classify_rule_based
from sendsmart.agent.planner import build_plan, recovery_plan
from sendsmart.control.user_control import apply_preferences, approve, reject
from sendsmart.core.fx import FXSnapshot, fetch_live, get_snapshot, is_stale, load_fallback
from sendsmart.core.ranking import rank_routes
from sendsmart.execution.sandbox import ExecutionRejected, SandboxExecutor
from sendsmart.models import (
    AmountMode,
    Intent,
    IntentType,
    PaymentRequest,
    Plan,
    PolicyDecision,
    Preferences,
    Quote,
    Tier,
)
from sendsmart.security.audit import AuditLog
from sendsmart.security.tokens import TokenAuthority


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"rates": {"GBP": 0.8}}


def test_live_fx_adapter_and_staleness():
    snapshot = fetch_live(requester=lambda *args, **kwargs: FakeResponse())
    assert snapshot.rate("USD", "GBP") == Decimal("0.8")
    old = FXSnapshot({"USD": Decimal("1")}, datetime.now(timezone.utc) - timedelta(hours=1), "test", True)
    assert is_stale(old)
    with pytest.raises(ValueError, match="Unsupported"):
        snapshot.rate("USD", "ZZZ")


def test_live_failure_falls_back(monkeypatch):
    import sendsmart.core.fx as fx_module

    monkeypatch.setattr(fx_module, "fetch_live", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    assert get_snapshot(allow_live=True).is_mock


def test_ranking_empty_and_invalid_weights():
    assert rank_routes([], Preferences()) == []
    quote = Quote(
        provider_id="p", provider_name="P", send_amount=Decimal("1"), send_currency="USD",
        recipient_amount=Decimal("1"), receive_currency="USD", fee=Decimal("0"),
        fx_markup_cost=Decimal("0"), total_cost=Decimal("0"), rate=Decimal("1"),
        eta_business_days=0, reliability=Decimal("1"), quoted_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="weights"):
        rank_routes([quote], Preferences(priority="custom", cost_weight=0, speed_weight=0, reliability_weight=0))


def test_intent_named_date_weekday_and_ambiguity():
    named = classify_rule_based("Pay GBP 500 tuition to Northbridge University from MYR by 30 October 2026")
    assert named.slots["deadline"] == date(2026, 10, 30)
    friday = classify_rule_based("Pay GBP 500 tuition to Northbridge University from MYR by Friday", now=datetime(2026, 10, 20))
    assert friday.slots["deadline"] == date(2026, 10, 23)
    ambiguous = classify_rule_based("Pay GBP 100 and GBP 200 tuition to Northbridge University from MYR by Friday")
    assert ambiguous.ambiguities


def test_cancel_and_recovery_plans():
    cancel_intent = Intent(type=IntentType.CANCEL_PAYMENT, confidence=Decimal("1"))
    plan = build_plan(cancel_intent, "r")
    assert [step.tool for step in plan.steps] == ["lookup_payment", "user_checkpoint", "cancel_payment"]
    recovery = recovery_plan(plan, "get_fx")
    assert recovery.steps[0].tool == "get_fx"
    generic = recovery_plan(plan, "unknown")
    assert generic.steps[0].requires_user_checkpoint


def make_request():
    return PaymentRequest(
        request_id="r", user_id="u", amount=Decimal("100"), currency_from="USD", currency_to="GBP",
        amount_mode=AmountMode.SEND, beneficiary_id="b", purpose="living costs", destination_country="GB",
    )


def make_quote():
    return Quote(
        provider_id="p", provider_name="P", send_amount=Decimal("100"), send_currency="USD",
        recipient_amount=Decimal("80"), receive_currency="GBP", fee=Decimal("1"),
        fx_markup_cost=Decimal("1"), total_cost=Decimal("2"), rate=Decimal("0.8"),
        eta_business_days=1, reliability=Decimal("0.9"), quoted_at=datetime.now(timezone.utc),
    )


def test_control_confirm_reject_and_limit_tightening():
    request = make_request()
    plan = Plan(request_id="r", intent_type=IntentType.SEND_LIVING_COSTS, steps=[])
    decision = PolicyDecision(tier=Tier.T2_CONFIRM, allowed=True, required_user_action="confirm")
    with pytest.raises(PermissionError):
        approve(plan, decision, "no", request, "B")
    assert approve(plan, decision, "CONFIRM", request, "B").approved
    assert not reject(plan).approved
    tightened = apply_preferences(Preferences(personal_limit_usd=Decimal("2000")), {"personal_limit_usd": "1000"})
    assert tightened.personal_limit_usd == Decimal("1000")


def test_sandbox_idempotency_expiry_and_cancel_window(tmp_path):
    request, quote = make_request(), make_quote()
    authority = TokenAuthority("secret", ttl_seconds=5)
    executor = SandboxExecutor(authority, AuditLog(tmp_path / "audit.jsonl"), cancel_window_seconds=1)
    now = datetime.now(timezone.utc)
    token = authority.mint(request, quote, "fp", now=now)
    first = executor.execute(request, quote, "fp", token, "same", now=now)
    assert executor.execute(request, quote, "fp", None, "same", now=now) == first
    with pytest.raises(ExecutionRejected, match="CANCEL_WINDOW_CLOSED"):
        executor.cancel("same", now=now + timedelta(seconds=2))
    expired = authority.mint(request, quote, "fp", now=now - timedelta(minutes=1))
    with pytest.raises(ExecutionRejected, match="INVALID_OR_EXPIRED"):
        executor.execute(request, quote, "fp", expired, "expired", now=now)


def test_empty_audit_is_valid(tmp_path):
    assert AuditLog(tmp_path / "missing.jsonl").verify_chain()

