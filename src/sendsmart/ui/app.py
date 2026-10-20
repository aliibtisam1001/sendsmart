from __future__ import annotations

import json
import sys
import tempfile
import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from sendsmart.agent.orchestrator import PreparedTransfer, SendSmartOrchestrator  # noqa: E402
from sendsmart.control.user_control import expected_approval_phrase  # noqa: E402
from sendsmart.core.advisory import CorridorPlan, build_corridor_plan  # noqa: E402
from sendsmart.core.benchmarks import find_world_bank_corridor, load_world_bank_snapshot  # noqa: E402
from sendsmart.core.decision import assess_quote, build_decision_report, decision_status  # noqa: E402
from sendsmart.core.destinations import load_destination_dataset, load_destinations  # noqa: E402
from sendsmart.core.fx import get_public_snapshot  # noqa: E402
from sendsmart.integrations.sanctions import load_un_snapshot, screen_un_name  # noqa: E402
from sendsmart.integrations.wise import WiseQuote, fetch_wise_quotes  # noqa: E402
from sendsmart.models import AmountMode, Tier  # noqa: E402


st.set_page_config(page_title="SendSmart | Global study payments", page_icon="🌏", layout="wide")
st.markdown(
    """
    <style>
    :root {--ss-ink:#111827;--ss-muted:#667085;--ss-purple:#5b21b6;--ss-violet:#7c3aed;--ss-navy:#0c1435;--ss-border:#dfe3ef;--ss-surface:#f7f8fc;}
    html, body, [class*="css"] {font-family:"Source Sans Pro","Segoe UI",sans-serif;}
    .stApp {background:linear-gradient(145deg,#f8f9fd 0%,#f2f5fb 52%,#f8f5ff 100%);color:var(--ss-ink)}
    .block-container {max-width:1328px;padding-top:1.1rem;padding-bottom:4rem}
    .topbar {display:flex;align-items:center;justify-content:space-between;padding:.2rem .15rem 1rem}
    .brand {display:flex;align-items:center;gap:.72rem}.brand-mark{display:grid;place-items:center;width:2.3rem;height:2.3rem;border-radius:.75rem;background:var(--ss-purple);color:white;font-weight:800;font-size:1.1rem;box-shadow:0 8px 20px rgba(91,33,182,.25)}
    .brand-copy b{display:block;font-size:1.05rem;line-height:1}.brand-copy span{font-size:.74rem;color:var(--ss-muted)}
    .mode-pill{padding:.42rem .72rem;border-radius:999px;background:#e9fbf3;color:#067647;font-size:.78rem;font-weight:700;border:1px solid #c9f1df}
    .hero {display:grid;grid-template-columns:minmax(0,1.6fr) minmax(260px,.72fr);gap:2rem;align-items:center;padding:2rem 2.2rem;border-radius:1.75rem;background:linear-gradient(120deg,#0c1435 0%,#151b47 60%,#31206b 100%);color:white;box-shadow:0 24px 60px rgba(15,23,42,.16);margin-bottom:1.2rem;overflow:hidden}
    .hero-kicker{display:inline-block;padding:.36rem .68rem;border-radius:999px;background:#7c3aed;color:white;font-size:.72rem;font-weight:800;letter-spacing:.04em;margin-bottom:.85rem}
    .hero h1{font-size:clamp(2.1rem,4vw,3.35rem);line-height:1.02;letter-spacing:-.035em;margin:0 0 .72rem;color:white;max-width:760px}.hero p{font-size:1.05rem;line-height:1.55;margin:0;color:#d8def5;max-width:760px}
    .hero-proof{padding:1.05rem 1.15rem;border:1px solid rgba(255,255,255,.18);border-radius:1.15rem;background:rgba(255,255,255,.09);backdrop-filter:blur(8px)}
    .hero-proof b{display:block;margin:.45rem 0 .6rem;font-size:1.02rem}.proof-status{font-size:.78rem;color:#d8def5}.proof-status:before{content:"";display:inline-block;width:.5rem;height:.5rem;border-radius:50%;background:#22d3ee;margin-right:.45rem}
    .proof-tags{display:flex;flex-wrap:wrap;gap:.45rem}.proof-tags span{padding:.32rem .55rem;border-radius:999px;background:white;color:#111827;font-size:.72rem;font-weight:700}
    .notice {display:flex;gap:.8rem;align-items:flex-start;padding:.9rem 1rem;border:1px solid #fed7aa;border-radius:1rem;background:#fffaf4;color:#7c2d12;margin:.2rem 0 1.25rem;box-shadow:0 8px 24px rgba(124,45,18,.04)}
    .notice strong{color:#9a3412}.success-card{padding:1.05rem 1.2rem;border:1px solid #a7f3d0;border-radius:1rem;background:linear-gradient(135deg,#ecfdf5,#f7fffb)}
    .step {padding:.7rem .82rem;margin:.42rem 0;border:1px solid var(--ss-border);border-radius:.75rem;background:white;box-shadow:0 3px 12px rgba(15,23,42,.035)}
    .muted {color:#64748b;font-size:.88rem}
    .flow{display:grid;grid-template-columns:repeat(4,1fr);gap:.55rem;margin:.2rem 0 1rem}.flow span{padding:.55rem .65rem;text-align:center;border-radius:999px;background:#f4f5fa;color:#667085;font-size:.8rem;font-weight:700}.flow span:first-child{background:var(--ss-purple);color:white}
    .section-label{font-size:.74rem;font-weight:800;letter-spacing:.06em;color:var(--ss-purple);margin-bottom:.1rem}.section-subtitle{color:var(--ss-muted);font-size:.93rem;margin-bottom:.4rem}
    [data-testid="stForm"] {background:rgba(255,255,255,.94);border:1px solid var(--ss-border);border-radius:1.35rem;padding:1.25rem 1.35rem 1.4rem;box-shadow:0 16px 46px rgba(15,23,42,.06)}
    [data-testid="stMetric"] {background:rgba(255,255,255,.9);border:1px solid var(--ss-border);padding:.85rem;border-radius:1rem;box-shadow:0 6px 18px rgba(15,23,42,.035)}
    [data-testid="stTabs"] [data-baseweb="tab-list"]{gap:.35rem;background:white;border:1px solid var(--ss-border);padding:.35rem;border-radius:1rem;box-shadow:0 8px 24px rgba(15,23,42,.04)}
    [data-testid="stTabs"] [data-baseweb="tab"]{border-radius:.72rem;padding:.5rem .82rem}
    [data-testid="stTabs"] [aria-selected="true"]{background:#efe9ff;color:var(--ss-purple)}
    .stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{border-radius:999px;font-weight:700;min-height:2.75rem;transition:transform .16s ease,box-shadow .16s ease}
    .stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover{transform:translateY(-1px);box-shadow:0 10px 24px rgba(91,33,182,.16)}
    [data-testid="stFormSubmitButton"]>button{background:linear-gradient(90deg,#5b21b6,#7c3aed);border:0;color:white}
    @media(max-width:760px){.hero{grid-template-columns:1fr;padding:1.45rem}.hero h1{font-size:2.25rem}.topbar{align-items:flex-start}.flow{grid-template-columns:1fr 1fr}.block-container{padding-left:1rem;padding-right:1rem}}
    </style>
    <div class="topbar"><div class="brand"><div class="brand-mark">S</div><div class="brand-copy"><b>SendSmart</b><span>Student payment intelligence</span></div></div><div class="mode-pill">● Advisory mode</div></div>
    <div class="hero"><div><span class="hero-kicker">BUILT FOR GLOBAL STUDENTS</span><h1>Know what arrives before you send.</h1>
      <p>Compare a public FX reference, provider preview, fees, timing and safety checks in one explainable plan.</p></div>
      <div class="hero-proof"><span class="proof-status">Data health: ready</span><b>Frankfurter · ECB rates</b><div class="proof-tags"><span>50 destinations</span><span>No money moved</span></div></div>
    </div>
    <div class="notice"><span>🛡️</span><div><strong>Clear safety boundary:</strong> the planner uses public data and may request a live Wise preview, but it cannot execute a transfer. The Safe execution demo is simulated.</div></div>
    """,
    unsafe_allow_html=True,
)

