from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sendsmart.models import AuditEvent


GENESIS_HASH = "0" * 64


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return GENESIS_HASH
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return json.loads(lines[-1])["hash"] if lines else GENESIS_HASH

    def append(
        self,
        event_type: str,
        actor: str,
        request_id: str,
        summary: str,
        decision: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> AuditEvent:
        occurred_at = timestamp or datetime.now(timezone.utc)
        base = {
            "timestamp": occurred_at.isoformat().replace("+00:00", "Z"),
            "event_type": event_type,
            "actor": actor,
            "request_id": request_id,
            "summary": summary,
            "decision": decision or {},
            "prev_hash": self._last_hash(),
        }
        digest = hashlib.sha256(_canonical(base).encode("utf-8")).hexdigest()
        event = AuditEvent(**base, hash=digest)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(event.model_dump_json() + "\n")
        return event

    def verify_chain(self) -> bool:
        if not self.path.exists():
            return True
        expected_prev = GENESIS_HASH
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            stored_hash = item.pop("hash", None)
            if item.get("prev_hash") != expected_prev:
                return False
            calculated = hashlib.sha256(_canonical(item).encode("utf-8")).hexdigest()
            if not stored_hash or not hmac_safe_equal(stored_hash, calculated):
                return False
            expected_prev = stored_hash
        return True


def hmac_safe_equal(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)

