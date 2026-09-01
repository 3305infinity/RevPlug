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
                               2. OPPORTUNITY DETECTION ENGINE
               ┌──────────────────────────────────────────────────────────────┐
               │ OpportunityDetector (app/services/opportunity_detector.py)   │
               │ Root Cause Classification & Net EV Scoring ($EV_net$)        │
               │ Deterministic Policy Shields (Fraud / Opt-out / Dispute)      │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                                3. RANKED OPPORTUNITY INBOX
               ┌──────────────────────────────────────────────────────────────┐
               │ Opportunity Inbox API (/api/opportunity-inbox)              │
               │ Pre-sorted descending by Expected Net Recovery ($EV_net$)    │
               │ Enterprise Client Names & Real Financial Ledger               │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                                4. CLOSED-LOOP REASONING LAYER
               ┌──────────────────────────────────────────────────────────────┐
               │ AIRouter (Clear vs Ambiguous Case Classifier)               │
               │ Groq Primary (llama-3.3-70b) / Gemini Secondary (gemini-pro)  │
               │ Prompt-Injection Defense: Customer Input = UNTRUSTED DATA    │
               │ Deterministic Fallback on Timeout or Confidence < 0.50       │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                                5. EXPECTED VALUE (EV) OPTIMIZER
               ┌──────────────────────────────────────────────────────────────┐
               │ Formula: EV_net = Gross * P_recovery - Cost - Friction       │
               │ Action vs Wait vs No-Action Financial Comparison              │
               └──────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                                6. SERVER-SIDE POLICY GATE
               ┌──────────────────────────────────────────────────────────────┐
               │ Deterministic Safety Engine (InterventionPolicy)             │
               │ Hard Safety Rules: Fraud Shield / Opt-out / Retry Limit       │
               │ Contact Fatigue Limit: Max 2 contacts per 24h window          │
               └──────────────────────────────┬───────────────────────────────┘
                                       ↙             ↘
                                [ALLOW]               [BLOCK / STOP]
                                   │                         │
                                   ▼                         ▼
                        7. BOUNDED EXECUTORS           0 API Calls Made
               ┌──────────────────────────────┐     Capital Protected (₹18.2k)
               │ Razorpay Test Mode Executor  │              │
               │ Simulated Multi-Channel      │              │
               └──────────────┬───────────────┘              │
                              │                              │
                              ▼                              │
                        8. OBSERVE OUTCOME                   │
               ┌──────────────────────────────┐              │
               │ Webhook Settlement Verification│             │
               │ Case State Machine Update    │              │
               │ Closed-Loop Dynamic Re-Plan  │              │
               └──────────────┬───────────────┘              │
                              │                              │
                              └───────────────┬──────────────┘
                                              ▼
                                 9. IMMUTABLE AUDIT LEDGER
               ┌──────────────────────────────────────────────────────────────┐
               │ AuditTrailService & AttemptLedger Repository                 │
               │ Persisted Settlement Evidence & Causal Attribution           │
               └──────────────────────────────────────────────────────────────┘
```

---

## Component Classification Matrix

| Component | Architecture Type | Execution Authority | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **OpportunityDetector** | **Event-Driven Engine** | Mandatory (Detection) | Ingest events, classify cause, score EV & check eligibility |
| **RecoveryFinancialsService**| **Financial Ledger** | Single Source of Truth | Calculate portfolio risk, recovered, actionable & Net EV |
| **AIRouter / Groq / Gemini** | **AI Reasoning** | Advisory (Candidate Proposals) | Cause diagnosis & candidate ranking |
| **ExpectedValueScorer** | **Deterministic** | Advisory (EV Ranking) | Calculate net expected value ($EV_{\text{net}}$) |
| **InterventionPolicy** | **Deterministic Safety** | Mandatory (Server-Side) | Enforce fraud, opt-out, and budget rules |
| **ActionRegistry** | **Deterministic Schema** | Mandatory (Validation) | Allowlist model output action strings |
| **RecoveryOrchestrator** | **State Machine** | Mandatory (Lifecycle) | Manage iterative step transitions & re-planning |
| **SettlementVerifier** | **Verification** | Mandatory (Settlement) | Verify HMAC settlement and update financial ledger |
| **Razorpay / Simulated Executor** | **External / Provider** | Bounded Execution | Execute API payment retries / payment links |
| **ProviderEventRepository** | **Persistence** | Mandatory (Idempotency) | Deduplicate incoming telemetry webhooks |
| **AttemptLedger & AuditLog** | **Persistence** | Mandatory (Audit) | Store immutable step evidence & outcomes |
