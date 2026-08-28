# Implementation Plan — Recovery Engine

> **Build order matters more than feature count.** Establish one reliable recovery loop first, prove it with real data, and then add additional recovery sources and AI capabilities without weakening the deterministic safety boundary.

**Legend:**  
- `[ ]` = TODO  
- **Deliverable** = what must work before moving forward  
- **Breaks-if** = failure to actively test for  
- **Proof** = evidence to capture for the final submission  

---

# Phase 0 — Freeze the Architecture

**Goal:** Establish the common data model and system boundaries before integrating either reference repository.

### Tasks

- [ ] Create the parent `recovery-engine/` repository.
- [ ] Keep the Etherlabs payment-recovery repository and Morsegrid repository as **reference sources**, not as blindly merged codebases.
- [ ] Define the canonical `recovery_items` model from `PROJECT.md`.
- [ ] Define `recovery_attempts`, `recovery_outcomes`, `promises`, and `audit_log`.
- [ ] Decide on **one PostgreSQL instance** for the final system.
- [ ] Choose one migration strategy and use it consistently.
- [ ] Define the boundary between ingestion, normalization, deterministic policy, AI reasoning, execution, outcome verification, and audit.
- [ ] Create the initial repository structure.

### Deliverable

```text
recovery-engine/
├── core/
├── recovery/
├── receivables/
├── ai/
├── db/
├── dashboard/
├── tests/
├── results/
├── PROJECT.md
├── PLAN.md
└── docker-compose.yml
```

### Breaks-if

Two independent databases, schemas, or state machines start developing independently.

---

# Phase 1 — Understand and Stabilize the Existing Payment Core

**Goal:** Run the deterministic payment-recovery foundation unchanged before modifying it.

### Tasks

- [ ] Run the Etherlabs payment-recovery repository locally.
- [ ] Understand its webhook ingestion, failure classification, retry policy, idempotency, recovery state, event/retry ledgers, and tests.
- [ ] Run its existing test suite.
- [ ] Record the baseline test result.
- [ ] Identify Stripe-specific components that must eventually be replaced.
- [ ] Identify reusable deterministic components that should remain.
- [ ] Move/reimplement the useful core into the new repository structure without changing behavior initially.

### Deliverable

The existing deterministic recovery core runs independently and its existing tests pass before Razorpay or AI changes are introduced.

### Proof

Save:

```text
results/baseline_core_tests.txt
```

### Breaks-if

You start modifying the payment engine before proving that the original implementation works.

---

# Phase 2 — Razorpay Vertical Slice

**Goal:** Get one real Razorpay test-mode failure through the entire recovery engine before adding other workflows.

This is the **first major milestone**.

### Tasks

- [ ] Create Razorpay test-mode credentials.
- [ ] Configure the required Razorpay webhook events.
- [ ] Expose the local webhook endpoint during development.
- [ ] Implement Razorpay webhook signature verification using the raw request body.
- [ ] Normalize Razorpay events into the internal payment-event format.
- [ ] Add idempotency protection.
- [ ] Replace Stripe-specific failure mappings with the appropriate Razorpay failure information.
- [ ] Preserve the deterministic policy structure:
  - temporary/recoverable → bounded recovery attempt
  - hard/fraud/auth-related → no blind retry
  - unknown → diagnosis / safe escalation
- [ ] Create/update the corresponding `recovery_items` row.
- [ ] Write the decision to `audit_log`.
- [ ] Execute the permitted recovery action in the test environment.
- [ ] Verify the resulting payment state.
- [ ] Record the final outcome in `recovery_outcomes`.

### Target flow

```text
Razorpay webhook
      ↓
Verify
      ↓
Normalize
      ↓
Idempotency
      ↓
Classify
      ↓
Create recovery_item
      ↓
Policy decision
      ↓
Execute
      ↓
Verify outcome
      ↓
Audit
```

### Deliverable

At least one Razorpay test-mode payment failure successfully completes this path.

### Proof

Capture:

- webhook received
- verification result
- classification
- policy decision
- database state
- audit record
- final outcome

### Breaks-if

**Webhook signature is verified against parsed/re-serialized JSON instead of the original raw request body.**

---

# Phase 3 — Recovery Scoring & Expected-Value Queue

**Goal:** Introduce the project's core business intelligence: deciding which revenue is worth recovering first.

### Tasks

- [ ] Define recovery-probability estimates for the initial failure categories.
- [ ] Implement:

```text
Expected Recovery Value
=
Amount at Risk
×
Recovery Probability
−
Intervention Cost
```

- [ ] Add urgency where appropriate.
- [ ] Store:
  - `recovery_probability`
  - `expected_recovery_value`
  - `priority_score`
- [ ] Build a ranked recovery queue.
- [ ] Ensure the ranking is deterministic and reproducible.
- [ ] Add unit tests for the scoring calculation.
- [ ] Add test cases where:
  - highest amount ≠ highest priority
  - highest probability ≠ highest priority
  - expected-value ranking changes when intervention cost changes

### Deliverable

Given a batch of open recovery items, the engine produces a reproducible ranked recovery queue.

### Proof

Demonstrate that the ranking is based on expected recoverable value rather than raw amount.

### Breaks-if

An LLM is allowed to invent or directly control the financial ranking.

---

# Phase 4 — Receivables Recovery Workflow

**Goal:** Prove that the same recovery engine can handle a second revenue-loss source without creating a separate system.

### Tasks

- [ ] Create an `invoices` model.
- [ ] Create synthetic overdue-invoice data.
- [ ] Seed 40–60 invoices with variation in amount, aging, customer history, payment behavior, and previous contact attempts.
- [ ] Convert each eligible invoice into a `recovery_item`.
- [ ] Calculate recovery probability and expected recovery value.
- [ ] Add a deterministic escalation state machine.

Initial ladder:

```text
Day 1  → gentle reminder
Day 3  → firmer reminder
Day 7  → escalation / permitted offer
Day 14 → human review
```

- [ ] Add maximum-contact limits.
- [ ] Add contact cooldowns.
- [ ] Stop immediately after payment.
- [ ] Stop on customer opt-out.
- [ ] Enforce discount/waiver limits.
- [ ] Record every transition in `audit_log`.

### Deliverable

A batch of overdue invoices flows through the same recovery engine and produces bounded escalation histories.

### Proof

Open one invoice and reconstruct its lifecycle from risk through recovery or escalation.

### Breaks-if

The receivables system becomes an independent reminder application instead of using the common recovery engine.

---

# Phase 5 — AI Decision Layer

**Goal:** Add AI where contextual judgment is genuinely useful while preserving the deterministic execution boundary.

## 5A — AI Diagnosis

### Tasks

- [ ] Keep deterministic classification as the first layer.
- [ ] Send only ambiguous/unmapped cases to the LLM.
- [ ] Require structured output.
- [ ] Restrict output to known root-cause categories.
- [ ] Return confidence.
- [ ] Record relevant evidence/features used by the model.
- [ ] Store the structured decision in `audit_log`.
- [ ] Add fallback behavior for timeout, invalid JSON, unavailable model, and low confidence.

### Deliverable

An ambiguous failure can be converted into a valid existing root-cause category without allowing the model to execute an action.

---

## 5B — AI Intervention Planner

### Tasks

Give the model structured context:

```text
customer
amount
root cause
payment history
previous attempts
recovery probability
expected recovery value
available channels
policy constraints
```

Ask it to recommend from a fixed action set:

```text
retry
payment_link
reminder
alternate_channel
promise_to_pay
human_escalation
stop
```

- [ ] Validate the output against a schema.
- [ ] Pass the recommendation to the policy engine.
- [ ] Never allow the LLM to call the execution function directly.
- [ ] Log recommendation + policy decision separately.

### Deliverable

```text
LLM recommendation
        ↓
Policy engine
        ↓
APPROVE / REJECT / HUMAN REVIEW
```

---

## 5C — Customer Interaction Intelligence

### Tasks

- [ ] Generate customer-facing recovery messages.
- [ ] Support configurable tone/language.
- [ ] Add Hinglish as an optional demo mode.
- [ ] Mark outbound communication as simulated unless an actual test integration is explicitly enabled.
- [ ] Extract promise-to-pay information from free-text replies.
- [ ] Store promised date, promised amount, and extraction confidence.
- [ ] Schedule deterministic follow-up.
- [ ] Escalate when the promise expires without payment.

### Deliverable

A customer response such as:

```text
"Friday ko ₹18,000 clear kar dunga."
```

becomes a structured promise and affects the subsequent workflow.

### Breaks-if

The LLM is allowed to create new financial actions outside the configured action/policy space.

---

# Phase 6 — Unified Audit & Outcome Verification

**Goal:** Make the system completely reconstructable.

### Tasks

