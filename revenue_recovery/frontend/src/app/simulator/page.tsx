"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { api, SimulationResult } from "@/lib/api";

const scenarios = [
  {
    id: "payment_timed_out",
    label: "Soft Timeout",
    desc: "Gateway timeout — recoverable, auto-retry",
    color: "var(--success)",
    icon: "🔄",
    expected: "Retry scheduled automatically",
  },
  {
    id: "gateway_technical_error",
    label: "Gateway Failure",
    desc: "Technical error — recoverable, auto-retry",
    color: "var(--success)",
    icon: "🔧",
    expected: "Retry scheduled automatically",
  },
  {
    id: "card_declined",
    label: "Hard Decline",
    desc: "Card declined — escalate to human",
    color: "var(--warning)",
    icon: "🚫",
    expected: "Escalated for human review",
  },
  {
    id: "payment_risk_check_failed",
    label: "Fraud Detected",
    desc: "Risk check failed — block recovery",
    color: "var(--danger)",
    icon: "⚠️",
    expected: "Blocked, escalated to human",
  },
  {
    id: "authentication_failed",
    label: "Auth Required",
    desc: "Customer must re-authenticate",
    color: "var(--accent)",
    icon: "🔐",
    expected: "Payment link sent",
  },
  {
    id: "unknown_reason",
    label: "Unknown Failure",
    desc: "Unclassified — safe escalation",
    color: "var(--text-muted)",
    icon: "❓",
    expected: "Escalated for manual review",
  },
];

type Stage = "idle" | "processing" | "complete" | "error";

const stages = [
  { key: "webhook", label: "Webhook Received", duration: 200 },
  { key: "verify", label: "Signature Verified", duration: 150 },
  { key: "classify", label: "Failure Classified", duration: 200 },
  { key: "score", label: "Expected Value Scored", duration: 150 },
  { key: "ai", label: "AI Recommendation", duration: 400 },
  { key: "policy", label: "Policy Evaluated", duration: 150 },
  { key: "execute", label: "Recovery Action", duration: 300 },
  { key: "outcome", label: "Outcome Recorded", duration: 150 },
];

export default function Simulator() {
  const [processing, setProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState(-1);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const trigger = useCallback(async (errorReason: string, expected: string) => {
    setProcessing(true);
    setCurrentStage(0);
    setResult(null);
    setError(null);

    try {
      // Animate through stages
      for (let i = 0; i < stages.length; i++) {
        await delay(stages[i].duration);
        setCurrentStage(i + 1);
      }

      const data = await api.triggerDemo({
        event_id: `evt_${errorReason}_${Date.now()}`,
        payment_id: `pay_${errorReason}_${Date.now()}`,
        error_reason: errorReason,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
      setCurrentStage(-1);
    } finally {
      setProcessing(false);
    }
  }, []);

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>Recovery Simulator</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
          Trigger synthetic payment failures and watch the recovery engine respond
        </p>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: "1.25rem", background: "var(--danger-subtle)", borderColor: "rgba(239, 68, 68, 0.2)", padding: "1rem 1.25rem" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.8125rem" }}>{error}</div>
        </div>
      )}

      {/* Stage indicator */}
      {(processing || currentStage >= 0) && (
        <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 500 }}>
            Processing Pipeline
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {stages.map((s, idx) => {
              const isActive = processing && idx === currentStage;
              const isComplete = currentStage > idx;
              return (
                <div key={s.key} style={{
                  display: "flex", alignItems: "center", gap: "0.4rem",
                  padding: "0.35rem 0.75rem", borderRadius: 6, fontSize: "0.75rem",
                  background: isComplete ? "var(--success-subtle)" : isActive ? "var(--accent-subtle)" : "var(--bg-tertiary)",
                  color: isComplete ? "var(--success)" : isActive ? "var(--accent)" : "var(--text-muted)",
                  border: `1px solid ${isComplete ? "rgba(16,185,129,0.2)" : isActive ? "rgba(6,182,212,0.2)" : "var(--border)"}`,
                  fontWeight: isActive || isComplete ? 500 : 400,
                  transition: "all 0.2s",
                }}>
                  {isComplete ? "✓" : isActive ? "⟳" : "○"} {s.label}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Result card */}
      {result && (
        <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", borderLeft: `3px solid ${result.status === "processed" ? "var(--success)" : "var(--warning)"}` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                Simulation Complete
              </div>
              <div style={{ fontSize: "1.125rem", fontWeight: 600 }}>
                {result.status === "processed" ? "Recovery Processed" : result.status === "duplicate" ? "Duplicate Ignored" : result.status}
              </div>
            </div>
            <StatusBadge status={result.status} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", marginBottom: "1.25rem" }}>
            <ResultItem label="Case ID" value={result.recovery_item_id || "—"} mono />
            <ResultItem label="Failure Category" value={result.failure_category || "—"} />
            <ResultItem label="Expected Recovery" value={result.expected_recovery_value != null ? `₹${(result.expected_recovery_value / 100).toLocaleString("en-IN")}` : "—"} />
            <ResultItem label="AI Proposed" value={result.proposed_action?.replace(/_/g, " ") || "—"} />
            <ResultItem label="Policy Decision" value={result.policy_allowed !== undefined ? (result.policy_allowed ? "Allowed" : "Denied") : "—"} />
            <ResultItem label="Execution" value={result.execution_status?.replace(/_/g, " ") || "—"} />
          </div>
          {result.recovery_item_id && (
            <Link href={`/recovery/${result.recovery_item_id}`} className="btn-primary" style={{ fontSize: "0.8125rem" }}>
              View Recovery Case →
            </Link>
          )}
        </div>
      )}

      {/* Scenario grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        {scenarios.map((s) => (
          <button
            key={s.id}
            onClick={() => trigger(s.id, s.expected)}
            disabled={processing}
            className="card"
            style={{
              cursor: processing ? "not-allowed" : "pointer",
              opacity: processing ? 0.5 : 1,
              textAlign: "left",
              padding: "1.5rem",
              border: `1px solid var(--border)`,
              transition: "transform 0.1s, border-color 0.15s",
            }}
          >
            <div style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>{s.icon}</div>
            <div style={{ fontWeight: 600, fontSize: "0.9375rem", marginBottom: "0.35rem" }}>{s.label}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>{s.desc}</div>
            <div style={{
              fontSize: "0.6875rem", color: s.color, fontWeight: 500,
              padding: "0.25rem 0.6rem", borderRadius: 4, background: `${s.color}15`,
              display: "inline-block",
            }}>
              {s.expected}
            </div>
          </button>
        ))}
      </div>

      {/* Info card */}
      <div className="card" style={{ padding: "1.25rem 1.5rem", background: "var(--accent-subtle)", border: "1px solid rgba(6,182,212,0.15)" }}>
        <div style={{ fontSize: "0.75rem", color: "var(--accent)", lineHeight: 1.6 }}>
          <strong>Simulator Mode:</strong> All execution is simulated. No real payments are processed.
          Each simulation runs through the complete backend pipeline — signature verification, failure classification,
          expected-value scoring, AI recommendation, policy validation, and execution. Results reflect actual backend behavior.
        </div>
      </div>
    </div>
  );
}

function ResultItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: "0.8125rem", fontWeight: 500, fontFamily: mono ? "monospace" : undefined, color: "var(--text-primary)" }}>
        {value}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls = `status-badge status-${status}`;
  return <span className={cls}>{status.replace(/_/g, " ")}</span>;
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
