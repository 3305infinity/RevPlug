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
    label: "Scenario 1: Successful Recovery (Soft Timeout)",
    sourceType: "payment_failure",
    reasonIndex: 0, // payment_timed_out
    amount: 2500000,
    customerId: "cust_soft_timeout",
    badge: "HAPPY PATH",
    badgeType: "success",
  },
  {
    id: "preset_2",
    label: "Scenario 2: Smart Stop (Hard Decline / Fraud)",
    sourceType: "payment_failure",
    reasonIndex: 3, // payment_risk_check_failed
    amount: 1500000,
    customerId: "cust_fraud_risk",
    badge: "SMART STOP",
    badgeType: "danger",
  },
  {
    id: "preset_3",
    label: "Scenario 3: Customer Opt-Out Protection",
    sourceType: "subscription_failure",
    reasonIndex: 1, // gateway_technical_error
    amount: 500000,
    customerId: "cust_opted_out",
    badge: "CONSENT BLOCK",
    badgeType: "warning",
  },
  {
    id: "preset_4",
    label: "Scenario 4: AI Failure & Safe Fallback",
    sourceType: "mandate_failure",
    reasonIndex: 5, // unknown_reason
    amount: 1200000,
    customerId: "cust_ai_fallback",
    badge: "FALLBACK",
    badgeType: "accent",
  },
  {
    id: "preset_5",
    label: "Scenario 5: Provider Timeout & Reconciliation",
    sourceType: "overdue_receivable",
    reasonIndex: 0, // payment_timed_out
    amount: 4500000,
    customerId: "cust_reconcile",
    badge: "IDEMPOTENT",
    badgeType: "purple",
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

  const outcomeColor = result?.recovery_status === "recovered" ? "var(--success)" : result?.recovery_status === "stopped" ? "var(--text-muted)" : result?.recovery_status === "escalated" ? "var(--danger)" : "var(--warning)";
  const outcomeLabel = result?.recovery_status === "recovered" ? "RECOVERED" : result?.recovery_status === "stopped" ? "STOPPED" : result?.recovery_status === "escalated" ? "ESCALATED" : result?.recovery_status?.toUpperCase() || "COMPLETE";

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>
          Interactive Recovery Demo & Control Plane
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: 750 }}>
          Watch RecoverOS evaluate revenue risk, consult AI diagnosis, enforce non-bypassable policy rules, execute bounded recovery actions, and verify settlement.
        </p>
      </div>

      {/* Canonical Judge Demo Presets */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", background: "rgba(99, 102, 241, 0.03)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
          ⚡ 5 Canonical Judge Demo Presets
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {CANONICAL_PRESETS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => applyPreset(preset)}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "0.375rem 0.75rem", display: "flex", alignItems: "center", gap: "0.375rem" }}
            >
              <span className={`badge badge-${preset.badgeType}`} style={{ fontSize: "0.625rem", padding: "0.125rem 0.35rem" }}>
                {preset.badge}
              </span>
              <span>{preset.label}</span>
            </button>
          ))}
        </div>
      </div>

      {phase === "idle" && (
        <div className="card" style={{ padding: "2rem", marginBottom: "1.5rem" }}>
          {/* Recovery Surface Type Selector */}
          <div style={{ marginBottom: "1.75rem" }}>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              1. Opportunity Type / Surface
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.75rem" }}>
              {RECOVERY_TYPES.map((t) => (
                <div
                  key={t.value}
                  onClick={() => setSourceType(t.value)}
                  style={{
                    padding: "0.875rem 1rem",
                    borderRadius: 6,
                    border: `1px solid ${sourceType === t.value ? "var(--accent)" : "var(--border)"}`,
                    background: sourceType === t.value ? "rgba(99, 102, 241, 0.08)" : "transparent",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "0.875rem", fontWeight: 600, color: sourceType === t.value ? "var(--accent)" : "var(--text-primary)" }}>{t.label}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>{t.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Failure Cause Selector */}
          <div style={{ marginBottom: "1.75rem" }}>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              2. Simulated Failure Cause
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem" }}>
              {FAILURE_REASONS.map((r, idx) => (
                <div
                  key={r.value}
                  onClick={() => setReasonKey(idx)}
                  style={{
                    padding: "0.75rem 0.875rem",
                    borderRadius: 6,
                    border: `1px solid ${reasonKey === idx ? "var(--accent)" : "var(--border)"}`,
                    background: reasonKey === idx ? "rgba(99, 102, 241, 0.08)" : "transparent",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: reasonKey === idx ? "var(--accent)" : "var(--text-primary)" }}>{r.label}</div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>{r.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Customer & Amount */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
            <div>
              <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.35rem" }}>
                Amount at Risk (INR)
              </label>
              <input
                type="number"
                value={amount / 100}
                onChange={(e) => setAmount(Math.max(1, Number(e.target.value)) * 100)}
                className="input"
                style={{ width: "100%" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.35rem" }}>
                Customer ID
              </label>
              <input
                type="text"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="input"
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <button onClick={handleRun} className="btn-primary" style={{ width: "100%", padding: "0.875rem", fontSize: "0.9375rem" }}>
            ⚡ Run Recovery Scenario
          </button>
        </div>
      )}

      {/* Running Spinner */}
      {phase === "running" && (
        <div className="card" style={{ padding: "4rem 2rem", textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>⚡</div>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.5rem" }}>Evaluating Scenario...</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            Assembling context $\to$ Consulting AI Diagnosis $\to$ Checking Deterministic Policy $\to$ Verifying Settlement
          </p>
        </div>
      )}

      {/* Result Display — Signature AI Proposed -> Policy Decided Flow */}
      {phase === "complete" && result && (
        <div>
          {/* Header Outcome Banner */}
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", borderLeft: `4px solid ${outcomeColor}`, background: "var(--bg-card)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span className="badge" style={{ background: outcomeColor, color: "#fff", fontWeight: 700, marginBottom: "0.5rem" }}>
                  {outcomeLabel}
                </span>
                <h2 style={{ fontSize: "1.5rem", fontWeight: 800, marginTop: 4 }}>
                  Case {result.item_id || result.recovery_item_id || "DEMO"}
                </h2>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 2 }}>
                  Customer: {result.customer_id || customerId} • Value at risk: {fmt(result.amount_minor || amount)}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Verified Settlement</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 800, color: outcomeColor }}>
                  {result.recovery_status === "recovered" ? fmt(result.actual_recovery_value || result.amount_minor || amount) : "₹0 (Unsettled)"}
                </div>
              </div>
            </div>
          </div>

          {/* AI Proposed -> Policy Decided Visual Sequence */}
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1.25rem", color: "var(--text-primary)" }}>
              🤖 AI Proposed → 🛡️ Policy Decided Execution Flow
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "1rem" }}>
              {/* Step 1: AI Proposal */}
              <div style={{ padding: "1rem", background: "rgba(99, 102, 241, 0.06)", borderRadius: 6, border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--accent)", fontWeight: 700, textTransform: "uppercase" }}>1. AI Diagnosis</div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 4, textTransform: "capitalize" }}>
                  {result.proposed_action ? result.proposed_action.replace(/_/g, " ") : "Rule Fallback"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Confidence: {((result.confidence || 0.85) * 100).toFixed(0)}%
                </div>
              </div>

              {/* Step 2: Policy Check */}
              <div style={{ padding: "1rem", background: "rgba(16, 185, 129, 0.06)", borderRadius: 6, border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--success)", fontWeight: 700, textTransform: "uppercase" }}>2. Policy Check</div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--success)", marginTop: 4 }}>
                  {result.policy_allowed ? "✓ ALLOWED" : "🛑 BLOCKED"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Rule: {result.policy_rule || "stopping_rules_pass"}
                </div>
              </div>

              {/* Step 3: Execution */}
              <div style={{ padding: "1rem", background: "rgba(245, 158, 11, 0.06)", borderRadius: 6, border: "1px solid rgba(245, 158, 11, 0.2)" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--warning)", fontWeight: 700, textTransform: "uppercase" }}>3. Action Executed</div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 4, textTransform: "capitalize" }}>
                  {result.action_executed ? result.action_executed.replace(/_/g, " ") : "None (Stopped)"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Attempts: {result.attempt_count || 1} / 3
                </div>
              </div>

              {/* Step 4: Settlement */}
              <div style={{ padding: "1rem", background: "rgba(59, 130, 246, 0.06)", borderRadius: 6, border: "1px solid rgba(59, 130, 246, 0.2)" }}>
                <div style={{ fontSize: "0.6875rem", color: "#60a5fa", fontWeight: 700, textTransform: "uppercase" }}>4. Verified Settlement</div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#60a5fa", marginTop: 4 }}>
                  {result.recovery_status === "recovered" ? "✓ VERIFIED" : "🛑 UNSETTLED"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Evidence: {result.settlement_verified ? "Razorpay Webhook" : "None"}
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: "1rem", marginTop: "1.5rem" }}>
            <button onClick={reset} className="btn-primary" style={{ fontSize: "0.8125rem" }}>
              ← Try Another Scenario
            </button>

            <Link href={`/recovery/${result.item_id || result.recovery_item_id || "demo"}`} className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
              Inspect Case Decision Trace →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
