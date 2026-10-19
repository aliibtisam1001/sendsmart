from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from sendsmart.agent.orchestrator import PreparedTransfer, SendSmartOrchestrator  # noqa: E402
from sendsmart.control.user_control import expected_approval_phrase  # noqa: E402
from sendsmart.models import Tier  # noqa: E402


st.set_page_config(page_title="SendSmart", page_icon="🌐", layout="wide")
st.markdown(
    """
    <style>
    .sandbox {background:#3b0764;color:#fff;padding:.65rem 1rem;border-radius:.6rem;font-weight:700;letter-spacing:.04em}
    .step {padding:.55rem .7rem;margin:.25rem 0;border:1px solid #ddd;border-radius:.45rem}
    .muted {color:#666;font-size:.9rem}
    </style>
    <div class="sandbox">SANDBOX / MOCK DATA — NO REAL PRICES OR FUNDS</div>
    """,
    unsafe_allow_html=True,
)
st.title("SendSmart")
st.caption("A security-first cross-border and student finance assistant. The LLM explains; deterministic code decides.")

if "agent" not in st.session_state:
    st.session_state.agent = SendSmartOrchestrator(ROOT / "evidence" / "ui_audit_log.jsonl")
if "prepared" not in st.session_state:
    st.session_state.prepared = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None

agent: SendSmartOrchestrator = st.session_state.agent


def render_plan(prepared: PreparedTransfer) -> None:
    st.subheader("Visible plan")
    icons = {"pending": "○", "running": "◉", "done": "✓", "failed": "✕", "skipped": "–"}
    for step in prepared.plan.steps:
        status = step.status.value
        checkpoint = " — USER CHECKPOINT" if step.requires_user_checkpoint else ""
        st.markdown(
            f"<div class='step'><b>{icons[status]} {step.id}. {step.action}{checkpoint}</b><br>"
            f"<span class='muted'>{step.rationale}</span></div>",
            unsafe_allow_html=True,
        )


chat_tab, compare_tab, attack_tab, audit_tab, value_tab, about_tab = st.tabs(
    ["Chat & Plan", "Compare", "Attack Lab", "Audit Log", "Value", "About / Limitations"]
)

with chat_tab:
    persona = st.selectbox("Persona", ["Aisha (MY → UK)", "Carlos (MX → US)"])
    user_id = "aisha" if persona.startswith("Aisha") else "carlos"
    examples = {
        "Tuition": "Pay GBP 9000 tuition to Northbridge University from MYR by 27 October 2026",
        "Living costs": "Send MYR 300 from MYR to GBP to my landlord for living costs",
        "Compare only": "Compare GBP 500 options from MYR to GBP for my landlord",
        "Needs clarification": "Send some money to my landlord",
    }
    cols = st.columns(len(examples))
    for column, (label, prompt) in zip(cols, examples.items()):
        if column.button(label, use_container_width=True):
            st.session_state.prompt = prompt
    prompt = st.text_area("What would you like to do?", value=st.session_state.get("prompt", examples["Tuition"]), height=100)
    uploaded = st.file_uploader("Optional invoice text", type=["txt"])
    document_text = uploaded.getvalue().decode("utf-8", errors="replace") if uploaded else None
    if st.button("Understand and create plan", type="primary"):
        st.session_state.prepared = agent.prepare(prompt, user_id=user_id, document_text=document_text)
        st.session_state.last_result = None

    prepared = st.session_state.prepared
    if isinstance(prepared, dict):
        intent = prepared.get("intent")
        if intent:
            st.info(f"Intent: {intent.type.value} · confidence {intent.confidence}")
        if prepared.get("clarification"):
            st.warning(prepared["clarification"])
        if prepared.get("message"):
            st.info(prepared["message"])
    elif isinstance(prepared, PreparedTransfer):
        st.write(f"Intent: **{prepared.intent.type.value}** · confidence **{prepared.intent.confidence}**")
        render_plan(prepared)
        tier_colors = {Tier.T1_ADVISE: "blue", Tier.T2_CONFIRM: "green", Tier.T3_APPROVE: "orange", Tier.BLOCKED: "red"}
        getattr(st, "error" if prepared.policy.tier == Tier.BLOCKED else "info")(
            f"{prepared.policy.tier.value}: {prepared.policy.required_user_action}"
        )
        st.write(prepared.explanation)
        if prepared.policy.triggered_rules:
            st.caption("Rules: " + ", ".join(prepared.policy.triggered_rules))
        if prepared.policy.tier == Tier.T2_CONFIRM:
            if st.button("Confirm simulated payment"):
                st.session_state.last_result = agent.execute(prepared, "CONFIRM")
        elif prepared.policy.tier == Tier.T3_APPROVE:
            expected = expected_approval_phrase(prepared.request, prepared.beneficiary["name"])
            phrase = st.text_input("Typed approval", placeholder=expected)
            if st.button("Approve simulated payment"):
                try:
                    st.session_state.last_result = agent.execute(prepared, phrase)
                except PermissionError as exc:
                    st.error(str(exc))
        reject_col, stop_col, reset_col = st.columns(3)
        if reject_col.button("Reject plan"):
            agent.reject(prepared); st.warning("Plan rejected. Nothing executed.")
        if stop_col.button("STOP AGENT", type="primary"):
            agent.executor.set_kill_switch(True); st.error("Kill switch active.")
        if reset_col.button("Reset STOP AGENT"):
            agent.executor.set_kill_switch(False); st.success("Kill switch reset.")

    if st.session_state.last_result:
        receipt = st.session_state.last_result["receipt"]
        st.success(f"Sandbox receipt received: {receipt['receipt_id']} ({receipt['status']})")
        st.json(receipt)
        if receipt["status"] == "PENDING" and st.button("Cancel during hold window"):
            try:
                cancelled = agent.executor.cancel(receipt["request_id"])
                st.session_state.last_result["receipt"] = cancelled
                st.success("Simulated payment cancelled.")
            except Exception as exc:
                st.error(str(exc))