- [ ] Route every consequential state transition through a shared audit mechanism.
- [ ] Record actor, event, action, input snapshot, decision, confidence, policy version, model, result, and timestamp.
- [ ] Ensure audit records are append-only.
- [ ] Add `recovery_outcomes`.
- [ ] Distinguish action executed, payment succeeded, and amount recovered.
- [ ] Verify dashboard metrics can be derived from stored state rather than manually maintained counters.
- [ ] Pick five random recovery items and reconstruct their complete lifecycle from the audit trail.

### Deliverable

One audit trail works across payment failures and receivables.

### Breaks-if

A code path updates business state without producing the corresponding audit event.

---

# Phase 7 — Failure Engineering

**Goal:** Deliberately test the system against failures that matter in production.

### Test scenarios

- [ ] Duplicate webhook.
- [ ] Concurrent duplicate webhook.
- [ ] Out-of-order event.
- [ ] Invalid webhook signature.
- [ ] Database unavailable.
- [ ] LLM timeout.
- [ ] LLM malformed output.
- [ ] LLM unavailable.
- [ ] Duplicate recovery job.
- [ ] Payment succeeds after a retry is scheduled.
- [ ] Customer opts out.
- [ ] Promise-to-pay expires.
- [ ] Retry limit reached.
- [ ] Human approval required.
- [ ] Unknown failure category.

### For every important failure

```text
Failure
   ↓
Observed behavior
   ↓
Root cause
   ↓
Fix
   ↓
Regression test
   ↓
Result
```

### Deliverable

A dedicated failure test suite covering the major reliability boundaries.

### Proof

At least one genuine development failure becomes the project's **“what broke at 2 AM”** story.

**Do not invent this story. Build the evidence as you go.**

---

# Phase 8 — Checkout Abandonment

**Goal:** Add a third entry point only after the common recovery engine is stable.

### Tasks

- [ ] Generate synthetic checkout-abandonment events.
- [ ] Normalize them into `recovery_items`.
- [ ] Calculate expected recovery value.
- [ ] Apply a shorter recovery window.
- [ ] Use the same scoring, intervention, policy, audit, and outcome pipeline.

### Deliverable

Checkout abandonment becomes another input into the same recovery engine.

### Priority

**Cut this phase first if time becomes constrained.**

Payment failure + receivables already prove the multi-source architecture.

---

# Phase 9 — Dashboard & Proof

**Goal:** Make the value of the system visible without requiring verbal explanation.

### Dashboard sections

#### Revenue overview

```text
₹ At Risk
₹ Recovered
Recovery Rate
Expected Recovery Value
Active Opportunities
Human Escalations
```

#### Recovery queue

```text
Priority
Customer
Amount
Root Cause
Recovery Probability
Expected Value
Recommended Action
Policy Status
```

#### Recovery performance

```text
By root cause
By intervention
By source
By channel
```

#### Expected vs Actual

```text
Expected Recovery Value
        vs
Actual Recovered Amount
```

#### Audit stream

```text
Timestamp
Item
Actor
Decision
Policy
Result
```

### Deliverable

A single dashboard screen clearly communicating:

> **How much money was at risk → what the engine prioritized → what it did → how much money came back.**

---

# Phase 10 — Benchmark Against the Baseline

**Goal:** Produce the strongest quantitative evidence for the project.

### Dataset

Create a reproducible batch of:

```text
50–100 recovery opportunities
```

containing diverse payment failures and overdue invoices.

### Run 1 — Baseline

Use a simple fixed strategy:

```text
Retry/remind
→ fixed delay
→ retry/remind
→ stop
```

### Run 2 — Recovery Engine

```text
Diagnosis
→ recovery probability
→ expected-value prioritization
→ intervention recommendation
→ policy gate
→ execution
→ outcome verification
```

### Compare

```text
Total amount at risk
Total recovered
Recovery rate
Average recovery time
Number of actions
Unnecessary actions
Human escalations
Cost per recovery
```

### Deliverable

```text
results/
├── baseline_run_01.json
├── recovery_engine_run_01.json
└── comparison_01.json
```

### Critical rule

**Never choose the numbers beforehand.**

The benchmark output determines the claims made in the README and demo.

---

# Phase 11 — Stress Test the System

**Goal:** Demonstrate that the system remains correct under repeated or adversarial event delivery.

### Tests

