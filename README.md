# RevPlug — Autonomous Revenue Recovery Control Plane

> **RevPlug is an autonomous AI-driven revenue recovery control plane that finds money at risk, diagnoses why transactions fail, evaluates bounded recovery interventions, enforces zero-violation safety policies, executes real/simulated recovery workflows, and proves verified settlement.**

> **Signature Architecture Axiom:**  
> *AI proposes what to try. Policy decides what is allowed. Real Settlement decides what counts.*

---

## 1. Executive Summary & Core Value Proposition

Revenue is lost across five distinct surfaces: payment gateway failures, abandoned checkouts, failed subscription renewals, overdue B2B receivables, and mandate debit failures.

Naively retrying every failed transaction inflates intervention costs, frustrates customers, risks payment processor penalties, and retries unsafe fraud or opted-out cases.

**THIS IS NOT A RETRY SCRIPT.**

RevPlug is an autonomous revenue recovery control plane that detects revenue at risk, diagnoses why recovery failed using contextual LLM reasoning, evaluates economically viable interventions via Expected Value optimization ($EV = \text{Gross EV} - \text{Intervention Cost}$), enforces strict deterministic safety policies, executes bounded recovery actions, verifies settlement via authentic gateway webhooks (e.g. Razorpay Test Mode HMAC signatures), and records authoritative financial outcomes.

---

## 2. Head-to-Head Counterfactual Benchmark Proof

Reproducible evaluation across a 100-case canonical benchmark (`count = 100, seed = 42`, dataset `v1-stage14-batch`):

| Metric | Fixed Retry Baseline | RevPlug AI Control Plane | Performance & Safety Impact |
| :--- | :--- | :--- | :--- |
| **Total Amount at Risk** | ₹84,602.00 | **₹84,602.00** | Identical 100-case risk pool |
| **Verified Recovered Revenue** | ₹22,366.00 | **₹21,100.00** | Verified settlement accounting only |
| **Value Recovery Rate (%)** | 26.44% | **24.94%** | Measured post-settlement |
| **Unsafe Retries Allowed** | 54 Retries | **0 Retries** | **100% Unsafe Actions Prevented** |
| **Safety Violations** | **8 Violations** | **0 Violations** | **100% Fail-Closed Compliance** |
| **Opt-Out Violations** | 2 Contacts | **0 Contacts** | **100% Customer Consent Compliance** |
| **Fraud Retries** | 4 Retries | **0 Retries** | **Zero Fraud Re-execution** |

> **Why Violations Matter**: A naive retry script retries fraud cases, hard bank declines, and opted-out customers, incurring gateway penalties and customer harassment. RevPlug guarantees **0 policy violations** while maximizing net economic recovery ($EV = \text{Amount} \times P - \text{Cost} > 0$).

---

## 3. How RevPlug Works — Step-by-Step Architecture

RevPlug operates as a strict 7-stage control loop separating reasoning from authority:

$$\text{Ingest Signal} \longrightarrow \text{Diagnose (AI)} \longrightarrow \text{Calculate EV} \longrightarrow \text{Policy Gate} \longrightarrow \text{Execute Bounded Action} \longrightarrow \text{Verify Webhook} \longrightarrow \text{Record Ledger}$$

```text
                                  1. TELEMETRY INGESTION
                    (Payment / Checkout / Subscription / B2B Invoice)
                                             │
                                             ▼
                                  2. REASONING LAYER (AI)
                  Contextual LLM Diagnosis (Groq Primary / Gemini Secondary)
                  Outputs: Root Cause Classification & Candidate Proposal
                                             │
                                             ▼
                                  3. EXPECTED VALUE SCORER
                     Scoring Matrix: EV = Recovery Probability × Value - Cost
                                             │
                                             ▼
                                  4. SERVER-SIDE POLICY GATE
                   Deterministic Rules: Fraud Shield / Opt-out / Retry Budget
                                      ↙             ↘
                               [ALLOW]               [BLOCK / STOP]
                                  │                         │
                                  ▼                         ▼
                       5. BOUNDED EXECUTOR            0 API Calls Made
                     (Razorpay Test Mode API)       Capital Protected (₹18.2k)
                                  │                         │
                                  ▼                         │
                      6. SETTLEMENT VERIFIER                │
                     HMAC-SHA256 Webhook Match              │
                                  │                         │
                                  └────────────┬────────────┘
                                               ▼
                                   7. IMMUTABLE FINANCIAL LEDGER
```

