"""Recovery Engine — Dashboard UI

Run with: streamlit run app/dashboard.py
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import requests
import streamlit as st

# Configuration
API_BASE = os.environ.get("RECOVERY_API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Recovery Engine",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for clean, professional look
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #e9ecef;
    }
    .status-recovered { color: #198754; font-weight: 600; }
    .status-escalated { color: #dc3545; font-weight: 600; }
    .status-pending { color: #ffc107; font-weight: 600; }
    .status-executed { color: #0d6efd; font-weight: 600; }
    .ai-badge { background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
    .policy-badge { background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
    .stage-ai { background: #e8f5e9; border-left: 4px solid #2e7d32; padding: 0.5rem; margin: 0.25rem 0; }
    .stage-deterministic { background: #e3f2fd; border-left: 4px solid #1565c0; padding: 0.5rem; margin: 0.25rem 0; }
    .stage-result { background: #fff3e0; border-left: 4px solid #e65100; padding: 0.5rem; margin: 0.25rem 0; }
</style>
""", unsafe_allow_html=True)


def api_get(path: str) -> dict | list | None:
    """Make a GET request to the API."""
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def api_post(path: str, data: dict | None = None) -> dict | None:
    """Make a POST request to the API."""
    try:
        resp = requests.post(f"{API_BASE}{path}", json=data or {}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def trigger_demo_event(error_reason: str, label: str) -> dict | None:
    """Trigger a demo payment failure event."""
    payload = {
        "event_id": f"evt_{error_reason}_{int(time.time())}",
        "payment_id": f"pay_{error_reason}_{int(time.time())}",
        "error_reason": error_reason,
        "error_description": f"Demo: {label}",
    }
    try:
        resp = requests.post(f"{API_BASE}/api/demo/payment-failure", json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


# Sidebar
with st.sidebar:
    st.title("💰 Recovery Engine")
    st.markdown("---")
    page = st.radio("Navigation", [
        "📊 Overview",
        "📋 Recovery Queue",
        "🧠 AI Decisions",
        "📈 Evaluation",
        "🎮 Demo",
    ])
    st.markdown("---")
    st.markdown(f"**API:** `{API_BASE}`")
    if st.button("🔄 Refresh"):
        st.rerun()

# ============================================================
# OVERVIEW PAGE
# ============================================================
if page == "📊 Overview":
    st.title("Recovery Overview")
    st.markdown("Real-time revenue recovery metrics")

    summary = api_get("/api/dashboard/summary")
    if summary is None:
        st.error("Cannot connect to API. Start the server with: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`")
    else:
        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Items", summary.get("total_items", 0))
        col2.metric("Recovered", summary.get("recovered_count", 0))
        col3.metric("Escalated", summary.get("escalated_count", 0))
        col4.metric("Pending", summary.get("pending_count", 0))

        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Recovery Rate", f"{summary.get('recovery_rate', 0):.1%}")
        col2.metric("Attempts", summary.get("attempts_total", 0))
        col3.metric("Policy Allowed", summary.get("policy_allowed", 0))
        col4.metric("Policy Denied", summary.get("policy_denied", 0))

        st.markdown("---")

        # Amount breakdown
        st.subheader("Financial Summary")
        col1, col2, col3 = st.columns(3)
        total_amount = summary.get("total_amount_minor", 0) / 100
        recovered_amount = summary.get("recovered_amount_minor", 0) / 100
        expected_value = summary.get("expected_recovery_value", 0) / 100
        col1.metric("Total at Risk", f"₹{total_amount:,.2f}")
        col2.metric("Recovered", f"₹{recovered_amount:,.2f}")
        col3.metric("Expected Value", f"₹{expected_value:,.2f}")

# ============================================================
# RECOVERY QUEUE PAGE
# ============================================================
elif page == "📋 Recovery Queue":
    st.title("Recovery Queue")
    st.markdown("All recovery cases")

    items = api_get("/api/recovery-items")
    if items is None:
        st.error("Cannot connect to API.")
    elif not items:
        st.info("No recovery items yet. Use the Demo page to trigger events.")
    else:
        # Status filter
        status_filter = st.selectbox("Filter by status", ["All"] + list(set(i["status"] for i in items)))
        if status_filter != "All":
            items = [i for i in items if i["status"] == status_filter]

        for item in items:
            with st.expander(f"{item['id']} — {item['currency']} {item['amount_minor']/100:,.2f} [{item['status']}]"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Category:** {item.get('root_cause', 'unknown')}")
                    st.markdown(f"**Expected Value:** ₹{(item.get('expected_recovery_value') or 0)/100:,.2f}")
                    st.markdown(f"**Status:** `{item['status']}`")
                with col2:
                    st.markdown(f"**Created:** {item['created_at']}")
                    if item.get("metadata", {}).get("proposed_action"):
                        st.markdown(f"**Proposed:** {item['metadata']['proposed_action']}")
                    if item.get("metadata", {}).get("policy_allowed") is not None:
                        allowed = item["metadata"]["policy_allowed"]
                        st.markdown(f"**Policy:** {'✅ Allowed' if allowed else '❌ Denied'}")

                # Link to detail
                if st.button("View Details", key=f"detail_{item['id']}"):
                    st.session_state["selected_item"] = item["id"]
                    st.rerun()

# ============================================================
# AI DECISIONS PAGE
# ============================================================
elif page == "🧠 AI Decisions":
    st.title("AI Decision Panel")
    st.markdown("Agent proposals and policy decisions")

    # Check for selected item
    selected_id = st.session_state.get("selected_item")
    if selected_id:
        st.markdown(f"**Selected:** `{selected_id}`")
        if st.button("Clear Selection"):
            st.session_state.pop("selected_item", None)
            st.run()

    items = api_get("/api/recovery-items")
    if items is None:
        st.error("Cannot connect to API.")
    elif not items:
        st.info("No recovery items yet.")
    else:
        # Show items with AI decisions
        ai_items = [i for i in items if i.get("metadata", {}).get("proposed_action")]
        if not ai_items:
            st.info("No AI decisions recorded yet.")
        else:
            for item in ai_items:
                with st.expander(f"{item['id']} — Proposed: {item['metadata']['proposed_action']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**AI Recommendation**")
                        st.markdown(f"Action: `{item['metadata']['proposed_action']}`")
                        if item.get("metadata", {}).get("confidence"):
                            st.markdown(f"Confidence: {item['metadata']['confidence']:.0%}")
                        st.markdown(f"Model: {item['metadata'].get('agent_model', 'unknown')}")
                    with col2:
                        st.markdown("**Deterministic Gate**")
                        allowed = item["metadata"].get("policy_allowed")
                        if allowed is not None:
                            st.markdown(f"Policy: {'✅ Allowed' if allowed else '❌ Denied'}")
                        st.markdown(f"Status: `{item['status']}`")

# ============================================================
# EVALUATION PAGE
# ============================================================
elif page == "📈 Evaluation":
    st.title("Agent Evaluation")
    st.markdown("Golden-scenario evaluation results")

    eval_report = api_get("/api/evaluations")
    if eval_report is None:
        st.error("Cannot connect to API.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total", eval_report.get("total", 0))
        col2.metric("Passed", eval_report.get("passed", 0))
        col3.metric("Failed", eval_report.get("failed", 0))
        col4.metric("Pass Rate", f"{eval_report.get('pass_rate', 0):.0%}")

        st.markdown("---")

        # Results table
        results = eval_report.get("results", [])
        if results:
            st.subheader("Scenario Results")
            for r in results:
                icon = "✅" if r["passed"] else "❌"
                with st.expander(f"{icon} {r['scenario_name']} — {r['proposal_action']}"):
                    st.markdown(f"**Expected:** {r['expected_action'] or 'any safe action'}")
                    st.markdown(f"**Confidence:** {r['proposal_confidence']:.2f}")
                    if r.get("issues"):
                        for issue in r["issues"]:
                            st.markdown(f"⚠️ {issue}")

# ============================================================
# DEMO PAGE
# ============================================================
elif page == "🎮 Demo":
    st.title("Demo — Trigger Failed Payments")
    st.markdown("Simulate failed payment events (no real Razorpay account needed)")

    st.subheader("Quick Scenarios")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("🔄 Soft Failure", help="Temporary timeout — should retry"):
            result = trigger_demo_event("payment_timed_out", "Payment timed out")
            if result:
                st.success(f"Processed: {result.get('recovery_item_id')}")
                st.session_state["selected_item"] = result.get("recovery_item_id")

    with col2:
        if st.button("🚫 Hard Failure", help="Card declined — should escalate"):
            result = trigger_demo_event("card_declined", "Card declined")
            if result:
                st.success(f"Processed: {result.get('recovery_item_id')}")
                st.session_state["selected_item"] = result.get("recovery_item_id")

    with col3:
        if st.button("⚠️ Fraud", help="Risk check failed — should escalate"):
            result = trigger_demo_event("payment_risk_check_failed", "Risk check failed")
            if result:
                st.success(f"Processed: {result.get('recovery_item_id')}")
                st.session_state["selected_item"] = result.get("recovery_item_id")

    with col4:
        if st.button("🔐 Auth", help="Authentication required"):
            result = trigger_demo_event("authentication_failed", "Auth failed")
            if result:
                st.success(f"Processed: {result.get('recovery_item_id')}")
                st.session_state["selected_item"] = result.get("recovery_item_id")

    with col5:
        if st.button("❓ Unknown", help="Unknown failure"):
            result = trigger_demo_event("unknown_reason", "Unknown error")
            if result:
                st.success(f"Processed: {result.get('recovery_item_id')}")
                st.session_state["selected_item"] = result.get("recovery_item_id")

    st.markdown("---")

    # Custom event
    st.subheader("Custom Event")
    col1, col2 = st.columns(2)
    with col1:
        custom_reason = st.selectbox("Error Reason", [
            "payment_timed_out", "gateway_technical_error", "card_declined",
            "payment_risk_check_failed", "authentication_failed", "unknown_reason",
        ])
        custom_amount = st.number_input("Amount (minor units)", value=50000, step=1000)
    with col2:
        custom_currency = st.selectbox("Currency", ["INR", "USD", "EUR"])
        custom_method = st.selectbox("Method", ["card", "upi", "netbanking", "wallet"])

    if st.button("Trigger Custom Event"):
        payload = {
            "event_id": f"evt_custom_{int(time.time())}",
            "payment_id": f"pay_custom_{int(time.time())}",
            "error_reason": custom_reason,
            "amount_minor": custom_amount,
            "currency": custom_currency,
            "method": custom_method,
        }
        try:
            resp = requests.post(f"{API_BASE}/api/demo/payment-failure", json=payload, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                st.success(f"Processed: {result.get('recovery_item_id')}")
                st.session_state["selected_item"] = result.get("recovery_item_id")
            else:
                st.error(f"Error: {resp.status_code}")
        except Exception as exc:
            st.error(f"Request failed: {exc}")

    st.markdown("---")

    # Selected item detail
    selected_id = st.session_state.get("selected_item")
    if selected_id:
        st.subheader(f"Case Detail: `{selected_id}`")
        detail = api_get(f"/api/recovery-items/{selected_id}")
        if detail:
            # Decision Timeline
            st.markdown("### 🔄 Recovery Decision Timeline")
            audit_events = detail.get("audit_events", [])
            for event in audit_events:
                actor = event.get("actor", "system")
                action = event.get("action", "")
                reason = event.get("reason", "")
                timestamp = event.get("timestamp", "")

                if actor == "agent":
                    st.markdown(f'<div class="stage-ai"><b>🤖 [{actor}]</b> {action}<br/><small>{reason}</small></div>', unsafe_allow_html=True)
                elif actor == "rule":
                    st.markdown(f'<div class="stage-deterministic"><b>📏 [{actor}]</b> {action}<br/><small>{reason}</small></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="stage-result"><b>⚙️ [{actor}]</b> {action}<br/><small>{reason}</small></div>', unsafe_allow_html=True)

            # Attempts
            attempts = detail.get("attempts", [])
            if attempts:
                st.markdown("### 🎯 Execution Attempts")
                for a in attempts:
                    icon = "✅" if a["outcome"] == "success" else "❌"
                    st.markdown(f"{icon} Attempt #{a['attempt_number']}: {a['action']} — {a['outcome']}")

            # Decisions
            decisions = detail.get("decisions", [])
            if decisions:
                st.markdown("### 🧠 AI Decisions")
                for d in decisions:
                    st.markdown(f"- **Action:** {d.get('proposed_action')} | **Confidence:** {d.get('confidence')} | **Policy:** {d.get('policy_allowed')}")
        else:
            st.warning("Item not found.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Recovery Engine** — AI-powered revenue recovery")
st.sidebar.markdown("Built with deterministic safety + AI reasoning")
