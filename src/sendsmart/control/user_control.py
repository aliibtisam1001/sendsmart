from __future__ import annotations

from decimal import Decimal

from sendsmart.config import settings
from sendsmart.models import PaymentRequest, Plan, PolicyDecision, Preferences, StepStatus, Tier


def expected_approval_phrase(request: PaymentRequest, beneficiary_name: str) -> str:
    currency = request.currency_to if request.amount_mode.value == "RECIPIENT" else request.currency_from
    return f"APPROVE {request.amount} {currency} TO {beneficiary_name}"


def approve(plan: Plan, decision: PolicyDecision, user_input: str, request: PaymentRequest, beneficiary_name: str) -> Plan:
    if not decision.allowed or decision.tier in (Tier.BLOCKED, Tier.T1_ADVISE):
        raise PermissionError("This plan is not executable")
    if decision.tier == Tier.T2_CONFIRM:
        valid = user_input.strip().upper() in {"CONFIRM", "APPROVE"}
    else:
        valid = user_input.strip() == expected_approval_phrase(request, beneficiary_name)
    if not valid:
        raise PermissionError("Approval did not match the required action")
    plan.approved = True
    return plan


def reject(plan: Plan) -> Plan:
    plan.approved = False
    for step in plan.steps:
        if step.tool in {"mint_token", "execute_sandbox", "report_result"}:
            step.status = StepStatus.SKIPPED
    return plan


def apply_preferences(current: Preferences, updates: dict[str, object]) -> Preferences:
    values = current.model_dump()
    values.update(updates)
    requested_limit = Decimal(str(values.get("personal_limit_usd", settings.hard_limit_usd)))
    values["personal_limit_usd"] = min(requested_limit, current.personal_limit_usd, settings.hard_limit_usd)
    return Preferences(**values)

