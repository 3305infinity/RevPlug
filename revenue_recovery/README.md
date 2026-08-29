# RecoverOS — Autonomous Revenue Recovery with Deterministic Controls

RecoverOS detects failed payments, diagnoses the failure, calculates the economic value of recovery, recommends an intervention, and executes only when deterministic safety controls allow it.

**Frontend:** Next.js + TypeScript + Tailwind CSS
**Backend:** FastAPI + PostgreSQL

## Quick Start

```powershell
# Terminal 1: Start backend
cd revenue_recovery
$env:RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"
$env:PERSISTENCE_MODE = "memory"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Start frontend
cd revenue_recovery/frontend
npm install
npm run dev
# Open http://localhost:3000
```

## Problem

Failed payments cost merchants significant revenue. Manual recovery is slow and inconsistent. Blind automated retries waste resources and annoy customers. RecoverOS intelligently decides the safest recovery strategy for each failed payment.

## Value Proposition

Recover more failed payments with safe autonomous recovery — AI reasons about the best action, deterministic policies enforce safety, and humans control risky outcomes.

## Target User

Payments / revenue operations teams at businesses using Razorpay.

## Architecture

```
Provider Event (e.g. payment.failed)
      ↓
Razorpay Adapter (signature verify → parse → normalize)
      ↓
Domain (RecoveryItem + NormalizedFailure)
      ↓
ExpectedValueScorer (deterministic)
      ↓
RecoveryContext (compact, relevant-only)
      ↓
RecoveryDecisionAgent (mock or LLM)
      ↓
STRUCTURED RecoveryProposal
      ↓
ProposalValidator (strict, fail-closed)
      ↓
StoppingRules (highest priority — idempotent)
      ↓
PolicyEngine = FINAL AUTHORITY
      ↓                    ↓
   DENIED               ALLOWED
      ↓                    ↓
  STOPPED            RecoveryExecutor (simulated)
      ↓                    ↓
  AUDIT            AttemptLedger
                        ↓
                   SUCCESS / FAILURE
                        ↓
                   RetryPolicy (exponential backoff)
                        ↓
                 RETRY / ESCALATE / STOP
                        ↓
                   StateMachine + AuditLog + PostgreSQL
```

### Agent boundary

The agent produces PROPOSALS only. It NEVER:
- Executes actions
- Moves money
- Contacts customers
- Overrides policy decisions
- Bypasses stopping rules

**Legal path:** `agent.propose()` → `validator.validate()` → `stopping_rules.evaluate()` → `policy_engine.evaluate()` → `executor.execute()`

### Why AI is used

The LLM reasons about failure context to recommend the best recovery strategy. It considers failure category, retryability, attempt count, amount, risk signals, and policy constraints. The deterministic ExpectedValueScorer handles numeric scoring; the LLM handles contextual judgment.

### Why deterministic policy remains authoritative

Free/weak LLMs can hallucinate, miss edge cases, or produce unsafe recommendations. The PolicyEngine enforces hard business rules (fraud → no retry, hard failures → no retry, opt-out → no contact) that the LLM cannot override. StoppingRules provide additional idempotent safety checks. The validator rejects malformed or unsafe proposals.

## Agent Modes

### Mock mode (default, no API key)

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Deterministic mock agent based on failure category:
- SOFT → retry_payment (if within budget)
- AUTHENTICATION_REQUIRED → send_recovery_message
- HARD → escalate_human
- FRAUD → stop_recovery / escalate_human
- UNKNOWN → escalate_human

### LLM mode (optional)

```powershell
$env:RECOVERY_AGENT_MODE = "llm"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Uses structured JSON output with strict validation. Falls back to mock on any failure (timeout, malformed output, API error).

## Frontend Application

The RecoverOS frontend is a Next.js application that provides an operational command center for revenue recovery.

### Pages

| Page | Description |
|------|-------------|
| **Revenue Recovery** | Operational command center showing revenue at risk, recovered amounts, recovery rate, expected recovery, needs attention, active recoveries, and recently recovered cases |
| **Recovery Cases** | Filterable queue of all recovery cases with status, amount, expected recovery, and probability |
| **Run Recovery** | Evaluate a revenue event and execute the safest eligible recovery action |
| **Batch Recovery** | Run recovery programs across a portfolio of revenue-risk events with measured outcomes |
| **Review Queue** | Cases awaiting human review; demonstrates that human approval cannot override safety policy |
| **Case Workspace** | Core product experience showing AI recommendation, system safety check, execution history, and recovery timeline |
| **Customers** | Account-level recovery view with total at risk, recovered, open cases, and case history |
| **Programs** | Recovery strategy configuration with workflow visualization and safety controls |
| **Activity** | Chronological audit stream of every recovery event with filters for system, AI, policy, stopped, escalated, and recovered events |
| **AI Performance** | Evaluation metrics showing decision accuracy, safety compliance, and golden scenario results |
| **Safety Controls** | Active policy configuration showing enforced controls (retry limits, fraud protection, opt-out, deadlines, etc.) |

### Key UX Principles

- **AI recommendation ≠ system decision** — The Case Workspace clearly separates the AI's informational recommendation from the deterministic safety check
- **Expected vs Actual** — Expected recovery and actually recovered amounts are never confused; they are visually distinct
- **Blocked cases explain why** — Every stopped case shows what was proposed, why it was blocked, which rule blocked it, and what happens next
- **No fake metrics** — All financial figures come from the backend; no fabricated data
- **Operational language** — Uses terms like "Recovery stopped", "Policy blocked this action", "Retry budget: 2 of 3 used"

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/webhooks/razorpay` | Razorpay webhook endpoint |
| `GET` | `/api/dashboard/summary` | Executive dashboard metrics |
| `GET` | `/api/recovery-items` | List all recovery cases |
| `GET` | `/api/recovery-items/{id}` | Case detail with audit/attempts/decisions |
| `GET` | `/api/evaluations` | Golden-scenario evaluation results |
| `POST` | `/api/demo/payment-failure` | Trigger a demo failed-payment event |
| `POST` | `/api/demo/batch-payment-failures` | Run batch recovery on multiple events |
| `GET` | `/api/reviews/pending` | Cases pending human review |
| `POST` | `/api/recovery-items/{id}/approve` | Approve action (policy still enforced) |
| `POST` | `/api/recovery-items/{id}/reject` | Reject case (transitions to STOPPED) |
| `GET` | `/api/controls` | Active safety controls configuration |
| `GET` | `/api/audit-events` | Chronological audit log |
| `GET` | `/api/customers/{id}` | Customer account detail with recovery history |
| `GET` | `/api/programs/config` | Recovery program configuration |
| `PUT` | `/api/programs/config` | Update program configuration |
| `POST` | `/api/demo/reset` | Safely clear synthetic demo data |

