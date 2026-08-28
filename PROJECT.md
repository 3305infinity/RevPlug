# Recovery Engine — AI-Assisted Revenue Recovery

> **A bounded revenue-recovery engine that ranks at-risk money by expected recoverable value, diagnoses why revenue is slipping, recommends the highest-value intervention, and executes only actions permitted by deterministic safety policies — with every outcome measured and audited.**

Built for **Razorpay AI Buildathon — AI Revenue Recovery Track**.

---

# 1. Problem

Revenue leakage rarely happens as a single obvious failure.

A recurring payment fails. A checkout is abandoned. An invoice becomes overdue. The business may know that money is at risk, but the difficult part is deciding:

- **Which revenue should be recovered first?**
- **Why did the revenue become at risk?**
- **Is recovery actually likely?**
- **What intervention is most appropriate?**
- **When should the system retry, contact, escalate, or stop?**
- **Did the intervention actually recover money?**

Most recovery systems treat these as separate workflows. Payment retries live in one system, receivables in another, and customer follow-ups somewhere else. This creates three major problems:

1. **No unified view of revenue at risk.**
2. **No consistent decision-making across recovery channels.**
3. **Actions are measured, but actual recovered revenue often is not.**

The goal is therefore not to build another generic AI agent that sends reminders.

The goal is to build a **recovery decision engine** that connects:

```text
Revenue at risk
      ↓
Diagnosis
      ↓
Expected recovery value
      ↓
Intervention selection
      ↓
Safety / policy gate
      ↓
Bounded execution
      ↓
Outcome verification
      ↓
₹ actually recovered
```

# 2. Core Idea

The system treats every revenue-loss event as a common **recovery opportunity**.

Three possible sources feed the same engine:

```text
Razorpay payment failure ───────┐
Overdue receivable ─────────────┼──→ Recovery Engine
Abandoned checkout ─────────────┘
```

The first two are the primary workflows. Checkout abandonment is an optional extension if the core system is already stable.

Every opportunity is normalized into a canonical `recovery_item`.

The engine then answers four questions:

### 1. What happened?

Determine the root cause using deterministic rules wherever possible and AI only for ambiguous cases.

### 2. Is this worth pursuing?

Estimate the expected recoverable value rather than simply prioritizing the largest amount.

### 3. What should we do?

Recommend an intervention based on the failure reason, customer history, amount, previous attempts, and recovery probability.

### 4. Are we allowed to do it?

A deterministic policy engine enforces retry limits, cooldowns, contact restrictions, discount limits, and human-approval requirements.

**The LLM never directly controls money movement or execution.**

# 3. Central Design Principle

## AI handles judgment. Deterministic systems handle money.

This is the most important architectural decision in the project.

| Responsibility | System | Reason |
|---|---|---|
| Webhook verification | Deterministic | Security-critical |
| Event normalization | Deterministic | Reproducibility |
| Known failure classification | Rules | Fast, cheap, predictable |
| Ambiguous failure diagnosis | LLM | Handles unstructured/unknown cases |
| Recovery probability | Deterministic/model-based | Must be measurable |
| Expected recovery value | Deterministic | Financial calculation must be reproducible |
| Recovery prioritization | Deterministic | Prevent arbitrary LLM decisions |
| Intervention recommendation | LLM + structured rules | Requires contextual judgment |
| Customer message generation | LLM | Natural-language task |
| Promise-to-pay extraction | LLM | Structured extraction from free text |
| Retry limits | Policy engine | Safety-critical |
| Discount/waiver approval | Policy engine | Financial control |
| Actual execution | Policy engine | LLM cannot execute directly |
| Outcome measurement | Deterministic | Must reflect actual state |
| Audit trail | Deterministic | Accountability |

The LLM **proposes**.

The policy engine **decides**.

The ledger **records**.

The payment state **determines whether recovery actually happened**.

# 4. Recovery Decision Flow

