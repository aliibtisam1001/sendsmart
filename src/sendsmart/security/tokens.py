from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sendsmart.config import settings
from sendsmart.models import ExecutionToken, PaymentRequest, Quote


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, Decimal)):
        return str(value)
    raise TypeError(f"Unsupported value: {type(value)!r}")


def request_binding(request: PaymentRequest, quote: Quote, beneficiary_fingerprint: str) -> str:
    payload = {
        "request": request.model_dump(mode="json"),
        "route": quote.model_dump(mode="json"),
        "beneficiary_fingerprint": beneficiary_fingerprint,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TokenAuthority:
    def __init__(self, secret: str | None = None, ttl_seconds: int | None = None):
        self._secret = (secret or settings.token_secret).encode("utf-8")
        self._ttl = ttl_seconds or settings.token_ttl_seconds

    def _signature(self, token_id: str, binding: str, issued_at: datetime, expires_at: datetime) -> str:
        material = "|".join((token_id, binding, issued_at.isoformat(), expires_at.isoformat()))
        return hmac.new(self._secret, material.encode("utf-8"), hashlib.sha256).hexdigest()

    def mint(
        self,
        request: PaymentRequest,
        quote: Quote,
        beneficiary_fingerprint: str,
        now: datetime | None = None,
    ) -> ExecutionToken:
        issued = now or datetime.now(timezone.utc)
        if issued.tzinfo is None:
            issued = issued.replace(tzinfo=timezone.utc)
        expires = issued + timedelta(seconds=self._ttl)
        token_id = str(uuid.uuid4())
        binding = request_binding(request, quote, beneficiary_fingerprint)
        return ExecutionToken(
            token_id=token_id,
            request_hash=binding,
            issued_at=issued,
            expires_at=expires,
            signature=self._signature(token_id, binding, issued, expires),
        )

    def verify(
        self,
        token: ExecutionToken,
        request: PaymentRequest,
        quote: Quote,
        beneficiary_fingerprint: str,
        now: datetime | None = None,
    ) -> bool:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        expected_binding = request_binding(request, quote, beneficiary_fingerprint)
        expected_signature = self._signature(token.token_id, token.request_hash, token.issued_at, token.expires_at)
        return (
            token.request_hash == expected_binding
            and current <= token.expires_at
            and hmac.compare_digest(token.signature, expected_signature)
        )

