export interface ScenarioStage {
  step: string;
  label: string;
  summary: string;
  details: {
    title: string;
    description: string;
    telemetry?: Record<string, string | number | boolean>;
    verdict?: string;
    isBlocked?: boolean;
  };
}

export interface RecoveryScenario {
  id: string;
  name: string;
  badge: string;
  badgeType: "success" | "danger" | "warning" | "info";
  description: string;
  amountAtRisk: number;
  rootCause: string;
  aiProvider: string;
  confidence: number;
  policyVerdict: "ALLOW" | "BLOCK";
  policyRule: string;
  actionExecuted: string;
  settlementVerified: boolean;
  actualRecovery: number;
  stoppingReason?: string;
  stages: ScenarioStage[];
  aiProposal: {
    provider: string;
    model: string;
    confidence: number;
    likelyCause: string;
    candidateAction: string;
    rationale: string;
  };
  policyDecision: {
    rule: string;
    eligibility: string;
    fraudCheck: string;
    retryBudget: string;
    contactLimit: string;
    verdict: "ALLOW" | "BLOCK";
    reason: string;
  };
  events: Array<{ time: string; event: string; status: string }>;
}

export const SCENARIOS: RecoveryScenario[] = [
  {
    id: "successful_recovery",
    name: "SUCCESSFUL RECOVERY",
    badge: "VERIFIED",
    badgeType: "success",
    description: "Soft gateway timeout → AI payment link proposal → Policy ALLOWED → Settlement Verified",
    amountAtRisk: 499900,
    rootCause: "payment_timed_out",
    aiProvider: "Groq (llama-3.3-70b)",
    confidence: 0.91,
    policyVerdict: "ALLOW",
    policyRule: "stopping_rules_pass",
    actionExecuted: "send_payment_link",
    settlementVerified: true,
    actualRecovery: 499900,
    aiProposal: {
      provider: "Groq",
      model: "llama-3.3-70b-versatile",
      confidence: 0.91,
      likelyCause: "Temporary gateway timeout during bank 3DS handshake",
      candidateAction: "send_payment_link",
      rationale: "Bypass card decline loop by issuing hosted payment link over SMS/Email.",
    },
    policyDecision: {
      rule: "stopping_rules_pass",
      eligibility: "PASS",
      fraudCheck: "CLEAR",
      retryBudget: "1 / 3 AVAILABLE",
      contactLimit: "1 / 2 AVAILABLE",
      verdict: "ALLOW",
      reason: "Action complies with consent policy, fraud checks, EV bounds, and retry budgets.",
    },
    events: [
      { time: "08:42:13", event: "payment.failed", status: "payment_timed_out" },
      { time: "08:42:14", event: "diagnosis.completed", status: "cause: gateway_timeout" },
      { time: "08:42:14", event: "policy.allowed", status: "rule: stopping_rules_pass" },
      { time: "08:42:15", event: "recovery.action.executed", status: "action: send_payment_link" },
      { time: "08:43:02", event: "settlement.verified", status: "amount: ₹4,999" },
    ],
    stages: [
      {
        step: "01",
        label: "PAYMENT SIGNAL",
        summary: "Payment failed (₹4,999)",
        details: {
          title: "Payment Failure Telemetry Received",
          description: "Gateway webhook payment.failed ingested for order_demo_9021.",
          telemetry: { Event: "payment.failed", Error: "payment_timed_out", Amount: "₹4,999", Customer: "cust_soft_timeout" },
        },
      },
      {
        step: "02",
        label: "AI DIAGNOSIS",
        summary: "Temporary gateway timeout",
        details: {
          title: "Groq LLM Failure Diagnosis",
          description: "Diagnosed failure as temporary 3DS handshake timeout. High probability of recovery via hosted link.",
          telemetry: { Provider: "Groq (llama-3.3-70b)", Confidence: "91%", CandidateAction: "send_payment_link" },
        },
      },
      {
        step: "03",
        label: "POLICY GATE",
        summary: "ALLOW (budget 1/3)",
        details: {
          title: "Deterministic Server-Side Policy Evaluation",
          description: "Fail-closed policy engine verified 0 fraud flags, active customer consent, and positive Net Expected Value.",
          verdict: "ALLOW",
          telemetry: { Rule: "stopping_rules_pass", FraudCheck: "CLEAR", RetryBudget: "1/3", Consent: "OK" },
        },
      },
      {
        step: "04",
        label: "BOUNDED ACTION",
        summary: "Payment link created",
        details: {
          title: "Bounded Intervention Execution",
          description: "Dispatched Razorpay Test Mode Payment Link API (plink_demo_9021).",
          telemetry: { Action: "send_payment_link", Provider: "Razorpay Test Mode", Status: "dispatched" },
        },
      },
      {
        step: "05",
        label: "SETTLEMENT",
        summary: "Verified (₹4,999)",
        details: {
          title: "Authoritative Webhook Settlement Verification",
          description: "Received payment.authorized webhook from gateway. Credited ₹4,999 to verified recovery ledger.",
          telemetry: { Settlement: "VERIFIED", LedgerCredit: "₹4,999", WebhookID: "rzp_pay_9021482" },
        },
      },
    ],
  },

  {
    id: "smart_stop",
    name: "SMART STOP",
    badge: "BLOCKED",
    badgeType: "danger",
    description: "Fraud risk signal detected → Policy halts automated retries → STOPPED (₹0 wasted)",
    amountAtRisk: 1820000,
    rootCause: "payment_risk_check_failed",
    aiProvider: "Groq (llama-3.3-70b)",
    confidence: 0.72,
    policyVerdict: "BLOCK",
    policyRule: "fraud_detected_block",
    actionExecuted: "none_stopped",
    settlementVerified: false,
    actualRecovery: 0,
    stoppingReason: "fraud_detected",
    aiProposal: {
      provider: "Groq",
      model: "llama-3.3-70b-versatile",
      confidence: 0.72,
      likelyCause: "Risk engine velocity check failure on high value transaction",
      candidateAction: "retry_payment",
      rationale: "Attempt standard retry with velocity delay.",
    },
    policyDecision: {
      rule: "fraud_detected_block",
      eligibility: "DENIED",
      fraudCheck: "FRAUD SIGNAL DETECTED",
      retryBudget: "0 / 3 HALTED",
      contactLimit: "0 CONTACTS MADE",
      verdict: "BLOCK",
      reason: "Policy Engine blocked recovery action to prevent merchant penalties and protect fraud compliance.",
    },
    events: [
      { time: "09:15:02", event: "payment.failed", status: "payment_risk_check_failed" },
      { time: "09:15:03", event: "diagnosis.completed", status: "cause: risk_check_failed" },
      { time: "09:15:03", event: "policy.blocked", status: "rule: fraud_detected_block" },
      { time: "09:15:04", event: "recovery.action.stopped", status: "reason: fraud_detected" },
      { time: "09:15:04", event: "settlement.unsettled", status: "amount: ₹0 credited" },
    ],
    stages: [
      {
        step: "01",
        label: "PAYMENT SIGNAL",
        summary: "Risk failure (₹18,200)",
        details: {
          title: "High Risk Payment Failure Ingested",
          description: "Gateway risk check failed for order_fraud_8819.",
          telemetry: { Event: "payment.failed", Error: "payment_risk_check_failed", Amount: "₹18,200" },
        },
      },
      {
        step: "02",
        label: "AI DIAGNOSIS",
        summary: "Risk check failure",
        details: {
          title: "AI Analysis & Proposal",
          description: "AI proposed retry payment after velocity buffer.",
          telemetry: { CandidateAction: "retry_payment", Confidence: "72%" },
        },
      },
      {
        step: "03",
        label: "POLICY GATE",
        summary: "BLOCK (Fraud rule)",
        details: {
          title: "Policy Engine Hard Block",
          description: "Server-side non-bypassable policy rule triggered: FRAUD_SIGNAL_DETECTED. Action denied.",
          isBlocked: true,
          verdict: "BLOCK",
          telemetry: { Rule: "fraud_detected_block", FraudCheck: "FLAGGED", ActionAllowed: "FALSE" },
        },
      },
      {
        step: "04",
        label: "BOUNDED ACTION",
        summary: "STOPPED (0 retries)",
        details: {
          title: "Recovery Halted",
          description: "No customer contact made. Zero execution dispatched.",
          isBlocked: true,
          telemetry: { Dispatched: "NONE", ContactsMade: "0", RetryAttempts: "0" },
        },
      },
      {
        step: "05",
        label: "SETTLEMENT",
        summary: "₹0 (Zero wasted)",
        details: {
          title: "Zero Revenue Recorded",
          description: "RevPlug chose NOT to recover this money to protect merchant reputation.",
          isBlocked: true,
          telemetry: { VerifiedRecovery: "₹0", CustomerPenalties: "₹0", PolicyViolations: "0" },
        },
      },
    ],
  },

  {
    id: "ai_fallback",
    name: "AI FALLBACK",
    badge: "FALLBACK",
    badgeType: "warning",
    description: "Groq API timeout → Deterministic fallback agent takes over → Safe policy recovery",
    amountAtRisk: 1200000,
    rootCause: "mandate_technical_failure",
    aiProvider: "Deterministic Fallback Agent",
    confidence: 1.0,
    policyVerdict: "ALLOW",
    policyRule: "fallback_rule_pass",
    actionExecuted: "issue_mandate_update",
    settlementVerified: true,
    actualRecovery: 1200000,
    aiProposal: {
      provider: "DeterministicFallbackAgent",
      model: "deterministic_rules_v3",
      confidence: 1.0,
      likelyCause: "AI Provider API timeout — fallback engaged automatically",
      candidateAction: "issue_mandate_update",
      rationale: "Groq provider unreachable; rule-based engine selects deterministic mandate update.",
    },
    policyDecision: {
      rule: "fallback_rule_pass",
      eligibility: "PASS",
      fraudCheck: "CLEAR",
      retryBudget: "1 / 3 AVAILABLE",
      contactLimit: "1 / 2 AVAILABLE",
      verdict: "ALLOW",
      reason: "Deterministic fallback rule passed policy checks seamlessly.",
    },
    events: [
      { time: "10:04:11", event: "payment.failed", status: "mandate_technical_failure" },
      { time: "10:04:12", event: "ai_provider.timeout", status: "groq_unreachable" },
      { time: "10:04:12", event: "fallback.engaged", status: "agent: DeterministicFallbackAgent" },
      { time: "10:04:13", event: "policy.allowed", status: "rule: fallback_rule_pass" },
      { time: "10:05:40", event: "settlement.verified", status: "amount: ₹12,000" },
    ],
    stages: [
      {
        step: "01",
        label: "PAYMENT SIGNAL",
        summary: "Mandate fail (₹12,000)",
        details: {
          title: "Subscription Mandate Failure Ingested",
          description: "Mandate recurring debit failed for order_sub_4102.",
          telemetry: { Event: "mandate.failed", Error: "mandate_technical_failure", Amount: "₹12,000" },
        },
      },
      {
        step: "02",
        label: "AI DIAGNOSIS",
        summary: "AI Outage → Fallback",
        details: {
          title: "Groq Provider Outage & Safe Fallback",
          description: "Primary LLM provider timed out after 1500ms. RevPlug automatically switched to Deterministic Fallback Agent.",
          telemetry: { Provider: "Deterministic Fallback", Reason: "groq_timeout", CandidateAction: "issue_mandate_update" },
        },
      },
      {
        step: "03",
        label: "POLICY GATE",
        summary: "ALLOW (Rule pass)",
        details: {
          title: "Fallback Policy Verification",
          description: "Fallback proposal passed all server-side policy guards.",
          verdict: "ALLOW",
          telemetry: { Rule: "fallback_rule_pass", FallbackActive: "TRUE" },
        },
      },
      {
        step: "04",
        label: "BOUNDED ACTION",
        summary: "Mandate link update",
        details: {
          title: "Mandate Update Dispatched",
          description: "Dispatched e-mandate re-authentication link.",
          telemetry: { Action: "issue_mandate_update", Dispatched: "TRUE" },
        },
      },
      {
        step: "05",
        label: "SETTLEMENT",
        summary: "Verified (₹12,000)",
        details: {
          title: "Gateway Settlement Verified",
          description: "Mandate debit processed. Credited ₹12,000 to ledger.",
          telemetry: { VerifiedRecovery: "₹12,000", Status: "VERIFIED" },
        },
      },
    ],
  },

  {
    id: "provider_timeout",
    name: "PROVIDER TIMEOUT",
    badge: "RECONCILE",
    badgeType: "info",
    description: "Gateway HTTP timeout → UNKNOWN state → Reconciles without duplicate retry",
    amountAtRisk: 4500000,
    rootCause: "gateway_http_timeout",
    aiProvider: "Groq (llama-3.3-70b)",
    confidence: 0.85,
    policyVerdict: "ALLOW",
    policyRule: "idempotency_lock_pass",
    actionExecuted: "reconcile_status",
    settlementVerified: false,
    actualRecovery: 0,
    aiProposal: {
      provider: "Groq",
      model: "llama-3.3-70b-versatile",
      confidence: 0.85,
      likelyCause: "Gateway HTTP timeout — status uncertain",
      candidateAction: "reconcile_status",
      rationale: "Do not retry payment to prevent double charge; dispatch status reconciliation polling.",
    },
    policyDecision: {
      rule: "idempotency_lock_pass",
      eligibility: "PASS",
      fraudCheck: "CLEAR",
      retryBudget: "LOCKED",
      contactLimit: "0 CONTACTS",
      verdict: "ALLOW",
      reason: "Idempotency key locked to prevent double charging customer during network partition.",
    },
    events: [
      { time: "11:20:00", event: "payment.unknown", status: "gateway_http_timeout" },
      { time: "11:20:01", event: "idempotency.locked", status: "key: idemp_90218" },
      { time: "11:20:01", event: "policy.allowed", status: "rule: idempotency_lock_pass" },
      { time: "11:20:02", event: "recovery.action.reconcile", status: "action: status_poll" },
      { time: "11:25:00", event: "settlement.pending", status: "awaiting_reconciliation" },
    ],
    stages: [
      {
        step: "01",
        label: "PAYMENT SIGNAL",
        summary: "Timeout (₹45,000)",
        details: {
          title: "Network Partition / Gateway HTTP Timeout",
          description: "Payment status uncertain after gateway HTTP socket timeout for order_invoice_9912.",
          telemetry: { Event: "gateway.timeout", Error: "http_504", Amount: "₹45,000" },
        },
      },
      {
        step: "02",
        label: "AI DIAGNOSIS",
        summary: "Status unconfirmed",
        details: {
          title: "AI Analysis: Reconcile First",
          description: "AI recommends status reconciliation over blind card retry to avoid double charge.",
          telemetry: { CandidateAction: "reconcile_status", DoubleChargeRisk: "PREVENTED" },
        },
      },
      {
        step: "03",
        label: "POLICY GATE",
        summary: "ALLOW (Idempotent)",
        details: {
          title: "Idempotency Lock Engaged",
          description: "Policy engine locks retry budget until gateway status is reconciled.",
          verdict: "ALLOW",
          telemetry: { Rule: "idempotency_lock_pass", KeyLocked: "TRUE" },
        },
      },
      {
        step: "04",
        label: "BOUNDED ACTION",
        summary: "Reconciliation poll",
        details: {
          title: "Status Reconciliation Polling Dispatched",
          description: "Initiated bank reconciliation API query.",
          telemetry: { Action: "status_poll", DuplicateAttemptPrevented: "TRUE" },
        },
      },
      {
        step: "05",
        label: "SETTLEMENT",
        summary: "Pending verification",
        details: {
          title: "Awaiting Gateway Reconciliation Evidence",
          description: "Holding in pending_verification ledger state.",
          telemetry: { Status: "PENDING_RECONCILIATION", Credit: "₹0 (Unconfirmed)" },
        },
      },
    ],
  },
];
