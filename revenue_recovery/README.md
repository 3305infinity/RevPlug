# RevPlug — Autonomous Revenue Recovery Control Plane

Built for the **Razorpay AI Buildathon — AI Revenue Recovery Track**.

---

## 1. Executive Summary

Businesses lose millions across failed payments, expired cards, abandoned checkouts, failed subscription renewals, and overdue B2B invoices because traditional automated retry scripts blindly retry unsafe fraud cases, inflate payment gateway costs, and harass opted-out customers.

**RevPlug** is an autonomous, AI-driven revenue recovery control plane that detects payment failures, produces a canonical recovery decision — **RECOVER, WAIT, ESCALATE, or STOP** — and counts money only after settlement is verified.

### The Four Decisions

| Decision | Meaning | When Applied |
|----------|---------|--------------|
| **RECOVER** | Act now within policy | Opportunity is viable, intervention is safe, expected value exceeds cost |
| **WAIT** | A better recovery window exists later | Cooldown active, promise pending, contact limits reached, systemic suppression |
| **ESCALATE** | Human judgment is required | High value, edge case, unusual pattern, ambiguous signals |
| **STOP** | Recovery is unsafe, uneconomic, or prohibited | Fraud signal, opted-out customer, uneconomic EV, terminal status |

---

## 2. Core Architectural Principles & Product Integrity

1. **Financial Truth Guarantee**:
   - Measured money recovered is strictly calculated from verified settlement evidence (`recovery_outcomes`), never derived from AI confidence, estimated EV, or planned interventions.
   - Clear distinction maintained across all surfaces: `Revenue at Risk`, `Expected Recovery`, `Verified Recovered`.

2. **Data Provenance & Provenance Labeling**:
   - Surfaces explicitly differentiate between `LIVE RECOVERY DATA`, `BENCHMARK / SYNTHETIC DATA`, and `VERIFIED SETTLEMENT EVIDENCE`.
   - Production analytics contain **zero fabricated/dummy metrics**. Empty states are honestly presented when insufficient data exists.

3. **Transactional Data Clearing Facility**:
   - Full-stack capability (`DELETE /api/recovery-items/{id}`) to clear any specific recovery case and all corresponding derived operational data (`attempts`, `decisions`, `outcomes`, `promises`, `jobs`, `provider_events`).
   - Includes backend dependency graph preview (`GET /api/recovery-items/{id}/clear-preview`) and an append-only compliance audit tombstone (`action="case_cleared"`).

4. **Deterministic Policy Shield**:
   - Strict server-side policy engine (`v1.0`, `v1.1`) enforcing 5 hard constraints (`retry_limit`, `block_hard_failure`, `opt_out_block`, `contact_frequency_limit`, `terminal_state_block`). AI agents are strictly forbidden from altering or bypassing policy rules.

---

## 3. Product Screens

### Operations
- **Dashboard** (`/dashboard`) — Revenue operations control plane pre-sorted by Expected Net Recovery ($EV_{\text{net}}$)
- **Activity** (`/activity`) — Decision stream: all decisions, interventions, outcomes, and settlement events
- **Incidents** (`/incidents`) — Systemic revenue incidents affecting multiple opportunities
- **Review Queue** (`/review`) — Cases requiring human review

### Recovery Intelligence
- **Customers** (`/customers`) — Customer list with revenue at risk, expected recovery, verified recovered, open opportunities
- **Customer Profile** (`/customers/[id]`) — Recovery intelligence profile: financial summary, posture, active opportunities, recovery history, what has worked, promises, incidents, timing context
- **Opportunities** (`/recovery`) — All open recovery cases
- **Recovery Case** (`/recovery/[id]`) — Full 10-stage operational timeline, decision trace, policy shield checks, settlement verifier

