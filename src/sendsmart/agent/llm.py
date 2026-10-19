from __future__ import annotations

import os
from typing import Protocol

from sendsmart.agent.intent import classify_rule_based
from sendsmart.models import Intent


class IntentModel(Protocol):
    def classify(self, text: str) -> Intent: ...


class RuleBasedModel:
    def classify(self, text: str) -> Intent:
        return classify_rule_based(text)


class AnthropicModel:
    """Optional adapter. Any failure is deliberately handled by the fallback."""

    def __init__(self) -> None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        from anthropic import Anthropic

        self.client = Anthropic()

    def classify(self, text: str) -> Intent:
        raise NotImplementedError("The demo uses the deterministic classifier; add provider structured output here.")


def classify_with_fallback(text: str, primary: IntentModel | None = None) -> Intent:
    if primary is not None:
        try:
            return primary.classify(text)
        except Exception:
            pass
    return RuleBasedModel().classify(text)

