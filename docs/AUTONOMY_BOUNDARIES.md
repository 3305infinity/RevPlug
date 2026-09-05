# Bounded Autonomous Agent Trust Model & Autonomy Boundaries

RevPlug operates as a **bounded autonomous agent**. It performs closed-loop revenue recovery while guaranteeing that safety, policy constraints, financial ledger integrity, and stopping conditions are strictly enforced by deterministic, non-bypassable code.

---

## 1. What the Agent Can Autonomously Do

1. **Detect Revenue Risk**: Automatically ingest payment failure webhooks, overdue receivables, and subscription renewal failures.
2. **Diagnose Failure Context**: Categorize failures (soft decline, hard decline, issuer timeout, fraud risk, authentication required) using deterministic classifiers or AI context interpretation.
3. **Generate & Rank Recovery Plans**: Formulate multi-step recovery plans (`ordered_actions`) prioritizing high Expected Value ($EV$) actions.
4. **Execute Bounded Low-Risk Interventions**: Autonomously dispatch retries, payment links, or customer reminder messages up to predefined budget limits.
5. **Event-Driven Waiting**: Pause workflows while awaiting payment provider webhooks or customer conversion events.
6. **Verify Settlement Outcomes**: Match authoritative provider settlement evidence against outstanding recovery items.
7. **Halt Execution Automatically**: Immediately stop recovery workflows upon detecting opt-outs, hard declines, fraud signals, negative $EV$, or budget exhaustion.
8. **Escalate to Human Review**: Escalate ambiguous cases, low AI confidence decisions, or high-value cases requiring manual approval.

---

## 2. What the Agent Cannot Autonomously Do

1. **Override Safety Policies**: Cannot execute actions blocked by `InterventionPolicy`, `StoppingRules`, or `RecoveryGuard`.
2. **Alter Financial Ledgers or Accounting Truth**: Cannot invent recovered amounts or declare revenue recovered without verified settlement evidence from a payment provider or bank webhook.
3. **Increase Autonomy Budgets**: Cannot modify `max_payment_retries`, `max_contact_attempts`, `max_total_cost`, or `workflow_ttl`.
4. **Bypass Approval Gates**: Cannot execute high-value or high-risk actions without explicit human reviewer approval.
5. **Reopen Terminal Cases**: Cannot execute actions on cases marked `RECOVERED`, `STOPPED`, `ESCALATED`, or `EXPIRED`.
6. **Invent Unsupported Actions**: Cannot execute arbitrary shell commands, unapproved API calls, or unsupported financial transactions.
7. **Confuse Execution with Recovery**: Cannot treat intervention dispatch as recovered revenue.

---

## 3. Closed-Loop Execution Lifecycle

```text
  DETECT (Ingest Webhook / Receivable)
    ↓
  DIAGNOSE (Categorize Failure & Context)
    ↓
  PLAN (Generate Multi-Step RecoveryPlan)
    ↓
  POLICY & SAFETY CHECK (Deterministic Policy Gate)
    ↓
  ECONOMIC CHECK (Expected Value Score EV > 0)
    ↓
  APPROVAL GATE (Human Review if Confidence < 0.80 or High-Value)
    ↓
  ACT (Idempotent Action Execution)
    ↓
  WAIT (Event-Driven Webhook / Settlement Verification)
    ↓
  VERIFY (Independent Settlement Verification)
    ↓
  RECOVER / STOP / ESCALATE (Authoritative State Transition)
```
