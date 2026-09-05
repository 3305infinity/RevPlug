# RevPlug — Autonomous AI Revenue Recovery Control Plane

Built for the **Razorpay AI Buildathon — AI Revenue Recovery Track**.

> **Control Principle:** AI proposes interventions. Deterministic policy gates execution. Verified settlement proves recovery.

---

## Key Features

- **Autonomous AI Opportunity Engine:** Real-time event ingestion across failed payments, checkout drop-offs, overdue invoices, and fraud risk. Powered by LLM diagnosis (Groq `llama-3.3-70b-versatile` / Gemini `gemini-1.5-pro`).
- **Net EV Optimization:** Ranks actions by expected net financial yield:
  $$\text{EV}_{\text{net}} = \text{Gross Amount} \times P_{\text{recovery}} - \text{Intervention Cost}$$
- **Deterministic Policy Shield:** Hard server-side enforcement (`PolicyEngine` & `StoppingRules`) blocking fraud, terminal decline codes, contact limits, and model hallucinations with 0 safety violations.
- **Authoritative Settlement Verification:** Recognized revenue requires HMAC-verified gateway settlement evidence. Unverified dispatches contribute ₹0.
- **Hinglish Voice PTP Assistant:** Browser-assisted voice capture and structured extraction parsing spoken customer promises into binding payment dates.
- **Reliability & Failure Lab:** Interactive developer sandbox for live testing of LLM timeouts, 502 gateway failures, idempotency deduplication, and hallucinated action rejection.

---

## Core Control Architecture

```
Events & Telemetry ──► Context Engine ──► AI Candidate Actions ──► Net EV Scorer
                                                                         │
Settlement Verification ◄── Verified Outcome ◄── Dispatch Engine ◄── Policy Shield Gate (ALLOW / STOP)
```

1. **Diagnose & Rank:** AI generates candidate interventions (retry, payment link, discount, hold, escalate) scored by Net EV.
2. **Policy Shield Gate:** Evaluates strict server-side rules. Execution occurs **only** if policy approves.
3. **Settlement Verification:** Recovery is recognized **only** upon receiving authoritative gateway settlement proof.

---

## Benchmark Proof Results

*Source of truth: `revenue_recovery/evaluation_report.json` and `docs/EVALUATION_REPORT.md`.*

### Multi-Seed Aggregate Evaluation (1,000 Cases / 10 Seeds)
Across 10 independent counterfactual benchmark seeds (100 cases/seed), RevPlug outperforms the Safe Baseline in **9/10 seeds (90% win rate)**:

| Metric | Naive Baseline | Safe Baseline | RevPlug Bounded Agent |
| :--- | :--- | :--- | :--- |
| **Mean Net Recovery** | ₹26,812.10 | ₹28,678.40 | **₹55,241.55 (+92.6% net lift)** |
| **Mean Safety Violations** | 39.3 | 28.4 | **0.0 (Zero Violations)** |
| **Intervention Efficiency** | High Cost | Moderate Cost | **-78% Cost Reduction** |

---

## Quick Start & Verification

### Setup
```bash
# Environment Setup
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

# Frontend Dependencies
cd frontend && npm install && cd ..
```

### Running the Application
```bash
# Start Backend (Port 8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Start Frontend (Port 3000)
cd frontend && npm run dev
```

### Verification & Benchmark Commands
```bash
# Run Pytest Suite (649 tests)
python -m pytest tests/ -v

# Run Canonical Evaluation Benchmark
python -m app.eval.run_benchmark
```
