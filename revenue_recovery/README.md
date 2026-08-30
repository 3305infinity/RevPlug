# RecoverOS

> Autonomous revenue-recovery control plane enforcing deterministic policy safety, financial value scoring, and verified outcome settlement.

---

## What is RecoverOS?

Revenue is lost across five distinct surfaces: payment gateway failures, abandoned checkouts, failed subscription renewals, overdue B2B receivables, and mandate debit failures. Naively retrying every failed transaction inflates intervention costs, frustrates customers, risks payment processor penalties, and retries unsafe fraud or opted-out cases.

RecoverOS provides an **autonomous control plane** designed around a single architectural foundation:

$$\text{Detect} \longrightarrow \text{Diagnose} \longrightarrow \text{Score} \longrightarrow \text{Guard} \longrightarrow \text{Execute} \longrightarrow \text{Verify} \longrightarrow \text{Record}$$

AI/LLM models recommend interventions, but **they do not hold execution authority**. Pure deterministic logic—policy safety guards, stopping rules, proposal validation, expected-value scoring, and payment settlement verification—remains the sole financial authority.

---

## Why RecoverOS?

| Capability | Naive Retry Automation | RecoverOS Control Plane |
| :--- | :--- | :--- |
| **Strategy** | Retries payment fixed $N$ times blindly | Contextual intervention tailored per revenue surface |
| **Safety** | Retries fraud, hard declines, opted-out users | Policy guard blocks fraud, hard declines, & opt-outs |
| **Financial Logic** | Ignores retry cost vs transaction value | Deterministic Expected Value scoring ($EV = P \times V - C$) |
| **Promise-to-Pay** | Overwrites active promises with retries | Hinglish extraction; pauses retries while promise active |
| **Verification** | Assumes executed action = recovered money | Requires verified payment settlement before recording revenue |
| **Auditability** | Ephemeral or missing logs | Immutable append-only audit trail for every state transition |

---

## The Recovery Pipeline

Every revenue opportunity passes through an 11-stage canonical lifecycle:

1. **`RecoveryItem` Creation**: Normalizes raw webhook events or synthetic opportunities into a unified canonical schema (`amount_minor`, `source_type`, `customer_id`, `created_at`).
2. **Diagnosis**: Classifies the root cause (`soft`, `hard`, `fraud`, `authentication_required`, `unknown`). Uses deterministic rule matching first, falling back to LLM analysis for ambiguous intent.
3. **Expected Value Scoring**: Computes $EV = \text{Amount} \times \text{Probability} - \text{Intervention Cost}$ to determine if recovery is net-positive.
4. **Recommendation**: Decision agent generates a structured `RecoveryProposal` specifying an action, reasoning, and confidence score.
5. **Proposal Validation**: `ProposalValidator` enforces the closed action set and schema constraints. Malformed proposals fail closed.
6. **Stopping Rules**: Evaluates absorbing terminal rules (fraud, customer opt-out, active promises, exhausted attempt budgets, cancelled subscriptions).
7. **Policy / Safety Guard**: `InterventionPolicy` evaluates mandatory rules. Unsafe actions return `DENY` or `ESCALATE`.
8. **Execution**: Policy-approved actions are dispatched through `RecoveryExecutor` (e.g. payment retry, payment link SMS/Email, channel escalation).
9. **Verification**: Holds execution in `pending_verification` until payment settlement is verified by gateway webhook or invoice status.
10. **Outcome**: Records a canonical `RecoveryOutcome` containing verified actual recovery amount and intervention cost.
11. **Audit**: Logs structured `AuditEvent` records to an append-only audit store.

---

## Supported Revenue Surfaces

RecoverOS supports five canonical revenue surfaces:

1. **Payment Failure**: Gateway authorizations (Razorpay, Stripe) with soft declines, card timeouts, or technical errors. Supports retry policies with backoff.
2. **Checkout Abandonment**: Cart drop-offs. Evaluates checkout age, stage, and cart value to dispatch payment links or customer reminders.
3. **Subscription Failure**: Recurring billing failures. Handles token errors, mandate declines, and grace period execution.
4. **Overdue Receivables**: B2B unpaid invoices. Evaluates aging metrics and applies a deterministic escalation ladder based on days overdue.
5. **Mandate Failure**: Auto-pay mandate failures (e.g., NACH / e-Mandate). Evaluates retry eligibility based on bank error codes.

---

## Intelligence + Deterministic Control

RecoverOS combines rules-first deterministic decisioning with LLM ambiguity resolution:

- **Rules-First Diagnosis**: Known gateway response codes (e.g., `payment_timed_out`, `insufficient_funds`, `payment_risk_check_failed`) are classified deterministically without LLM latency or cost.
- **LLM Fallback**: Ambiguous customer text or unstructured payloads route to the LLM decision agent.
- **Proposal Object**: LLM output is treated purely as a `RecoveryProposal`. It has zero execution privilege.
- **Closed Action Set**: Enforces a strict closed action enum:
  - `retry_payment`
  - `send_payment_link`
  - `send_reminder`
  - `send_customer_message`
  - `alternate_channel`
  - `promise_to_pay`
  - `escalate_human`
  - `stop_recovery`
  - `no_action`
- **Fail-Closed Validation**: Any action outside the closed set (e.g. `give_customer_50_percent_discount`) throws a `ProposalValidationError` and is rejected immediately.
- **Hard Safety Override Prevention**: Human approvals via `/api/recovery-items/{id}/approve` must pass through the policy engine. Human approval of a hard safety violation (e.g., retrying fraud or contacting an opted-out user) is **denied by policy**.

---

## Financial Decisioning

RecoverOS uses a deterministic Expected Value ($EV$) model to prevent unprofitable or unsafe recovery attempts.

### Expected Value Formula

$$EV = (\text{Amount at Risk} \times P_{\text{recovery}}) - C_{\text{intervention}}$$

Where:
- $\text{Amount at Risk}$: Transaction value in minor currency units (e.g., paise).
- $P_{\text{recovery}}$: Base recovery probability derived from failure category, proposed action, and attempt count.
  - Soft failure + `retry_payment`: $0.70$ (attempt 1)
  - Hard failure + `retry_payment`: $0.35$
  - Fraud + `retry_payment`: $0.00$
- $C_{\text{intervention}}$: Estimated direct execution cost:
  - `retry_payment`: 500 minor units (₹5.00)
  - `send_payment_link`: 200 minor units (₹2.00)
  - `send_customer_message`: 150 minor units (₹1.50)
  - `escalate_human`: 1000 minor units (₹10.00)
  - `stop_recovery`: 0 minor units

### Sample Calculation
For a soft failure of ₹50,000 (5,000,000 paise) using `retry_payment`:
$$EV = (5,000,000 \times 0.70) - 500 = 3,499,500 \text{ paise} = \text{₹}34,995.00$$

If $EV \le 0$ or probability is zero (e.g., fraud), the action is deemed non-worthwhile and blocked.

---

## Safety & Stopping Rules

Recovery automatically halts when any absorbing stopping condition is met:

1. **Fraud / Hard Failures**: `fraud_detected` or `hard_decline` stops automated retries immediately.
2. **Retry Budget Exhaustion**: Maximum attempt count (default: 3) halts further retry attempts.
3. **Customer Opt-Out**: Opted-out customer IDs suppress all outbound messages (`customer_opted_out`).
4. **Active Promise-to-Pay**: An active promise pauses automated recovery until the promised date.
5. **Checkout Converted**: Cart checkout completed out-of-band halts recovery (`checkout_already_converted`).
6. **Subscription Cancelled**: User cancellation terminates renewal recovery (`subscription_cancelled`).
7. **Invoice Terminal State**: Invoices paid, disputed, or written off stop recovery.
8. **Policy Guard Override Prevention**: Policy engine rules cannot be bypassed by human operator intervention.

---

## Promise-to-Pay

RecoverOS includes a dedicated promise-to-pay lifecycle service:

- **Lifecycle States**: `PROMISED` $\rightarrow$ `FULFILLED` / `BROKEN` / `EXPIRED`.
- **Automated Pause**: An active promise pauses ordinary automated retries.
- **Settlement Verification**: Payment settlement during an active promise window marks the promise `FULFILLED` and updates the item to `RECOVERED`.
- **Expiration Handling**: Expired promises automatically trigger stopping rules or re-enter recovery queue.
- **Hinglish Intent Extraction**: Extracts promise date and amount from Hinglish messages using pattern matching.
  - *Example*: `"Friday ko ₹18,000 clear kar dunga"` $\rightarrow$ extracts ₹18,000 amount and Friday date.
  - **Fail-Closed**: If amount or date cannot be safely resolved, extraction returns `incomplete_promise` and refuses to create a promise.

---

## B2B Receivables Ladder

For overdue receivables, RecoverOS executes a deterministic aging ladder based on days overdue:

```
Day 1–2 Overdue  ──>  send_reminder            (Gentle invoice reminder)
Day 3–6 Overdue  ──>  send_payment_link        (Payment link SMS/Email)
Day 7–13 Overdue ──>  alternate_channel        (Urgent multi-channel notice)
Day 14+ Overdue  ──>  escalate_human           (Human finance team review)
```

This ladder is enforced as deterministic policy logic rather than unconstrained LLM output.

---

## Verification & Financial Truth

Executing an action does **NOT** mean revenue has been recovered.

RecoverOS enforces strict **Financial Truth Invariants**:

1. **`actually_recovered`**: Sum of `actual_recovery_minor` strictly from verified records in the `recovery_outcomes` table.
2. **No Execution Credit**: An executed intervention is marked `intervention_executed` / `pending_verification`. It does not count toward recovered revenue until verified.
3. **No Heuristic Credit**: Expected value, AI confidence, or proposed amounts are never used as actual recovered revenue.

---

## Auditability

RecoverOS logs every state transition, policy decision, agent proposal, and execution attempt to an **append-only audit log**:

- `AuditEvent` contains `id`, `recovery_item_id`, `actor` (`system`, `agent`, `rule`, `human`), `action`, `reason`, `metadata`, and `timestamp`.
- Audit logs are queryable per recovery item (`/api/recovery-items/{id}`) and customer history (`/api/customers/{id}`).

---

## Evaluation: RecoverOS vs Baseline

RecoverOS includes a deterministic evaluation benchmark (`/batch-recovery`) comparing RecoverOS policy-driven execution against a fixed-strategy baseline (`retry -> retry -> stop`) on the **EXACT SAME dataset**.

### Benchmark Specifications
- **Dataset Size**: 50 synthetic opportunities (seed `42`).
- **Surface Coverage**: Payment Failure (22), Checkout Abandonment (7), Subscription Failure (7), Overdue Receivables (5), Mandate Failure (5), Fraud (4), Opt-Outs (3), Promises (6).

### Benchmark Results (Seed 42)

| Metric | Fixed Baseline | RecoverOS Control Plane | Difference / Improvement |
| :--- | :--- | :--- | :--- |
| **Opportunities Processed** | 50 | 50 | Same Dataset |
| **Total Amount at Risk** | ₹42,67,400 | ₹42,67,400 | — |
| **Actually Recovered** | ₹8,16,000 | ₹11,39,000 | **+₹3,23,000** |
| **Recovery Rate** | 19.1% | 26.7% | **+39.6% relative gain** |
| **Unnecessary Interventions** | High (Retried Fraud) | 1 (Failed soft retry) | Reduced wasted attempts |
| **Cost Per Recovery** | ₹3.23 | ₹5.26 | Safety-constrained |
| **Rules-First Classification** | 0% | 100% (bypassed LLM) | Low latency, 0 inference cost |

---

## Reliability & Stress Testing

The engine includes full stress and reliability test suites:

- **Idempotency**: Duplicate webhook payloads (identical provider event IDs) return `duplicate` status without duplicating `RecoveryItem` or `RecoveryOutcome` records.
- **Concurrent PostgreSQL Outlets**: Verified under 500-item batch execution and concurrent database connection pool stress.
- **Failure Injection**: Chaos testing verifies system degrades gracefully when agent or LLM calls fail.

---

## Architecture

```
                               ┌────────────────────────┐
                               │   Next.js 14 Web App   │
                               └───────────┬────────────┘
                                           │ HTTP / REST
                               ┌───────────▼────────────┐
                               │    FastAPI API App     │
                               └───────────┬────────────┘
                                           │
                               ┌───────────▼────────────┐
                               │  RecoveryOrchestrator  │
                               └───────────┬────────────┘
                                           │
         ┌──────────────────┬──────────────┼──────────────┬──────────────────┐
         │                  │              │              │                  │
┌────────▼─────────┐ ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐ ┌─────────▼────────┐
│ Diagnosis / Rules│ │  EV Scorer  │ │ Policy    │ │ Recovery    │ │ Verification     │
│ & LLM Agent      │ │ (Formula)   │ │ Guard     │ │ Executor    │ │ & Outcomes       │
└──────────────────┘ └─────────────┘ └───────────┘ └─────────────┘ └──────────────────┘
                                           │
                               ┌───────────▼────────────┐
                               │ Append-Only Audit Log  │
                               └───────────┬────────────┘
                                           │
                               ┌───────────▼────────────┐
                               │ PostgreSQL Persistence │
                               └────────────────────────┘
```

### Benchmarking Subsystem
`EvaluationService` instantiates both `RecoveryOrchestrator` and `BaselineEvaluator` side-by-side, executing them against deterministic items generated by `generate_evaluation_dataset()`.

---

## Tech Stack

### Backend
- **Python**: 3.11+
- **FastAPI**: 0.115.6 (REST API, OpenAPI schema, CORS middleware)
- **PostgreSQL**: `psycopg` v3 binary driver & connection pool
- **Pydantic**: Domain validation & data serialization
- **pytest**: 8.3.3 (Unit, integration, and stress test suites)

### Frontend
- **Next.js**: 14.2.18 (App Router, static prerendering, server/client components)
- **React**: 18.3.1
- **TypeScript**: 5.6.3
- **TailwindCSS**: 3.4.15 (Vanilla CSS design system tokens)

---

## Project Structure

