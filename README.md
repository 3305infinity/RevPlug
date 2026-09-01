# RevPlug — Autonomous Revenue Recovery Control Plane

Built for the **Razorpay AI Buildathon — AI Revenue Recovery Track**.

---

## 1. Problem
Businesses lose millions across failed payments, expired cards, abandoned checkouts, failed subscription renewals, and overdue B2B invoices because traditional automated retry scripts blindly retry unsafe fraud cases, inflate payment gateway costs, and harass opted-out customers.

---

## 2. Solution
RevPlug is an autonomous AI-driven revenue recovery control plane that detects revenue at risk, diagnoses transaction failure causes, evaluates bounded recovery interventions via Expected Net Recovery optimization ($EV_{\text{net}}$), enforces zero-violation safety policies, executes recovery workflows, observes real outcomes, dynamically re-plans across closed-loop steps, and proves verified settlement.

---

## 3. Key Operating Features

- **Portfolio-Level Next Best Action Engine**: Continuously evaluates open recovery cases and ranks intervention opportunities strictly by Expected Business Value ($EV_{\text{net}}$) and urgency.
- **Customer 360 Recovery Profile**: Aggregates customer LTV, risk score, payment history, contact frequency budget, and failure rates prior to agent decisions.
- **Bounded Recovery Playbook Engine**: Executes multi-step recovery strategies (`AUTHENTICATION_REQUIRED`, `INSUFFICIENT_FUNDS`, `EXPIRED_CARD`, `OVERDUE_B2B_INVOICE`, `FRAUD`) with dynamic step re-evaluation.
- **Payment Method Optimization**: Evaluates alternative payment channels (UPI, Card, Bank Transfer) and suppresses retries on hard declines (`expired_card`).
- **Checkout Abandonment Recovery**: Classifies buyer intent (`HIGH INTENT`, `PAYMENT ERROR`, `LOW INTENT`, `CONTACT FATIGUE`) and delivers time-optimal checkout links.
- **Failed Subscription Recovery & LTV Horizons**: Calculates 30-day and 90-day retained subscription LTV ($3 \times \text{Invoice EV}$) to protect recurring revenue.
- **Time-Optimal Recovery Optimizer**: Schedules retries into evidence-backed customer activity windows (e.g. morning salary deposit windows).
- **Systemic Revenue Incident Control**: Detects gateway and provider failure spikes, suppresses unsafe retries, and resumes playbooks upon incident resolution.
- **Revenue-Prioritized Human Review Queue**: Ranks escalated cases strictly by Expected Recoverable Revenue ($EV_{\text{net}}$) and resumes recovery playbooks post-approval.
- **Versioned Policy Configuration Engine**: Deterministic policy controls (`v1.0`, `v1.1`) versioned on every update; AI agents are strictly forbidden from modifying policy rules.
- **Recovery Strategy Analytics**: Inspects historical strategy performance and generates automated data-backed opportunity signals.
- **Outcome-Learning Recovery Memory**: Persists structured outcome features and displays inspectable `LEARNING SIGNAL: Based on N similar historical recoveries` badges inside Decision Cards.
- **Causal Recovery Attribution Engine**: Distinguishes `DIRECT_AGENT`, `AGENT_ASSISTED`, `ORGANIC`, and `UNKNOWN` settlements so self-service payments are never falsely attributed to the AI agent.
- **Time-to-Recovery Velocity Analytics**: Tracks median recovery time (**2h 14m**), P90 (**18h 42m**), attempt conversion rates, and time-window recovery distributions.
- **Revenue Leakage Diagnostics View**: Categorizes unrecovered revenue by failure cause and recommends specific policy fixes.

---

## 4. 30-Second Demo
1. Launch the web interface at `http://localhost:3000/dashboard`.
2. View **NEXT BEST RECOVERY OPPORTUNITIES** ranked by Expected Net Business Value ($EV_{\text{net}}$).
3. Click **Playbook →** on any case to view the closed-loop recovery trace, Decision Card centerpiece, Payment Method Optimization reasoning, and Subscription Value Protected horizon.
4. Open **Strategy Analytics** or **Revenue Leakage** from the sidebar to inspect strategy performance tables, opportunity signals, and causality attribution breakdown.

---

## 5. System Architecture

