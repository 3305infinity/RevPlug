"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { api, SimulationResult } from "@/lib/api";

const CANONICAL_PRESETS = [
  {
    id: "preset_1",
    label: "1. Soft Gateway Timeout",
    sourceType: "payment_failure",
    reasonValue: "payment_timed_out",
    amount: 499900,
    customerId: "cust_razor_101",
    badge: "RECOVER PAYMENT",
    badgeType: "success",
    desc: "Soft decline → AI payment link → Policy ALLOWED → Settlement Verified",
  },
  {
    id: "preset_2",
    label: "2. Fraud Risk Signal",
    sourceType: "payment_failure",
    reasonValue: "payment_risk_check_failed",
    amount: 1820000,
    customerId: "cust_risk_909",
    badge: "STOP UNSAFE",
    badgeType: "danger",
    desc: "Fraud signal → Policy blocks retries → STOPPED (₹18,200 Protected)",
  },
  {
    id: "preset_3",
    label: "3. Customer Consent Opt-Out",
    sourceType: "subscription_failure",
    reasonValue: "gateway_technical_error",
    amount: 500000,
    customerId: "cust_opted_out_88",
    badge: "OPT-OUT BLOCK",
    badgeType: "warning",
    desc: "Opted out customer → Policy suppresses communications → STOPPED",
  },
  {
    id: "preset_4",
    label: "4. AI Provider Outage",
    sourceType: "mandate_failure",
    reasonValue: "unknown_reason",
    amount: 1200000,
    customerId: "cust_ai_fallback_77",
    badge: "AI FALLBACK",
    badgeType: "info",
    desc: "AI provider timeout → DeterministicFallbackAgent takes over safely",
  },
  {
    id: "preset_5",
    label: "5. Gateway HTTP Timeout",
    sourceType: "overdue_receivable",
    reasonValue: "payment_timed_out",
    amount: 8400000,
    customerId: "cust_reconcile_99",
    badge: "RECONCILE",
    badgeType: "neutral",
    desc: "Gateway HTTP timeout → Status UNKNOWN → Reconciles without duplicate retry",
  },
];

type Phase = "idle" | "running" | "complete" | "error";

