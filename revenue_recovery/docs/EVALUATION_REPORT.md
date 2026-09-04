# RevPlug Benchmark & Counterfactual ROI Report

**Generated At:** 2026-09-04 06:26:58 UTC
**Canonical Benchmark Scale:** 10 seeds (100 cases/seed, 1000 total) | Version `2.0-canonical`
**Evaluation Mode:** AI_ASSISTED (AI Contextual Routing + Deterministic Safety Shield)

---

## 1. Executive Summary

RevPlug is a **bounded autonomous revenue recovery system** designed to maximize settlement-verified revenue while enforcing strict deterministic safety policies and retry budgets.

In this multi-seed benchmark of **10 seeds (100 cases/seed, 1000 total)**:
- **39 AI-Assisted Cases** (single-seed detailed trace)
- **11 Deterministic Cases** (single-seed detailed trace)
- **39 AI Proposals Generated** (single-seed)
- **31 AI Proposals Accepted & Executed** (single-seed)
- **8 AI Proposals Blocked by Deterministic Policy Shield** (single-seed)
- **0 AI Fallbacks Triggered** (single-seed)
- **0 Safety Policy Violations** (single-seed)

Across 10 seeds, RevPlug won 9/10 seeds (90%) against the Safe Baseline. Mean Net Recovery: **₹55,241.55** vs Safe Baseline mean **₹28,678.40**.

---

## 2. Single-Seed Detailed Trace (Canonical Seed 42)

| Metric | Naive Fixed Retry | Safe Fixed Retry | RevPlug Bounded AI Agent | Net Uplift vs Safe |
| :--- | :--- | :--- | :--- | :--- |
| **Total Revenue at Risk** | ₹42,674.00 | ₹42,674.00 | ₹42,674.00 | — |
| **AI-Assisted Cases** | 0 | 0 | **39 (78.0%)** | — |
| **Deterministic Cases** | 50 (100%) | 50 (100%) | **11 (22.0%)** | — |
| **Verified Recovered Revenue** | ₹13,608.50 | ₹13,608.50 | **₹16,060.00** | **₹2,451.50** |
| **Verified Recovery Rate** | 31.9% | 31.9% | **37.6%** | **5.7% pts** |
| **Intervention Cost** | ₹455.00 | ₹395.00 | **₹87.00** | **-₹368.00** |
| **Net Recovered Revenue** | ₹13,153.50 | ₹13,213.50 | **₹15,973.00** | **₹2,759.50 (+20.9%)** |
| **AI Proposals Blocked by Policy** | 0 | 0 | **8** | — |
| **Safety Policy Violations** | **17** | **0** | **0** | — |

---

## 3. Revenue Attribution Breakdown (Single Seed)

| Attribution Category | Cases | Recovered Amount | Description |
| :--- | :--- | :--- | :--- |
| **DIRECT_AGENT** | 31 | ₹16,060.00 | Realized recovery directly driven by automated retries or alternate channels. |
| **AGENT_ASSISTED** | 8 | ₹0.00 | Realized recovery following payment links, reminders, or promise-to-pay workflows. |
| **ORGANIC** | 0 | ₹0.00 | Payment settled independently without qualifying agent intervention. |
| **UNKNOWN** | 11 | ₹0.00 | Unassigned attribution. |

---

## 4. Multi-Seed Statistical Robustness (Canonical Result)

**Total Seeds Evaluated:** 10 (Seeds 42–51) | **Cases per Seed:** 100

| Metric | Baseline A (Naive Retry) | Baseline B (Safe Retry) | RevPlug Autonomous Agent | RevPlug vs Safe |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Gross Recovery** | ₹29,499.40 | ₹29,499.40 | **₹55,380.75** | +87.7% |
| **Mean Net Recovery** | ₹28,569.40 | ₹28,678.40 | **₹55,241.55** | +92.6% |
| **Mean Recovery Rate** | 28.5% | 28.5% | **53.5%** | +25.0% pts |
| **Mean Safety Violations** | 39.3 | 28.4 | **0.0** | — |
| **Mean Decision Quality** | — | — | **63.9%** | — |

- **RevPlug Win Count vs Safe Baseline:** 9/10 seeds (90%)
- **95% Confidence Interval (Net Lift):** [+48.61%, +136.64%]
- **Mean Net Recovery per Seed:** ₹55,241.55
- **Safe Baseline Mean Net per Seed:** ₹28,678.40
- **Net Difference (RevPlug − Safe):** ₹26,563.15

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