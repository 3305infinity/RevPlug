# RevPlug Evaluation & Benchmark Methodology

This document outlines the evaluation methodology, baseline definitions, metrics, and safety guarantees for RevPlug.

---

## 1. Canonical Benchmark Location

The canonical machine-readable benchmark report is stored at:
`artifacts/evaluation_report.json`

Human-readable summaries are rendered directly from this artifact to prevent documentation drift.

---

## 2. Evaluation Methodology & Scale

RevPlug is evaluated using counterfactual batch evaluation across **10 pseudo-random seeds** (Seeds 42–51).

* **Dataset Scale:** 10 seeds $\times$ 100 cases = **1,000 total counterfactual evaluation cases**.
* **Failure Surfaces Evaluated:**
  * Payment failures (soft declines, authentication required, hard declines, fraud flags)
  * Checkout abandonment
  * Failed recurring subscription renewals
  * Overdue receivables & promise-to-pay commitments

Each case in the counterfactual dataset contains ground-truth failure parameters, customer preferences (e.g., opt-out flags), and exact outcome matrices for all candidate interventions.

---

## 3. Baseline Definitions

RevPlug performance is compared against two standardized operational baselines:

1. **Naive Fixed Retry Baseline (Baseline A):**
   * Executes standard automated retry attempts up to the maximum attempt budget ($N=3$).
   * Does not inspect failure root cause, customer opt-out status, fraud flags, or expected net value.
2. **Safe Fixed Retry Baseline (Baseline B):**
   * Enforces basic static retry budgets and filters hard fraud blocks.
   * Lacks dynamic channel routing, timing intelligence, expected value (EV) gating, and contextual AI reasoning.

---

## 4. How Revenue is Measured

Revenue is counted as **recovered** strictly when **settlement is verified**:

$$\text{Net Recovered Revenue} = \text{Verified Recovered Gross Revenue} - \text{Intervention Costs}$$

* **Settlement Verification:** Revenue is recognized ONLY when external settlement (webhook event, payment ID confirmation, or bank credit) is confirmed.
* **No Unverified / Projected Revenue:** Expected Recovery Value (EV) and AI confidence scores are decision-making inputs; they are **never** counted as realized revenue.
* **Simulated vs Real Money:** Benchmark evaluations run in counterfactual simulation or provider test-mode. All monetary amounts represent simulated test-mode recovery values and are never described as real customer funds.

---

## 5. Safety Violations & Bounded Autonomy

A **Safety Violation** occurs if any recovery action violates predefined policy constraints. RevPlug enforces a zero-tolerance policy shield (`InterventionPolicy` & `StoppingRules`).

The evaluation measures 10 specific safety violation classes:
1. Retrying fraud-flagged transactions (`fraud_retry`)
2. Retrying hard bank declines (`hard_decline_retry`)
3. Contacting opted-out customers (`opt_out_contact`)
4. Exceeding maximum retry budgets (`retry_budget_exceeded`)
5. Exceeding 24-hour contact limits (`contact_budget_exceeded`)
6. Contacting customers during an active Promise-to-Pay window (`promise_to_pay_violation`)
7. Intervening on expired cases (`expired_case_violation`)
8. Intervening on disputed invoices (`disputed_invoice_violation`)
9. Intervening on cancelled subscriptions (`cancelled_subscription_violation`)
10. Executing actions on terminal cases (`terminal_state_violation`)

**Benchmark Result:** Across all 1,000 benchmark cases, RevPlug recorded **0.0 safety violations**.

---

## 6. Stopping Rules & EV Gating

RevPlug halts automated recovery under any of the following stopping rules:
* **EV Gate Enforcement:** If $\text{Expected Net Value} \le 0$, recovery is stopped to prevent negative-ROI interventions.
* **Hard Decline / Fraud Block:** Immediately stops retries on non-retryable failure codes.
* **Opt-Out Compliance:** Immediately stops outbound communications if customer opts out.
* **Systemic Incident Suppression:** Automatically suppresses retries when an upstream gateway/issuer outage is detected.

---

## 7. Canonical Benchmark Results (10-Seed Aggregate)

| Metric | Baseline A (Naive) | Baseline B (Safe) | RevPlug Autonomous Agent | RevPlug vs Safe Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Net Recovery** | ₹28,569.40 | ₹28,678.40 | **₹55,241.55** | **+92.6% uplift** |
| **Mean Recovery Rate** | 28.5% | 28.5% | **53.5%** | **+25.0% pts** |
| **Mean Safety Violations** | 39.3 | 28.4 | **0.0** | **100% violation-free** |
| **Seed Win Rate** | 0/10 seeds | 1/10 seeds | **9/10 seeds (90.0%)** | — |

$$\text{Net Uplift \%} = \frac{\text{₹55,241.55} - \text{₹28,678.40}}{\text{₹28,678.40}} = +92.6\%$$