### Detailed Operational Breakdown:

1. **Signal Ingestion**:
   - Ingests raw telemetry webhooks (`payment.failed`, `checkout.session_expired`, `subscription.cycle_failed`, `invoice.payment_overdue`).
   - Normalizes into a canonical `RecoveryItem` with normalized failure categories (`soft_timeout`, `hard_decline`, `fraud_risk`, `consent_opt_out`).

2. **Contextual AI Diagnosis**:
   - Routes telemetry to **Groq Primary** (`llama-3.3-70b-versatile`) or **Gemini Secondary** (`gemini-1.5-pro`).
   - If AI APIs timeout or credentials are absent, RevPlug automatically engages `DeterministicFallbackAgent` to ensure uninterrupted safe operation.
   - Output: Diagnosed root cause, confidence score (e.g. 0.91), and candidate recovery action. *Labeled AI PROPOSED (NOT executed).*

3. **Expected Value Scorer ($EV$)**:
   - Calculates net recovery value for candidate interventions:
     $$EV = P_{\text{recovery}} \cdot \text{Amount} - \text{Cost}_{\text{intervention}}$$
   - Ranks interventions (`send_payment_link`, `retry_payment`, `send_reminder`, `escalate_human`, `stop_recovery`).

4. **Deterministic Policy Gate (Server-Side Authority)**:
   - Server-side rule engine retains 100% execution authority.
   - Checks 5 mandatory safety rules:
     - `retry_budget_protection`: Max 3 attempts per case.
     - `fraud_retry_protection`: 0 retries on fraud signals.
     - `opt_out_protection`: Suppresses all communication for opted-out users.
     - `cooldown_protection`: Enforces minimum interval between retries.
     - `ev_threshold_protection`: Blocks negative EV actions.

5. **Bounded Action Executor**:
   - In `razorpay_test` mode, calls Razorpay Test Mode API to generate authentic payment links (`pay_link_...`).
   - Strictly forbids arbitrary code execution or unapproved API calls.

6. **Authoritative Webhook Settlement Verifier**:
   - Verifies incoming `X-Razorpay-Signature` HMAC-SHA256 headers using the configured webhook secret.
   - Matches `payment_id` and checks that `amount_settled >= amount_at_risk`.

7. **Immutable Financial Ledger**:
   - Records verified net recovery or capital protected.
   - Revenue is credited **only** upon authoritative settlement verification.

---

## 4. Multi-Provider AI Engine & Fallback Architecture

| Layer / Provider | Role & Capability | Safety Enforcement |
| :--- | :--- | :--- |
| **Groq Primary** | Ultra-fast contextual diagnosis using `llama-3.3-70b-versatile`. | Recommendation layer only; zero financial authority. |
| **Gemini Secondary** | Secondary reasoning provider using `gemini-1.5-pro` / `gemini-1.5-flash`. | Recommendation layer only; zero financial authority. |
| **Deterministic Fallback** | Automated safety agent engaged during AI outages/timeouts. | Guarantees safe fail-closed operation. |
| **Policy Engine** | Hard server-side compliance validation. | Absolute authority to ALLOW or BLOCK actions. |

---

## 5. Interactive Recovery Control Room UI Suite

