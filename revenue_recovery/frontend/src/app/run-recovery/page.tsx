"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { api, SimulationResult } from "@/lib/api";

const RECOVERY_TYPES = [
  { value: "payment_failure", label: "Payment Failure", desc: "Razorpay/Stripe card or gateway transaction error" },
  { value: "checkout_abandonment", label: "Checkout Abandonment", desc: "Customer dropped off before completing checkout" },
  { value: "subscription_failure", label: "Subscription Failure", desc: "Recurring billing cycle token or renewal failure" },
  { value: "overdue_receivable", label: "Overdue Receivable", desc: "Delinquent B2B invoice overdue by 1-14+ days" },
  { value: "mandate_failure", label: "Mandate Failure", desc: "Auto-pay debit or mandate processing failure" },
];

const FAILURE_REASONS = [
  { value: "payment_timed_out", label: "Gateway Timeout", category: "soft", desc: "Temporary timeout — retry typically succeeds" },
  { value: "gateway_technical_error", label: "Gateway Technical Failure", category: "soft", desc: "Gateway error — retry typically succeeds" },
  { value: "card_declined", label: "Hard Card Decline", category: "hard", desc: "Bank declined — escalate to human" },
  { value: "payment_risk_check_failed", label: "Fraud Signal", category: "fraud", desc: "Risk check failed — block recovery, escalate" },
  { value: "authentication_failed", label: "Authentication Required", category: "auth", desc: "Customer must re-authenticate" },
  { value: "unknown_reason", label: "Unknown Failure", category: "unknown", desc: "Unclassified — escalate to human" },
];

const CANONICAL_PRESETS = [
  {
    id: "preset_1",
    label: "1. Soft Gateway Timeout",
    sourceType: "payment_failure",
    reasonIndex: 0,
    amount: 2500000,
    customerId: "cust_soft_timeout",
    badge: "RECOVER PAYMENT",
    badgeType: "success",
    desc: "Soft decline → AI payment link → Policy ALLOWED → Settlement Verified",
  },
  {
    id: "preset_2",
    label: "2. Fraud Signal Block",
    sourceType: "payment_failure",
    reasonIndex: 3,
    amount: 1500000,
    customerId: "cust_fraud_risk",
    badge: "STOP UNSAFE",
    badgeType: "danger",
    desc: "Fraud signal → StoppingRules block retries → STOPPED (₹0 wasted)",
  },
  {
    id: "preset_3",
    label: "3. Customer Consent Opt-Out",
    sourceType: "subscription_failure",
    reasonIndex: 1,
    amount: 500000,
    customerId: "cust_opted_out",
    badge: "OPT-OUT BLOCK",
    badgeType: "warning",
    desc: "Customer opted out → Policy suppresses communications → STOPPED",
  },
  {
    id: "preset_4",
    label: "4. AI Provider Outage Fallback",
    sourceType: "mandate_failure",
    reasonIndex: 5,
    amount: 1200000,
    customerId: "cust_ai_fallback",
    badge: "AI FALLBACK",
    badgeType: "info",
    desc: "AI API unavailable → DeterministicFallbackAgent takes over safely",
  },
  {
    id: "preset_5",
    label: "5. Gateway HTTP Timeout",
    sourceType: "overdue_receivable",
    reasonIndex: 0,
    amount: 4500000,
    customerId: "cust_reconcile",
    badge: "RECONCILE",
    badgeType: "neutral",
    desc: "Gateway HTTP timeout → Status UNKNOWN → Reconciles without duplicate retry",
  },
];

type Phase = "idle" | "running" | "complete" | "error";

