# RevPlug Scientific Benchmark Methodology & Specification

> **A scientifically defensible, judge-proof benchmark comparing autonomous recovery agents against fixed retry baselines under 100% fair and identical evaluation conditions.**

---

## 1. Evaluation Architecture & Pipeline

```text
                  SYNTHETIC CASE GENERATION (Seeds 42..51)
                                      │
                                      ▼
                        IDENTICAL 100-CASE BATCH POOL
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
   BASELINE A (NAIVE RETRY)   BASELINE B (SAFE RETRY)   BASELINE C (BEST FIXED)
   (No Policy / 2 Retries)    (100% Policy Compliant)   (Failure-Matched Action)
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                          REVPLUG AUTONOMOUS AGENT
                       (Closed-Loop Dynamic Re-Plan)
                                      │
                                      ▼
                         PAIRED STATISTICAL COMPARISON
                  (Gross EV, Net EV, Lift %, 95% Confidence CI)
```

---

## 2. Baselines Evaluated

1. **Baseline A (Naive Fixed Retry)**:
   - Always retries twice regardless of root cause.
   - Ignores fraud risk flags, customer opt-outs, and bank failure codes.
   - Demonstrates the financial and safety risks of naive automated retry scripts.

2. **Baseline B (Safe Fixed Retry)**:
   - Enforces 100% identical policy rules as RevPlug (0 safety violations).
   - If a case is flagged as fraud or opted-out, Baseline B halts with 0 retries.
   - Non-adaptive: retries payment up to 2 times for non-blocked cases, but cannot pivot strategy if retries fail.

3. **Baseline C (Best Single Fixed Action)**:
   - Selects the best single fixed action matched to initial failure class (`retry_payment` for soft, `send_payment_link` for auth/card, `send_reminder` for invoice).
   - Non-adaptive: executes the fixed action but cannot re-plan if execution fails.

4. **RevPlug Autonomous Agent**:
   - Closed-loop agent that evaluates candidates, checks policy, executes bounded action, observes outcome, and dynamically re-plans strategy on failure.

---

## 3. Fairness Invariants & Causal Cleanliness

1. **Identical Risk Pool**: All evaluators receive identical cases generated from reproducible random seeds.
2. **Identical Ground-Truth Outcomes**: Counterfactual outcomes are evaluated against identical underlying failure-class probability distributions.
3. **Zero Target Leakage**: The agent decision engine receives context snapshot attributes available *prior* to decision time. Future counterfactual outcomes are isolated exclusively to the evaluation layer.
4. **Identical Cost Structure**: All systems use identical intervention cost models (Retry: ₹5.00, Payment Link: ₹25.00, Reminder: ₹5.00).

---

## 4. Statistical Metrics Reported

- **Mean Gross & Net Recovery**: Measured across 10 seeds (1,000 total cases).
- **Distribution Metrics**: Mean, Median, P25, P75, Standard Deviation.
- **95% Confidence Interval**: Calculated via Student's $t$-distribution on paired net recovery differences:
  $$CI_{95} = \bar{d} \pm t_{0.025, n-1} \cdot \frac{s_d}{\sqrt{n}}$$
- **Seed Win Rate**: Percentage of evaluation seeds where RevPlug net recovery exceeds baseline net recovery.
