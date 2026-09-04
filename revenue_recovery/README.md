# RevPlug — Autonomous Revenue Recovery Control Plane

Built for the **Razorpay AI Buildathon — AI Revenue Recovery Track**.

> **Control Principle:** AI proposes candidates. Deterministic policy gates execution. Verified settlement proves recovery.

---

## The Problem
Revenue leakage across failed payments, checkout drop-offs, failed subscription renewals, and overdue B2B receivables is often exacerbated by blind retry scripts that retry fraud cases, waste gateway fees, and contact opted-out users. The core challenge is deciding what action to take, evaluating expected value, enforcing policy bounds, and verifying settlement before recognizing recovery.

---

## Core Control Loop
```
Events / Telemetry ──► Opportunity Context ──► Candidate Actions ──► Expected Value Scorer
                                                                          │
Settlement Verification ◄── Verified Outcome ◄── Execution ◄── Policy Shield Gate (ALLOW/STOP)
```

1. **Diagnose & Select:** Evaluates candidate interventions (retry, payment link, message, discount, hold, escalate).
2. **Score Expected Value:** Ranks candidates by $EV_{\text{net}} = \text{Gross} \times P_{\text{recovery}} - \text{Intervention Cost}$.
3. **Policy Shield Gate:** Evaluates strict server-side rules. Execution occurs **only** if policy ALLOWS.
4. **Settlement Verification:** Recovery is recognized **only** upon receiving authoritative gateway settlement evidence. Unverified dispatches contribute ₹0 to recovered revenue.

---

## AI vs Deterministic Boundary
- **AI Layer (Groq `llama-3.3-70b-versatile` / Gemini `gemini-1.5-pro` / MockLLM fallback):** Root cause diagnosis, contextual intervention proposal generation, and customer communication rationale.
- **Deterministic Layer (`PolicyEngine` & `StoppingRules`):** Financial math, retry budget limits, hard decline blocks, opt-out compliance, contact frequency caps, and HMAC settlement verification.

---

## Safety & Policy Engine
- **Stopping Rules:** Fraud signals, opted-out customers, terminal decline codes, and expired cases trigger immediate `STOP`.
- **Policy Enforcement:** Unsafe AI proposals and invalid human overrides return policy rejections (`HTTP 400`).
- **Hinglish Voice Promise-to-Pay:** Browser-assisted voice capture (Web Speech API) parses spoken customer promises into structured `PromiseRecord` instances with amount and date limits, placing recovery on hold until promised dates.

---

## Benchmark Results (Seeded Counterfactual Evaluation)
*Source of truth: `revenue_recovery/evaluation_report.json` and `docs/EVALUATION_REPORT.md` (synthetic counterfactual benchmark dataset).*

### Single-Seed Trace (Seed 42, 50 Cases)
| Metric | Naive Baseline | Safe Baseline | RevPlug Bounded Agent |
| :--- | :--- | :--- | :--- |
| **Total Risk Pool** | ₹42,674.00 | ₹42,674.00 | **₹42,674.00** |
| **Verified Gross Recovery** | ₹13,608.50 (31.9%) | ₹13,608.50 (31.9%) | **₹16,060.00 (37.6%)** |
| **Net Recovery (minus cost)** | ₹13,153.50 | ₹13,213.50 | **₹15,973.00 (+20.9% net lift)** |
| **Intervention Cost** | ₹455.00 | ₹395.00 | **₹87.00 (-78% cost)** |
| **Safety Violations** | 17 | 0 | **0** |

### Multi-Seed Aggregate (10 Seeds, 1,000 Cases Total)
Across 10 independent counterfactual seeds (100 cases/seed), RevPlug outperforms the Safe Baseline in **9/10 seeds (90% win rate)**:
- **Mean Net Recovery:** **₹55,241.55** vs Safe Baseline **₹28,678.40** (+92.6% net recovery lift, 95% CI: [+48.6%, +136.6%]).
- **Mean Safety Violations:** **0.0** vs Safe Baseline **28.4** vs Naive Baseline **39.3**.

---

## Repository Structure
```
revenue_recovery/
├── app/               # FastAPI backend (agents, policies, scoring, API, ledgers)
│   ├── agents/        # Contextual LLM reasoning (Groq, Gemini, MockLLM)
│   ├── policies/      # Deterministic PolicyEngine & hard stopping rules
│   ├── scoring/       # Expected Net Value (EV) & timing scorers
│   └── services/      # Orchestrator, settlement verifier, PTP extraction, financials
├── frontend/          # Next.js 14 dashboard (App Router, Tailwind CSS)
└── tests/             # pytest suite (649 tests covering safety, EV, settlement, API)
```

---

## Quick Start & Verification

### Prerequisites & Setup
```bash
cd revenue_recovery
python -m venv .venv && source .venv/bin/activate  # (.venv\Scripts\activate on Windows)
pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

### Running Application
```bash
# Backend (Port 8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (Port 3000)
cd frontend && npm run dev
```

### Verification & Benchmark Commands
```bash
# Run pytest suite
python -m pytest tests/ -v

# Run canonical evaluation benchmark
python -m app.eval.run_benchmark
```

---

## Current Limitations
1. **Counterfactual Benchmark:** Proof Lab benchmarks use seeded synthetic cases to evaluate policies reproducibly; they do not represent live merchant revenue.
2. **Browser Voice PTP:** Hinglish PTP uses browser Web Speech API (STT/TTS) connected to structured backend extraction, not production telephony (Twilio/Exotel).
3. **Execution Modes:** Razorpay integrations run with simulated webhooks/adapters for testing and local demonstration.