```
revenue_recovery/
├── app/
│   ├── adapters/          # Razorpay webhook handlers & event parsers
│   ├── agents/            # Decision agents, prompt builders, proposal validators
│   ├── api/               # FastAPI route modules (auth, dashboard, evaluations, etc.)
│   ├── audit/             # Audit event models and append-only log repositories
│   ├── datasets/          # Synthetic dataset generation for batch evaluations
│   ├── db/                # PostgreSQL schema, connection pooling, and repositories
│   ├── domain/            # Core domain models (RecoveryItem, Context, Proposals)
│   ├── idempotency/       # Webhook deduplication store
│   ├── interventions/     # Action execution layer (SimulatedRecoveryExecutor)
│   ├── ledger/            # Attempt record ledger
│   ├── policies/          # InterventionPolicy, StoppingRules, DefaultRecoveryGuard
│   ├── scoring/           # Deterministic EV scorer, probability, cost, priority models
│   ├── services/          # Evaluation, Promise, Receivable, and Webhook services
│   └── main.py            # FastAPI application entrypoint & middleware configuration
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router pages (batch-recovery, customers, etc.)
│   │   ├── components/    # Navigation shell, metrics, cards, timeline components
│   │   └── lib/           # API client SDK and TypeScript interfaces
│   └── package.json
├── tests/                 # 440+ pytest unit, integration, and safety test modules
├── pyproject.toml
└── README.md
```

---

## API Surface

### Authentication
- `POST /api/auth/signup`: Register new user account.
- `POST /api/auth/login`: Login & issue HttpOnly session cookie + Bearer token.
- `GET /api/auth/me`: Get current authenticated user session.
- `POST /api/auth/logout`: Invalidate session.

### Recovery Operations & Dashboard
- `GET /api/dashboard/summary`: Executive financial truth summary.
- `GET /api/recovery-items`: Queue of recovery items ordered by priority.
- `GET /api/recovery-items/{id}`: Detailed case workspace (item, decisions, attempts, audit).
- `POST /api/recovery-items/{id}/approve`: Human review approval endpoint (policy guarded).
- `GET /api/customers`: Customers list with aggregate financial metrics.
- `GET /api/customers/{customer_id}`: Customer detail with chronological event history timeline.
- `GET /api/audit-log`: System-wide audit event stream.

### Evaluations & Demo Triggers
- `POST /api/evaluations/batch`: Run head-to-head evaluation run (RecoverOS vs Baseline).
- `POST /api/demo/payment-failure`: Trigger single synthetic recovery event.
- `POST /api/demo/batch-payment-failures`: Trigger batch synthetic payment failures.

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- PostgreSQL (optional; defaults to in-memory mode if `PERSISTENCE_MODE` is unset)

### Backend Setup
```powershell
# Install dependencies
pip install -e .

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:PERSISTENCE_MODE = "postgres"  # or "memory"
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/revenue_recovery"

# Initialize PostgreSQL database schema
python scripts/init_db.py

# Run FastAPI backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Testing

Run the full Python automated test suite:
```powershell
python -m pytest -v
```

### Verified Test Suite Results
- **Step 3 (5 Revenue Surfaces)**: **23/23 passed**.
- **Step 4 (Evaluation Proof & Safety)**: **7/7 passed**.
- **Step 5 (Data Integrity & Persistence)**: **5/5 passed**.
- **Full Pytest Suite**: **410 passed, 32 skipped, 0 failed** in 10.83s.
- **Frontend Production Build**: **16/16 static/dynamic routes compiled clean** with 0 errors (`npm run build`).

---

## Design Principles

1. **AI Proposes, Deterministic Controls Decide**: LLMs generate recommendations; pure software logic enforces financial rules and safety bounds.
2. **Never Retry Blindly**: Retries must be justified by positive Expected Value and clean safety policy evaluation.
3. **Verify Recovery Before Claiming Revenue**: Execution is not recovery. Settlement verification is mandatory.
4. **Fail Closed on Unsafe Ambiguity**: Ambiguous intent, missing dates, or unclassified actions halt execution safely.
5. **Human Approval Cannot Override Safety**: Human operators cannot approve hard policy violations (e.g. retrying fraud).
6. **Immutable Audit Trail**: Every financial decision and execution must be completely traceable.

---

## Current Status

RecoverOS is fully implemented and verified as of **Step 5**:
- Full 11-stage recovery pipeline.
- 5 revenue surfaces implemented.
- Rules-first + LLM fallback diagnosis.
- Closed action set & proposal validator.
- Policy safety guard & stopping rules engine.
- Deterministic Expected Value scoring.
- Hinglish promise-to-pay lifecycle & extraction.
- Overdue receivables escalation ladder.
- PostgreSQL persistence for items, decisions, attempts, outcomes, and audit logs.
- Head-to-head batch evaluation engine against fixed baseline.
- Next.js Web UI dashboard with live evaluation, customer history timeline, and case workspaces.