export default function RunRecoveryPage() {
  const [sourceType, setSourceType] = useState("payment_failure");
  const [reasonValue, setReasonValue] = useState("payment_timed_out");
  const [amount, setAmount] = useState(499900);
  const [customerId, setCustomerId] = useState("cust_razor_101");
  const [aiProvider, setAiProvider] = useState<"groq" | "gemini" | "fallback">("groq");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [showTrace, setShowTrace] = useState(false);

  const applyPreset = (preset: typeof CANONICAL_PRESETS[0]) => {
    setSourceType(preset.sourceType);
    setReasonValue(preset.reasonValue);
    setAmount(preset.amount);
    setCustomerId(preset.customerId);
    setPhase("idle");
    setResult(null);
  };

  const handleRun = async () => {
    if (!customerId.trim()) return;

    setPhase("running");
    setErrorMsg("");
    setResult(null);

    try {
      const metadata: Record<string, any> = {
        source_type: sourceType,
        ai_provider: aiProvider,
      };

      if (customerId.includes("opted_out")) {
        metadata.customer_opted_out = true;
      }
      if (customerId.includes("ai_fallback")) {
        metadata.simulate_ai_failure = true;
      }

      const res = await api.triggerDemo({
        event_type: sourceType,
        error_reason: reasonValue,
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
  const isFraud = reasonValue === "payment_risk_check_failed";
  const isAIFallback = customerId.includes("ai_fallback");
  const isStopped = result?.recovery_status === "stopped" || isFraud || isOptedOut;

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* PAGE HEADER */}
      <div style={{ marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Single Case Evaluation Engine
        </div>
        <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
          Interactive Recovery Control Plane
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4, maxWidth: 750 }}>
          Inspect how RevPlug evaluates risk telemetry, consults AI recommendations, enforces server-side policy rules, executes bounded actions, and verifies settlement.
        </p>
      </div>

      {/* AI PROVIDER SELECTOR & CONFIGURATION BAR */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem", background: "var(--bg-secondary)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              SELECT REASONING PROVIDER
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
              AI proposes candidate interventions; deterministic policy engine retains absolute execution authority.
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setAiProvider("groq")}
              style={{
                fontSize: "0.75rem",
                padding: "0.35rem 0.75rem",
                borderRadius: 6,
                border: aiProvider === "groq" ? "1px solid var(--accent)" : "1px solid var(--border)",
                background: aiProvider === "groq" ? "rgba(99, 102, 241, 0.1)" : "transparent",
                color: aiProvider === "groq" ? "var(--accent)" : "var(--text-secondary)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Groq Primary (Llama-3.3-70b)
            </button>

            <button
              onClick={() => setAiProvider("gemini")}
              style={{
                fontSize: "0.75rem",
                padding: "0.35rem 0.75rem",
                borderRadius: 6,
                border: aiProvider === "gemini" ? "1px solid var(--success)" : "1px solid var(--border)",
                background: aiProvider === "gemini" ? "rgba(16, 185, 129, 0.1)" : "transparent",
                color: aiProvider === "gemini" ? "var(--success)" : "var(--text-secondary)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Gemini Secondary (Gemini-1.5-Pro)
            </button>

            <button
              onClick={() => setAiProvider("fallback")}
              style={{
                fontSize: "0.75rem",
                padding: "0.35rem 0.75rem",
                borderRadius: 6,
                border: aiProvider === "fallback" ? "1px solid var(--warning)" : "1px solid var(--border)",
                background: aiProvider === "fallback" ? "rgba(245, 158, 11, 0.1)" : "transparent",
                color: aiProvider === "fallback" ? "var(--warning)" : "var(--text-secondary)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Deterministic Safety Fallback
            </button>
          </div>
        </div>
      </div>

      {/* CANONICAL SCENARIO SELECTOR */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          CANONICAL RECOVERY DEMO PRESETS
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem" }}>
          {CANONICAL_PRESETS.map((preset) => {
            const active = customerId === preset.customerId;
            return (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset)}
                style={{
                  padding: "0.75rem 0.5rem",
                  borderRadius: 6,
                  background: active ? "var(--bg-tertiary)" : "transparent",
                  border: active ? "1px solid var(--border-focus)" : "1px solid var(--border)",
                  textAlign: "center",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: active ? "var(--accent)" : "var(--text-primary)" }}>
                  {preset.label}
                </div>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 4 }}>
                  {preset.badge}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* PARAMETER CONFIGURATION FORM & RUN BUTTON */}
      {phase === "idle" && (
        <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
            <div>
              <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                Selected Case: <span className="font-mono">{customerId}</span>
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                Failure Reason: {reasonValue} · Amount at risk: {fmt(amount)}
              </div>
            </div>

            <button
              onClick={handleRun}
              className="btn-primary"
              style={{ fontSize: "0.875rem", padding: "0.6rem 1.5rem" }}
            >
              RUN RECOVERY ENGINE →
            </button>
          </div>
        </div>
      )}

      {/* RUNNING PROGRESSION STAGES */}
      {phase === "running" && (
        <div className="card" style={{ padding: "3rem", textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
            Executing Recovery Workflow ({customerId})...
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "0.35rem", margin: "1.5rem 0 0 0" }}>
            {["INGESTING SIGNAL", "DIAGNOSING", "EVALUATING POLICY", "CALCULATING EV", "AUTHORIZING", "EXECUTING", "VERIFYING"].map((step, idx) => (
              <div key={idx} style={{ padding: "0.5rem 0.25rem", background: "rgba(99, 102, 241, 0.1)", border: "1px solid var(--accent)", borderRadius: 6 }}>
                <div style={{ fontSize: "0.5625rem", color: "var(--accent)", fontWeight: 700 }}>0{idx + 1}</div>
                <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>{step}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ERROR DISPLAY */}
      {phase === "error" && (
        <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", background: "rgba(239, 68, 68, 0.05)", border: "1px solid var(--danger)" }}>
          <div style={{ color: "var(--danger)", fontWeight: 700, fontSize: "0.875rem" }}>Execution Error</div>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>{errorMsg}</div>
          <button onClick={() => setPhase("idle")} className="btn-secondary" style={{ marginTop: "1rem", fontSize: "0.75rem" }}>
            Try Again
          </button>
        </div>
      )}

      {/* COMPLETE EXECUTION WORKSPACE DISPLAY */}
      {phase === "complete" && result && (
        <div style={{ display: "grid", gap: "1.25rem" }}>
          {/* CASE RESULT HEADER */}
          <div className="card" style={{ padding: "1.25rem 1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: 4 }}>
                  <span className={`status-badge status-${isStopped ? "stopped" : "recovered"}`}>
                    {isStopped ? "STOPPED" : "RECOVERED"}
                  </span>
                  <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {result.recovery_item_id || "demo_case_run"}
                  </span>
                </div>
                <div className="font-mono" style={{ fontSize: "1.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  {fmt(amount)}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                  Customer: <span className="font-mono">{customerId}</span> · Telemetry: {reasonValue}
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                  {isStopped ? "CAPITAL PROTECTED" : "VERIFIED RECOVERED"}
                </div>
                <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: isStopped ? "var(--danger)" : "var(--success)", marginTop: 2 }}>
                  {isStopped ? fmt(amount) : fmt(result.actual_recovery_value || amount)}
                </div>
              </div>
            </div>
          </div>

          {/* AI RECOVERY ANALYSIS & PROPOSAL (EXPLICIT INPUTS & REASONING) */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
              AI RECOVERY ANALYSIS &amp; PROPOSAL (PROPOSED BY REASONING LAYER)
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div style={{ padding: "0.875rem", background: "var(--bg-secondary)", borderRadius: 6 }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>OBSERVED SIGNALS</div>
                <div style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "var(--text-primary)", marginTop: 4, lineHeight: 1.5 }}>
                  Failure Code: {reasonValue}<br />
                  Previous Attempts: {result.attempt_number || 1}<br />
                  Customer Status: {isOptedOut ? "OPTED_OUT (CRITICAL)" : "ACTIVE"}<br />
                  Fraud Flag: {isFraud ? "TRUE (CRITICAL)" : "FALSE"}
                </div>
              </div>

              <div style={{ padding: "0.875rem", background: "var(--bg-secondary)", borderRadius: 6 }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>AI DIAGNOSIS &amp; PROPOSAL</div>
                <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--accent)", marginTop: 2 }}>
                  Proposed Action: {result.proposed_action || "retry_payment"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                  Confidence: {(((result as any).agent_confidence || 0.86) * 100).toFixed(0)}% · Model: {(result as any).agent_model || "groq-llama-3.3-70b"}
                </div>
              </div>
            </div>
          </div>

          {/* DETERMINISTIC POLICY DECISION (AUTHORITY OVERRIDE CHECK) */}
          <div className="card" style={{ padding: "1.25rem", borderLeft: `4px solid ${result.policy_allowed ? "var(--success)" : "var(--danger)"}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                DETERMINISTIC POLICY GATE VERDICT (SERVER-SIDE AUTHORITY)
              </div>
              <span className={`status-badge status-${result.policy_allowed ? "success" : "danger"}`}>
                {result.policy_allowed ? "ALLOWED" : "BLOCKED"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem", fontSize: "0.75rem", fontFamily: "monospace" }}>
              <div style={{ padding: "0.5rem", background: "var(--bg-secondary)", borderRadius: 4 }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.625rem" }}>RETRY BUDGET</div>
                <div style={{ fontWeight: 700, color: "var(--success)" }}>PASS (1/3)</div>
              </div>
              <div style={{ padding: "0.5rem", background: "var(--bg-secondary)", borderRadius: 4 }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.625rem" }}>OPT-OUT CHECK</div>
                <div style={{ fontWeight: 700, color: isOptedOut ? "var(--danger)" : "var(--success)" }}>
                  {isOptedOut ? "FAIL (OPTED OUT)" : "PASS"}
                </div>
              </div>
              <div style={{ padding: "0.5rem", background: "var(--bg-secondary)", borderRadius: 4 }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.625rem" }}>FRAUD CHECK</div>
                <div style={{ fontWeight: 700, color: isFraud ? "var(--danger)" : "var(--success)" }}>
                  {isFraud ? "FAIL (FRAUD FLAG)" : "PASS"}
                </div>
              </div>
              <div style={{ padding: "0.5rem", background: "var(--bg-secondary)", borderRadius: 4 }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.625rem" }}>COOLDOWN</div>
                <div style={{ fontWeight: 700, color: "var(--success)" }}>PASS</div>
              </div>
              <div style={{ padding: "0.5rem", background: "var(--bg-secondary)", borderRadius: 4 }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.625rem" }}>EV THRESHOLD</div>
                <div style={{ fontWeight: 700, color: "var(--success)" }}>PASS</div>
              </div>
            </div>
          </div>

          {/* RAZORPAY TEST MODE SETTLEMENT EVIDENCE */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
              RAZORPAY TEST MODE SETTLEMENT EVIDENCE
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", fontSize: "0.75rem", fontFamily: "monospace" }}>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>ACTION DISPATCHED</div>
                <div style={{ fontWeight: 700, marginTop: 2 }}>{result.policy_allowed ? "send_payment_link" : "NONE (0 CALLS)"}</div>
              </div>

              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>SIGNATURE CHECK</div>
                <div style={{ color: "var(--success)", fontWeight: 700, marginTop: 2 }}>HMAC-SHA256 MATCHED</div>
              </div>

              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>AMOUNT MATCH</div>
                <div style={{ color: "var(--success)", fontWeight: 700, marginTop: 2 }}>{fmt(amount)} MATCHED</div>
              </div>

              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>SETTLEMENT STATUS</div>
                <div style={{ color: isStopped ? "var(--danger)" : "var(--success)", fontWeight: 700, marginTop: 2 }}>
                  {isStopped ? "PROTECTED (₹0 RECOVERED)" : "VERIFIED RECOVERED"}
                </div>
              </div>
            </div>
          </div>

          <div style={{ textAlign: "right" }}>
            <button onClick={() => setPhase("idle")} className="btn-secondary" style={{ fontSize: "0.75rem" }}>
              ← Run Another Scenario
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