```text
                    REVENUE EVENTS
                          │
          ┌───────────────┼────────────────┐
          ↓               ↓                ↓
   Payment Failure    Receivable       Checkout
     Razorpay          Overdue         Abandon
          │               │                │
          └───────────────┼────────────────┘
                          ↓
                EVENT NORMALIZATION
                          ↓
                  recovery_items
                          ↓
                 ROOT-CAUSE ANALYSIS
                    /          \
                   /            \
             Known case       Ambiguous
                ↓                ↓
             Rules             LLM
                \                /
                 \              /
                  └──────┬─────┘
                         ↓
               RECOVERY PROBABILITY
                         ↓
             EXPECTED VALUE SCORING
                         ↓
                 PRIORITY QUEUE
                         ↓
             INTERVENTION PLANNER
                         ↓
              POLICY / SAFETY GATE
                    /          \
                   /            \
               Allowed        Blocked
                  ↓               ↓
              Execute         Escalate
                  ↓               ↓
             Verify outcome    Human review
                  │
          ┌───────┴────────┐
          ↓                ↓
       Recovered        Not recovered
          │                │
          └───────┬────────┘
                  ↓
              AUDIT LOG
                  ↓
              DASHBOARD
```

# 5. Expected Recovery Value — The Core Intelligence

The system does not simply sort opportunities by amount.

Instead, each open recovery opportunity receives an expected-value score:

```text
Expected Recovery Value
=
Amount at Risk
×
Probability of Recovery
−
Intervention Cost
```

A priority score can additionally account for urgency:

```text
Priority Score
=
Expected Recovery Value
×
Urgency Factor
```

The ranking calculation is deterministic and reproducible.

The LLM may explain the ranking or resolve a genuine tie, but it does not invent the financial score.

# 6. Primary Workflow — Razorpay Payment Recovery

```text
Razorpay payment.failed webhook
            ↓
Signature verification
            ↓
Event normalization
            ↓
Idempotency check
            ↓
Deterministic failure classification
            ↓
Recovery probability
            ↓
Expected recovery value
            ↓
Recovery queue
            ↓
Intervention recommendation
            ↓
Policy validation
            ↓
Bounded retry / customer action / escalation
            ↓
Payment state verification
            ↓
Recovered / failed / stopped
            ↓
Audit + metrics
```

Known cases are handled through deterministic mappings. Unknown or ambiguous cases are passed to the AI diagnosis layer.

**Unknown does not mean “auto-retry.”**

# 7. Secondary Workflow — B2B Receivables Recovery

Overdue invoices enter the same recovery engine.

Synthetic invoice data is used for the build and evaluation.

Initial escalation ladder:

```text
Day 1  → gentle reminder
Day 3  → firmer reminder
Day 7  → escalation / permitted offer
Day 14 → human review
```

The exact thresholds remain configurable.

Every transition is recorded in the audit log.

# 8. Customer Interaction Intelligence

## 8.1 Message Generation

The LLM receives structured context such as customer tier, amount, root cause, days overdue, previous attempts, and preferred language, then produces a customer-facing draft.

Messages are **simulated/logged in the demo** unless an explicitly configured test integration is used.

## 8.2 Promise-to-Pay Extraction

A response such as:

```text
"Friday ko ₹18,000 clear kar dunga."
```

is converted into structured data:

```json
{
  "promised_date": "2026-08-28",
  "promised_amount": 18000,
  "confidence": 0.96
}
```

The system then creates a deterministic follow-up state.

> **LLM extracts structured intent; deterministic workflow handles the consequence.**

# 9. Intervention Planner

The AI produces a structured recommendation from a fixed action set:

```text
retry
payment_link
reminder
alternate_channel
promise_to_pay
human_escalation
stop
```

The policy engine evaluates the recommendation.

```text
LLM recommendation
        ↓
Policy engine
        ↓
APPROVE / REJECT / HUMAN REVIEW
```

The LLM cannot call the execution function directly.

# 10. Safety and Stopping Rules

### Payment retries

- Hard declines are never blindly retried.
- Fraud/risk-related failures are not automatically retried.
- Authentication-required failures are routed appropriately.
- Temporary failures can receive bounded retries.
- Maximum retry count is configurable.
- Cooldown between attempts is mandatory.
- Duplicate webhook events cannot create duplicate recovery actions.

### Customer communication

- Respect opt-out / do-not-contact state.
- Maximum number of automated contacts is configurable.
- Minimum cooldown between contacts is enforced.
- The system stops when payment is confirmed.
- The system stops when a customer requests no further contact.

### Financial offers

- Discounts/waivers have a configurable ceiling.
- Actions above the ceiling require human approval.
- The LLM cannot approve its own recommendation.

### Unknown cases

```text
Unknown
≠
Safe to retry
```

