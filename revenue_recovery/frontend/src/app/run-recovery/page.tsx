"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { api, SimulationResult } from "@/lib/api";

const FAILURE_REASONS = [
  { value: "payment_timed_out", label: "Gateway Timeout", category: "soft", desc: "Network timeout — retry typically succeeds" },
  { value: "gateway_technical_error", label: "Gateway Technical Failure", category: "soft", desc: "Gateway error — retry typically succeeds" },
  { value: "card_declined", label: "Hard Card Decline", category: "hard", desc: "Bank declined — do not retry automatically" },
  { value: "payment_risk_check_failed", label: "Fraud Signal", category: "fraud", desc: "Risk check failed — block recovery, escalate" },
  { value: "authentication_failed", label: "Authentication Required", category: "auth", desc: "Customer must re-authenticate" },
  { value: "unknown_reason", label: "Unknown Failure", category: "unknown", desc: "Unclassified — escalate to human" },
];

type Phase = "idle" | "running" | "complete" | "error";

export default function RunRecoveryPage() {
  const [reasonKey, setReasonKey] = useState(0);
  const [amount, setAmount] = useState(50000);
  const [customerName, setCustomerName] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [runningStep, setRunningStep] = useState(0);

  const selectedReason = FAILURE_REASONS[reasonKey];

  const STEPS = [
    "Webhook received",
    "Signature verified",
    "Failure classified",
    "Value scored",
    "AI decision",
    "Policy evaluated",
    "Action executed",
    "Outcome recorded",
  ];

  const reset = useCallback(() => {
    setPhase("idle");
    setResult(null);
    setErrorMsg("");
    setRunningStep(0);
  }, []);

  const handleRun = async () => {
    if (!customerName.trim()) return;

    setPhase("running");
    setErrorMsg("");
    setResult(null);
    setRunningStep(0);

    for (let i = 0; i < STEPS.length; i++) {
      await new Promise((r) => setTimeout(r, 220));
      setRunningStep(i + 1);
    }

    try {
      const res = await api.triggerDemo({
        event_type: "payment_failure",
        error_reason: selectedReason.value,
        amount_minor: amount,
        customer_id: customerName.trim(),
      });
      setResult(res);
      setPhase("complete");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Execution failed");
      setPhase("error");
    }
  };

  const fmt = (n: number) => "Rs" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const outcomeColor = result?.status === "processed" ? "var(--success)" : result?.status === "escalated" ? "var(--danger)" : "var(--warning)";
  const outcomeLabel = result?.status === "processed" ? "RECOVERED" : result?.status === "escalated" ? "ESCALATED" : result?.status?.toUpperCase() || "COMPLETE";

  return (
    <div style={{ maxWidth: 860, margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>Run Recovery</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Simulate a payment failure and execute a recovery workflow. Every action is logged and audited.
        </p>
      </div>

      {phase === "idle" && (
        <div className="card" style={{ padding: "2rem", marginBottom: "1.5rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div>
              <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
                Failure Type
              </label>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
                {FAILURE_REASONS.map((r, i) => (
                  <button
                    key={r.value}
                    onClick={() => setReasonKey(i)}
                    style={{
                      padding: "0.75rem 1rem",
                      borderRadius: 8,
                      border: `1px solid ${reasonKey === i ? "var(--accent)" : "var(--border)"}`,
                      background: reasonKey === i ? "var(--accent-subtle)" : "var(--bg-tertiary)",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.15s",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.2rem" }}>
                      <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: reasonKey === i ? "var(--accent)" : "var(--text-primary)" }}>
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

            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <div>
                <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
                  Amount (₹)
                </label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(Math.max(100, Number(e.target.value)))}
                  className="input"
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
                  Customer ID
                </label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="e.g. cust_3Xt8Gk"
                  className="input"
                  style={{ width: "100%" }}
                />
              </div>

              <div style={{ marginTop: "auto", padding: "1rem", background: "var(--bg-tertiary)", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Expected outcome</div>
                <div style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-primary)" }}>
                  {selectedReason.category === "soft" && "Automatic retry — recovery likely"}
                  {selectedReason.category === "hard" && "Payment link or escalation"}
                  {selectedReason.category === "fraud" && "Blocked — escalated to human"}
                  {selectedReason.category === "auth" && "Payment link sent"}
                  {selectedReason.category === "unknown" && "Escalated for review"}
                </div>
              </div>

              <button
                onClick={handleRun}
                disabled={!customerName.trim()}
                className="btn-primary"
                style={{ width: "100%", padding: "0.875rem", fontSize: "0.875rem" }}
              >
                Execute Recovery Workflow
              </button>
            </div>
          </div>
        </div>
      )}

      {phase === "running" && (
        <div className="card" style={{ padding: "2rem" }}>
          <div style={{ marginBottom: "1.5rem" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
              Executing Recovery Workflow
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
              {STEPS.map((step, i) => {
                const done = runningStep > i;
                const active = runningStep === i + 1;
                return (
                  <div key={step} style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "0.75rem 0", borderBottom: i < STEPS.length - 1 ? "1px solid var(--border-subtle)" : "none" }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: "50%",
                      background: done ? "var(--success)" : active ? "var(--accent)" : "var(--bg-tertiary)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "0.6875rem", fontWeight: 700,
                      color: done || active ? "#fff" : "var(--text-muted)",
                      flexShrink: 0,
                      transition: "all 0.2s",
                    }}>
                      {done ? "✓" : i + 1}
                    </div>
                    <span style={{ fontSize: "0.8125rem", color: done || active ? "var(--text-primary)" : "var(--text-muted)", fontWeight: done || active ? 500 : 400 }}>
                      {step}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {phase === "complete" && result && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card" style={{ padding: "2rem", borderLeft: `4px solid ${outcomeColor}` }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
              <div>
                <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>Outcome</div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: outcomeColor, letterSpacing: "-0.03em" }}>{outcomeLabel}</div>
              </div>
              {result.recovery_item_id && (
                <Link href={`/recovery/${result.recovery_item_id}`} className="btn-primary">
                  Open Case →
                </Link>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.25rem" }}>
              <ResultCell label="Case ID" value={result.recovery_item_id || "—"} mono />
              <ResultCell label="Failure" value={result.failure_category?.replace(/_/g, " ") || "—"} />
              <ResultCell label="AI Action" value={result.proposed_action?.replace(/_/g, " ") || "—"} />
              <ResultCell label="Policy" value={result.policy_allowed ? "Allowed" : "Blocked"} success={result.policy_allowed} danger={!result.policy_allowed} />
            </div>

            {result.expected_recovery_value && (
              <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--success)", fontFamily: "monospace" }}>
                {fmt(result.expected_recovery_value)} expected recovery
              </div>
            )}
          </div>

          <button onClick={reset} className="btn-secondary" style={{ alignSelf: "flex-start" }}>
            Run Another Recovery
          </button>
        </div>
      )}

      {phase === "error" && (
        <div className="card" style={{ padding: "2rem", borderLeft: "4px solid var(--danger)" }}>
          <div style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>⚠️</div>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>Execution Failed</h3>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>{errorMsg}</p>
          <button onClick={reset} className="btn-primary">Try Again</button>
        </div>
      )}
    </div>
  );
}

function ResultCell({ label, value, mono, success, danger }: { label: string; value: string; mono?: boolean; success?: boolean; danger?: boolean }) {
  return (
    <div style={{ padding: "0.875rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8 }}>
      <div style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.35rem" }}>{label}</div>
      <div style={{ fontSize: "0.8125rem", fontWeight: 600, fontFamily: mono ? "monospace" : undefined, color: success ? "var(--success)" : danger ? "var(--danger)" : "var(--text-primary)", textTransform: "capitalize" }}>
        {value}
      </div>
    </div>
  );
}

function categoryColor(cat: string): string {
  const map: Record<string, string> = { soft: "var(--success)", hard: "var(--warning)", fraud: "var(--danger)", auth: "var(--accent)", unknown: "var(--text-muted)" };
  return map[cat] || "var(--text-muted)";
}
