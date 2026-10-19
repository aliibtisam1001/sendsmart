from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sendsmart.config import settings
from sendsmart.models import ExecutionToken, PaymentRequest, Quote
from sendsmart.security.audit import AuditLog
from sendsmart.security.tokens import TokenAuthority


class ExecutionRejected(RuntimeError):
    pass


class SandboxExecutor:
    def __init__(self, authority: TokenAuthority, audit: AuditLog, cancel_window_seconds: int | None = None):
        self.authority = authority
        self.audit = audit
        self.cancel_window_seconds = cancel_window_seconds or settings.cancel_window_seconds
        self.used_tokens: set[str] = set()
        self.receipts_by_key: dict[str, dict[str, Any]] = {}
        self.stopped = False

    def set_kill_switch(self, stopped: bool, actor: str = "user") -> None:
        self.stopped = stopped
        self.audit.append("KILL_SWITCH", actor, "global", "STOP AGENT engaged" if stopped else "STOP AGENT reset")

    def execute(
        self,
        request: PaymentRequest,
        quote: Quote,
        beneficiary_fingerprint: str,
        token: ExecutionToken | None,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        if self.stopped:
            raise ExecutionRejected("KILL_SWITCH_ACTIVE")
        if idempotency_key in self.receipts_by_key:
            return self.receipts_by_key[idempotency_key]
        if token is None:
            raise ExecutionRejected("MISSING_EXECUTION_TOKEN")
        if token.token_id in self.used_tokens:
            raise ExecutionRejected("TOKEN_REPLAY")
        if not self.authority.verify(token, request, quote, beneficiary_fingerprint, current):
            raise ExecutionRejected("INVALID_OR_EXPIRED_TOKEN")
        receipt = {
            "receipt_id": f"sandbox-{uuid.uuid4()}",
            "request_id": request.request_id,
            "provider": quote.provider_name,
            "status": "PENDING",
            "send_amount": str(quote.send_amount),
            "send_currency": quote.send_currency,
            "recipient_amount": str(quote.recipient_amount),
            "receive_currency": quote.receive_currency,
            "created_at": current.isoformat(),
            "cancel_until": (current + timedelta(seconds=self.cancel_window_seconds)).isoformat(),
            "disclosure": "SIMULATED PAYMENT - NO REAL FUNDS MOVED",
        }
        self.used_tokens.add(token.token_id)
        self.receipts_by_key[idempotency_key] = receipt
        self.audit.append("PAYMENT_EXECUTED", "sandbox", request.request_id, "Simulated payment accepted", receipt)
        return receipt

    def cancel(self, idempotency_key: str, now: datetime | None = None) -> dict[str, Any]:
        if self.stopped:
            raise ExecutionRejected("KILL_SWITCH_ACTIVE")
        if idempotency_key not in self.receipts_by_key:
            raise ExecutionRejected("PAYMENT_NOT_FOUND")
        receipt = self.receipts_by_key[idempotency_key]
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        if current > datetime.fromisoformat(receipt["cancel_until"]):
            raise ExecutionRejected("CANCEL_WINDOW_CLOSED")
        receipt["status"] = "CANCELLED"
        self.audit.append("PAYMENT_CANCELLED", "user", receipt["request_id"], "Payment cancelled during hold window")
        return receipt