Unknown cases are explicitly routed to diagnosis and policy evaluation.

# 11. Canonical Data Model

## `recovery_items`

```text
id
source_type
customer_id
amount
currency
created_at
due_at
status
root_cause
root_cause_confidence
recovery_probability
expected_recovery_value
priority_score
attempt_count
last_action_at
next_action_at
recovered_amount
recovered_at
```

`source_type`:

```text
payment_failure
receivable
checkout_abandon
```

## `recovery_attempts`

```text
id
recovery_item_id
attempt_number
action
channel
scheduled_at
executed_at
outcome
```

## `promises`

```text
id
recovery_item_id
promised_date
promised_amount
confidence
extracted_from
fulfilled
```

## `recovery_outcomes`

This table separates **action taken** from **money actually recovered**.

```text
id
recovery_item_id
action
amount_before
amount_recovered
outcome
occurred_at
```

## `audit_log`

Append-only record of every important decision.

```text
id
recovery_item_id
actor
event_type
action
input_snapshot
decision
reasoning
confidence
policy_version
model_name
result
timestamp
```

A single recovery item should be reconstructable completely from the audit log.

# 12. Idempotency

Payment systems may deliver the same event more than once.

The system therefore treats webhook processing as idempotent:

```text
Webhook A
   ↓
process
   ↓
store event ID

Webhook A again
   ↓
event already processed
   ↓
NO duplicate recovery action
```

A unique database constraint protects against duplicate processing even if multiple workers receive the same event concurrently.

# 13. Reliability Model

Important failure scenarios include:

```text
Duplicate webhook
Concurrent webhook
Out-of-order webhook
Invalid webhook signature
Database unavailable
LLM timeout
LLM malformed JSON
LLM unavailable
Duplicate retry job
Payment succeeds after retry was scheduled
Customer opts out
Promise-to-pay expires
```

For each failure:

```text
Failure
   ↓
Detection
   ↓
Safe fallback
   ↓
Audit
   ↓
Regression test
```

The final project will document at least one **real engineering failure encountered during development**, what caused it, how it was fixed, and how the fix was tested.

# 14. Baseline Evaluation

The system should demonstrate whether the decision engine performs better than a simpler strategy.

### Baseline

```text
Retry / remind
→ fixed delay
→ retry / remind
→ stop
```

### Recovery Engine

```text
Diagnose
→ estimate recovery probability
→ calculate expected recovery value
→ prioritize
→ choose intervention
→ apply policy
→ execute
→ verify
```

Both strategies are evaluated on the same synthetic dataset.

Metrics include:

```text
Total amount at risk
Total amount recovered
Recovery rate
Expected vs actual recovered value
Average recovery time
Number of interventions
Unnecessary interventions
Human escalations
Cost per recovery
```

The project reports actual observed numbers from a reproducible batch.

# 15. Evaluation Dataset

Target:

```text
50–100 recovery opportunities
```

containing:

```text
Temporary payment failures
Hard payment failures
Authentication failures
Unknown failures
High-value overdue invoices
Low-value overdue invoices
Customers with strong payment history
Customers with weak payment history
Repeated failed attempts
Customers who opt out
Customers making promises to pay
Promises that are fulfilled
Promises that expire
```

The dataset should expose false positives and poor prioritization rather than containing only easy recoveries.

# 16. Proof / Evidence

### Proof 1 — Working repository

A clean clone should start using documented setup commands.

### Proof 2 — Real Razorpay test-mode event

Show:

```text
Razorpay
→ webhook
→ verification
→ classification
→ recovery decision
→ database
→ audit
```

### Proof 3 — Batch recovery

Show:

```text
100 opportunities
₹X at risk
₹Y recovered
Z% recovery rate
```

using actual reproducible results.

### Proof 4 — Baseline comparison

Show whether the recovery engine outperformed the fixed strategy on the same batch.

### Proof 5 — Auditability

Open one recovery item and reconstruct its entire lifecycle.

### Proof 6 — Safety

Demonstrate:

```text
duplicate webhook
→ one recovery action
```

and:

```text
discount above limit
→ human approval
```

### Proof 7 — Failure recovery

Show one genuine engineering failure:

```text
What broke
→ why
→ fix
→ test
→ resulting behavior
```

# 17. Dashboard

The dashboard should make the business result immediately visible.

### Executive metrics