## Retry Behavior

- Soft failures: retried up to `max_attempts` (default 3)
- Exponential backoff: `base_delay * 2^(attempt-1)`, capped at `max_delay`
- Hard failures, fraud, authentication-required: NOT retried
- Retry exhaustion → STOPPED state
- Customer opt-out → STOPPED state (terminal)
- Payment success → RECOVERED state (terminal)

## Stopping Rules

RecoverOS enforces idempotent stopping rules before any execution:

| Rule | Trigger | Result |
|------|---------|--------|
| `payment_succeeded` | Payment received mid-flow | RECOVERED |
| `customer_opted_out` | Customer in opted-out set | STOPPED |
| `fraud_detected` | Failure classified as fraud | STOPPED |
| `retry_budget_exhausted` | Attempts >= max_attempts | STOPPED |
| `recovery_deadline_expired` | Current time > deadline | STOPPED |
| `promise_expired` | Active promise past due date | STOPPED |
| `terminal_state_reached` | Already RECOVERED/STOPPED/ESCALATED | Absorbed |

## Human-in-the-loop

Risky proposals (fraud, high-value, low-confidence, unknown) require human approval before execution. The API exposes endpoints for approval/rejection. Even human-approved actions must pass through the PolicyEngine — unsafe actions are blocked with a clear explanation.

## Safety

- Simulated executor has NO real payment side effects
- All execution is deterministic and injectable
- Deterministic Python controls all safety constraints; the LLM only proposes
- Human approval cannot override mandatory safety controls
- Stopping rules are idempotent and cannot be bypassed

## Run Tests

```bash
python -m pytest
```

## Database

### Start PostgreSQL

```bash
docker compose up -d
```

### Initialize schema (all migrations)

```bash
python -m scripts.init_db
```

### Check connection

```bash
python -m scripts.check_db
```

### Stop

```bash
docker compose down
```

### Run tests with PostgreSQL

```powershell
$env:DATABASE_URL = "postgresql://recovery:recovery_dev_password@localhost:5432/recovery_engine"
python -m pytest
```

### Run smoke test

```powershell
# Terminal 1: Start server
$env:RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Run smoke test
python -m scripts.smoke_test_razorpay
```

Expected output:
```
HTTP 200
{"status":"processed","recovery_item_id":"pay_smoke_001","failure_category":"soft",
 "expected_recovery_value":17500,"proposed_action":"retry_payment","policy_allowed":true,
 "execution_status":"succeeded","attempt_number":1,"retry_scheduled":false}
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RAZORPAY_WEBHOOK_SECRET` | (required) | Razorpay webhook secret |
| `PERSISTENCE_MODE` | `memory` | `memory` or `postgres` |
| `DATABASE_URL` | (auto) | PostgreSQL connection URL |
| `RECOVERY_AGENT_MODE` | `mock` | `mock` or `llm` |

## Engineering Rules

- Python 3.11
- No global mutable state
- No external APIs

## BUILT

- Razorpay webhook verification and parsing
- Failure classification and expected-value scoring
- Agentic decision layer (mock + LLM with fallback)
- Proposal validation (strict, fail-closed)
- Stopping rules (idempotent, highest priority)
- Policy engine with safety guards
- Retry policy with exponential backoff
- State machine with terminal absorption
- Idempotency at multiple layers
- Attempt ledger and audit trail
- PostgreSQL persistence
- Decision persistence
- Evaluation framework with golden scenarios
- Human-in-the-loop API structure
- Next.js operational frontend
- Demo event triggers (single + batch)
- Case workspace with AI/safety separation
- Activity audit stream
- Customer account view
- Recovery program configuration
- Safety controls dashboard
- Async background recovery worker (Stage 7)
- Real revenue operations data model and financial truth (Stage 8)
- Judge-proof systemic constraints and UI refinements (Stage 9)
- Secure synthetic data scope and reset capabilities

## FUTURE (ROADMAP)

- Real Razorpay payment execution
- Real LLM provider integration (OpenAI, Anthropic, etc.)
- Multi-channel customer communication (email, SMS)
- Advanced metrics and reporting
- A/B testing framework