### Evaluation & Proof
- **Strategy Analytics** (`/strategy-analytics`) — Data-driven strategy performance tables, model calibration, causality attribution
- **Proof Lab** (`/proof-lab`) — Controlled benchmark evaluation comparing RevPlug against baselines
- **Policy Simulator** (`/policy-simulator`) — Preview how policy changes affect recovery decisions without executing anything

### Controls
- **Safety Controls** (`/controls`) — Stopping rules, policy configuration
- **Policy Config** (`/policy-config`) — Active policy settings
- **Capital Allocation** (`/allocation`) — Recovery capital management

---

## 4. Operating Experience

1. Launch the web interface at `http://localhost:3000/dashboard`
2. View **REVENUE OPERATIONS CONTROL PLANE** pre-sorted by Expected Net Recovery ($EV_{\text{net}}$)
3. Click any case (`/recovery/[id]`) to inspect the full 10-Stage Operational Timeline, Decision Card centerpiece, Policy Shield checks, and HMAC settlement verifier
4. Open **Customers** (`/customers`) to see customer-level recovery intelligence: revenue at risk, expected recovery, verified recovered, active opportunities, and posture
5. Click **Preview Policy Impact** on any opportunity to open the Policy Simulator (`/policy-simulator`) and see how different policy rules would change decisions
6. Open **Strategy Analytics** (`/strategy-analytics`) or **Proof Lab** (`/proof-lab`) to inspect data-driven strategy performance and controlled benchmark results
7. Click **Clear recovery data** inside any case view to inspect the backend dependency graph and clear the case transactionally

---

## 5. Architecture

```text
                                1. TELEMETRY & WEBHOOK INGESTION
              (Provider-Neutral HMAC Verification & Idempotency Deduplication)
                                               │
                                               ▼
                              2. OPPORTUNITY DETECTION ENGINE
                     (Root Cause Classifier & Expected Net EV Scorer)
                                               │
                                               ▼
                              3. CUSTOMER 360 RECOVERY PROFILE
                    (LTV, Payment History, Contact Budget, Risk Score)
                                               │
                                               ▼
                              4. REASONING & PLAYBOOK LAYER (AI)
                    Contextual LLM Reasoning (Groq Primary / Gemini Secondary)
                    Outputs: Bounded Strategy & Candidate Ranking
                                               │
                                               ▼
                              5. EXPECTED VALUE & TIMING SCORER
                    Scoring Formula: EV_net = Gross * P_recovery - Cost - Friction
                                               │
                                               ▼
                              6. SERVER-SIDE POLICY GATE
                     Deterministic Rules: Fraud Shield / Opt-out / Contact Budget
                                        ↙             ↘
                                 [ALLOW]               [BLOCK / STOP]
                                    │                         │
                                    ▼                         ▼
                         7. BOUNDED EXECUTOR            0 API Calls Made
                       (Razorpay / Simulated API)     Capital Protected (₹18.2k)
                                    │                         │
                                    ▼                         │
                        8. OBSERVE REAL OUTCOME               │
                      (Gateway Webhook Verification)          │
                                    │                         │
                                    ▼                         │
                        9. CLOSED-LOOP RE-PLAN                │
                     (Pivot Strategy if Failed)               │
                                    │                         │
                                    └────────────┬────────────┘
                                                 ▼
                                     10. IMMUTABLE AUDIT LEDGER
                                (Causal Attribution & Outcome Learning)
```

---

## 6. Safety Model & Compliance Invariants

- **Deterministic Policy Engine**: 5 hard safety rules (`retry_limit`, `block_hard_failure`, `opt_out_block`, `contact_frequency_limit`, `terminal_state_block`).
- **Human Override Protection**: Human escalations CANNOT bypass hard safety rules (`HTTP 400 Policy Violation`).
- **Prompt-Injection Defense**: System prompts explicitly declare all customer message text, notes, and error descriptions as `UNTRUSTED DATA`.
- **ActionRegistry Allowlist**: Validates model output action strings against an allowlist before policy or execution.
- **Audit Log Append-Only Guarantee**: Audit log records remain immutable. Deleting a case appends a tombstone record while purging operational state.

