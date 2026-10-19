from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sendsmart.agent.explain import explain_route, numbers_match
from sendsmart.agent.intent import clarification_question, classify_rule_based
from sendsmart.agent.parser import parse_document
from sendsmart.agent.planner import build_plan
from sendsmart.agent.tools import compare_routes, find_record, load_json
from sendsmart.config import EVIDENCE_DIR
from sendsmart.control.user_control import approve, reject
from sendsmart.core.eta import meets_deadline
from sendsmart.core.fx import FXSnapshot, get_snapshot
from sendsmart.core.ranking import rank_routes
from sendsmart.execution.sandbox import SandboxExecutor
from sendsmart.metrics.value import build_value_report
from sendsmart.models import AmountMode, Intent, PaymentRequest, Plan, PolicyDecision, Preferences, Quote, Route, StepStatus, ValueReport
from sendsmart.security.audit import AuditLog
from sendsmart.security.injection import InjectionFlag
from sendsmart.security.policy import evaluate
from sendsmart.security.tokens import TokenAuthority


@dataclass
class PreparedTransfer:
    intent: Intent
    request: PaymentRequest
    plan: Plan
    fx: FXSnapshot
    quotes: list[Quote]
    routes: list[Route]
    selected: Route
    policy: PolicyDecision
    beneficiary: dict[str, Any]
    user: dict[str, Any]
    preferences: Preferences
    explanation: str
    value_report: ValueReport
    bank_fingerprint: str
    comparison_seconds: Decimal