- [ ] Replay the same webhook repeatedly.
- [ ] Send concurrent duplicate events.
- [ ] Run large synthetic batches.
- [ ] Inject random LLM failures.
- [ ] Inject random database failures where practical.
- [ ] Verify recovery actions remain bounded.
- [ ] Verify recovered amount is not double-counted.
- [ ] Verify audit history remains consistent.

### Deliverable

A stress-test result demonstrating:

```text
N events
→ M unique recovery items
→ K actual actions
→ no duplicate recovery
→ correct final ledger
```

---

# Phase 12 — Final Packaging

**Goal:** Turn the engineering work into a submission that is easy to evaluate.

### README

Include:

- problem
- product thesis
- architecture
- setup
- demo instructions
- AI vs deterministic boundary
- safety rules
- benchmark methodology
- actual results
- evidence-status table
- known limitations
- failure story

### Evidence status

Clearly distinguish:

```text
REAL
- Razorpay test-mode webhook
- webhook verification
- database state transitions
- policy execution
- automated tests

SIMULATED
- outbound customer messaging
- synthetic receivables
- synthetic benchmark dataset

NOT YET PROVEN
- production recovery rate
- real-world customer ROI
```

### Clean-clone test

Before submission:

- [ ] Clone repository into a fresh directory.
- [ ] Follow README without relying on local files.
- [ ] Start the system.
- [ ] Run tests.
- [ ] Run the demo dataset.
- [ ] Confirm dashboard works.
- [ ] Confirm no secrets are committed.

### Deliverable

A repository that another person can actually run.

---

# Phase 13 — 5-Minute Demo

## 0:00–0:30 — Problem

Show:

```text
₹X revenue at risk
across failed payments + overdue invoices
```

Explain:

> “The problem isn't detecting failed payments. The problem is deciding which money to pursue, what intervention makes sense, and when automation should stop.”

## 0:30–1:15 — Architecture

Show:

```text
Events
 ↓
Normalization
 ↓
Expected Value
 ↓
AI Diagnosis / Intervention
 ↓
Policy Gate
 ↓
Execution
 ↓
Verification
 ↓
Audit
```

Explicitly explain:

> **AI proposes; deterministic policy controls execution.**

## 1:15–2:45 — Live Recovery

Show one payment failure:

```text
Razorpay webhook
→ diagnosis
→ expected recovery value
→ intervention
→ policy approval
→ recovery
```

Then show one receivable:

```text
overdue invoice
→ priority
→ message
→ promise-to-pay
→ follow-up
```

## 2:45–3:30 — Proof

Show:

```text
₹ At Risk
₹ Recovered
Recovery Rate
Expected Value
```

Then:

```text
Baseline
vs
Recovery Engine
```

## 3:30–4:30 — What Broke

Show the actual engineering failure:

```text
What happened
→ Why it happened
→ How we detected it
→ Fix
→ Regression test
```

## 4:30–5:00 — Closing

End with:

> **“The system doesn't give an LLM control over money. It uses AI where ambiguity exists, deterministic policies where safety matters, and measures success by money actually recovered.”**

---

# Cross-Cutting Engineering Rules

| Risk | Protection |
|---|---|
| Duplicate webhook | Idempotency key + unique DB constraint |
| Concurrent processing | Transactional state transition / locking |
| Invalid webhook | Raw-body signature verification |
| Unknown failure | Safe fallback / no blind retry |
| Unlimited retries | Hard retry budget |
| Customer spam | Contact cooldown + maximum attempts |
| Customer opt-out | Immediate stop |
| Excessive discount | Human approval |
| LLM hallucination | Structured output + schema validation |
| LLM outage | Deterministic fallback / safe stop |
| LLM execution | Prohibited |
| Double-counted recovery | Outcome ledger + idempotent settlement |
| Dashboard mismatch | Derive metrics from canonical state |
| Timezone errors | Store timestamps in UTC |
| Benchmark cherry-picking | Fixed reproducible dataset |
| Demo failure | Pre-generated reproducible dataset + recorded evidence |

---

# Final Build Order

If you get overwhelmed, **ignore every phase except the next one**.

```text
1. Run existing payment core
          ↓
2. Razorpay vertical slice
          ↓
3. Expected-value scoring
          ↓
4. Receivables
          ↓
5. AI diagnosis + intervention
          ↓
6. Audit + outcome verification
          ↓
7. Failure testing
          ↓
8. Dashboard
          ↓
9. Baseline benchmark
          ↓
10. Optional checkout
          ↓
11. Final demo + README
```

**Rule for the entire project:**

> **Never add the next feature until the previous stage has a working test and a piece of evidence.**