destinations = load_destinations()
destination_data = load_destination_dataset()
by_iso = {item.iso3: item for item in destinations}
options = [item.iso3 for item in destinations]

STATE_SCHEMA_VERSION = 3
if st.session_state.get("state_schema_version") != STATE_SCHEMA_VERSION:
    # Streamlit preserves Python objects across hot reloads. Clear only the
    # planner fields whose dataclass shape may have changed between versions.
    for key in (
        "corridor_plan",
        "wise_quotes",
        "wise_error",
        "corridor_benchmark",
        "sanctions_matches",
        "screened_name",
    ):
        st.session_state.pop(key, None)
    st.session_state.state_schema_version = STATE_SCHEMA_VERSION

if "agent" not in st.session_state:
    audit_dir = Path(tempfile.gettempdir()) / "sendsmart-audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    st.session_state.agent = SendSmartOrchestrator(audit_dir / f"session-{uuid.uuid4()}.jsonl")
if "prepared" not in st.session_state:
    st.session_state.prepared = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "corridor_plan" not in st.session_state:
    st.session_state.corridor_plan = None
if "wise_quotes" not in st.session_state:
    st.session_state.wise_quotes = []
if "wise_error" not in st.session_state:
    st.session_state.wise_error = None
if "corridor_benchmark" not in st.session_state:
    st.session_state.corridor_benchmark = None