class SendSmartOrchestrator:
    def __init__(self, audit_path: str | Path | None = None, token_secret: str | None = None):
        path = Path(audit_path or EVIDENCE_DIR / "audit_log.jsonl")
        self.audit = AuditLog(path)
        self.authority = TokenAuthority(token_secret)
        self.executor = SandboxExecutor(self.authority, self.audit)

    def understand(
        self, text: str, user_id: str = "aisha", now: datetime | None = None, defaults: dict[str, Any] | None = None
    ) -> tuple[Intent, str | None]:
        user = find_record("users.json", user_id)
        merged = {
            "currency_from": "MYR" if user_id == "aisha" else "MXN",
            "currency_to": "GBP" if user_id == "aisha" else "USD",
            "priority": user.get("priority", "balanced"),
            **(defaults or {}),
        }
        intent = classify_rule_based(text, now=now, defaults=merged)
        return intent, clarification_question(intent)

    def prepare(
        self,
        text: str,
        user_id: str = "aisha",
        document_text: str | None = None,
        now: datetime | None = None,
        preferences: Preferences | None = None,
    ) -> PreparedTransfer | dict[str, Any]:
        clock = now or datetime.now(timezone.utc)
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        intent, question = self.understand(text, user_id, clock)
        if intent.type.value == "OUT_OF_SCOPE":
            return {"intent": intent, "message": "SendSmart can compare or simulate cross-border tuition and living-cost payments; it cannot trade investments."}
        parsed = parse_document(document_text) if document_text else None
        if parsed:
            mapping = {"beneficiary_id": "beneficiary", "amount": "amount", "currency_to": "currency_to", "deadline": "deadline"}
            for source, target in mapping.items():
                if parsed.fields.get(source) is not None and not intent.slots.get(target):
                    intent.slots[target] = parsed.fields[source]
                    if target in intent.missing_slots:
                        intent.missing_slots.remove(target)
            question = clarification_question(intent)
        if intent.missing_slots or intent.ambiguities:
            return {"intent": intent, "clarification": question or clarification_question(intent), "executable": False}
        if intent.type.value in {"CHECK_STATUS", "CANCEL_PAYMENT", "CHANGE_PREFERENCE"}:
            return {"intent": intent, "plan": build_plan(intent, str(uuid.uuid4())), "executable": False}

        request_id = str(uuid.uuid4())
        beneficiary_id = str(intent.slots["beneficiary"])
        beneficiary = find_record("beneficiaries.json", beneficiary_id)
        if not beneficiary:
            return {"intent": intent, "clarification": "Please select a saved beneficiary.", "executable": False}
        deadline = intent.slots.get("deadline")
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline).date()
        request = PaymentRequest(
            request_id=request_id,
            user_id=user_id,
            amount=Decimal(str(intent.slots["amount"])),
            currency_from=str(intent.slots["currency_from"]),
            currency_to=str(intent.slots["currency_to"]),
            amount_mode=AmountMode(intent.slots["amount_mode"]),
            beneficiary_id=beneficiary_id,
            purpose=str(intent.slots["purpose"]),
            destination_country=beneficiary["country"],
            deadline=deadline,
            source_document="attached" if document_text else None,
        )
        plan = build_plan(intent, request_id)
        self.audit.append("PLAN_CREATED", "agent", request_id, "Deterministic plan created", plan.model_dump(mode="json"))
        start = time.perf_counter()
        fx = get_snapshot(allow_live=False)
        quotes = compare_routes(request, fx, quoted_at=clock)
        for quote in quotes:
            quote.deadline_ok = meets_deadline(quote.eta_business_days, request.deadline, clock)
        prefs = preferences or Preferences(priority=str(intent.slots.get("priority") or "balanced"))
        routes = rank_routes(quotes, prefs)
        if not routes:
            raise RuntimeError("No routes are available")
        selected = routes[0]
        elapsed = Decimal(str(time.perf_counter() - start))
        user = find_record("users.json", user_id)
        flags: list[InjectionFlag] = parsed.injection_flags if parsed else []
        supplied_fingerprint = str(parsed.fields.get("bank_fingerprint")) if parsed and parsed.fields.get("bank_fingerprint") else None
        sanctions = set(load_json("sanctioned_countries.json")["countries"])
        usd_equivalent = selected.quote.send_amount / fx.rates[request.currency_from]
        policy = evaluate(
            request,
            selected.quote,
            user,
            beneficiary,
            usd_equivalent,
            intent_type=intent.type,
            injection_flags=flags,
            supplied_bank_fingerprint=supplied_fingerprint,
            sanctioned_countries=sanctions,
            quote_stale=False,
            preferences=prefs,
        )
        explanation = explain_route(selected, quotes)
        if not numbers_match(explanation, selected.quote):
            explanation = explain_route(selected, quotes)
        bank = next(quote for quote in quotes if quote.provider_id == "bankwire")
        default = next(quote for quote in quotes if quote.provider_id == "swiftfox")
        value = build_value_report(
            request_id, selected.quote, bank, default,
            Decimal("1") / fx.rates[request.currency_from], quotes, elapsed,
            risks_blocked=policy.triggered_rules if not policy.allowed else [],
        )
        for step in plan.steps:
            if step.tool == "user_checkpoint":
                break
            step.status = StepStatus.DONE
        self.audit.append("POLICY_DECISION", "policy", request_id, policy.tier.value, policy.model_dump(mode="json"))
        return PreparedTransfer(
            intent, request, plan, fx, quotes, routes, selected, policy, beneficiary, user, prefs,
            explanation, value, beneficiary["bank_fingerprint"], elapsed,
        )

    def execute(self, prepared: PreparedTransfer, user_input: str, idempotency_key: str | None = None) -> dict[str, Any]:
        approve(prepared.plan, prepared.policy, user_input, prepared.request, prepared.beneficiary["name"])
        self.audit.append("PLAN_APPROVED", "user", prepared.request.request_id, "User approved plan and route")
        token = self.authority.mint(prepared.request, prepared.selected.quote, prepared.bank_fingerprint)
        receipt = self.executor.execute(
            prepared.request,
            prepared.selected.quote,
            prepared.bank_fingerprint,
            token,
            idempotency_key or prepared.request.request_id,
        )
        for step in prepared.plan.steps:
            if step.tool in {"user_checkpoint", "mint_token", "execute_sandbox", "report_result"}:
                step.status = StepStatus.DONE
        return {"receipt": receipt, "value_report": prepared.value_report.model_dump(mode="json"), "plan": prepared.plan.model_dump(mode="json")}

    def reject(self, prepared: PreparedTransfer) -> Plan:
        plan = reject(prepared.plan)
        self.audit.append("PLAN_REJECTED", "user", prepared.request.request_id, "User rejected plan; nothing executed")
        return plan

