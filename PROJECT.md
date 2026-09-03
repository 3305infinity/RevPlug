# RevPlug — Autonomous Revenue Recovery Control Plane

> **RevPlug is an autonomous AI-driven revenue recovery control plane that detects revenue at risk via an event-driven Opportunity Detection Engine, diagnoses transaction failure causes, evaluates bounded recovery interventions via Expected Net Recovery optimization ($EV_{\text{net}}$), enforces zero-violation safety policies, executes real/simulated recovery workflows, observes real outcomes, dynamically re-plans across closed-loop steps, and proves verified settlement.**

Built for **Razorpay AI Buildathon — AI Revenue Recovery Track**.


# 1. Problem Statement & Architecture Vision

Revenue leakage rarely happens as a single obvious failure. A recurring payment fails due to authorization timeout. An invoice becomes overdue. A customer card expires. A checkout is abandoned. A dispute is opened.

Naively retrying every failed transaction inflates intervention costs, frustrates customers, risks payment gateway penalties, and retries unsafe fraud or opted-out cases.

RevPlug solves this by acting as an **event-driven closed-loop bounded recovery agent**:

```text
DETECT REVENUE AT RISK (Opportunity Detection Engine)
      ↓
CLASSIFY ROOT CAUSE & COMPUTE EXPECTED NET EV ($EV_{net}$)
      ↓
CUSTOMER 360 PROFILE & LTV AGGREGATION
      ↓
DIAGNOSE FAILURE REASON & BOUNDED PLAYBOOK
      ↓
EXPECTED VALUE & TIMING OPTIMIZATION ($EV_{net}$)
      ↓
SERVER-SIDE POLICY GATE & VERSIONED GOVERNANCE
      ↓
EXECUTE BOUNDED ACTION (RETRY / LINK / REMINDER / WAIT)
      ↓
OBSERVE REAL OUTCOME VIA WEBHOOK / SETTLEMENT VERIFIER
      ↓
UPDATE CASE CONTEXT & CLOSED-LOOP RE-PLAN
      ↓
CAUSAL ATTRIBUTION LEDGER (DIRECT_AGENT vs ORGANIC)
```

---

# 2. Key System Boundaries & Signature Axiom

> **Signature Architecture Axiom:**  
> *AI proposes what to try. Policy decides what is allowed. Real Settlement decides what counts.*

1. **Event-Driven Detection Boundary**: Normalized revenue events (`payment_failed`, `subscription_payment_failed`, `invoice_overdue`, `checkout_abandoned`, `payment_requires_action`, `dispute_created`, `fraud_flagged`, `payment_succeeded`) are processed by `OpportunityDetector` idempotently.
2. **AI Reasoning Boundary**: Contextual LLM reasoning (Groq Primary `llama-3.3-70b-versatile` / Gemini Secondary `gemini-1.5-pro`) diagnoses failure root cause and generates candidate bounded recovery playbooks. Model outputs are strictly validated against an allowlisted `ActionRegistry`.
3. **Deterministic Policy Boundary**: Server-side code retains 100% execution authority. Enforces hard safety rules (`retry_limit`, `block_hard_failure`, `opt_out_block`, `contact_frequency_limit`, `terminal_state_block`, `incident_suppression`). Human overrides CANNOT bypass hard safety rules (`HTTP 400 Policy Violation`).
4. **Execution & Webhook Boundary**: Executes bounded gateway actions (Razorpay Test Mode / Simulated API) and verifies settlement via authentic HMAC-SHA256 webhooks and `SettlementVerifier`.
5. **Causal Attribution Invariant**: Every settlement is strictly attributed (`DIRECT_AGENT`, `AGENT_ASSISTED`, `ORGANIC`, `UNKNOWN`). Organic self-service payments increment `ORGANIC RECOVERY` and contribute ₹0 to `AGENT-ATTRIBUTED RECOVERY`.

---

# 3. Core Domain Capabilities

### 1. Event-Driven Opportunity Detection Engine (`app/services/opportunity_detector.py`)
Translates incoming normalized revenue telemetry into prioritized, scored, and policy-governed `RecoveryItem` opportunities. Enforces idempotency across repeated webhook events.

### 2. Ranked Opportunity Inbox API (`GET /api/opportunity-inbox`)
Serves active revenue opportunities pre-ranked strictly by Expected Net Recovery ($EV_{\text{net}}$) and business priority on the operations dashboard.

### 3. Portfolio Financial Summary (`app/services/financials.py`)
Calculates single-source-of-truth financial metrics: Total Revenue at Risk, Actionable Revenue, Revenue Waiting (Policy/Systemic), Revenue Recovered, Revenue Intentionally Not Pursued, Available Net EV, and High Priority Count.

### 4. Portfolio-Level Next Best Action Engine (`app/services/portfolio_nba.py`)
Continuously evaluates open recovery cases and ranks intervention opportunities strictly by Expected Business Value ($EV_{\text{net}}$) and urgency.

### 5. Customer 360 Recovery Profile (`app/services/customer_recovery_profile.py`)
Aggregates customer lifetime revenue, risk score, payment method history, contact frequency budget (max 2/24h), and failure rates prior to agent decisions.