if "sanctions_matches" not in st.session_state:
    st.session_state.sanctions_matches = []
if "screened_name" not in st.session_state:
    st.session_state.screened_name = ""
if "planner_origin" not in st.session_state:
    st.session_state.planner_origin = "CHN"
if "planner_destination" not in st.session_state:
    st.session_state.planner_destination = "GBR"
if "planner_amount" not in st.session_state:
    st.session_state.planner_amount = 25000.0

agent: SendSmartOrchestrator = st.session_state.agent


def option_label(iso3: str) -> str:
    return by_iso[iso3].label


def choose_wise_quote(quotes: list[WiseQuote], priority: str) -> WiseQuote | None:
    if not quotes:
        return None
    if priority == "fastest":
        return min(quotes, key=lambda quote: (quote.estimated_delivery is None, quote.estimated_delivery, quote.fee))
    if priority == "cheapest":
        return min(quotes, key=lambda quote: (quote.fee, -quote.target_amount))
    bank_options = [quote for quote in quotes if quote.pay_in == "BANK_TRANSFER"]
    return min(bank_options or quotes, key=lambda quote: (quote.fee, -quote.target_amount))


def recommendation_reason(quote: WiseQuote, priority: str) -> str:
    route = f"{quote.pay_in.replace('_', ' ').title()} to {quote.pay_out.replace('_', ' ').title()}"
    if priority == "fastest":
        return f"{route} has the earliest provider ETA among the enabled options."
    if priority == "cheapest":
        return f"{route} has the lowest disclosed fee among the enabled options."
    return f"{route} favors a bank-transfer route with a low disclosed fee for a balanced choice."


def reference_amounts(plan: CorridorPlan) -> tuple[Decimal, Decimal]:
    """Calculate an always-available, before-fees reference conversion."""

    if plan.request.amount_mode == AmountMode.SEND:
        source = plan.request.amount
        target = source * plan.reference_rate
    else:
        target = plan.request.amount
        source = target / plan.reference_rate
    money = Decimal("0.01")
    return source.quantize(money, rounding=ROUND_HALF_UP), target.quantize(money, rounding=ROUND_HALF_UP)


def wise_rows(quotes: list[WiseQuote]) -> list[dict[str, str]]:
    return [
        {
            "Provider": "Wise",
            "Pay in": quote.pay_in.replace("_", " ").title(),
            "Pay out": quote.pay_out.replace("_", " ").title(),
            f"Send ({quote.source_currency})": f"{quote.source_amount:,.2f}",
            f"Recipient gets ({quote.target_currency})": f"{quote.target_amount:,.2f}",
            f"Fee ({quote.source_currency})": f"{quote.fee:,.2f}",
            "Provider ETA": quote.estimated_delivery_text,
            "Status": "Preview only — not executable",
        }
        for quote in quotes
    ]


def render_execution_plan(prepared: PreparedTransfer) -> None:
    icons = {"pending": "○", "running": "◉", "done": "✓", "failed": "✕", "skipped": "–"}
    for step in prepared.plan.steps:
        status = step.status.value
        checkpoint = " · USER CHECKPOINT" if step.requires_user_checkpoint else ""
        st.markdown(
            f"<div class='step'><b>{icons[status]} {step.id}. {step.action}{checkpoint}</b><br>"
            f"<span class='muted'>{step.rationale}</span></div>",
            unsafe_allow_html=True,
        )


