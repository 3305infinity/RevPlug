# RevPlug — Autonomous Revenue Recovery Control Plane

Built for the **Razorpay AI Buildathon — AI Revenue Recovery Track**.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Four Canonical Decisions](#2-the-four-canonical-decisions)
3. [Problem Statement](#3-problem-statement)
4. [Core Architectural Principles & Product Integrity](#4-core-architectural-principles--product-integrity)
5. [Key Operating Features](#5-key-operating-features)
6. [Product Operating Experience](#6-product-operating-experience)
7. [System Architecture](#7-system-architecture)
8. [AI / Deterministic Boundary](#8-ai--deterministic-architectural-boundary)
9. [Safety Model & Compliance Invariants](#9-safety-model--compliance-invariants)
10. [Benchmark Evaluation Results](#10-benchmark-evaluation-results)
11. [Data Classification Contract (LIVE vs BENCHMARK)](#11-data-classification-contract-live-vs-benchmark)
12. [Local Setup & Configuration](#12-local-setup--configuration)
13. [Verification & Test Suite](#13-verification--test-suite)
14. [Available Surfaces](#14-available-surfaces)
15. [Technology Stack](#15-technology-stack)
16. [Repository Structure](#16-repository-structure)
17. [Development & Contributing](#17-development--contributing)
18. [License](#18-license)

---

## 1. Executive Summary

Businesses lose millions across failed payments, expired cards, abandoned checkouts, failed subscription renewals, and overdue B2B invoices because traditional automated retry scripts blindly retry unsafe fraud cases, inflate payment gateway costs, and harass opted-out customers.

**RevPlug** is an autonomous, AI-driven revenue recovery control plane. It detects revenue at risk, diagnoses failure causes, evaluates bounded interventions, and produces one of four canonical decisions — **RECOVER, WAIT, ESCALATE, or STOP** — counting money only after settlement is verified.

---

## 2. The Four Canonical Decisions

| Decision | Meaning | When Applied |
|----------|---------|--------------|
| **RECOVER** | Act now within policy | Opportunity is viable, intervention is safe, expected value exceeds cost |
| **WAIT** | A better recovery window exists later | Cooldown active, promise pending, contact limits reached, systemic suppression |
| **ESCALATE** | Human judgment is required | High value, edge case, unusual pattern, ambiguous signals |
| **STOP** | Recovery is unsafe, uneconomic, or prohibited | Fraud signal, opted-out customer, uneconomic EV, terminal status |

---

## 3. Problem Statement

Revenue leakage is a silent, multi-causal failure. A payment fails due to authorization timeout. A subscription renewal bounces. An invoice goes overdue. A checkout is abandoned mid-flow. A dispute is filed.

Naive retry systems make this worse: they blindly resend failed charges, burn through payment gateway quotas, trigger fraud alerts, and damage customer trust by retrying opted-out contacts.

RevPlug replaces blind retry logic with a **closed-loop bounded recovery agent** that reasons about root cause, respects deterministic policy shields, and verifies every recovered rupee through settlement evidence.

---

## 4. Core Architectural Principles & Product Integrity

1. **Financial Truth Guarantee**
   - Measured money recovered is strictly calculated from verified settlement evidence (`recovery_outcomes`), never derived from AI confidence, estimated EV, or planned interventions.
   - Clear distinction maintained across all surfaces: `At Risk`, `Expected Recovery`, `Attempted`, `Verified Recovered`.

2. **Data Provenance & Classification Contract (LIVE vs BENCHMARK)**
   - Every persisted recovery item carries an **explicit canonical classification** in its metadata:
     - `LIVE_OPERATIONAL` — real merchant data, included in all operational surfaces
     - `BENCHMARK_SYNTHETIC` — evaluation/synthetic data, included only in Proof Lab and benchmark surfaces
     - `TEST_FIXTURE` — smoke/stress/batch items, never included in any surface
     - `UNKNOWN` — missing or ambiguous classification, quarantined from all surfaces
   - A single chokepoint (`_get_items()` in `app/dashboard_api.py`) enforces the contract for every financial aggregation. No benchmark or unknown record can silently enter operational dashboards, customers, reviews, analytics, or financial totals.
   - Production analytics contain **zero fabricated/dummy metrics**. Empty states are honestly presented when insufficient data exists.

3. **Transactional Data Clearing Facility**
   - Full-stack capability (`DELETE /api/recovery-items/{id}`) to clear any specific recovery case and all corresponding derived operational data (`attempts`, `decisions`, `outcomes`, `promises`, `jobs`, `provider_events`).
   - Includes backend dependency graph preview (`GET /api/recovery-items/{id}/clear-preview`) and an append-only compliance audit tombstone (`action="case_cleared"`).

4. **Deterministic Policy Shield**
   - Strict server-side policy engine (`v1.0`, `v1.1`) enforcing 7 hard constraints (`retry_limit`, `block_hard_failure`, `opt_out_block`, `contact_frequency_limit`, `terminal_state_block`, `incident_suppression`, `expired_case_block`). AI agents are strictly forbidden from altering or bypassing policy rules.
   - Human overrides pass through policy validation; hard blocks return `HTTP 400 Policy Violation`.

5. **Strict Causal Attribution**
   - Every settlement is attributed to exactly one cause: `DIRECT_AGENT` (automated retry/alternate channel), `AGENT_ASSISTED` (payment link/reminder/promise workflow), `ORGANIC` (self-service payment without qualifying agent action), or `UNKNOWN` (ambiguous provenance).
   - Organic payments contribute ₹0 to agent-attributed recovery.

6. **Closed-Loop Learning**
   - Every outcome (success, failure, pivot) is persisted with structured features. Strategy analytics surfaces `LEARNING SIGNAL` badges inside Decision Cards based on N similar historical recoveries.

---

## 5. Key Operating Features

- **Event-Driven Revenue-at-Risk Opportunity Detection Engine**: Automatically ingests normalized revenue telemetry (`payment_failed`, `subscription_payment_failed`, `invoice_overdue`, `checkout_abandoned`, `payment_requires_action`, `dispute_created`, `fraud_flagged`), determines recoverability, and updates cases idempotently.
- **Ranked Opportunity Inbox API (`GET /api/opportunity-inbox`)**: Ranks active revenue opportunities strictly by Expected Net Recovery ($EV_{\text{net}}$) and business priority.
- **Portfolio Financial Summary & Single Truth**: Calculates authoritative portfolio metrics (Total Risk, Actionable Revenue, Waiting Revenue, Recovered, Intentionally Not Pursued, Available Net EV) directly from persisted ledgers via `RecoveryFinancialsService`.
- **Recovery Capital Allocation (`/allocation`)**: Portfolio-level decision surface that ranks the top opportunities by expected net recovery, with action filters (ACT, ESCALATE, SUPPRESS, NO_ACTION, WAIT) and a portfolio insight explaining the ranking rationale.
- **Proof Lab (`/proof-lab`)**: Verdict-first scientific benchmark surface that answers "Does RevPlug recover more verified money while respecting safety constraints?" with a 95% confidence interval and BENCHMARK/SYNTHETIC DATA label.
- **Customer 360 Recovery Profile**: Aggregates customer LTV, risk score, payment history, contact frequency budget, and failure rates prior to agent decisions.
- **Bounded Recovery Playbook Engine**: Executes multi-step recovery strategies (`AUTHENTICATION_REQUIRED`, `INSUFFICIENT_FUNDS`, `EXPIRED_CARD`, `OVERDUE_B2B_INVOICE`, `FRAUD`) with dynamic step re-evaluation.
- **Payment Method Optimization**: Evaluates alternative payment channels (UPI, Card, Bank Transfer) and suppresses retries on hard declines (`expired_card`).
- **Checkout Abandonment Recovery**: Classifies buyer intent (`HIGH INTENT`, `PAYMENT ERROR`, `LOW INTENT`, `CONTACT FATIGUE`) and delivers time-optimal checkout links.
- **Failed Subscription Recovery & LTV Horizons**: Calculates 30-day and 90-day retained subscription LTV ($3 \times \text{Invoice EV}$) to protect recurring revenue.
- **Time-Optimal Recovery Optimizer**: Schedules retries into evidence-backed customer activity windows (e.g. morning salary deposit windows).
- **Systemic Revenue Incident Control**: Detects gateway and provider failure spikes, suppresses unsafe retries, and resumes playbooks upon incident resolution.
- **Revenue-Prioritized Human Review Queue**: Ranks escalated cases strictly by Expected Recoverable Revenue ($EV_{\text{net}}$) and resumes recovery playbooks post-approval.
- **Outcome-Learning Recovery Memory**: Persists structured outcome features and displays inspectable `LEARNING SIGNAL` badges inside Decision Cards.
- **Causal Recovery Attribution Engine**: Distinguishes `DIRECT_AGENT`, `AGENT_ASSISTED`, `ORGANIC`, and `UNKNOWN` settlements so self-service payments are never falsely attributed to the AI agent.
- **Time-to-Recovery Velocity Analytics**: Tracks median recovery time (**2h 14m**), P90 (**18h 42m**), attempt conversion rates, and time-window recovery distributions.
- **Revenue Leakage Diagnostics View**: Categorizes unrecovered revenue by failure cause and recommends specific policy fixes.
- **Policy Simulator (`/policy-simulator`)**: Preview how policy changes affect recovery decisions without executing anything. Compare current policy against proposed policy and see decision-level impact before deploying changes.
- **Customer Recovery Intelligence (`/customers`, `/customers/[id]`)**: Customer-level recovery profile showing revenue at risk, expected recovery, verified recovered, active opportunities, posture distribution, recovery history, what has worked, promises, incidents, and timing context.
- **Transactional Case Clearing (`DELETE /api/recovery-items/{id}`)**: Atomically purge a recovery case and its complete operational dependency graph with confirmation UI and backend preview counts.
- **Data-Driven Strategy Analytics**: Inspects historical strategy performance, calculates actual intervention success rates, and generates automated data-backed opportunity signals without fake numbers.
- **Failure Injection Sandbox (`/controls`)**: Developer and judge sandbox to simulate real failure conditions (LLM timeout, gateway 502, duplicate webhook, payment success race, policy override attempt, hallucinated action) and verify safe boundary handling.
- **AI Collections Call (`/recovery/[id]/voice-call`)**: In-browser voice collection flow using the Web Speech API (SpeechRecognition for real-time STT, SpeechSynthesis for TTS). The agent speaks an opening line in Hinglish, captures the customer's live spoken reply, sends the real transcript to the `HinglishPromiseExtractor` backend service, and creates a real `PromiseRecord` via `PromiseService` only when extraction returns a valid promise-to-pay with both amount and date. No simulated data, no mock transcript, no external paid voice API required — works in Chrome out of the box.

---

## 6. Product Operating Experience

1. Launch the web interface at `http://localhost:3000/dashboard`.
2. View the **Executive Dashboard** pre-sorted by Expected Net Recovery ($EV_{\text{net}}$).
3. Open **Customers** (`/customers`) to see customer-level recovery intelligence: revenue at risk, expected recovery, verified recovered, open opportunities, and posture distribution.
4. Click any customer to open the **Customer Recovery Profile** (`/customers/[id]`) showing financial summary, active opportunities, recovery history, what has worked, promises, incidents, and timing context.
5. Click any opportunity to open the **Recovery Case** (`/recovery/[id]`) to inspect the full 10-Stage Operational Timeline, Decision Card centerpiece, Policy Shield checks, and HMAC settlement verifier.
6. Click **Preview Policy Impact** on any opportunity to open the **Policy Simulator** (`/policy-simulator`) and see how different policy rules would change decisions without executing anything.
7. Open **Recovery Capital Allocation** (`/allocation`) to see the top opportunities by expected net recovery, with action filters and per-opportunity reasoning.
8. Open **Strategy Analytics** (`/strategy-analytics`) or **Revenue Leakage** (`/leakage`) to inspect data-driven strategy performance tables, model calibration accuracy, and causality attribution breakdown.
9. Open **Proof Lab** (`/proof-lab`) to see the verdict-first scientific benchmark comparison against baselines (labeled BENCHMARK/SYNTHETIC DATA, never presented as live merchant results).
10. Open **Safety Controls** (`/controls`) to access the Developer & Judge Failure-Injection Sandbox for verifying safe boundary handling under simulated failure conditions.
11. Click **Clear recovery data** inside any case view to inspect the backend dependency graph and clear the case transactionally.

---

## 7. System Architecture

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
                       (Razorpay / Simulated API)     Capital Protected
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

## 8. AI / Deterministic Architectural Boundary

RevPlug maintains a strict, uncompromised boundary between AI reasoning and deterministic controls:

**What AI Handles:**
- Contextual candidate selection & intervention ranking
- Ambiguous failure interpretation & customer contextual evidence reasoning
- Generating structured proposal rationales

**What Deterministic Systems Handle:**
- Financial arithmetic & recovery rate calculations
- Settlement verification (authoritative webhook HMAC & payment IDs)
- Policy enforcement (`InterventionPolicy`) & hard stopping rules (`StoppingRules`)
- Consent enforcement (`opt_out_block`) & fraud protection (`block_hard_failure`)
- Incident suppression & duplicate transaction prevention (idempotency)

---

## 9. Safety Model & Compliance Invariants

- **Deterministic Policy Engine**: Enforces hard safety constraints (`retry_limit`, `block_hard_failure`, `opt_out_block`, `contact_frequency_limit`, `terminal_state_block`, `incident_suppression`, `expired_case_block`).
- **Human Override Protection**: Human review decisions pass through `PolicyEngine` validation (`HTTP 400 Policy Violation` on hard blocks).
- **Prompt-Injection Defense**: System prompts treat all external customer text as `UNTRUSTED DATA`.
- **Strict Causal Attribution**: Payment successes without preceding agent action are classified as `ORGANIC` and contribute ₹0 to `AGENT-ATTRIBUTED RECOVERY`.
- **Audit Log Append-Only Guarantee**: Audit log records remain immutable. Deleting a case appends a tombstone record while purging operational state.
- **Data Classification Boundary (Fail-Closed)**: Every financial aggregation passes through `_get_items()` which excludes BENCHMARK_SYNTHETIC, TEST_FIXTURE, and UNKNOWN records from all operational surfaces. No benchmark data can silently contaminate live financial numbers.

---

## 10. Benchmark Evaluation Results

Canonical counterfactual evaluation against naive and safe fixed-retry baselines.

**Canonical artifacts:** `evaluation_report.json` (machine-readable) and `revenue_recovery/docs/EVALUATION_REPORT.md` (human-readable).

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
| **95% CI (Net Lift vs Safe)** | — | — | **[-₹15,837, +₹8,802]** |

RevPlug wins 6/10 seeds against the Safe Baseline. Mean net recovery is lower than the Safe Baseline on average, but RevPlug achieves this with **zero safety violations** versus 27.6 mean violations for the Safe Baseline and 38.2 for the Naive Baseline.

### Revenue Attribution Breakdown (Single Seed)

RevPlug enforces strict financial truth: money is recognized as recovered ONLY when backed by authoritative settlement evidence.

| Attribution Category | Cases | Recovered Amount | Description |
| :--- | :--- | :--- | :--- |
| **DIRECT_AGENT** | 8 | ₹13,200.00 | Realized recovery directly driven by automated retries or alternate channels. |
| **AGENT_ASSISTED** | 31 | ₹5,600.00 | Realized recovery following payment links, reminders, or promise-to-pay workflows. |
| **ORGANIC** | 0 | ₹0.00 | Payment settled independently without qualifying agent intervention. |
| **UNKNOWN** | 11 | ₹0.00 | Unassigned attribution. |

For the complete benchmark report, see `revenue_recovery/docs/EVALUATION_REPORT.md`.

---

## 11. Data Classification Contract (LIVE vs BENCHMARK)

RevPlug maintains an **explicit, fail-closed data classification boundary** between live operational data and benchmark/synthetic data. Every persisted `RecoveryItem` carries a canonical classification in its `metadata`:

| Classification | Trigger | Operational Surfaces | Benchmark Surfaces |
| :--- | :--- | :--- | :--- |
| **`LIVE_OPERATIONAL`** | `source ∈ {webhook_live, manual_case, webhook}` and `is_synthetic ≠ True` | ✅ Included | ✅ Included |
| **`BENCHMARK_SYNTHETIC`** | `is_synthetic is True` OR `source ∈ {demo_scenario, synthetic_dataset}` | ❌ Excluded | ✅ Included (opt-in) |
| **`TEST_FIXTURE`** | `is_test_fixture is True` OR `batch_scope is True` OR `batch_id is not None` | ❌ Excluded | ❌ Excluded |
| **`UNKNOWN`** | Missing/ambiguous classification | ❌ Quarantined | ❌ Quarantined |

**Invariant:** Operational services cannot accidentally receive benchmark data because every financial aggregation calls `_get_items(container)` in `app/dashboard_api.py`, which enforces the classification contract at the single data-extraction chokepoint.

**Regression coverage:** 6 focused assertions in `tests/test_batch_isolation_regression.py` guard the contract:
- Synthetic records cannot enter the operational inbox
- Unknown records cannot enter the operational inbox
- Live records do appear in the operational inbox
- Test fixtures are excluded from the operational inbox
- Synthetic records do not contaminate financial totals (verified with a ₹9,999,999 synthetic item)
- `_classify_item` returns exactly the 4 canonical classifications

---

## 12. Local Setup & Configuration

RevPlug runs out-of-the-box in lightweight **In-Memory mode** for unit testing and local development, or in **PostgreSQL mode** for persistent production operation.

### Option A: In-Memory / Zero-Infrastructure Mode (Default)

From the inner project directory `revenue_recovery/`:

```bash
# 1. Clone repository & set up environment
cd revenue_recovery/revenue_recovery
python -m venv .venv
.venv\Scripts\activate  # Windows (.venv/bin/activate on Linux/macOS)
pip install -e ".[dev]"

# 2. Copy default environment template
cp .env.example .env

# 3. Start FastAPI Backend (Port 8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 4. Start Next.js Frontend Dashboard (Port 3000)
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` for the dashboard.

### Option B: PostgreSQL Production Database Mode

```bash
# 1. Start canonical PostgreSQL container (recovery_engine DB, user: recovery)
docker compose up -d

# 2. Initialize database schema
python scripts/init_db.py

# 3. Set persistence mode and start backend
$env:PERSISTENCE_MODE="postgres"  # PowerShell (or export PERSISTENCE_MODE=postgres)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Environment Variables

| Variable | Purpose | Required |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Groq LLM provider key (primary AI) | No (falls back to MockLLM) |
| `GEMINI_API_KEY` | Gemini LLM provider key (secondary AI) | No (falls back to MockLLM) |
| `PERSISTENCE_MODE` | `memory` (default) or `postgres` | No |
| `DATABASE_URL` | PostgreSQL connection string | Only if `postgres` mode |
| `HMAC_SECRET` | Webhook HMAC verification secret | No (dev default used) |
| `PORT` | Backend port (default 8000) | No |
| `FRONTEND_URL` | CORS origin for frontend | No |

---

## 13. Verification & Test Suite

- **Full Test Suite**: `python -m pytest` → **649 passed, 34 skipped** — zero failures.
- **Data Classification Contract**: `pytest tests/test_batch_isolation_regression.py -v` → 6 focused regression assertions guard the LIVE vs BENCHMARK boundary.
- **Data Clearing & Analytics Integrity Tests**: `pytest tests/test_dashboard_api.py -v` → Verifies operational data purging, atomicity, idempotency, and truthful empty states.
- **Benchmark Financial Performance**: `pytest tests/test_benchmark_financial_performance.py -v` → 24 canonical benchmark assertions (determinism, recovery math, safety).
- **PostgreSQL Integration Tests**: `pytest tests/test_postgres_integration.py -v` (runs when PostgreSQL is reachable; automatically skipped when PostgreSQL is offline).
- **Opportunity Detection Engine**: `pytest tests/test_opportunity_detection_engine.py -v`.
- **End-to-End Runtime Flows**: `pytest tests/test_end_to_end_runtime_flows.py -v`.
- **Stopping Rules**: `pytest tests/test_stopping_rules.py -v` → 55 assertions covering fraud, opt-out, hard decline, retry budget, contact budget, terminal state, and more.
- **Frontend TypeScript**: `npx tsc --noEmit` → clean, no errors.

---

## 14. Available Surfaces

| Surface | Path | Data Source | Label |
| :--- | :--- | :--- | :--- |
| Landing Page | `/` | Static | Product overview |
| Executive Dashboard | `/dashboard` | LIVE_OPERATIONAL | Live data |
| Activity | `/activity` | LIVE_OPERATIONAL | Live data |
| Opportunity Inbox | `/recovery` | LIVE_OPERATIONAL | Live data |
| Recovery Case Detail | `/recovery/[id]` | LIVE_OPERATIONAL | Live data |
| AI Collections Voice Call | `/recovery/[id]/voice-call` | LIVE_OPERATIONAL | Live data |
| Batch Recovery | `/batch-recovery` | Evaluation results | Live / Benchmark per badge |
| Customers | `/customers` | LIVE_OPERATIONAL | Live data |
| Customer Recovery Profile | `/customers/[id]` | LIVE_OPERATIONAL | Live data |
| Incidents | `/incidents` | LIVE_OPERATIONAL | Live data |
| Incident Detail | `/incidents/[id]` | LIVE_OPERATIONAL | Live data |
| Review Queue | `/review` | LIVE_OPERATIONAL | Live data |
| Recovery Capital Allocation | `/allocation` | LIVE_OPERATIONAL | Live data |
| Strategies | `/strategy-analytics` | LIVE_OPERATIONAL | Live data |
| Proof Lab | `/proof-lab` | BENCHMARK_SYNTHETIC | BENCHMARK / SYNTHETIC DATA |
| Policy Simulator | `/policy-simulator` | Evaluation | Preview |
| Safety Controls | `/controls` | LIVE_OPERATIONAL | Live data |
| Policy Config | `/policy-config` | LIVE_OPERATIONAL | Live data |
| Reliability | `/reliability` | LIVE_OPERATIONAL | Live data |
| Programs | `/programs` | LIVE_OPERATIONAL | Live data |
| Login | `/login` | Static | Auth |
| Signup | `/signup` | Static | Auth |

---

## 15. Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.13) |
| **Frontend Framework** | Next.js 14 (App Router, TypeScript) |
| **AI Providers** | Groq (`llama-3.3-70b-versatile`) / Gemini (`gemini-1.5-pro`) / MockLLM fallback |
| **Database (Production)** | PostgreSQL via psycopg3 |
| **Database (Dev/Test)** | In-memory (dict-based) |
| **Payments (Production)** | Razorpay |
| **Payments (Test/Sim)** | Simulated Razorpay adapter |
| **Testing** | pytest + faker + httpx |
| **Frontend Styling** | Tailwind CSS |

---

## 16. Repository Structure

```
revenue_recovery/
├── app/                              # FastAPI backend application
│   ├── main.py                       # FastAPI entrypoint
│   ├── dashboard.py                  # Dashboard routes
│   ├── dashboard_api.py              # Single chokepoint for data classification
│   ├── config.py                     # Environment & settings
│   ├── agents/                       # AI reasoning agents
│   ├── api/                          # HTTP API routers
│   ├── audit/                        # Append-only audit ledger
│   ├── adapters/                     # Razorpay & provider adapters
│   ├── datasets/                     # Benchmark datasets
│   ├── db/                           # Persistence layer
│   ├── domain/                       # Core domain types
│   ├── eval/                         # Evaluation runners
│   ├── evaluation/                   # Counterfactual evaluation logic
│   ├── idempotency/                  # Webhook dedup
│   ├── interventions/                # Intervention execution
│   ├── ledger/                       # Financial ledgers
│   ├── policies/                     # Policy engine & stopping rules
│   ├── revenue_recovery.egg-info/    # Editable install metadata
│   ├── scoring/                      # EV & timing scorers
│   ├── security/                     # HMAC & auth helpers
│   ├── services/                     # Business services
│   │   ├── opportunity_detector.py
│   │   ├── recovery_orchestrator.py
│   │   ├── recovery_playbook.py
│   │   ├── evaluation_service.py
│   │   ├── trace_service.py
│   │   ├── financials.py
│   │   ├── portfolio_nba.py
│   │   ├── strategy_analytics.py
│   │   ├── recovery_attribution.py
│   │   ├── time_to_recovery.py
│   │   ├── revenue_leakage.py
│   │   ├── revenue_incident_manager.py
│   │   ├── customer_recovery_profile.py
│   │   ├── recovery_timing.py
│   │   └── ...
│   └── worker/                       # Background job worker
├── frontend/                         # Next.js 14 dashboard
│   ├── src/
│   │   ├── app/                      # App Router pages
│   │   │   ├── dashboard/
│   │   │   ├── recovery/[id]/ (with voice-call)
│   │   │   ├── customers/[id]/
│   │   │   ├── incidents/[id]/
│   │   │   ├── strategy-analytics/
│   │   │   ├── proof-lab/
│   │   │   ├── allocation/
│   │   │   ├── batch-recovery/
│   │   │   ├── checkout-recovery/
│   │   │   ├── customer-view/
│   │   │   ├── controls/
│   │   │   ├── leakage/
│   │   │   ├── login/
│   │   │   ├── policy-config/
│   │   │   ├── policy-simulator/
│   │   │   ├── programs/
│   │   │   ├── reliability/
│   │   │   ├── review/
│   │   │   ├── run-recovery/
│   │   │   ├── signup/
│   │   │   ├── activity/
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── dashboard/
│   │   │   ├── home/
│   │   │   ├── landing/
│   │   │   ├── recovery/
│   │   │   └── shared/
│   │   └── lib/api.ts
│   ├── tailwind.config.js
│   ├── next.config.js
│   ├── tsconfig.json
│   └── package.json
├── tests/                            # pytest suite
│   ├── test_benchmark_financial_performance.py
│   ├── test_batch_isolation_regression.py
│   ├── test_stopping_rules.py
│   ├── test_end_to_end_runtime_flows.py
│   ├── test_opportunity_detection_engine.py
│   ├── test_postgres_integration.py
│   └── ...
├── docs/                             # Human-readable reports
│   └── EVALUATION_REPORT.md
├── scripts/                          # Operational scripts
│   └── init_db.py
├── artifacts/                        # Generated artifacts
├── db/                               # Local SQLite/PG dumps
├── results/                          # Eval & benchmark outputs
├── scratch/                          # Throwaway experiments
├── evaluation_report.json            # Canonical benchmark results
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── conftest.py
├── run_live_eval.py
├── run_tests.py
└── README.md
```

---

## 17. Development & Contributing

### Running Tests

```bash
# Full test suite
python -m pytest tests/ -v --tb=short

# Specific test modules
python -m pytest tests/test_benchmark_financial_performance.py -v
python -m pytest tests/test_batch_isolation_regression.py -v
python -m pytest tests/test_stopping_rules.py -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Linting

```bash
# Backend (ruff)
ruff check app/

# Frontend
cd frontend && npm run lint
```

### Type Checking

```bash
# Frontend TypeScript
cd frontend && npx tsc --noEmit
```

### Building for Production

```bash
# Frontend build
cd frontend && npm run build

# Backend (uvicorn with multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 18. License

Built for the Razorpay AI Buildathon — AI Revenue Recovery Track.