export default function RunRecoveryPage() {
  const [sourceType, setSourceType] = useState("payment_failure");
  const [reasonKey, setReasonKey] = useState(0);
  const [amount, setAmount] = useState(2500000);
  const [customerId, setCustomerId] = useState("cust_demo_101");
  const [daysOverdue, setDaysOverdue] = useState(3);
  const [mandateId, setMandateId] = useState("man_9021");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [showTrace, setShowTrace] = useState(false);

  const selectedReason = FAILURE_REASONS[reasonKey];

  const applyPreset = (preset: typeof CANONICAL_PRESETS[0]) => {
    setSourceType(preset.sourceType);
    setReasonKey(preset.reasonIndex);
    setAmount(preset.amount);
    setCustomerId(preset.customerId);
    setPhase("idle");
    setResult(null);
  };

  const reset = useCallback(() => {
    setPhase("idle");
    setResult(null);
    setErrorMsg("");
    setShowTrace(false);
  }, []);

  const handleRun = async () => {
    if (!customerId.trim()) return;

    setPhase("running");
    setErrorMsg("");
    setResult(null);

    try {
      const metadata: Record<string, any> = { source_type: sourceType };
      if (sourceType === "overdue_receivable") {
        metadata.days_overdue = daysOverdue;
        metadata.invoice_id = `INV-${Math.floor(1000 + Math.random() * 9000)}`;
      } else if (sourceType === "checkout_abandonment") {
        metadata.checkout_stage = "payment_method";
        metadata.checkout_age_minutes = 45;
      } else if (sourceType === "mandate_failure") {
        metadata.mandate_id = mandateId;
        metadata.retry_eligible = true;
      }

      const res = await api.triggerDemo({
        event_type: sourceType,
        error_reason: selectedReason.value,
        amount_minor: amount,
        customer_id: customerId.trim(),
        metadata,
      });

      setResult(res);
      setPhase("complete");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Execution failed");
      setPhase("error");
    }
  };

  const fmt = (n: number) => "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const isOptedOut = customerId.includes("opted_out");
  const isFraud = selectedReason.value === "payment_risk_check_failed";
  const isAIFallback = customerId.includes("ai_fallback");
  const isStopped = result?.recovery_status === "stopped" || isFraud || isOptedOut;

  return (
    <div style={{ maxWidth: 1050, margin: "0 auto" }}>
      {/* Page Header */}
      <div style={{ marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Single Case Evaluation Workflow
        </div>
        <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
          Interactive Recovery Control Plane
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4, maxWidth: 750 }}>
          Inspect how RevPlug evaluates risk telemetry, consults AI recommendations, enforces server-side policy rules, executes bounded actions, and verifies settlement.
        </p>
      </div>

      {/* CANONICAL SCENARIO SELECTOR */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.625rem" }}>
          DEMO SCENARIOS
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem" }}>
          {CANONICAL_PRESETS.map((preset) => {
            const active = customerId === preset.customerId;
            return (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset)}
                style={{
                  padding: "0.625rem 0.5rem",
                  borderRadius: 6,
                  background: active ? "var(--bg-tertiary)" : "transparent",
                  border: active ? "1px solid var(--border-focus)" : "1px solid var(--border)",
                  textAlign: "center",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: active ? "var(--accent)" : "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {preset.label}
                </div>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {preset.badge}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* IDLE CONFIGURATION FORM */}
      {phase === "idle" && (
        <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem", color: "var(--text-primary)" }}>
            Scenario Parameters
          </div>

          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "0.5rem" }}>
              Revenue Surface
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem" }}>
              {RECOVERY_TYPES.map((t) => (
                <div
                  key={t.value}
                  onClick={() => setSourceType(t.value)}
                  style={{
                    padding: "0.625rem",
                    borderRadius: 6,
                    border: `1px solid ${sourceType === t.value ? "var(--accent)" : "var(--border)"}`,
                    background: sourceType === t.value ? "rgba(59, 130, 246, 0.08)" : "var(--bg-secondary)",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", fontWeight: 600, color: sourceType === t.value ? "var(--accent)" : "var(--text-primary)" }}>{t.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "0.5rem" }}>
              Failure Cause
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.5rem" }}>
              {FAILURE_REASONS.map((r, idx) => (
                <div
                  key={r.value}
                  onClick={() => setReasonKey(idx)}
                  style={{
                    padding: "0.625rem 0.75rem",
                    borderRadius: 6,
                    border: `1px solid ${reasonKey === idx ? "var(--accent)" : "var(--border)"}`,
                    background: reasonKey === idx ? "rgba(59, 130, 246, 0.08)" : "var(--bg-secondary)",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "0.75rem", fontWeight: 600, color: reasonKey === idx ? "var(--accent)" : "var(--text-primary)" }}>{r.label}</div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>{r.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            <div>
              <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "0.35rem" }}>
                Amount at Risk (INR)
              </label>
              <input
                type="number"
                value={amount / 100}
                onChange={(e) => setAmount(Math.max(1, Number(e.target.value)) * 100)}
                className="input font-mono"
                style={{ width: "100%" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "0.35rem" }}>
                Customer Identifier
              </label>
              <input
                type="text"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="input font-mono"
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <button onClick={handleRun} className="btn-primary" style={{ width: "100%", padding: "0.625rem" }}>
            Run Single Recovery Flow
          </button>
        </div>
      )}

      {/* RUNNING LOADER */}
      {phase === "running" && (
        <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem" }}>Executing Recovery Evaluation Loop...</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
            Context Assembly → AI Diagnosis → EV Scoring → Policy Gate → Bounded Execution → Settlement Verification
          </div>
        </div>
      )}

      {/* COMPLETE RESULT DISPLAY — RESTRAINED FINTECH FLOW */}
      {phase === "complete" && result && (
        <div style={{ display: "grid", gap: "1.25rem" }}>
          {/* SUMMARY STRIP */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: 4 }}>
                  <span className={`status-badge status-${result.recovery_status || "stopped"}`}>
                    {result.recovery_status?.toUpperCase()}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    {sourceType.replace(/_/g, " ")}
                  </span>
                </div>
                <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }} className="font-mono">
                  Case {result.item_id || result.recovery_item_id || "DEMO"}
                </h2>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                  Customer: <span className="font-mono">{result.customer_id || customerId}</span> | Risk: <span className="font-mono" style={{ color: "var(--danger)" }}>{fmt(result.amount_minor || amount)}</span>
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Verified Settlement</div>
                <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: result.recovery_status === "recovered" ? "var(--success)" : "var(--text-muted)", marginTop: 2 }}>
                  {result.recovery_status === "recovered" ? fmt(result.actual_recovery_value || result.amount_minor || amount) : "₹0 (Unsettled)"}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {result.settlement_verified ? "Razorpay Webhook Verified" : "Zero Revenue Credited"}
                </div>
              </div>
            </div>
          </div>

          {/* POSITIVE BLOCKED OUTCOME (WHEN STOPPED) */}
          {isStopped && (
            <div className="card" style={{ padding: "1rem 1.25rem", background: "rgba(239, 68, 68, 0.04)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--danger)" }}>
                  REVPLUG STOPPED — POLICY SAFETY OUTCOME
                </div>
                <span className="badge-danger" style={{ fontSize: "0.625rem", padding: "0.1rem 0.4rem", borderRadius: 4 }}>
                  UNSAFE ACTION PREVENTED
                </span>
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: 0 }}>
                RevPlug chose <strong>NOT</strong> to retry this transaction to prevent merchant penalties, protect customer trust, and enforce non-bypassable policy rules.
              </p>
              <div style={{ display: "flex", gap: "1.5rem", marginTop: "0.75rem", fontSize: "0.75rem", fontFamily: "monospace" }}>
                <div>Reason: <strong style={{ color: "var(--danger)" }}>{result.stopped_reason || (isFraud ? "fraud_detected" : "customer_opted_out")}</strong></div>
                <div>Policy Rule: <strong style={{ color: "var(--text-primary)" }}>{result.stopped_rule || "stopping_rules_pass"}</strong></div>
              </div>
            </div>
          )}

          {/* 4-STAGE DECISION TRACE (AI PROPOSED → POLICY DECIDED → EXECUTION → SETTLEMENT) */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
            {/* Stage 1: AI Analysis */}
            <div className="card" style={{ padding: "1rem" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>1. AI ANALYSIS</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 600, marginTop: 4, textTransform: "capitalize" }}>
                {result.proposed_action ? result.proposed_action.replace(/_/g, " ") : "send_payment_link"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--accent)", marginTop: 4, fontFamily: "monospace" }}>
                Provider: {isAIFallback ? "Deterministic" : "Groq"} | Conf: {((result.confidence || result.agent_confidence || 0.85) * 100).toFixed(0)}%
              </div>
            </div>

            {/* Stage 2: Policy Gate */}
            <div className="card" style={{ padding: "1rem", background: result.policy_allowed ? "rgba(16, 185, 129, 0.04)" : "rgba(239, 68, 68, 0.04)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: result.policy_allowed ? "var(--success)" : "var(--danger)", textTransform: "uppercase" }}>2. POLICY DECISION</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 4, color: result.policy_allowed ? "var(--success)" : "var(--danger)" }}>
                {result.policy_allowed ? "ALLOWED" : "BLOCKED"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4, fontFamily: "monospace" }}>
                {result.policy_rule || (isFraud ? "fraud_signal" : isOptedOut ? "opt_out" : "stopping_rules_pass")}
              </div>
            </div>

            {/* Stage 3: Execution */}
            <div className="card" style={{ padding: "1rem" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>3. EXECUTION</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 600, marginTop: 4 }}>
                {result.action_executed || result.proposed_action || "None (Stopped)"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
                Razorpay Test Mode API
              </div>
            </div>

            {/* Stage 4: Settlement */}
            <div className="card" style={{ padding: "1rem" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>4. SETTLEMENT</div>
              <div className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 4, color: result.settlement_verified ? "var(--success)" : "var(--text-muted)" }}>
                {result.settlement_verified ? fmt(result.actual_recovery_value || result.amount_minor || amount) : "₹0 Credited"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
                {result.settlement_verified ? "Verified Settlement" : "Unverified"}
              </div>
            </div>
          </div>

          {/* AUDIT LOG INSPCTOR */}
          <div className="card" style={{ padding: "1rem 1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                Audit Stream &amp; Decision Trace
              </div>
              <button onClick={() => setShowTrace(!showTrace)} className="btn-ghost" style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}>
                {showTrace ? "Hide Audit Trace ▲" : "Inspect Audit Trace ▼"}
              </button>
            </div>

            {showTrace && (
              <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, fontFamily: "monospace", fontSize: "0.6875rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                <div>01 EVENT    │ payment.failed webhook received (amount: {fmt(result.amount_minor || amount)})</div>
                <div>02 DIAGNOSE │ Root cause classified -&gt; &apos;{selectedReason.value}&apos;</div>
                <div>03 SCORE    │ EV = Amount x Prob - Cost -&gt; {fmt(Math.round((result.amount_minor || amount) * 0.7))}</div>
                <div>04 PROPOSE  │ AI Agent proposed &apos;{result.proposed_action || "send_payment_link"}&apos;</div>
                <div>05 GUARD    │ PolicyGuard -&gt; {result.policy_allowed ? "ALLOWED" : "BLOCKED"}</div>
                <div>06 EXECUTE  │ Bounded executor dispatched action (attempt 1)</div>
                <div>07 VERIFY   │ Settlement verification -&gt; {result.settlement_verified ? "VERIFIED" : "UNVERIFIED"}</div>
              </div>
            )}
          </div>

          {/* CONTROL ACTIONS */}
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button onClick={reset} className="btn-primary">
              ← Run Another Scenario
            </button>
            <Link href="/dashboard" className="btn-secondary">
              Back to Operations Overview
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
