from __future__ import annotations

from sendsmart.models import Intent, IntentType, Plan, PlanStep


GUARDRAIL_TOOLS = ["validate_request", "verify_beneficiary", "check_policy", "user_checkpoint"]


def build_plan(intent: Intent, request_id: str) -> Plan:
    if intent.type == IntentType.OUT_OF_SCOPE:
        return Plan(request_id=request_id, intent_type=intent.type, steps=[])
    if intent.type == IntentType.CANCEL_PAYMENT:
        specs = [
            ("Locate sandbox payment", "lookup_payment", False),
            ("Confirm cancellation", "user_checkpoint", True),
            ("Cancel within hold window", "cancel_payment", False),
        ]
    elif intent.type in (IntentType.CHECK_STATUS, IntentType.CHANGE_PREFERENCE):
        specs = [("Validate request", "validate_request", False), ("Apply read-only request", "read_or_update", False)]
    else:
        specs = [
            ("Validate the structured request", "validate_request", False),
            ("Verify beneficiary and bank fingerprint", "verify_beneficiary", False),
            ("Fetch FX and check freshness", "get_fx", False),
            ("Compare deterministic route costs", "compare_routes", False),
            ("Rank feasible routes", "rank_routes", False),
            ("Recommend and explain", "explain", False),
        ]
        if intent.type != IntentType.COMPARE_ONLY:
            specs.extend([
                ("Run policy guardrails", "check_policy", False),
                ("User approves plan and route", "user_checkpoint", True),
                ("Mint a bound execution token", "mint_token", False),
                ("Execute in the sandbox", "execute_sandbox", False),
                ("Return receipt, audit and value report", "report_result", False),
            ])
    steps = [
        PlanStep(
            id=index,
            action=action,
            tool=tool,
            depends_on=[index - 1] if index > 1 else [],
            requires_user_checkpoint=checkpoint,
            rationale=_rationale(tool),
        )
        for index, (action, tool, checkpoint) in enumerate(specs, start=1)
    ]
    plan = Plan(request_id=request_id, intent_type=intent.type, steps=steps)
    validate_plan(plan)
    return plan


def _rationale(tool: str) -> str:
    explanations = {
        "validate_request": "Reject missing or malformed values before comparison.",
        "verify_beneficiary": "Prevent redirection to unknown or changed accounts.",
        "get_fx": "Use a traceable rate and reject stale quotes.",
        "compare_routes": "Compute every amount in deterministic Decimal arithmetic.",
        "rank_routes": "Respect cost, speed, reliability and deadline preferences.",
        "explain": "Show the user why the route was selected.",
        "check_policy": "Code, not the language model, determines permission tier.",
        "user_checkpoint": "Nothing executes until the user explicitly approves.",
        "mint_token": "Bind authorization to this exact request and route.",
        "execute_sandbox": "Move no real funds; accept only a valid one-time token.",
        "report_result": "Claim success only after a sandbox receipt exists.",
    }
    return explanations.get(tool, "Perform the requested controlled operation.")


def validate_plan(plan: Plan) -> None:
    tools = [step.tool for step in plan.steps]
    if plan.intent_type in (IntentType.PAY_TUITION, IntentType.SEND_LIVING_COSTS):
        positions = []
        for required in GUARDRAIL_TOOLS:
            if required not in tools:
                raise ValueError(f"Mandatory guardrail step missing: {required}")
            positions.append(tools.index(required))
        if positions != sorted(positions):
            raise ValueError("Mandatory guardrail steps are out of order")
        if tools.index("check_policy") > tools.index("mint_token") or tools.index("user_checkpoint") > tools.index("mint_token"):
            raise ValueError("Token issuance cannot precede policy and approval")


def recovery_plan(plan: Plan, failed_tool: str) -> Plan:
    recovery = {
        "get_fx": ("Refresh stale FX quote", "get_fx"),
        "verify_beneficiary": ("Ask user to verify beneficiary outside SendSmart", "user_checkpoint"),
        "rank_routes": ("Show deadline alternatives", "explain"),
    }.get(failed_tool, ("Ask the user how to proceed", "user_checkpoint"))
    return Plan(
        request_id=plan.request_id,
        intent_type=plan.intent_type,
        steps=[PlanStep(id=1, action=recovery[0], tool=recovery[1], requires_user_checkpoint=recovery[1] == "user_checkpoint", rationale="Recover safely without bypassing policy.")],
    )

