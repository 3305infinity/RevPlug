# RevPlug Benchmark & Counterfactual ROI Report

**Generated At:** 2026-09-03 09:23:09 UTC
**Canonical Benchmark Scale:** 10 cases | 10 seeds (`42` to `51`) | Version `2.0-canonical`
**Evaluation Mode:** AI_ASSISTED (AI Contextual Routing + Deterministic Safety Shield)

---

## 1. Executive Summary

RevPlug is a **bounded autonomous revenue recovery system** designed to maximize settlement-verified revenue while enforcing strict deterministic safety policies and retry budgets.

In this multi-seed benchmark of **10 cases** across 10 deterministic seeds:
- **7 AI-Assisted Cases** (contextual candidate selection & ranking)
- **1 Deterministic Cases** (opt-out compliance, fraud protection, retry budget enforcement)
- **7 AI Proposals Generated**
- **3 AI Proposals Accepted & Executed**
- **4 AI Proposals Blocked by Deterministic Policy Shield**
- **2 AI Fallbacks Triggered**
- **0 Safety Policy Violations**

RevPlug achieved a **-101.7% Net Recovery Lift** over naive fixed-retry baselines and **-101.7% Net Lift** over safe fixed-retry baselines, recovering **₹0.00** with **ZERO safety policy violations**.

---

## 2. Benchmark Financial & AI Decision Proof

| Metric | Naive Fixed Retry | Safe Fixed Retry | RevPlug Bounded AI Agent | Net Uplift |
| :--- | :--- | :--- | :--- | :--- |
| **Total Revenue at Risk** | ₹8,401.50 | ₹8,401.50 | ₹8,401.50 | — |
| **AI-Assisted Cases** | 0 | 0 | **7 (70.0%)** | **+7 AI Cases** |
| **Deterministic Cases** | 10 (100%) | 10 (100%) | **1 (10.0%)** | — |
| **Verified Recovered Revenue** | ₹1,751.50 | ₹1,751.50 | **₹0.00** | **+₹-1,751.50** |
| **Verified Recovery Rate** | 20.8% | 20.8% | **0.0%** | **+-20.8% Uplift** |
| **Intervention Cost** | ₹95.00 | ₹85.00 | **₹28.00** | **-₹67.00 Cost** |
| **Net Recovered Revenue** | ₹1,656.50 | ₹1,666.50 | **₹-28.00** | **+₹-1,694.50 (-101.7%)** |
| **AI Proposals Blocked by Policy** | 0 | 0 | **4** | **100% Policy Shield Protection** |
| **Safety Policy Violations** | **3** | **0** | **0** | **-100% Policy Violations** |

---

## 3. Revenue Attribution Breakdown

RevPlug enforces strict financial truth: money is recognized as recovered ONLY when backed by authoritative settlement evidence.

| Attribution Category | Cases | Recovered Amount | Description |
| :--- | :--- | :--- | :--- |
| **DIRECT_AGENT** | 3 | ₹0.00 | Realized recovery directly driven by automated retries or alternate channels. |
| **AGENT_ASSISTED** | 6 | ₹0.00 | Realized recovery following payment links, reminders, or promise-to-pay workflows. |
| **ORGANIC** | 0 | ₹0.00 | Payment settled independently without qualifying agent intervention. |
| **UNKNOWN** | 1 | ₹0.00 | Unassigned attribution. |

---

## 4. Multi-Seed Statistical Robustness

- **Total Seeds Evaluated:** 10 (Seeds 42–51)
- **RevPlug Win Rate vs Safe Baseline:** 0/10 seeds (0%)
- **95% Confidence Interval (Net Lift):** [-4886387.46%, -1747082.54%]
- **Mean Net Recovery per Seed:** ₹-195.70

---

## 5. AI / Deterministic Architectural Boundary

RevPlug maintains a strict, un-compromised boundary between AI reasoning and deterministic controls:

### What AI Handles
- Contextual candidate selection & intervention ranking
- Ambiguous failure interpretation & customer contextual evidence reasoning
- Generating structured proposal rationales

### What Deterministic Systems Handle
- Financial arithmetic & recovery rate calculations
- Settlement verification (authoritative webhook HMAC & payment IDs)
- Policy enforcement (`InterventionPolicy`) & hard stopping rules (`StoppingRules`)
- Consent enforcement (`opt_out_block`) & fraud protection (`block_hard_failure`)
- Incident suppression & duplicate transaction prevention (idempotency)

---

## 6. Reproducibility

To reproduce this exact benchmark report, execute:
```bash
python -m app.eval.run_benchmark
```