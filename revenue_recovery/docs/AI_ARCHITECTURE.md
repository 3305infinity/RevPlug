# RevPlug AI Architecture & Deterministic Safety Boundary

## Overview

RevPlug uses a hybrid architecture combining **LLM-based contextual reasoning** with **deterministic safety guardrails**:

- **AI Reasoning Layer**: Evaluates ambiguous failures, ranks candidate actions, interprets context, and generates structured proposal rationales.
- **Deterministic Safety Layer**: Enforces policy rules, retry budgets, fraud protection, consent/opt-out boundaries, financial arithmetic, and settlement verification.

---

## Architectural Decision Boundary

```text
                 ┌───────────────┐
                 │ Deterministic │
                 │ safety/policy │
                 └───────┬───────┘
                         │
Opportunity → Diagnose → Candidate Set
                         │
                         ↓
                 AI reasoning (AIRouter)
                         │
                         ↓
                  Proposed Action
                         │
                         ↓
                 Policy / Safety Shield
                    (InterventionPolicy)
                         │
                ┌────────┴────────┐
                ↓                 ↓
             Allowed           Denied
                ↓                 ↓
            Execute             STOP
                ↓
          Settlement Verify
                ↓
           Recovery Truth
```

### What AI Handles
- Contextual candidate selection among valid recovery options
- Intervention ranking based on failure context and customer history
- Contextual diagnosis and user-safe explanation generation

### What Deterministic Systems Handle
- Financial calculations (amount at risk, net recovery, recovery rate)
- Authoritative settlement verification (webhook HMAC, payment ID verification)
- Policy enforcement (`InterventionPolicy`) & hard stopping rules (`StoppingRules`)
- Consent / opt-out enforcement (`opt_out_block`) & fraud protection (`block_hard_failure`)
- Idempotency & duplicate execution prevention

---

## Explicit Decision Methods

Every evaluated case in RevPlug traces to one of 5 canonical decision methods:

| Decision Method | Description |
|---|---|
| `AI_ASSISTED` | Case routed to AI for contextual candidate selection; proposal allowed by policy. |
| `DETERMINISTIC` | Clear case or deterministic safety bypass (opt-out, fraud, retry limit). |
| `AI_FALLBACK` | AI attempted but failed schema/confidence check; safe deterministic fallback used. |
| `AI_REJECTED_BY_POLICY` | AI proposed an action, but policy gate blocked it for safety. |
| `UNEVALUABLE` | Case processing error. |

---

## Fallback & Idempotency Guarantees

1. **Safe Fallback**: If LLM times out, returns invalid JSON, violates schema, or produces confidence < 0.50, the system falls back safely to deterministic rules without failing open.
2. **Idempotency**: Execution requests enforce idempotent deduplication via `event_id` and `RecoveryStateMachine`. Evaluating the same case multiple times produces consistent outcomes without duplicate interventions.
