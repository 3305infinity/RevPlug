# RevPlug System Architecture Diagram & Component Boundaries

```text
                               1. TELEMETRY & WEBHOOK INGESTION
               ┌──────────────────────────────────────────────────────────────┐
               │ Provider-Neutral Webhook Adapter (/webhooks/events)          │
               │ HMAC-SHA256 Signature Verification                           │
               │ Idempotency Deduplication (ProviderEventRepository)          │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                               2. PERSISTED RECOVERY CASE STATE
               ┌──────────────────────────────────────────────────────────────┐
               │ Canonical RecoveryItem Model                                 │
               │ Context Snapshot: Amount, Root Cause, Metadata                │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                               3. CLOSED-LOOP REASONING LAYER
               ┌──────────────────────────────────────────────────────────────┐
               │ AIRouter (Clear vs Ambiguous Case Classifier)               │
               │ Groq Primary (llama-3.3-70b) / Gemini Secondary (gemini-pro)  │
               │ Prompt-Injection Defense: Customer Input = UNTRUSTED DATA    │
               │ Deterministic Fallback on Timeout or Confidence < 0.50       │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                               4. EXPECTED VALUE (EV) OPTIMIZER
               ┌──────────────────────────────────────────────────────────────┐
               │ Formula: EV_net = Gross * P_recovery - Cost - Friction       │
               │ Action vs Wait vs No-Action Financial Comparison              │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                               5. SERVER-SIDE POLICY GATE
               ┌──────────────────────────────────────────────────────────────┐
               │ Deterministic Safety Engine (InterventionPolicy)             │
               │ Hard Safety Rules: Fraud Shield / Opt-out / Retry Limit       │
               │ Contact Fatigue Limit: Max 2 contacts per 24h window          │
               └──────────────────────────────┬───────────────────────────────┘
                                       ↙             ↘
                                [ALLOW]               [BLOCK / STOP]
                                   │                         │
                                   ▼                         ▼
                        6. BOUNDED EXECUTORS           0 API Calls Made
               ┌──────────────────────────────┐     Capital Protected (₹18.2k)
               │ Razorpay Test Mode Executor  │              │
               │ Simulated Multi-Channel      │              │
               └──────────────┬───────────────┘              │
                              │                              │
                              ▼                              │
                        7. OBSERVE OUTCOME                   │
               ┌──────────────────────────────┐              │
               │ Webhook Settlement Verification│             │
               │ Case State Machine Update    │              │
               │ Closed-Loop Dynamic Re-Plan  │              │
               └──────────────┬───────────────┘              │
                              │                              │
                              └───────────────┬──────────────┘
                                              ▼
                                 8. IMMUTABLE AUDIT LEDGER
               ┌──────────────────────────────────────────────────────────────┐
               │ AuditTrailService & AttemptLedger Repository                 │
               │ Persisted Verification Evidence                              │
               └──────────────────────────────────────────────────────────────┘
```

---

## Component Classification Matrix

| Component | Architecture Type | Execution Authority | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **AIRouter / Groq / Gemini** | **AI Reasoning** | Advisory (Candidate Proposals) | Cause diagnosis & candidate ranking |
| **ExpectedValueScorer** | **Deterministic** | Advisory (EV Ranking) | Calculate net expected value ($EV_{\text{net}}$) |
| **InterventionPolicy** | **Deterministic Safety** | Mandatory (Server-Side) | Enforce fraud, opt-out, and budget rules |
| **ActionRegistry** | **Deterministic Schema** | Mandatory (Validation) | Allowlist model output action strings |
| **RecoveryOrchestrator** | **State Machine** | Mandatory (Lifecycle) | Manage iterative step transitions & re-planning |
| **Razorpay / Simulated Executor** | **External / Provider** | Bounded Execution | Execute API payment retries / payment links |
| **ProviderEventRepository** | **Persistence** | Mandatory (Idempotency) | Deduplicate incoming telemetry webhooks |
| **AttemptLedger & AuditLog** | **Persistence** | Mandatory (Audit) | Store immutable step evidence & outcomes |