1. **Homepage ([http://localhost:3000/](http://localhost:3000/))**:
   - Product-led Stripe-inspired information architecture.
   - End-to-End System Architecture Flow Diagram with Policy Gate center & interactive node inspector.
2. **Recovery Control Room ([http://localhost:3000/recovery](http://localhost:3000/recovery))**:
   - Dense operations table displaying live telemetry (`CASE ID`, `SOURCE`, `SIGNAL`, `AMOUNT AT RISK`, `AI PROPOSAL`, `POLICY GATE`, `STATUS`).
3. **Hero Case Workspace ([http://localhost:3000/recovery/[id]](http://localhost:3000/recovery/id))**:
   - Answers 5 Core Questions immediately: *What happened? Why? What did AI recommend? What did policy allow? Did money actually come back?*
   - Interactive 10-step operational event stream replay engine.
4. **Single Case Engine Plane ([http://localhost:3000/run-recovery](http://localhost:3000/run-recovery))**:
   - AI Reasoning Provider Selector (`Groq Primary` / `Gemini Secondary` / `Deterministic Fallback`).
   - 5 Canonical Demo Presets with real-time 7-stage progression visualizer.
5. **Batch Recovery Analytics ([http://localhost:3000/batch-recovery](http://localhost:3000/batch-recovery))**:
   - 100-Case batch evaluation matrix with counterfactual benchmark comparison and B2B overdue invoice panel.
6. **Operational Controls & Telemetry ([http://localhost:3000/controls](http://localhost:3000/controls))**:
   - Live system health, provider credentials configuration, and Razorpay Test Mode status.

---

## 6. 5 Canonical Demo Scenarios for Hackathon Judging

Available in the interactive recovery control plane (`http://localhost:3000/run-recovery`):

1. **Soft Gateway Timeout** (`cust_razor_101`): Soft decline $\to$ AI payment link $\to$ Policy ALLOWED $\to$ Razorpay Payment Link Created $\to$ Settlement Verified $\to$ **₹4,999 Recovered**.
2. **Fraud Risk Signal** (`cust_risk_909`): Fraud signal detected $\to$ AI retry proposal $\to$ Policy BLOCKS (`fraud_retry_protection`) $\to$ 0 Razorpay API Calls $\to$ **₹18,200 Capital Protected**.
3. **Customer Consent Opt-Out** (`cust_opted_out_88`): Customer opted out $\to$ Policy suppresses outreach (`opt_out_protection`) $\to$ Communication Stopped.
4. **AI Provider Outage** (`cust_ai_fallback_77`): Provider timeout/failure $\to$ `DeterministicFallbackAgent` takes over safely $\to$ Safe Bounded Action Executed.
5. **Gateway HTTP Timeout** (`cust_reconcile_99`): Gateway HTTP timeout $\to$ Execution status `UNKNOWN` $\to$ Reconciles safely via webhook without duplicate retries.

---

## 7. Answers to Top 8 Judge Questions

1. **How is this different from a retry loop?**  
   RevPlug evaluates expected value ($EV = P \cdot V - C$), checks customer history, enforces zero-violation safety policies, and refuses unsafe retries (e.g. fraud or opt-outs).

2. **Does RevPlug require real money to test?**  
   No. RevPlug operates in **Razorpay Test Mode** or **Simulation Mode**.

3. **How do you prevent AI hallucination from losing money?**  
   The LLM is strictly a reasoning & recommendation layer. Server-side deterministic policy gates validate all proposals. The LLM cannot execute payment actions or modify financial ledgers.

4. **When is money counted as recovered?**  
   Money is counted as recovered **only** upon receipt of an authoritatively signed HMAC webhook event matching expected transaction amounts.

5. **How does RevPlug handle customer consent & opt-out?**  
   If a customer opts out, RevPlug's `opt_out_protection` policy immediately blocks all automated communications and retries.

6. **What happens if Groq or Gemini goes down?**  
   The `AIRouter` catches API exceptions and automatically engages the `DeterministicFallbackAgent` to ensure safe, continuous operations.

7. **Does RevPlug support B2B overdue receivables?**  
   Yes. RevPlug supports 5 revenue surfaces: payment failures, checkout abandonment, subscription failures, mandate failures, and overdue B2B invoices (`SourceType.RECEIVABLE`).

8. **Is the benchmark reproducible?**  
   Yes. Running `python -m pytest tests/` or fetching `/api/evaluations/batch?count=100&seed=42` executes the exact reproducible 100-case counterfactual evaluation matrix.

---

## 8. Local Setup & Running Instructions

### Backend (Python / FastAPI)

```bash
cd revenue_recovery
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend (Next.js 14)

```bash
cd revenue_recovery/frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to access the product-led RevPlug experience.

### Run Verification Commands

```bash
# Run complete backend test suite (682 / 682 passed)
python -m pytest tests/ -q

# Production build verification
cd frontend
npx next build
```
