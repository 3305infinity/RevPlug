# RevPlug Benchmark & Counterfactual ROI Report

**Generated At:** 2026-09-03 17:30:35 UTC
**Canonical Benchmark Scale:** 10 seeds (100 cases/seed, 1000 total) | Version `2.0-canonical`
**Evaluation Mode:** AI_ASSISTED (AI Contextual Routing + Deterministic Safety Shield)

---

## 1. Executive Summary

RevPlug is a **bounded autonomous revenue recovery system** designed to maximize settlement-verified revenue while enforcing strict deterministic safety policies and retry budgets.

In this multi-seed benchmark of **10 seeds (100 cases/seed, 1000 total)**:
- **30 AI-Assisted Cases** (single-seed detailed trace)
- **11 Deterministic Cases** (single-seed detailed trace)
- **30 AI Proposals Generated** (single-seed)
- **8 AI Proposals Accepted & Executed** (single-seed)
- **22 AI Proposals Blocked by Deterministic Policy Shield** (single-seed)
- **9 AI Fallbacks Triggered** (single-seed)
- **0 Safety Policy Violations** (single-seed)

Across 10 seeds, RevPlug won 4/10 seeds (40%) against the Safe Baseline. Mean Net Recovery: **₹25,973.20** vs Safe Baseline mean **₹32,971.65**.

---

## 2. Single-Seed Detailed Trace (Canonical Seed 42)

| Metric | Naive Fixed Retry | Safe Fixed Retry | RevPlug Bounded AI Agent | Net Uplift vs Safe |
| :--- | :--- | :--- | :--- | :--- |
| **Total Revenue at Risk** | ₹42,674.00 | ₹42,674.00 | ₹42,674.00 | — |
| **AI-Assisted Cases** | 0 | 0 | **30 (60.0%)** | — |
| **Deterministic Cases** | 50 (100%) | 50 (100%) | **11 (22.0%)** | — |
| **Verified Recovered Revenue** | ₹13,608.50 | ₹13,608.50 | **₹15,950.00** | **₹2,341.50** |
| **Verified Recovery Rate** | 31.9% | 31.9% | **37.4%** | **5.5% pts** |
| **Intervention Cost** | ₹455.00 | ₹395.00 | **₹135.00** | **-₹320.00** |
| **Net Recovered Revenue** | ₹13,153.50 | ₹13,213.50 | **₹15,815.00** | **₹2,601.50 (+19.7%)** |
| **AI Proposals Blocked by Policy** | 0 | 0 | **22** | — |
| **Safety Policy Violations** | **17** | **0** | **0** | — |

---

## 3. Revenue Attribution Breakdown (Single Seed)

| Attribution Category | Cases | Recovered Amount | Description |
| :--- | :--- | :--- | :--- |
| **DIRECT_AGENT** | 8 | ₹13,200.00 | Realized recovery directly driven by automated retries or alternate channels. |
| **AGENT_ASSISTED** | 31 | ₹2,750.00 | Realized recovery following payment links, reminders, or promise-to-pay workflows. |
| **ORGANIC** | 0 | ₹0.00 | Payment settled independently without qualifying agent intervention. |
| **UNKNOWN** | 11 | ₹0.00 | Unassigned attribution. |

---

## 4. Multi-Seed Statistical Robustness (Canonical Result)

**Total Seeds Evaluated:** 10 (Seeds 42–51) | **Cases per Seed:** 100

| Metric | Baseline A (Naive Retry) | Baseline B (Safe Retry) | RevPlug Autonomous Agent | RevPlug vs Safe |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Gross Recovery** | ₹33,799.15 | ₹33,799.15 | **₹26,272.00** | -22.3% |
| **Mean Net Recovery** | ₹32,865.65 | ₹32,971.65 | **₹25,973.20** | -21.2% |
| **Mean Recovery Rate** | 31.0% | 31.0% | **24.1%** | -6.9% pts |
| **Mean Safety Violations** | 38.2 | 27.6 | **0.0** | — |
| **Mean Decision Quality** | — | — | **39.0%** | — |

- **RevPlug Win Count vs Safe Baseline:** 4/10 seeds (40%)
- **95% Confidence Interval (Net Lift):** [-1,991,537.83%, +591,847.83%]
- **Mean Net Recovery per Seed:** ₹25,973.20
- **Safe Baseline Mean Net per Seed:** ₹32,971.65
- **Net Difference (RevPlug − Safe):** ₹-6,998.45

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