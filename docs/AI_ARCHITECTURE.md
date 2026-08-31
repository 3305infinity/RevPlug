# RevPlug AI Architecture & Boundary Definition

## 1. Core Architectural Principle

RevPlug follows a strict **hybrid control plane** architecture:

> **AI may recommend, classify, reason, and rank candidates, but AI MUST NOT override hard safety constraints, retry limits, opt-out rules, fraud blocks, state transitions, or financial calculations.**

```text
                               1. REVENUE EVENT
                                      │
                                      ▼
                             2. AI ROUTER CHECK
                      (Clear Case vs Ambiguous Case)
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
           ┌──────────────────┐              ┌──────────────────┐
           │ Clear Case Path  │              │ Ambiguous Case   │
           │ (Deterministic)  │              │ AI Reasoning     │
           └────────┬─────────┘              └────────┬─────────┘
                    │                                 │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                            3. CANDIDATE GENERATION
                                     │
                                     ▼
                            4. AI CANDIDATE RANKING
                                     │
                                     ▼
                            5. ACTION REGISTRY CHECK
                             (Allowlist Validation)
                                     │
                                     ▼
                            6. DETERMINISTIC POLICY GATE
                         (Fraud Shield / Opt-out / Frequency)
                                     │
                                     ▼
                            APPROVE / STOP / ESCALATE
                                     │
                                     ▼
                          7. BOUNDED EXECUTION
```

---

## 2. Expected Net Recovery Formula & Candidate Ranking

RevPlug ranks candidate interventions using an explicit Net Recovery formula:

$$EV_{\text{net}} = \text{Gross Amount} \cdot P_{\text{recovery}} - \text{Intervention Cost} - \text{Friction Penalty}$$

Where:
- $P_{\text{recovery}}$ is estimated based on failure root cause, attempt count, and `RecoveryMemory` historical channel performance.
- $\text{Intervention Cost}$ is determined by `InterventionCostModel` (e.g. Retry: ₹5.00, Payment Link: ₹25.00, Reminder: ₹5.00, Human Escalation: ₹10.00).
- $\text{Friction Penalty}$ penalizes customer harassment for frequent outbound communications.

RevPlug exposes structured EV comparisons (`ACTION VALUE` vs `WAIT VALUE` vs `NO-ACTION VALUE`) as financial evidence in decision traces.

---

## 3. Security & Prompt-Injection Defense

1. **Untrusted Data Boundaries**: System prompts explicitly declare all customer message text, invoice notes, customer names, and gateway error descriptions as `UNTRUSTED DATA`.
2. **System Prompt Isolation**: Prompts enforce that embedded customer text cannot modify system instructions or bypass policy rules.
3. **Action Registry Allowlist**: All model recommendations are validated against `ActionRegistry`. Unregistered or hallucinated action strings are rejected before reaching policy checks or execution boundaries.
4. **Deterministic Safety Gate Enforcement**: Even if a prompt injection succeeded in coercing the LLM into recommending an unsafe action, the downstream `InterventionPolicy` and `DefaultRecoveryGuard` deterministically block execution.

---

## 4. Confidence & Safe Fallback Policy

- `confidence >= 0.80`: High-confidence recommendation proceeds to policy evaluation.
- `0.50 <= confidence < 0.80`: Medium confidence; requires conservative policy validation.
- `confidence < 0.50` OR schema validation error OR timeout OR API outage: Triggers **Safe Fallback** to deterministic rules engine (`NO_ACTION` or `STOP_RECOVERY`). The orchestrator never fails open.

---

## 5. Recovery Memory & Target Leakage Prevention

- `RecoveryMemoryStore` tracks historical channel performance (`retry_payment`, `send_payment_link`, `send_reminder`) per customer.
- **Causal Cleanliness Guarantee**: Only historical records created *prior* to current decision time are accessible to the agent. Future counterfactual outcomes are strictly isolated to the evaluation layer.