### 6. Bounded Recovery Playbook Engine (`app/services/recovery_playbook.py`)
Generates category-specific recovery sequences (`AUTHENTICATION_REQUIRED`, `INSUFFICIENT_FUNDS`, `EXPIRED_CARD`, `OVERDUE_B2B_INVOICE`, `FRAUD`) with dynamic step re-evaluation.

### 7. Payment Method Optimization (`app/services/payment_method_optimizer.py`)
Evaluates alternative payment methods (UPI, Card, Bank Transfer) based on transaction costs, failure compatibility, and historical customer success. Suppresses retries on hard declines (`expired_card`).

### 8. Checkout Abandonment Recovery (`app/services/checkout_abandonment_detector.py`)
Classifies checkout abandonment buyer intent (`HIGH INTENT`, `PAYMENT ERROR`, `LOW INTENT`, `CONTACT FATIGUE`) and delivers time-optimal checkout links.

### 9. Failed Subscription Recovery & LTV Horizons
Calculates 30-day and 90-day retained subscription LTV ($3 \times \text{Invoice EV}$) to prioritize high-tenure subscription renewals over one-off payments.

### 10. Time-Optimal Recovery Optimizer (`app/services/recovery_timing.py`)
Schedules retries into evidence-backed customer activity windows (e.g. morning salary deposit windows).

### 11. Systemic Revenue Incident Control (`app/services/revenue_incident_manager.py`)
Detects gateway and provider failure spikes, suppresses unsafe retries, and resumes playbooks upon incident resolution.

### 12. Revenue-Prioritized Human Review Queue (`frontend/src/app/review/page.tsx`)
Ranks escalated cases strictly by Expected Recoverable Revenue ($EV_{\text{net}}$) and resumes recovery playbooks post-approval.

### 13. Versioned Policy Configuration Engine (`app/services/policy_config_service.py`)
Deterministic policy controls (`v1.0`, `v1.1`) versioned on every update; AI agents are strictly forbidden from modifying policy rules.

### 14. Recovery Strategy Analytics (`app/services/strategy_analytics.py`)
Inspects historical strategy performance and generates automated data-backed opportunity signals.

### 15. Outcome-Learning Recovery Memory (`app/memory/store.py`)
Persists structured outcome features and displays inspectable `LEARNING SIGNAL: Based on N similar historical recoveries` badges inside Decision Cards.

### 16. Causal Recovery Attribution Engine (`app/services/recovery_attribution.py`)
Distinguishes `DIRECT_AGENT`, `AGENT_ASSISTED`, `ORGANIC`, and `UNKNOWN` settlements so self-service payments are never falsely attributed to the AI agent.

### 17. Time-to-Recovery Velocity Analytics (`app/services/time_to_recovery.py`)
Tracks median recovery time (**2h 14m**), P90 (**18h 42m**), attempt conversion rates, and time-window recovery distributions.

### 18. Revenue Leakage Diagnostics View (`app/services/revenue_leakage.py`)
Categorizes unrecovered revenue by failure cause and recommends specific policy fixes.

### 19. AI Collections Call (`frontend/src/app/recovery/[id]/voice-call/page.tsx`)
End-to-end voice collection flow for overdue B2B/subscription cases using the browser's built-in Web Speech API (no external paid telephony/voice API required). The agent speaks an opening line in Hinglish via `SpeechSynthesis`, captures the customer's live spoken reply via `SpeechRecognition` (`lang: 'en-IN'`), sends the real transcript to `POST /api/recovery-items/{id}/voice-promise`, which calls the existing `HinglishPromiseExtractor.extract()` and `PromiseService.create_promise()` on the REAL transcript. A `PromiseRecord` is only created when extraction returns `intent == "promise_to_pay"` with both `amount_minor` and `promised_date` resolved; otherwise the extraction result is shown honestly (fail-closed). Works in Chrome out of the box, zero API keys, zero cost.

---

# 4. Benchmark Evaluation Results

Canonical counterfactual evaluation: **50 cases | Seed 42** against naive and safe fixed-retry baselines.

| Metric | Baseline A (Naive Retry) | Baseline B (Safe Fixed Retry) | RevPlug Bounded AI Agent | RevPlug Lift / Advantage |
| :--- | :--- | :--- | :--- | :--- |
| **Total Revenue at Risk** | ₹42,674.00 | ₹42,674.00 | **₹42,674.00** | Identical risk pool |
| **Verified Recovery Rate** | 31.9% | 31.9% | **44.1%** | **+12.2% pts vs Baseline** |
| **Verified Recovered Revenue** | ₹13,608.50 | ₹13,608.50 | **₹18,800.00** | **+₹5,191.50** |
| **Net Recovered Revenue** | ₹13,153.50 | ₹13,213.50 | **₹18,688.00** | **+₹5,474.50 (+41.4%)** |
| **AI Proposals (of 50 cases)** | — | — | **30 AI proposals; 8 accepted; 22 rejected by policy; 9 fallbacks** | — |
| **Safety Policy Violations** | **17** | **0** | **0** | **-100% Policy Violations** |
| **Decision Quality: Root Cause Accuracy** | — | — | **1.0** | — |
| **Decision Quality: Proposal Action Accuracy** | — | — | **0.9** | — |
| **Decision Quality: Stopping Rule Compliance** | — | — | **0.8182** | — |
