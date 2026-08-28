# Recovery Engine — AI Revenue Recovery

An AI-powered revenue recovery engine for Razorpay that detects failed payments, reasons about the safest recovery action, validates it against deterministic business policy, executes safely, learns from outcomes, and escalates uncertain cases to humans.

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

Failed payments cost merchants significant revenue. Manual recovery is slow and inconsistent. Blind automated retries waste resources and annoy customers. This system intelligently decides the safest recovery strategy for each failed payment.

## Value Proposition

Recover more failed payments with safe autonomous recovery — AI reasons about the best action, deterministic policies enforce safety, and humans control risky outcomes.

## Target User

Payments/revenue operations teams at businesses using Razorpay.

## Architecture

```
Razorpay payment.failed
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
PolicyEngine = FINAL AUTHORITY
      ↓                    ↓
   DENIED               ALLOWED
      ↓                    ↓
 ESCALATE            RecoveryExecutor (simulated)
      ↓                    ↓
 AUDIT            AttemptLedger
                       ↓
                  SUCCESS / FAILURE
                       ↓
                  RetryPolicy (exponential backoff)
                       ↓
                RETRY / ESCALATE
                       ↓
                  StateMachine + AuditLog + PostgreSQL
```

### Agent boundary

The agent produces PROPOSALS only. It NEVER:
- Executes actions
- Moves money
- Contacts customers
- Overrides policy decisions

**Legal path:** `agent.propose()` → `validator.validate()` → `policy_engine.evaluate()` → `executor.execute()`

### Why AI is used

The LLM reasons about failure context to recommend the best recovery strategy. It considers failure category, retryability, attempt count, amount, risk signals, and policy constraints. The deterministic ExpectedValueScorer handles numeric scoring; the LLM handles contextual judgment.

### Why deterministic policy remains authoritative

Free/weak LLMs can hallucinate, miss edge cases, or produce unsafe recommendations. The PolicyEngine enforces hard business rules (fraud → no retry, hard failures → no retry, opt-out → no contact) that the LLM cannot override. The validator rejects malformed or unsafe proposals.

## Agent modes

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

## Dashboard UI

```powershell
streamlit run app/dashboard.py
```

The dashboard provides:
- **Overview** — revenue metrics, recovery rate, financial summary
- **Recovery Queue** — filterable list of all cases with status/category/policy filters
- **AI Decisions** — agent proposals vs policy decisions
- **Evaluation** — golden-scenario evaluation results
- **Demo** — trigger synthetic failed-payment events with 5 quick scenarios
- **Human Review** — approve/reject escalated cases (policy still enforced)

### Recovery Decision Timeline

The centerpiece feature: click any case to see the complete reasoning-to-execution lifecycle:

```
PAYMENT FAILED → FAILURE CLASSIFIED → RECOVERY VALUE SCORED →
AI CONTEXT BUILT → AI PROPOSAL → VALIDATION → POLICY GATE →
EXECUTION → RECOVERED / RETRY / ESCALATED
```

AI-driven stages are clearly labeled separately from deterministic stages.

## Retry behavior

- Soft failures: retried up to `max_attempts` (default 3)
- Exponential backoff: `base_delay * 2^(attempt-1)`, capped at `max_delay`
- Hard failures, fraud, authentication-required: NOT retried
- Retry exhaustion → ESCALATED state

## Human-in-the-loop

Risky proposals (fraud, high-value, low-confidence, unknown) require human approval before execution. The API exposes endpoints for approval/rejection.

## Safety

- Simulated executor has NO real payment side effects
- All execution is deterministic and injectable
- Real Razorpay executor can later replace `SimulatedRecoveryExecutor` via the `RecoveryExecutor` protocol
- Deterministic Python controls all safety constraints; the LLM only proposes

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

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/webhooks/razorpay` | Razorpay webhook endpoint |
| `GET` | `/api/dashboard/summary` | Executive dashboard metrics |
| `GET` | `/api/recovery-items` | List all recovery cases |
| `GET` | `/api/recovery-items/{id}` | Case detail with audit/attempts/decisions |
| `GET` | `/api/recovery-items/{id}/agent-trace` | Agent decision trace |
| `GET` | `/api/evaluations` | Golden-scenario evaluation results |
| `POST` | `/api/demo/payment-failure` | Trigger a demo failed-payment event |
| `GET` | `/api/reviews/pending` | Cases pending human review |
| `POST` | `/api/recovery-items/{id}/approve` | Approve action (policy still enforced) |
| `POST` | `/api/recovery-items/{id}/reject` | Reject case (transitions to STOPPED) |

## Human-in-the-loop

Risky proposals (fraud, high-value, low-confidence, unknown) require human approval before execution. Even human-approved actions must pass through the PolicyEngine — unsafe actions are blocked with a clear explanation.

### From payment_recovery_engine-main
- State machine with terminal absorption (can't exit RECOVERED/ESCALATED/STOPPED)
- Retry scheduling with absolute timestamps and exponential backoff
- Attempt ledger with unique constraints
- Multi-layer idempotency (event dedup + UNIQUE constraints)
- Fail-safe defaults (unknown → manual review)
- Database CHECK constraints enforcing state invariants

### From morsegrid-agentic-pipeline-main
- Multi-stage agent workflow (context build → decision → validation → policy)
- Structured prompt builders (compact context injection)
- Agent tracing (tool calls, decision reasoning)
- Graceful degradation (agent failure → deterministic fallback)
- Per-item error isolation (one failure doesn't cascade)
- Evaluation framework with golden scenarios

## Run tests

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

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `RAZORPAY_WEBHOOK_SECRET` | (required) | Razorpay webhook secret |
| `PERSISTENCE_MODE` | `memory` | `memory` or `postgres` |
| `DATABASE_URL` | (auto) | PostgreSQL connection URL |
| `RECOVERY_AGENT_MODE` | `mock` | `mock` or `llm` |

## Engineering rules

- Python 3.11
- No global mutable state
- No external APIs
- No background workers
- No frontend

## Known limitations

- Simulated executor only (no real payment API calls)
- Single attempt per webhook (background worker needed for scheduled retries)
- Deterministic LLM mock used when `RECOVERY_AGENT_MODE=llm` (replace `DeterministicLLMClient` with real provider)

## BUILT vs FUTURE

### BUILT
- Razorpay webhook verification and parsing
- Failure classification and expected-value scoring
- Agentic decision layer (mock + LLM with fallback)
- Policy engine with safety guards
- Retry policy with exponential backoff
- State machine with terminal absorption
- Idempotency at multiple layers
- Attempt ledger and audit trail
- PostgreSQL persistence
- Decision persistence
- Evaluation framework with golden scenarios
- Human-in-the-loop API structure
- Streamlit dashboard UI
- Demo event triggers

### FUTURE (ROADMAP)
- Real Razorpay payment execution
- Background retry worker
- Full dashboard with case detail timeline
- Real LLM provider integration (OpenAI, Anthropic, etc.)
- Advanced metrics and reporting
- Multi-channel customer communication (email, SMS)
- A/B testing framework