builder_tab, execution_tab, safety_tab, evidence_tab, data_tab, limits_tab = st.tabs(
    ["🌐 Plan", "🔐 Sandbox task", "🧪 Attack lab", "🏆 Evidence", "📊 Sources", "ℹ️ Limits"]
)

with builder_tab:
    st.markdown("<div class='section-label'>BUILD YOUR CORRIDOR</div>", unsafe_allow_html=True)
    st.subheader("Plan a student payment")
    st.markdown(
        "<div class='section-subtitle'>Choose any two of the top 50 study destinations. SendSmart verifies the public rate, checks a provider preview, and explains the evidence.</div>"
        "<div class='flow'><span>1 · Corridor</span><span>2 · Amount</span><span>3 · Priorities</span><span>4 · Review</span></div>",
        unsafe_allow_html=True,
    )
    st.caption("Popular student routes")
    preset_columns = st.columns(3)
    presets = [
        ("🇨🇳 China → UK tuition", "CHN", "GBR", 25000.0),
        ("🇮🇳 India → Canada living", "IND", "CAN", 500000.0),
        ("🇲🇾 Malaysia → Australia fees", "MYS", "AUS", 30000.0),
    ]
    for column, (label, preset_origin, preset_destination, preset_amount) in zip(preset_columns, presets):
        with column:
            if st.button(label, width="stretch", key=f"preset_{preset_origin}_{preset_destination}"):
                st.session_state.planner_origin = preset_origin
                st.session_state.planner_destination = preset_destination
                st.session_state.planner_amount = preset_amount
                st.rerun()
    with st.form("corridor_builder"):
        left, middle, right = st.columns([1, .12, 1])
        with left:
            origin_iso = st.selectbox("Sending from", options, format_func=option_label, key="planner_origin")
        with middle:
            st.markdown("<div style='text-align:center;font-size:2rem;padding-top:1.55rem'>→</div>", unsafe_allow_html=True)
        with right:
            destination_iso = st.selectbox("Studying in", options, format_func=option_label, key="planner_destination")
        origin, destination = by_iso[origin_iso], by_iso[destination_iso]
        col1, col2, col3 = st.columns(3)
        with col1:
            amount_mode_label = st.radio("Amount means", [f"I send {origin.currency}", f"Recipient gets {destination.currency}"])
            amount_mode = AmountMode.SEND if amount_mode_label.startswith("I send") else AmountMode.RECIPIENT
        with col2:
            amount = st.number_input("Amount", min_value=1.0, step=100.0, key="planner_amount")
            purpose = st.selectbox("Purpose", ["Tuition", "Living costs", "Accommodation deposit", "Application fee"])
        with col3:
            priority = st.radio("Optimise for", ["balanced", "cheapest", "fastest"], horizontal=True)
            deadline = st.date_input("Needed by", value=date.today() + timedelta(days=10), min_value=date.today())
        recipient_name = st.text_input(
            "University or recipient name (optional)",
            placeholder="Used only for preliminary UN public-list screening",
        )
        submitted = st.form_submit_button("Verify rate and build my plan", type="primary", width="stretch")

    if submitted:
        if origin_iso == destination_iso:
            st.error("Choose two different countries to create a cross-border plan.")
        else:
            with st.spinner("Checking Frankfurter, Wise, World Bank and the UN public list…"):
                try:
                    fx = get_public_snapshot(allow_live=True)
                    plan = build_corridor_plan(
                        origin, destination, Decimal(str(amount)), amount_mode, priority,
                        purpose.lower(), deadline, fx,
                    )
                    st.session_state.corridor_plan = plan
                    st.session_state.corridor_benchmark = find_world_bank_corridor(origin.iso3, destination.iso3)
                    st.session_state.screened_name = recipient_name.strip()
                    st.session_state.sanctions_matches = (
                        screen_un_name(recipient_name.strip()) if recipient_name.strip() else []
                    )
                    try:
                        st.session_state.wise_quotes = fetch_wise_quotes(
                            origin.currency, destination.currency, Decimal(str(amount)), amount_mode,
                        )
                        st.session_state.wise_error = None if st.session_state.wise_quotes else "Wise returned no enabled payment option for this request."
                    except Exception:
                        st.session_state.wise_quotes = []
                        st.session_state.wise_error = "The provider endpoint could not be reached from this environment."
                except Exception as exc:
                    st.error(f"Could not build the plan: {exc}")

    plan = st.session_state.corridor_plan
    if isinstance(plan, CorridorPlan):
        quotes: list[WiseQuote] = st.session_state.wise_quotes
        plan_priority = getattr(plan, "priority", priority)
        selected = choose_wise_quote(quotes, plan_priority)
        benchmark = st.session_state.corridor_benchmark
        assessment = assess_quote(selected, plan.reference_rate, plan.request.deadline) if selected else None
        reference_source, reference_target = reference_amounts(plan)
        screened_name = st.session_state.screened_name
        matches = st.session_state.sanctions_matches
        plan_status, status_reason = decision_status(selected, screened_name, matches, assessment)
        is_live = "(live)" in plan.fx.source
        st.divider()
        status_text = "LIVE PUBLIC RATE" if is_live else "CACHED PUBLIC RATE"
        status_icon = "🟢" if is_live else "🟠"
        st.markdown(
            f"<div class='success-card'><b>{status_icon} {status_text}</b><br>"
            f"{plan.origin.country} ({plan.origin.currency}) → {plan.destination.country} ({plan.destination.currency})<br>"
            f"<span class='muted'>Source: {plan.fx.source} · corridor reference date "
            f"{plan.fx.rate_date(plan.origin.currency, plan.destination.currency).isoformat()}</span></div>",
            unsafe_allow_html=True,
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Reference FX rate", f"1 {plan.origin.currency} = {plan.reference_rate:,.6f} {plan.destination.currency}")
        if selected:
            m2.metric("Real preview", f"Wise · {selected.pay_in.replace('_', ' ').title()}")
            m3.metric("Recipient gets", f"{selected.target_amount:,.2f} {selected.target_currency}")
            m4.metric("Quoted fee", f"{selected.fee:,.2f} {selected.source_currency}")
        else:
            m2.metric("Reference estimate", "Frankfurter only")
            m3.metric("Recipient before fees", f"{reference_target:,.2f} {plan.destination.currency}")
            m4.metric("Provider fee", "Unknown")

        status_renderer = st.success if plan_status == "READY FOR USER REVIEW" else st.error if plan_status.startswith("STOP") else st.warning
        status_renderer(f"**Agent decision: {plan_status}**  \n{status_reason}")
        st.subheader("Your plan")
        for number, step in enumerate(plan.steps, start=1):
            st.markdown(f"<div class='step'><b>{number}. {step}</b></div>", unsafe_allow_html=True)
        st.subheader("Live provider preview")
        if quotes:
            st.dataframe(wise_rows(quotes), hide_index=True, width="stretch")
            st.info(
                f"Suggested preview for **{plan_priority}**: {recommendation_reason(selected, plan_priority)} "
                f"Provider ETA: **{selected.estimated_delivery_text}**. "
                "This is an unauthenticated estimate, not a locked quote; SendSmart cannot execute it."
            )
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Provider rate", f"{selected.rate:,.6f}")
            a2.metric("Rate vs reference", f"{assessment.rate_difference_percent:+.2f}%")
            a3.metric("Fee share", f"{assessment.fee_percent:.2f}%")
            a4.metric("Indicative total cost", f"{assessment.effective_cost_percent:.2f}%")
            if assessment.deadline_ok is True:
                st.success(f"Provider ETA is on or before your {plan.request.deadline.isoformat()} deadline.")
            elif assessment.deadline_ok is False:
                st.error(f"Provider ETA is later than your {plan.request.deadline.isoformat()} deadline. Choose another option or change the date.")
            else:
                st.caption("Deadline feasibility is unavailable because the provider did not return a timestamp.")
            st.caption(
                "Indicative total cost compares the recipient amount with converting the full source amount at the independent Frankfurter rate. "
                "It is an explanation metric, not a provider accounting figure."
            )
        else:
            st.warning(
                "No live Wise preview is available for this request right now. SendSmart calculated the reference-only amount below; "
                "it excludes provider fees and FX margins. "
                f"Connection status: {st.session_state.wise_error or 'No enabled option returned.'}"
            )
            st.dataframe(
                [{
                    "Estimate": "Independent reference before fees",
                    f"Send ({plan.origin.currency})": f"{reference_source:,.2f}",
                    f"Recipient ({plan.destination.currency})": f"{reference_target:,.2f}",
                    "Provider fee": "Unknown",
                    "Provider ETA": "Unknown",
                    "Can execute": "No",
                }],
                hide_index=True,
                width="stretch",
            )
            st.caption("This calculation uses the displayed Frankfurter rate. A provider can return a different rate and deduct or add fees.")

        st.subheader("Independent cost benchmark")
        if benchmark:
            b1, b2, b3 = st.columns(3)
            b1.metric("World Bank period", load_world_bank_snapshot()["period"])
            b2.metric("Median cost · small transfer", f"{benchmark['median_cost_200_pct']:.2f}%")
            b3.metric("Minimum observed", f"{benchmark['minimum_cost_200_pct']:.2f}%")
            st.caption(
                f"Based on {benchmark['transparent_observations']} transparent historical observations for "
                f"{benchmark['source']} → {benchmark['destination']}. It is a benchmark, not a current offer."
            )
            with st.expander("See the lowest observed World Bank services"):
                st.dataframe(benchmark["lowest_observed_services"], hide_index=True, width="stretch")
        else:
            st.caption(
                "World Bank Remittance Prices Worldwide does not cover this exact country pair in its latest bundled quarter. "
                "No benchmark is invented for uncovered corridors."
            )

        st.subheader("Preliminary public-list screen")
        if not screened_name:
            st.info("Not run. Add a university or recipient name to compare it with the UN Security Council Consolidated List.")
        elif matches:
            st.error(
                f"Possible name match found ({len(matches)}). This is not a final identity decision: stop and send it to trained compliance staff for review with additional identifiers."
            )
            st.dataframe(
                [{"UN reference": item.reference, "Type": item.kind, "Matched name": item.matched_name, "Similarity": f"{item.score:.0%}"} for item in matches],
                hide_index=True,
                width="stretch",
            )
        else:
            st.success(
                f"No preliminary name match for “{screened_name}” in the bundled UN snapshot. This is not KYC, AML clearance, or proof of identity."
            )

        decision_report = build_decision_report(plan, selected, assessment, benchmark, screened_name, matches)
        st.download_button(
            "Download decision report",
            data=json.dumps(decision_report, indent=2, ensure_ascii=False),
            file_name=f"sendsmart-{plan.origin.iso3.lower()}-{plan.destination.iso3.lower()}-decision.json",
            mime="application/json",
            width="stretch",
        )
        st.caption("The report preserves the selected evidence, source dates, decision status and non-execution boundary for review.")

        with st.expander("Show exactly what is real and what remains simulated"):
            st.markdown(
                "- **Real public data:** UNESCO destination ranking, Frankfurter reference FX, World Bank corridor benchmarks, and the UN consolidated-list snapshot.\n"
                "- **Real provider preview:** Wise returns current fee, conversion and ETA estimates when the corridor is supported. It is not logged in, funded, locked or executable.\n"
                "- **Not implemented:** beneficiary ownership checks, invoice/reference validation, KYC, source-of-funds, provider onboarding, legal eligibility and payment execution.\n"
                "- **Still simulated:** only the separate Safe execution demo, retained to demonstrate approval and security controls."
            )

with execution_tab:
    st.subheader("Guardrailed payment simulation")
    st.caption("This separate flow demonstrates approvals. It retains two fixed fictional personas and never sends money.")
    persona = st.selectbox("Demo persona", ["Aisha (MY → UK)", "Carlos (MX → US)"])
    user_id = "aisha" if persona.startswith("Aisha") else "carlos"
    examples = {
        "Tuition": "Pay GBP 9000 tuition to Northbridge University from MYR by 27 October 2026",
        "Living costs": "Send MYR 300 from MYR to GBP to my landlord for living costs",
        "Compare only": "Compare GBP 500 options from MYR to GBP for my landlord",
        "Needs clarification": "Send some money to my landlord",
    }
    quick_cols = st.columns(len(examples))
    for column, (label, prompt_text) in zip(quick_cols, examples.items()):
        if column.button(label, width="stretch"):
            st.session_state.prompt = prompt_text
    prompt = st.text_area("Describe the payment", value=st.session_state.get("prompt", examples["Tuition"]), height=95)
    uploaded = st.file_uploader("Optional invoice text", type=["txt"])
    document_text = uploaded.getvalue().decode("utf-8", errors="replace") if uploaded else None
    if st.button("Understand and create guarded plan", type="primary"):
        st.session_state.prepared = agent.prepare(prompt, user_id=user_id, document_text=document_text)
        st.session_state.last_result = None
    prepared = st.session_state.prepared
    if isinstance(prepared, dict):
        if prepared.get("clarification"):
            st.warning(prepared["clarification"])
        elif prepared.get("message"):
            st.info(prepared["message"])
    elif isinstance(prepared, PreparedTransfer):
        st.write(f"Intent: **{prepared.intent.type.value}** · confidence **{prepared.intent.confidence}**")
        render_execution_plan(prepared)
        getattr(st, "error" if prepared.policy.tier == Tier.BLOCKED else "info")(
            f"{prepared.policy.tier.value}: {prepared.policy.required_user_action}"
        )
        st.write(prepared.explanation)
        if prepared.policy.tier == Tier.T2_CONFIRM and st.button("Confirm simulated payment"):
            st.session_state.last_result = agent.execute(prepared, "CONFIRM")
        elif prepared.policy.tier == Tier.T3_APPROVE:
            expected = expected_approval_phrase(prepared.request, prepared.beneficiary["name"])
            phrase = st.text_input("Typed approval", placeholder=expected)
            if st.button("Approve simulated payment"):
                try:
                    st.session_state.last_result = agent.execute(prepared, phrase)
                except PermissionError as exc:
                    st.error(str(exc))
        c1, c2, c3 = st.columns(3)
        if c1.button("Reject plan"):
            agent.reject(prepared)
            st.warning("Plan rejected. Nothing executed.")
        if c2.button("STOP AGENT", type="primary"):
            agent.executor.set_kill_switch(True)
            st.error("Kill switch active.")
        if c3.button("Reset STOP AGENT"):
            agent.executor.set_kill_switch(False)
            st.success("Kill switch reset.")
    if st.session_state.last_result:
        receipt = st.session_state.last_result["receipt"]
        st.success(f"Sandbox receipt: {receipt['receipt_id']} ({receipt['status']})")
        st.json(receipt)

with safety_tab:
    st.subheader("Try the safety controls")
    st.write("These attacks are intentionally blocked by the deterministic policy boundary.")
    attack_files = {"Injection invoice": "injection_invoice.txt", "Changed bank details": "tampered_invoice.txt"}
    cols = st.columns(3)
    for column, (label, filename) in zip(cols[:2], attack_files.items()):
        if column.button(label, width="stretch"):
            invoice_text = (ROOT / "data" / "sample_invoices" / filename).read_text(encoding="utf-8")
            st.session_state.attack_result = agent.prepare("Pay the tuition invoice from MYR", document_text=invoice_text)
    if cols[2].button("Unverified beneficiary", width="stretch"):
        st.session_state.attack_result = agent.prepare("Send GBP 300 from MYR to GBP to new beneficiary")
    attack_result = st.session_state.get("attack_result")
    if isinstance(attack_result, PreparedTransfer):
        st.error(f"{attack_result.policy.tier.value}: {', '.join(attack_result.policy.triggered_rules)}")
        st.json(attack_result.policy.model_dump(mode="json"))

with evidence_tab:
    st.subheader("Competition evidence — generated, not hand-scored")
    st.caption("The official rubric weights task completion 40%, security and compliance 30%, and innovation and interaction 30%.")
    metrics = json.loads((ROOT / "evidence" / "metrics.json").read_text(encoding="utf-8"))
    intent_evidence = json.loads((ROOT / "evidence" / "intent_eval.json").read_text(encoding="utf-8"))
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Sandbox scenarios", f"{metrics['scenario_pass_count']}/{metrics['scenario_count']}")
    e2.metric("Attack block rate", f"{metrics['attack_block_rate']:.0%}")
    e3.metric("False-block rate", f"{metrics['false_block_rate']:.0%}")
    e4.metric("Intent benchmark", f"{intent_evidence['intent_accuracy']:.0%}")
    st.warning("These are controlled prototype results on bundled scenarios. They do not establish production accuracy or regulatory compliance.")

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown("**Task completion · 40%**")
        st.write("Real-data corridor plan, provider preview, deadline check, downloadable decision report, and guarded sandbox receipt.")
    with r2:
        st.markdown("**Security and compliance · 30%**")
        st.write("Permission tiers, typed approval, beneficiary fingerprint, hard caps, injection blocking, one-time tokens, kill switch, and hash-chained audit.")
    with r3:
        st.markdown("**Innovation and interaction · 30%**")
        st.write("Independent rate triangulation, provider-cost explanation, visible agent plan, attack lab, and graceful offline behavior.")

    st.subheader("Audit evidence")
    audit_path = agent.audit.path
    st.metric("Hash chain", "VERIFIED" if agent.audit.verify_chain() else "TAMPERED")
    content = audit_path.read_text(encoding="utf-8") if audit_path.exists() else ""
    audit_rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    if audit_rows:
        st.dataframe(audit_rows, width="stretch")
        st.download_button(
            "Download audit data",
            data=json.dumps(audit_rows, indent=2),
            file_name="sendsmart-audit.json",
            mime="application/json",
        )

with data_tab:
    st.subheader("Public data and live integration coverage")
    world_bank_data = load_world_bank_snapshot()
    un_data = load_un_snapshot()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Destinations", len(destinations))
    c2.metric("Currencies", len({item.currency for item in destinations}))
    c3.metric("World Bank corridors", len(world_bank_data["corridors"]))
    c4.metric("UN list entries", len(un_data["entries"]))
    st.markdown(
        f"**Ranking:** {destination_data['indicator']}  \n**Release:** {destination_data['release']}  \n"
        f"**Method:** {destination_data['method']}  \n"
        f"[UNESCO source]({destination_data['source_url']}) · [Frankfurter](https://frankfurter.dev/) · "
        f"[World Bank RPW]({world_bank_data['source_url']}) · [UN consolidated list]({un_data['source_url']}) · "
        "[Wise API documentation](https://docs.wise.com/api-reference)"
    )
    st.warning(
        "Countries report on different schedules, so observations span multiple years. "
        "The ranking measures all inbound mobile students, not only students from China. World Bank coverage is also a subset of all possible country pairs."
    )
    rows = [
        {"Rank": d.rank, "Destination": d.country, "Currency": d.currency, "Observation year": d.year, "Inbound students": d.students}
        for d in destinations
    ]
    st.dataframe(rows, hide_index=True, width="stretch")

with limits_tab:
    st.subheader("Exactly what is real, simulated, and still missing")
    st.markdown(
        """
        **Real now**

        - Select both countries from the UNESCO top 50.
        - Verify a live Frankfurter reference rate, with a cached public snapshot if offline.
        - Request a real unauthenticated Wise fee, conversion and ETA preview when supported.
        - Compare against the latest bundled World Bank remittance-cost benchmark when that corridor is covered.
        - Run preliminary name matching against a dated UN Security Council Consolidated List snapshot.

        **Still simulated**

        - The separate Safe execution demo uses two fictional personas, six fictional providers, synthetic beneficiaries and simulated receipts.
        - Its security limits and destination blocklist are test fixtures, not production compliance policy.

        **Best real replacements still requiring contracts or credentials**

        - **Execution and locked quotes:** Wise Platform partner onboarding and OAuth/API credentials.
        - **Education beneficiary and reference validation:** Flywire Education APIs plus institutional onboarding.
        - **Identity/KYC and case management:** a regulated vendor such as Sumsub, reviewed by compliance counsel.
        - **Broader sanctions/PEP/adverse-media screening:** a licensed screening service with human case review; the UN name check alone is insufficient.
        - **Production ledger and audit:** bank-grade double-entry ledger, durable authorization store, HSM-backed signing, monitoring and external audit retention.

        **Restrictions you must remember while testing**

        - The main planner is advisory only and never sends money.
        - Wise previews are estimates: unauthenticated, not rate-locked and not guaranteed available to the user.
        - Frankfurter is an independent reference rate, not a remittance offer.
        - World Bank figures are historical corridor benchmarks and many of the 50×49 possible pairs are not covered.
        - A name-screen result is preliminary; it is neither identity verification nor legal clearance.
        - The destination ranking is global inbound mobility, not a China-only outbound ranking.
        """
    )
