# RevPlug Benchmark & Counterfactual ROI Report

**Generated At:** 2026-09-03 06:06:11 UTC
**Canonical Benchmark Scale:** 50 cases | 10 seeds (`42` to `51`) | Version `2.0-canonical`
**Evaluation Mode:** AI_ASSISTED (AI Contextual Routing + Deterministic Safety Shield)

---

## 1. Executive Summary

RevPlug is a **bounded autonomous revenue recovery system** designed to maximize settlement-verified revenue while enforcing strict deterministic safety policies and retry budgets.

In this multi-seed benchmark of **50 cases** across 10 deterministic seeds:
- **30 AI-Assisted Cases** (contextual candidate selection & ranking)
- **11 Deterministic Cases** (opt-out compliance, fraud protection, retry budget enforcement)
- **30 AI Proposals Generated**
- **8 AI Proposals Accepted & Executed**
- **22 AI Proposals Blocked by Deterministic Policy Shield**
- **9 AI Fallbacks Triggered**
- **0 Safety Policy Violations**

RevPlug achieved a **+42.1% Net Recovery Lift** over naive fixed-retry baselines and **+41.4% Net Lift** over safe fixed-retry baselines, recovering **₹18,800.00** with **ZERO safety policy violations**.

---

## 2. Benchmark Financial & AI Decision Proof

| Metric | Naive Fixed Retry | Safe Fixed Retry | RevPlug Bounded AI Agent | Net Uplift |
| :--- | :--- | :--- | :--- | :--- |
| **Total Revenue at Risk** | ₹42,674.00 | ₹42,674.00 | ₹42,674.00 | — |
| **AI-Assisted Cases** | 0 | 0 | **30 (60.0%)** | **+30 AI Cases** |
| **Deterministic Cases** | 50 (100%) | 50 (100%) | **11 (22.0%)** | — |
| **Verified Recovered Revenue** | ₹13,608.50 | ₹13,608.50 | **₹18,800.00** | **+₹5,191.50** |
| **Verified Recovery Rate** | 31.9% | 31.9% | **44.1%** | **+12.2% Uplift** |
| **Intervention Cost** | ₹455.00 | ₹395.00 | **₹112.00** | **-₹343.00 Cost** |
| **Net Recovered Revenue** | ₹13,153.50 | ₹13,213.50 | **₹18,688.00** | **+₹5,474.50 (+41.4%)** |
| **AI Proposals Blocked by Policy** | 0 | 0 | **22** | **100% Policy Shield Protection** |
| **Safety Policy Violations** | **17** | **0** | **0** | **-100% Policy Violations** |

---

## 3. Revenue Attribution Breakdown

RevPlug enforces strict financial truth: money is recognized as recovered ONLY when backed by authoritative settlement evidence.

| Attribution Category | Cases | Recovered Amount | Description |
| :--- | :--- | :--- | :--- |
| **DIRECT_AGENT** | 8 | ₹13,200.00 | Realized recovery directly driven by automated retries or alternate channels. |
| **AGENT_ASSISTED** | 31 | ₹5,600.00 | Realized recovery following payment links, reminders, or promise-to-pay workflows. |
| **ORGANIC** | 0 | ₹0.00 | Payment settled independently without qualifying agent intervention. |
| **UNKNOWN** | 11 | ₹0.00 | Unassigned attribution. |

---

## 4. Multi-Seed Statistical Robustness

- **Total Seeds Evaluated:** 10 (Seeds 42–51)
- **RevPlug Win Rate vs Safe Baseline:** 7/10 seeds (70%)
- **95% Confidence Interval (Net Lift):** [-1446345.78%, +999275.78%]
- **Mean Net Recovery per Seed:** ₹30,736.30

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