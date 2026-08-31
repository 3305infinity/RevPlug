"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CaseDetail } from "@/lib/api";

type Status = "loading" | "error" | "ready";

interface DecisionRow {
  proposed_action: string;
  confidence: number;
  reason: string;
  model_name: string;
  policy_allowed: boolean;
  policy_rule: string;
  policy_reason: string;
}

const fmt = (n: number) =>
  "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

export default function CaseWorkspace() {
  const params = useParams();
  const id = params?.id as string;
  const [status, setStatus] = useState<Status>("loading");
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [techOpen, setTechOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    setStatus("loading");
    api.itemDetail(id)
      .then(setDetail)
      .catch(() => {
        setError("not-found");
        setDetail(null);
      })
      .finally(() => setStatus("ready"));
  }, [id]);

  if (status === "loading" || !detail) {
    return (
      <div style={{ maxWidth: 1050, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 48, marginBottom: "1.5rem" }} />
        <div className="skeleton" style={{ height: 200, marginBottom: "1.5rem" }} />
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  if (error === "not-found") {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--danger)" }}>Case Not Found</div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
          The requested recovery case does not exist.
        </p>
        <Link href="/recovery" className="btn-primary" style={{ marginTop: "1rem" }}>
          Back to Queue
        </Link>
      </div>
    );
  }

  const firstDecision: DecisionRow | null = detail.decisions?.[0]
    ? {
        proposed_action: String(detail.decisions[0].proposed_action || "—"),
        confidence: typeof detail.decisions[0].confidence === "number" ? detail.decisions[0].confidence : 0,
        reason: String(detail.decisions[0].reason || ""),
        model_name: String(detail.decisions[0].model_name || ""),
        policy_allowed: Boolean(detail.decisions[0].policy_allowed),
        policy_rule: String(detail.decisions[0].policy_rule || ""),
        policy_reason: String(detail.decisions[0].policy_reason || ""),
      }
    : null;

  const isStopped = detail.status === "stopped";
  const isRecovered = detail.status === "recovered";
  const isBlocked = isStopped || detail.status === "failed";
  const recoveredAmount = detail.actual_recovery_value || (isRecovered ? detail.expected_recovery_value : null);

  const timelineSteps = [
    { label: "Payment Failed", detail: detail.root_cause || "Telemetry Error", status: "complete" },
    { label: "Risk Detected", detail: fmt(detail.amount_minor), status: "complete" },
    { label: "AI Diagnosis", detail: firstDecision ? firstDecision.proposed_action : "Evaluated", status: "complete" },
    { label: "Policy Check", detail: firstDecision?.policy_allowed ? "ALLOWED" : "BLOCKED", status: firstDecision?.policy_allowed ? "complete" : "blocked" },
    { label: "Action Executed", detail: detail.attempts[0]?.action || "Payment Link", status: isBlocked ? "skipped" : "complete" },
    { label: "Settlement Verified", detail: isRecovered ? fmt(recoveredAmount || 0) : "Unverified", status: isRecovered ? "complete" : "pending" },
  ];

  return (
    <div style={{ maxWidth: 1050, margin: "0 auto" }}>
      <div style={{ marginBottom: "1rem" }}>
        <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          ← Back to Recovery Queue
        </Link>
      </div>

      {/* CASE HEADER */}
      <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: 4 }}>
              <span className={`status-badge status-${detail.status}`}>
                {detail.status.replace(/_/g, " ")}
              </span>
              <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {detail.id}
              </span>
            </div>
            <h1 className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)" }}>
              {fmt(detail.amount_minor)}
            </h1>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
              Customer: <span className="font-mono">{detail.customer_id}</span> · Surface: {detail.source_type} · {new Date(detail.created_at).toLocaleString()}
            </div>
          </div>

          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Verified Recovered</div>
            <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: isRecovered ? "var(--success)" : "var(--text-muted)", marginTop: 2 }}>
              {recoveredAmount ? fmt(recoveredAmount) : "₹0"}
            </div>
          </div>
        </div>
      </div>

      {/* HORIZONTAL OPERATIONAL TIMELINE */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.25rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
          OPERATIONAL INVESTIGATION TIMELINE
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "0.5rem", alignItems: "center" }}>
          {timelineSteps.map((step, idx) => (
            <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <div
                style={{
                  flex: 1,
                  padding: "0.625rem 0.5rem",
                  borderRadius: 6,
                  background: step.status === "blocked" ? "rgba(239, 68, 68, 0.08)" : step.status === "complete" ? "var(--bg-secondary)" : "rgba(255, 255, 255, 0.02)",
                  border: step.status === "blocked" ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid var(--border)",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
                  {step.label}
                </div>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, marginTop: 2, color: step.status === "blocked" ? "var(--danger)" : "var(--text-primary)" }}>
                  {step.detail}
                </div>
              </div>
              {idx < timelineSteps.length - 1 && <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>→</span>}
            </div>
          ))}
        </div>
      </div>

      {/* DECISION ANALYSIS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
        {/* AI Analysis */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "0.75rem" }}>
            1. AI DIAGNOSIS &amp; PROPOSAL
          </div>
          {firstDecision ? (
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Recommended Action:</div>
              <div style={{ fontSize: "1rem", fontWeight: 700, marginTop: 2, textTransform: "capitalize" }}>
                {firstDecision.proposed_action.replace(/_/g, " ")}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--accent)", marginTop: 4 }}>
                Confidence: {(firstDecision.confidence * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 8, lineHeight: 1.4 }}>
                {firstDecision.reason}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>No AI proposal recorded.</div>
          )}
        </div>

        {/* Policy Decision */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "0.75rem" }}>
            2. POLICY ENGINE DECISION
          </div>
          {firstDecision ? (
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Policy Gate Verdict:</div>
              <div style={{ fontSize: "1rem", fontWeight: 700, marginTop: 2, color: firstDecision.policy_allowed ? "var(--success)" : "var(--danger)" }}>
                {firstDecision.policy_allowed ? "ALLOWED" : "BLOCKED"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                Rule: {firstDecision.policy_rule || "stopping_rules_pass"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 8, lineHeight: 1.4 }}>
                {firstDecision.policy_reason || "Evaluated against opt-out, fraud checks, and retry limits."}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>No policy evaluation recorded.</div>
          )}
        </div>
      </div>

      {/* TECHNICAL AUDIT EVENTS */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
            Immutable Audit Trail ({detail.audit_events?.length || 0} events)
          </div>
          <button onClick={() => setTechOpen(!techOpen)} className="btn-ghost" style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}>
            {techOpen ? "Hide Technical Details ▲" : "Inspect Technical Details ▼"}
          </button>
        </div>

        {techOpen && (
          <div style={{ marginTop: "1rem", display: "grid", gap: "0.5rem" }}>
            {detail.audit_events?.map((ev, idx) => (
              <div key={idx} style={{ padding: "0.5rem 0.75rem", background: "var(--bg-secondary)", borderRadius: 6, fontSize: "0.75rem", fontFamily: "monospace", display: "flex", justifyContent: "space-between" }}>
                <span>{ev.action}</span>
                <span style={{ color: "var(--text-muted)" }}>{new Date(ev.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