---

## 7. Benchmark Evaluation Results

Canonical counterfactual evaluation against naive and safe fixed-retry baselines.

**Canonical artifacts:** `evaluation_report.json` (machine-readable) and `docs/EVALUATION_REPORT.md` (human-readable).

### Single-Seed Detailed Trace (Seed 42, 50 cases)

| Metric | Baseline A (Naive Retry) | Baseline B (Safe Fixed Retry) | RevPlug Bounded AI Agent | RevPlug Lift / Advantage |
| :--- | :--- | :--- | :--- | :--- |
| **Total Revenue at Risk** | ₹42,674.00 | ₹42,674.00 | **₹42,674.00** | Identical risk pool |
| **Verified Recovery Rate** | 31.9% | 31.9% | **44.1%** | **+12.2% pts vs Baseline** |
| **Verified Recovered Revenue** | ₹13,608.50 | ₹13,608.50 | **₹18,800.00** | **+₹5,191.50** |
| **Net Recovered Revenue** | ₹13,153.50 | ₹13,213.50 | **₹18,693.00** | **+₹5,479.50 (+41.5%)** |
| **Intervention Cost** | ₹455.00 | ₹395.00 | **₹107.00** | **-₹348.00 Cost Savings** |
| **AI Proposals (of 50 cases)** | — | — | **30 AI proposals; 8 accepted; 22 rejected by policy; 9 fallbacks** | — |
| **Safety Policy Violations** | **17** | **0** | **0** | **-100% Policy Violations** |

### Multi-Seed Statistical Robustness (10 seeds, 1000 cases total)

| Metric | Baseline A (Naive Retry) | Baseline B (Safe Retry) | RevPlug Autonomous Agent |
| :--- | :--- | :--- | :--- |
| **Mean Gross Recovery** | ₹33,799.15 | ₹33,799.15 | **₹29,647.00** |
| **Mean Net Recovery** | ₹32,865.65 | ₹32,971.65 | **₹29,454.30** |
| **Mean Recovery Rate** | 31.0% | 31.0% | **27.2%** |
| **Mean Safety Violations** | 38.2 | 27.6 | **0.0** |
| **RevPlug Win Rate vs Safe** | — | — | **6/10 seeds (60%)** |

RevPlug wins 6/10 seeds against the Safe Baseline. Mean net recovery is lower than the Safe Baseline on average, but RevPlug achieves this with **zero safety violations** versus 27.6 mean violations for the Safe Baseline and 38.2 for the Naive Baseline.

For the complete benchmark report, see [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md).

---

## 8. Verification & Test Suite

- **Default Test Suite**: `python -m pytest` → **649 passed, 34 skipped, 0 failed**.
- **Data Clearing & Analytics Integrity Tests**: `pytest tests/test_dashboard_api.py -v` → Verifies operational data purging, atomicity, idempotency, and truthful empty states.
- **PostgreSQL Integration Tests**: `pytest tests/test_postgres_integration.py -v` (runs when PostgreSQL is reachable; automatically skipped when PostgreSQL is offline).
- **Frontend Build**: `npx tsc --noEmit` & `npm run build` → **0 errors (24 routes compiled successfully)**.
- **AI & Decision Tests**: Agent routing, fallback behavior, timing intelligence, and policy evaluation tests all pass.
- **Financial Truth Tests**: Settlement attribution, verified/unverified recovery, and intervention cost accounting validated.
- **Trace State Tests**: Full 10-stage operational timeline and decision trace integrity verified.

---

## 9. Running the Application

```bash
# Backend (from revenue_recovery/ directory)
cd revenue_recovery
python -m uvicorn app.main:app --reload --port 8000

# Frontend (from revenue_recovery/frontend/ directory)
cd frontend
npm run dev
```

Open `http://localhost:3000` to see the landing page, then navigate to `/dashboard` for the control plane.
