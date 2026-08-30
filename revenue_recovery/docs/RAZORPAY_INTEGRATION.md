# RevPlug — Real Razorpay Test Mode Integration Architecture

This document describes the production architecture for RevPlug's real Razorpay Test Mode integration, signature verification, payment link execution, and settlement evidence validation.

---

## 1. End-to-End Lifecycle Architecture

```text
Razorpay Webhook / Gateway Failure Event
                 ↓
     Signature Verification & Ingestion
                 ↓
   Failure Classification & Risk Scoring
                 ↓
       Groq LLM AI Diagnosis & Proposal
                 ↓
   Server-side Deterministic Policy Engine Gate
                 ↓
      [ ALLOW ]          [ BLOCKED ]
          ↓                   ↓
Razorpay Test Mode API    Stop / Escalate
 (Payment Link Created)
          ↓
  Customer Payment Event (Test Mode Checkout)
          ↓
 Razorpay Webhook (payment_link.paid)
          ↓
   HMAC-SHA256 Signature Verification
          ↓
 Amount & Currency Integrity Validation
          ↓
      Verified Money Settlement (Ledger)
```

---

## 2. Core Architectural Invariants

> **CRITICAL INVARIANT 1: ZERO EXECUTION PRIVILEGE FOR AI**
> The AI reasoning agent (Groq / Gemini) produces proposals with confidence scores. The AI CANNOT invoke the Razorpay API, issue refunds, or move money directly. Only the server-side `PolicyEngine` can approve an action.

> **CRITICAL INVARIANT 2: ACTION EXECUTED ≠ MONEY RECOVERED**
> Creating a Razorpay Test Mode Payment Link marks an intervention as `ACTION_EXECUTED`. Money is NOT counted as recovered until a signed, verified Razorpay webhook (`payment_link.paid` or `payment.captured`) is processed and validated against the expected recovery item amount.

> **CRITICAL INVARIANT 3: STRICT FINANCIAL BOUNDS**
> Recovered value is strictly capped: `0 <= verified_recovery <= amount_at_risk`. Webhooks reporting higher amounts or mismatched currencies are rejected from settlement calculations.

---

## 3. Razorpay Test Mode API Client & Executor

The Razorpay integration operates in two distinct modes:

- `RECOVERY_EXECUTION_MODE=simulation` (Default for tests, CI, and benchmark runs): Uses `SimulatedRecoveryExecutor` to mock payment actions without network calls.
- `RECOVERY_EXECUTION_MODE=razorpay_test` (Judge & Live Demo path): Uses `RazorpayClient` to create real Razorpay Test Mode Payment Links via `https://api.razorpay.com/v1/payment_links`.

### API Credentials Configuration (`.env`)

```env
RECOVERY_EXECUTION_MODE=razorpay_test
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_test_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_ENV=test
```

---

## 4. Idempotency & Unknown Outcome Reconciliation

- **Request Idempotency:** Payment link creation requests use `reference_id = item.id` to prevent duplicate resource creation on API retries.
- **Network Timeout Handling:** If a network timeout occurs while calling Razorpay, the executor records `error_code="EXECUTION_UNKNOWN"` and sets `reconciliation_required=True` rather than creating a duplicate payment link.
- **Webhook Idempotency:** `RazorpayWebhookService` verifies `provider_events` table for previous event ID processing to prevent double-counting duplicate webhooks.

---

## 5. Razorpay Webhook Signature Verification

All incoming webhooks at `/api/razorpay/webhook` are validated using HMAC-SHA256 against `RAZORPAY_WEBHOOK_SECRET`:

$$\text{Expected Signature} = \text{HMAC-SHA256}(\text{RAZORPAY\_WEBHOOK\_SECRET}, \text{Raw Request Body})$$

- Missing, invalid, or tampered signature headers return `HTTP 400 Bad Request` and halt processing immediately.

---

## 6. MCP Preparation (Stage 12 Readiness)

The `RazorpayRecoveryExecutor` isolates provider API interaction behind the standard `RecoveryExecutor` protocol interface:

```python
class RecoveryExecutor(Protocol):
    def execute(self, item: RecoveryItem, action: str, *, attempt_number: int) -> ExecutionResult:
        ...
```

This ensures that upgrading to Razorpay MCP in Stage 12 will require zero changes to the AI agent, policy engine, financial ledger, or audit subsystem.
