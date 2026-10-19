from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntentType(str, Enum):
    PAY_TUITION = "PAY_TUITION"
    SEND_LIVING_COSTS = "SEND_LIVING_COSTS"
    COMPARE_ONLY = "COMPARE_ONLY"
    CHECK_STATUS = "CHECK_STATUS"
    CANCEL_PAYMENT = "CANCEL_PAYMENT"
    CHANGE_PREFERENCE = "CHANGE_PREFERENCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class AmountMode(str, Enum):
    SEND = "SEND"
    RECIPIENT = "RECIPIENT"


class Intent(StrictModel):
    type: IntentType
    confidence: Decimal = Field(ge=0, le=1)
    slots: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class PaymentRequest(StrictModel):
    request_id: str
    user_id: str
    amount: Decimal = Field(gt=0)
    currency_from: str = Field(min_length=3, max_length=3)
    currency_to: str = Field(min_length=3, max_length=3)
    amount_mode: AmountMode = AmountMode.SEND
    beneficiary_id: str
    purpose: str
    destination_country: str
    deadline: date | None = None
    source_document: str | None = None


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(StrictModel):
    id: int
    action: str
    tool: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    requires_user_checkpoint: bool = False
    rationale: str


class Plan(StrictModel):
    request_id: str
    intent_type: IntentType
    steps: list[PlanStep]
    approved: bool = False


class Quote(StrictModel):
    provider_id: str
    provider_name: str
    send_amount: Decimal
    send_currency: str
    recipient_amount: Decimal
    receive_currency: str
    fee: Decimal
    fx_markup_cost: Decimal
    total_cost: Decimal
    rate: Decimal
    eta_business_days: int
    reliability: Decimal
    quoted_at: datetime
    deadline_ok: bool = True
    is_mock: bool = True


class Route(StrictModel):
    quote: Quote
    score: Decimal
    rank: int
    rationale: list[str] = Field(default_factory=list)


class Tier(str, Enum):
    T1_ADVISE = "T1_ADVISE"
    T2_CONFIRM = "T2_CONFIRM"
    T3_APPROVE = "T3_APPROVE"
    BLOCKED = "BLOCKED"


class PolicyDecision(StrictModel):
    tier: Tier
    allowed: bool
    required_user_action: str
    reasons: list[str] = Field(default_factory=list)
    triggered_rules: list[str] = Field(default_factory=list)


class ExecutionToken(StrictModel):
    token_id: str
    request_hash: str
    issued_at: datetime
    expires_at: datetime
    signature: str


class AuditEvent(StrictModel):
    timestamp: datetime
    event_type: str
    actor: str
    request_id: str
    summary: str
    decision: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    hash: str


class Preferences(StrictModel):
    priority: str = "balanced"
    cost_weight: Decimal = Decimal("0.5")
    speed_weight: Decimal = Decimal("0.3")
    reliability_weight: Decimal = Decimal("0.2")
    max_fee_percent: Decimal = Decimal("5")
    preferred_providers: list[str] = Field(default_factory=list)
    notify_risks: bool = True
    personal_limit_usd: Decimal = Decimal("10000")


class ValueReport(StrictModel):
    request_id: str
    selected_provider: str
    savings_vs_bank_send: Decimal
    savings_vs_bank_usd: Decimal
    savings_vs_bank_percent: Decimal
    savings_vs_default_send: Decimal
    savings_vs_default_usd: Decimal
    savings_vs_default_percent: Decimal
    deadline_risk_avoided: int
    comparison_seconds: Decimal
    estimated_manual_minutes: Decimal
    risk_events_blocked: list[str] = Field(default_factory=list)
    is_mock: bool = True