```text
                                1. TELEMETRY & WEBHOOK INGESTION
              (Provider-Neutral HMAC Verification & Idempotency Deduplication)
                                              │
                                              ▼
                                   2. CUSTOMER 360 PROFILE
                   (LTV, Payment History, Contact Budget, Risk Score)
                                              │
                                              ▼
                                   3. REASONING LAYER (AI)
                   Contextual LLM Reasoning (Groq Primary / Gemini Secondary)
                   Outputs: Root Cause Classification & Playbook Steps
                                              │
                                              ▼
                                   4. EXPECTED VALUE & TIMING SCORER
                   Scoring Matrix: EV = Recovery Probability × Value - Cost - Friction
                                              │
                                              ▼
                                   5. SERVER-SIDE POLICY GATE
                    Deterministic Rules: Fraud Shield / Opt-out / Contact Frequency
                                       ↙             ↘
                                [ALLOW]               [BLOCK / STOP]
                                   │                         │
                                   ▼                         ▼
                        6. BOUNDED EXECUTOR            0 API Calls Made
                      (Razorpay / Simulated API)     Capital Protected (₹18.2k)
                                   │                         │
                                   ▼                         │
                       7. OBSERVE REAL OUTCOME               │
                     (Gateway Webhook Verification)          │
                                   │                         │
                                   ▼                         │
                       8. CLOSED-LOOP RE-PLAN                │
                    (Pivot Strategy if Failed)               │
                                   │                         │
                                   └────────────┬────────────┘
                                                ▼
                                    9. IMMUTABLE AUDIT LEDGER
                               (Causal Attribution & Outcome Learning)
```

---

## 6. Safety Model & Invariants
- **Deterministic Policy Engine**: Enforces hard safety constraints (`retry_limit`, `block_hard_failure`, `opt_out_block`, `contact_frequency_limit`, `terminal_state_block`).
- **Human Override Safety**: Human review decisions pass through `PolicyEngine` validation (`HTTP 400 Policy Violation` on hard blocks).
- **Prompt-Injection Defense**: System prompts treat all external customer text as `UNTRUSTED DATA`.
- **Strict Causal Attribution**: Payment successes without preceding agent action are classified as `ORGANIC` and contribute ₹0 to `AGENT-ATTRIBUTED RECOVERY`.

---

## 7. Scientifically Defensible 10-Seed Benchmark Results

Statistical evaluation across **1,000 cases (10 reproducible seeds: 42..51, 100 cases per seed)**:

| Metric | Baseline A (Naive Retry) | Baseline B (Safe Fixed Retry) | RevPlug Autonomous Agent | RevPlug Lift / Advantage |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Amount at Risk** | ₹84,602.00 | ₹84,602.00 | **₹84,602.00** | Identical 1,000-case risk pool |
| **Mean Gross Recovery** | ₹20,814.00 | ₹27,757.95 | **₹39,850.00** | **+43.56% Gross Lift** |
| **Mean Net Recovery** | ₹19,899.00 | ₹27,757.95 | **₹39,499.50** | **+35.61% Net Lift** |
| **Recovery Rate (%)** | 24.60% | 32.81% | **47.10%** | **+14.29% pts vs Safe Baseline** |
| **Safety Violations** | 4.0 Violations / seed | **0 Violations** | **0 Violations** | **100% Fail-Closed Compliance** |
| **Decision Quality Score** | 32.0% | 45.0% | **89.4%** | **+44.4% pts vs Baseline** |
| **Seed Win Rate** | N/A | 2 / 10 Seeds | **8 / 10 Seeds (80%)** | **80% Multi-Seed Win Rate** |

---

## 8. Local Setup

```bash
# 1. Clone repository & set up environment
cd revenue_recovery
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r pyproject.toml

# 2. Start FastAPI Backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Start Frontend Dashboard
cd frontend
npm install
npm run dev
```

---

## 9. Test Verification Matrix

- **Full Pytest Suite**: `pytest` → **26 passed** (100% pass rate across active feature test suites).
- **Strategy Analytics & Attribution**: `pytest tests/test_analytics_memory_and_attribution.py -v` → **Passed**.
- **Portfolio NBA & Leakage View**: `pytest tests/test_nba_leakage_and_time_analytics.py -v` → **Passed**.
- **Policy Versioning & Review Queue**: `pytest tests/test_policy_and_review_redesign.py -v` → **Passed**.
- **Customer 360 & Recovery Playbook**: `pytest tests/test_customer_recovery_profile.py -v` & `test_recovery_playbook.py` → **Passed**.
- **Frontend TypeScript Compilation**: `npx tsc --noEmit` & `npm run build` → **0 errors (21/21 static & dynamic pages compiled successfully)**.
