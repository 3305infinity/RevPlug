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

type Phase = "idle" | "running" | "complete" | "error";

export default function RunRecoveryPage() {
  const [sourceType, setSourceType] = useState("payment_failure");
  const [reasonKey, setReasonKey] = useState(0);
  const [amount, setAmount] = useState(50000);
  const [customerId, setCustomerId] = useState("cust_demo_101");
  const [daysOverdue, setDaysOverdue] = useState(3);
  const [mandateId, setMandateId] = useState("man_9021");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const selectedReason = FAILURE_REASONS[reasonKey];

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
    <div style={{ maxWidth: 860, margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>Run Recovery</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Evaluate a revenue event across canonical surfaces and execute the safest eligible recovery action.
        </p>
      </div>

      {phase === "idle" && (
        <div className="card" style={{ padding: "2rem", marginBottom: "1.5rem" }}>
          {/* Recovery Surface Type Selector */}
          <div style={{ marginBottom: "1.75rem" }}>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              1. Opportunity Type / Surface
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "0.5rem" }}>
              {RECOVERY_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setSourceType(t.value)}
                  style={{
                    padding: "0.65rem 0.85rem",
                    borderRadius: 4,
                    border: `1px solid ${sourceType === t.value ? "var(--orange)" : "var(--border)"}`,
                    background: sourceType === t.value ? "rgba(249, 115, 22, 0.1)" : "#0b0f17",
                    color: sourceType === t.value ? "var(--orange)" : "var(--text-primary)",
                    fontWeight: sourceType === t.value ? 600 : 400,
                    cursor: "pointer",
                    fontSize: "0.78125rem",
                    textAlign: "left",
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div>
              <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
                2. Failure / Reason Code
              </label>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
                {FAILURE_REASONS.map((r, i) => (
                  <button
                    key={r.value}
                    onClick={() => setReasonKey(i)}
                    style={{
                      padding: "0.65rem 0.85rem",
                      borderRadius: 4,
                      border: `1px solid ${reasonKey === i ? "var(--orange)" : "var(--border)"}`,
                      background: reasonKey === i ? "rgba(249, 115, 22, 0.1)" : "#0b0f17",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.15s",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.2rem" }}>
                      <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: reasonKey === i ? "var(--orange)" : "var(--text-primary)" }}>
                        {r.label}
                      </span>
                      <span style={{ fontSize: "0.625rem", fontWeight: 600, padding: "0.15rem 0.5rem", borderRadius: 4, background: categoryColor(r.category), color: "#fff", textTransform: "uppercase" }}>
                        {r.category}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>{r.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
                3. Opportunity Details
              </label>
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
                    Amount at Risk (₹)
                  </div>
                  <input
                    type="number"
                    value={amount / 100}
                    onChange={(e) => setAmount(Math.max(0, Math.round(Number(e.target.value) * 100)))}
                    style={{
                      width: "100%",
                      padding: "0.625rem 0.875rem",
                      borderRadius: 4,
                      border: "1px solid var(--border)",
                      background: "#080c14",
                      color: "#fff",
                      fontSize: "0.875rem",
                    }}
                  />
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                    {fmt(amount)} minor units
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
                    Customer Identifier
                  </div>
                  <input
                    type="text"
                    placeholder="e.g. cust_razorpay_99"
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "0.625rem 0.875rem",
                      borderRadius: 4,
                      border: "1px solid var(--border)",
                      background: "#080c14",
                      color: "#fff",
                      fontSize: "0.875rem",
                    }}
                  />
                </div>

                {sourceType === "overdue_receivable" && (
                  <div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
                      Days Overdue (Ladder Day 1/3/7/14)
                    </div>
                    <select
                      value={daysOverdue}
                      onChange={(e) => setDaysOverdue(Number(e.target.value))}
                      style={{
                        width: "100%",
                        padding: "0.625rem 0.875rem",
                        borderRadius: 4,
                        border: "1px solid var(--border)",
                        background: "#080c14",
                        color: "#fff",
                        fontSize: "0.875rem",
                      }}
                    >
                      <option value={1}>Day 1 — Gentle Reminder</option>
                      <option value={3}>Day 3 — Strong Reminder + Payment Link</option>
                      <option value={7}>Day 7 — Alternate Channel Notice</option>
                      <option value={14}>Day 14 — Escalate to Human Operator</option>
                    </select>
                  </div>
                )}

                {sourceType === "mandate_failure" && (
                  <div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
                      Mandate ID
                    </div>
                    <input
                      type="text"
                      value={mandateId}
                      onChange={(e) => setMandateId(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.625rem 0.875rem",
                        borderRadius: 4,
                        border: "1px solid var(--border)",
                        background: "#080c14",
                        color: "#fff",
                        fontSize: "0.875rem",
                      }}
                    />
                  </div>
                )}

                <div style={{ marginTop: "1rem" }}>
                  <button
                    onClick={handleRun}
                    disabled={!customerId.trim()}
                    style={{
                      width: "100%",
                      padding: "0.75rem 1rem",
                      borderRadius: 4,
                      background: "var(--orange)",
                      color: "#fff",
                      fontWeight: 600,
                      border: "none",
                      cursor: customerId.trim() ? "pointer" : "not-allowed",
                      fontSize: "0.875rem",
                    }}
                  >
                    Evaluate & Execute Recovery →
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {phase === "running" && (
        <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
          <div style={{ fontSize: "1.25rem", fontWeight: 600, color: "#fff", marginBottom: "1rem" }}>
            Running Recovery Control Pipeline...
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", fontFamily: "monospace" }}>
            [Detecting → EV Scoring → Safety Policy Check → Bounded Dispatch]
          </div>
        </div>
      )}

      {phase === "error" && (
        <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>⚠️</div>
          <div style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--danger)", marginBottom: "0.5rem" }}>Execution Failed</div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "1.5rem" }}>{errorMsg}</div>
          <button onClick={reset} style={{ padding: "0.5rem 1rem", background: "var(--bg-tertiary)", border: "1px solid var(--border)", color: "#fff", borderRadius: 4, cursor: "pointer" }}>
            Try Again
          </button>
        </div>
      )}

      {phase === "complete" && result && (
        <div>
          <div className="card" style={{ padding: "1.75rem", marginBottom: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <span style={{ fontSize: "0.6875rem", fontWeight: 700, fontFamily: "monospace", color: "var(--text-muted)", textTransform: "uppercase" }}>
                PIPELINE EXECUTION OUTCOME
              </span>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, fontFamily: "monospace", padding: "0.25rem 0.6rem", borderRadius: 4, background: outcomeColor + "20", color: outcomeColor, border: `1px solid ${outcomeColor}40` }}>
                {outcomeLabel}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem" }}>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>ITEM ID</div>
                <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#fff", fontFamily: "monospace" }}>{result.recovery_item_id}</div>
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>RECOVERED VALUE</div>
                <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--success)" }}>{fmt(result.actual_recovery_value || 0)}</div>
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>EXECUTED ACTION</div>
                <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--orange)", fontFamily: "monospace" }}>{result.proposed_action || "none"}</div>
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>POLICY RULE</div>
                <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>{result.policy_rule || "n/a"}</div>
              </div>
            </div>

            <div style={{ marginTop: "1.5rem", display: "flex", gap: "1rem" }}>
              <Link href={`/recovery/${result.recovery_item_id}`} style={{ padding: "0.5rem 1rem", background: "var(--orange)", color: "#fff", borderRadius: 4, textDecoration: "none", fontSize: "0.8125rem", fontWeight: 600 }}>
                Open Case Workspace →
              </Link>
              <button onClick={reset} style={{ padding: "0.5rem 1rem", background: "#0b0f17", border: "1px solid var(--border)", color: "#fff", borderRadius: 4, cursor: "pointer", fontSize: "0.8125rem" }}>
                Run Another Evaluation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function categoryColor(cat: string) {
  switch (cat) {
    case "soft": return "var(--orange)";
    case "hard": return "var(--danger)";
    case "fraud": return "var(--danger)";
    case "auth": return "var(--warning)";
    default: return "var(--text-muted)";
  }
}