with compare_tab:
    prepared = st.session_state.prepared
    if isinstance(prepared, PreparedTransfer):
        rows = []
        for quote in prepared.quotes:
            rows.append({
                "Recommended": "✓" if quote.provider_id == prepared.selected.quote.provider_id else "",
                "Provider (MOCK)": quote.provider_name,
                f"Send ({quote.send_currency})": quote.send_amount,
                f"Recipient ({quote.receive_currency})": quote.recipient_amount,
                "Fee + FX markup": quote.total_cost,
                "ETA business days": quote.eta_business_days,
                "Deadline OK": quote.deadline_ok,
            })
        st.dataframe(rows, hide_index=True, use_container_width=True)
        st.subheader("Why this route")
        st.write(prepared.explanation)
    else:
        st.info("Create a plan in Chat & Plan to compare routes.")

with attack_tab:
    st.write("Run prebuilt attacks against the same deterministic policy boundary.")
    attack_files = {
        "Injection invoice": "injection_invoice.txt",
        "Changed bank details": "tampered_invoice.txt",
    }
    for label, filename in attack_files.items():
        if st.button(label):
            text = (ROOT / "data" / "sample_invoices" / filename).read_text(encoding="utf-8")
            result = agent.prepare("Pay the tuition invoice from MYR", document_text=text)
            st.session_state.attack_result = result
    if st.button("Unverified beneficiary"):
        st.session_state.attack_result = agent.prepare("Send GBP 300 from MYR to GBP to new beneficiary")
    result = st.session_state.get("attack_result")
    if isinstance(result, PreparedTransfer):
        st.error(f"{result.policy.tier.value}: {', '.join(result.policy.triggered_rules)}")
        st.json(result.policy.model_dump(mode="json"))

with audit_tab:
    path = agent.audit.path
    st.metric("Hash chain", "VERIFIED" if agent.audit.verify_chain() else "TAMPERED")
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    st.dataframe(rows, use_container_width=True)
    st.download_button("Download my audit data", data=json.dumps(rows, indent=2), file_name="sendsmart-audit.json", mime="application/json")

with value_tab:
    prepared = st.session_state.prepared
    if isinstance(prepared, PreparedTransfer):
        value = prepared.value_report
        col1, col2, col3 = st.columns(3)
        col1.metric("Savings vs bank (MOCK USD)", value.savings_vs_bank_usd)
        col2.metric("Deadline risks avoided", value.deadline_risk_avoided)
        col3.metric("Manual comparison estimate", f"{value.estimated_manual_minutes} min")
        st.json(value.model_dump(mode="json"))
    metrics_path = ROOT / "evidence" / "metrics.json"
    if metrics_path.exists():
        st.subheader("Scenario aggregate")
        st.json(json.loads(metrics_path.read_text(encoding="utf-8")))

with about_tab:
    st.markdown(
        """
        ### What this demonstrates
        SendSmart separates language understanding from authorization. It uses deterministic Decimal math,
        permission tiers, a user checkpoint, a five-minute request-bound HMAC token, replay protection,
        a kill switch, and a hash-chained audit log.

        ### Important limitations
        All providers, prices, sanctions, beneficiaries, FX rates and payments are fictional or simulated.
        This prototype is not a bank, payment service, KYC/AML system, or financial adviser. Its regex-based
        injection detector is illustrative and bypassable. Never use it to move real funds.
        """
    )

