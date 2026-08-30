# RevPlug AI Architecture & Boundary Definition

## 1. Core Architectural Principle
RevPlug follows a strict **hybrid control plane** architecture:

> **AI may recommend, classify, reason, and rank candidates, but AI MUST NOT override hard safety constraints, retry limits, opt-out rules, fraud blocks, state transitions, or financial calculations.**

```
                    RECOVERY EVENT
                          │
                          ▼
                 ┌─────────────────┐
                 │ Deterministic   │
                 │ Validation      │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ AIRouter Check  │
                 │ (Clear/Ambig)   │
                 └────────┬────────┘
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐
│ Clear Case Path  │             │ Ambiguous Case   │
│ (Deterministic)  │             │ AI Reasoning     │
└────────┬─────────┘             └────────┬─────────┘
         │                                 │
         └────────────────┬────────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Candidate       │
                 │ Generation      │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ AI Ranking &    │
                 │ Recommendation  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Deterministic   │
                 │ Safety Gate     │
                 └────────┬────────┘
                          │
                          ▼
                 APPROVE / STOP / ESCALATE
                          │
                          ▼
                    EXECUTION
```

---

## 2. "Why AI?" vs "Why NOT AI?"

### Why AI?
- **Ambiguous Failure Descriptions**: Free-text error messages from payment gateways (e.g. *"Issuer 3DS challenge timeout"*, *"Cardholder velocity limit reached"*) require semantic interpretation that rigid regex or code matching cannot parse robustly.
- **Unstructured Context & Notes**: Customer service notes, invoice comments, and multi-channel communication histories contain qualitative signals relevant to choosing the right recovery strategy.
- **Candidate Ranking**: AI excels at ranking valid candidate interventions based on qualitative customer context.

### Why NOT AI?
- **Hard Safety & Compliance**: Opt-out consent, fraud blocks, chargeback protection, and regulatory contact windows require deterministic, zero-tolerance guarantees.
- **Financial Calculations & Arithmetic**: Expected Value (EV), net recovery margin, ROI, and ledger balances belong exclusively to deterministic code.
- **State Machine Transitions**: Financial item status transitions (`QUEUED`, `INTERVENTION_PENDING`, `PENDING_VERIFICATION`, `RECOVERED`) must remain state-machine controlled to prevent ledger corruption.

---

## 3. Security & Prompt-Injection Defense
1. **Untrusted Data Boundaries**: System prompts explicitly declare all customer message text, invoice notes, and gateway error descriptions as `UNTRUSTED DATA`.
2. **Sanitized Input Objects**: `RecoveryContext` excludes API keys, secrets, credentials, and unnecessary PII before prompt construction.
3. **Deterministic Safety Gate Enforcement**: Even if a malicious prompt injection succeeds in coercing the LLM into recommending a unsafe action, the downstream `InterventionPolicy` and `DefaultRecoveryGuard` deterministically block the execution.

---

## 4. Confidence & Safe Fallback Policy
- `confidence >= 0.80`: High-confidence AI recommendation proceeds to deterministic policy check.
- `0.50 <= confidence < 0.80`: Medium confidence; requires conservative policy validation.
- `confidence < 0.50` OR schema validation error OR timeout OR API outage: Triggers **Safe Fallback** to deterministic rules engine. The orchestrator never fails open.