```text
₹ At Risk
₹ Recovered
Recovery Rate
Expected Recovery Value
Active Recovery Items
Human Escalations
```

### Recovery breakdown

```text
By source
By root cause
By intervention
By customer segment
```

### Expected vs Actual

```text
Expected Recovery Value
        vs
Actual Recovered Amount
```

### Recovery queue

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

### Audit stream

```text
Timestamp
Item
Actor
Decision
Policy
Result
```

The dashboard should answer:

> **“How much money was at risk, what did the system do, and how much did it actually recover?”**

# 18. Technology Stack

### Backend
```text
Python
FastAPI
```

### Database
```text
PostgreSQL
```

### Payment Integration
```text
Razorpay Test Mode
Webhooks
```

### AI
```text
LLM API
Structured JSON outputs
```

The model/provider should remain replaceable behind an AI service interface.

### Orchestration
```text
Deterministic policy engine
State-machine based recovery workflows
```

n8n may be used for scheduling or auxiliary orchestration, but business-critical policy and classification remain inside application code.

### Dashboard
```text
Streamlit
```

### Infrastructure
```text
Docker Compose
pytest
GitHub Actions
```

# 19. Repository Structure

```text
recovery-engine/
│
├── core/
│   ├── ingestion/
│   ├── normalization/
│   ├── classification/
│   ├── policy/
│   ├── execution/
│   └── idempotency/
│
├── recovery/
│   ├── scoring/
│   ├── prioritization/
│   ├── intervention/
│   └── outcomes/
│
├── receivables/
│   ├── invoices/
│   ├── escalation/
│   └── promises/
│
├── ai/
│   ├── diagnosis/
│   ├── intervention/
│   ├── messaging/
│   └── extraction/
│
├── db/
│   ├── migrations/
│   └── seed/
│
├── dashboard/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── failure/
│   └── benchmark/
│
├── results/
│
├── docker-compose.yml
├── README.md
├── PROJECT.md
└── PLAN.md
```

# 20. What This Project Is — and Is Not

### This IS

- A revenue recovery decision engine.
- A combination of deterministic financial controls and AI-assisted reasoning.
- A measurable recovery system.
- A multi-source recovery architecture.
- A bounded automation system.
- An auditable system where consequential decisions can be reconstructed.

### This is NOT

- A generic chatbot.
- An LLM that autonomously moves money.
- A blind payment retry script.
- A system that claims recovery without verifying payment.
- A collection bot that sends unlimited reminders.
- An AI ranking system with unexplained financial decisions.

# 21. Build Philosophy

> **Build the smallest complete recovery loop first, then expand.**

The first milestone is not three triggers, four AI features, and a dashboard.

The first milestone is:

```text
Razorpay failure
      ↓
Normalize
      ↓
Classify
      ↓
Score
      ↓
Policy
      ↓
Recover / Stop
      ↓
Verify
      ↓
Audit
      ↓
Metric
```

Once this works reliably, receivables and additional AI capabilities are added on top of the same recovery engine.

# 22. Success Criteria

### Build Quality

- Clean repository structure.
- Reproducible setup.
- Automated tests.
- Idempotent event processing.
- Explicit state transitions.
- No uncontrolled LLM execution path.

### AI Judgment

- AI is used for ambiguity, interpretation and communication.
- Deterministic logic handles financial calculations and safety.
- AI recommendations are structured and policy-gated.
- AI failure has a safe fallback.

### Business Value

- Revenue at risk is measurable.
- Expected recovery value is measurable.
- Actual recovered amount is measurable.
- Baseline comparison is reproducible.

### Reliability

- Duplicate events are safely handled.
- Invalid events are rejected.
- LLM failures do not cause unsafe actions.
- Recovery actions are bounded.
- Every important transition is auditable.

### Proof

- Working repository.
- Real Razorpay test-mode webhook flow.
- Reproducible batch results.
- Dashboard.
- Audit trail.
- 5-minute working demo.
- Real engineering failure and documented recovery.

# 23. Final Product Statement

> **Recovery Engine turns revenue leakage into a measurable decision problem. It unifies failed payments and overdue receivables into a common recovery model, ranks opportunities by expected recoverable value, uses AI only where contextual judgment is required, and keeps every financial action behind deterministic safety policies. The system doesn't just report revenue at risk — it executes bounded recovery workflows, verifies the outcome, and proves how much money was actually recovered.**
