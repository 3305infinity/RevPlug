# RevPlug — AI Revenue Recovery Control Plane

Autonomous revenue recovery system that pairs AI-assisted contextual reasoning with strict deterministic policy guards to maximize settlement-verified revenue.

> **Core Control Principle:** AI decides what might work. Deterministic policy decides what is allowed. Execution is bounded. Money is counted only after verified settlement.

---

## Why This Matters

Revenue leakage occurs across failed payments, checkout drop-offs, failed subscription renewals, and overdue B2B receivables. Unmanaged retry scripts often exacerbate losses by retrying fraud-flagged transactions, incurring unnecessary payment gateway fees, and contacting opted-out users. 

RevPlug solves this by dynamically ranking candidate actions, evaluating net expected value, enforcing strict policy bounds, and verifying settlement before recognizing recovery.

---

## How It Works

RevPlug processes recovery cases through an 8-stage bounded control loop:

$$\text{Detect} \longrightarrow \text{Diagnose} \longrightarrow \text{Decide} \longrightarrow \text{Guard} \longrightarrow \text{Execute} \longrightarrow \text{Verify} \longrightarrow \text{Stop/Escalate} \longrightarrow \text{Audit}$$

1. **Detect:** Captures payment failures, abandoned checkouts, subscription renewal failures, and overdue receivable events via webhooks or API.
2. **Diagnose:** Identifies failure root cause (e.g., soft decline, authentication required, hard decline, fraud flag).
3. **Decide:** Contextual AI ranks candidate actions (payment link, retry, reminder, alternate channel) and scores Expected Value:
   $$EV_{\text{net}} = \text{Gross Amount} \times P_{\text{recovery}} - \text{Intervention Cost}$$
4. **Guard:** Server-side deterministic policy shield (`InterventionPolicy` & `StoppingRules`) checks rules before any action is dispatched. Actions proceed **only** if status is `ALLOWED`.
5. **Execute:** Dispatches approved interventions via integrated payment adapters (e.g., Razorpay test mode).
6. **Verify:** Tracks settlement status using HMAC-verified gateway webhooks. Unverified dispatches contribute ₹0 to recovered revenue.
7. **Stop/Escalate:** Automatically halts recovery on fraud, opt-out, or exhausted budgets; escalates ambiguous cases to human review.
8. **Audit:** Records immutable audit logs for every decision, policy check, attempt, and settlement.

---

## AI Judgment vs Deterministic Controls

RevPlug enforces an architectural boundary between AI recommendations and system controls:

| System Layer | Implementation | Responsibilities |
| :--- | :--- | :--- |
| **AI Layer** | Primary: Groq (`llama-3.3-70b-versatile`) <br> Secondary: Google Gemini (`gemini-1.5-flash`) <br> Fallback: `MockLLMProvider` | Contextual root-cause diagnosis, intervention candidate ranking, customer promise extraction, and communication rationales. |
| **Deterministic Layer** | `InterventionPolicy`, `StoppingRules`, `ExpectedValueScorer` | Financial math, retry budget limits, hard decline blocks, opt-out compliance, contact frequency caps, and HMAC settlement verification. |

AI models propose interventions; they **cannot** execute actions, bypass policy limits, or recognize unverified revenue.

---

## Recovery Workflows

RevPlug unifies multiple recovery patterns into a single control plane:

* **Payment Failures:** Recovers soft declines via optimized retry timing, alternate payment links, and authentication prompts.
* **Checkout & Subscription Renewals:** Re-engages abandoned checkouts and handles recurring subscription payment failures.
* **Receivables & Promise-to-Pay (PTP):** Captures customer payment commitments (including voice-assisted Hinglish promises) and pauses automated retries until promised dates.

---

## Measured Recovery

RevPlug is evaluated using counterfactual multi-seed benchmark suites (10 seeds, Seeds 42–51, 100 cases/seed, 1,000 total cases). Full methodology is documented in [`docs/EVALUATION.md`](docs/EVALUATION.md).

### 10-Seed Aggregate Benchmark Results

| Metric | Baseline A (Naive Retry) | Baseline B (Safe Retry) | RevPlug Autonomous Agent | RevPlug vs Safe Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Net Recovery** | ₹28,569.40 | ₹28,678.40 | **₹55,241.55** | **+92.6% net lift** |
| **Mean Recovery Rate** | 28.5% | 28.5% | **53.5%** | **+25.0% pts** |
| **Mean Safety Violations** | 39.3 | 28.4 | **0.0** | **100% violation-free** |
| **Seed Win Rate** | 0/10 seeds | 1/10 seeds | **9/10 seeds (90.0%)** | — |

*Source artifact: [`artifacts/evaluation_report.json`](artifacts/evaluation_report.json).*

*Note: All benchmark evaluations run on counterfactual test-mode data. Revenue is counted as recovered strictly after settlement verification.*

---

## Failure Recovery & Resilience

RevPlug is designed for fail-safe operations under external failures:

* **AI Provider Failures & Malformed Output:** If an LLM call times out or returns invalid JSON, the system triggers `fallback_used=True` and falls back to deterministic rule-based candidate selection.
* **Uncertain Provider States:** If a payment gateway response is ambiguous or times out, the case transitions to `PENDING_VERIFICATION` rather than assuming success.
* **Idempotency Safeguards:** Every intervention is tagged with a unique idempotency key to prevent duplicate payment charges.
* **Hard Stopping Rules:** Recovery stops immediately if a transaction is flagged for fraud, a customer opts out, or retry budgets are exhausted.

---

## Run Locally

### Prerequisites & Installation

```bash
# Clone and set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies in editable mode
pip install -e ".[dev]"

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

### Running the Application

```bash
# Start FastAPI Backend (Port 8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Start Next.js Frontend (Port 3000)
cd frontend
npm run dev
```

### Test Suite & Benchmark Execution

```bash
# Run pytest test suite
python -m pytest

# Execute canonical evaluation benchmark
python -m app.eval.run_benchmark
```

---

## Repository Documentation

* [**AI Architecture & Safety Shield**](docs/AI_ARCHITECTURE.md): AI routing, prompt construction, and deterministic safety shield.
* [**Autonomy Boundaries**](docs/AUTONOMY_BOUNDARIES.md): Policy rules, EV gating, and stopping conditions.
* [**Benchmark & Evaluation Methodology**](docs/EVALUATION.md): Counterfactual dataset structure, baseline definitions, and metrics.
* [**Security Model**](docs/SECURITY_MODEL.md): Authentication, data privacy, and audit logs.
* [**Razorpay Gateway Integration**](docs/RAZORPAY_INTEGRATION.md): Real and test-mode payment gateway integration guide.
