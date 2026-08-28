"use client";

import { useEffect, useState, useMemo } from "react";
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

export default function CaseWorkspace() {
  const params = useParams();
  const id = params?.id as string;
  const [status, setStatus] = useState<Status>("loading");
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setStatus("loading");
    api.itemDetail(id)
      .then(setDetail)
      .catch(() => { setError("not-found"); setDetail(null); })
      .finally(() => setStatus("ready"));
  }, [id]);

  if (status === "loading" || !detail) {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
        </div>
        <div className="skeleton" style={{ height: 400 }} />
      </div>
    );
  }

  if (error === "not-found") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🔍</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Case not found</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>
          The recovery case you&apos;re looking for doesn&apos;t exist or has been removed.
        </p>
        <Link href="/recovery" className="btn-primary">Back to Queue</Link>
      </div>
    );
  }

  const fmt = (n: number) => `₹${(n / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  const firstDecision: DecisionRow | null = detail.decisions?.[0] ? {
    proposed_action: String(detail.decisions[0].proposed_action || "—"),
    confidence: typeof detail.decisions[0].confidence === "number" ? detail.decisions[0].confidence : 0,
    reason: String(detail.decisions[0].reason || ""),
    model_name: String(detail.decisions[0].model_name || ""),
    policy_allowed: Boolean(detail.decisions[0].policy_allowed),
    policy_rule: String(detail.decisions[0].policy_rule || ""),
    policy_reason: String(detail.decisions[0].policy_reason || ""),
  } : null;

  const journeyStages = useMemo(() => buildJourney(detail, firstDecision), [detail, firstDecision]);

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      {/* Breadcrumb */}
      <div style={{ marginBottom: "1.25rem" }}>
        <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none" }}>
          ← Recovery Queue
        </Link>
      </div>

      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "0.75rem" }}>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700, fontFamily: "monospace", letterSpacing: "-0.02em" }}>
              {detail.id}
            </h1>
            <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
              <StatusBadge status={detail.status} />
              <span style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                {detail.root_cause || "unknown"} failure
              </span>
              <span style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>·</span>
              <span style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                {fmt(detail.amount_minor)}
              </span>
            </div>
          </div>
          <Link href={`/recovery/${detail.id}`} className="btn-secondary" style={{ fontSize: "0.75rem" }}>
            Refresh
          </Link>
        </div>
      </div>

      {/* Key metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <MetricCard label="Amount at Risk" value={fmt(detail.amount_minor)} />
        <MetricCard
          label="Expected Recovery"
          value={detail.expected_recovery_value ? fmt(detail.expected_recovery_value) : "—"}
          accent="var(--accent)"
        />
        <MetricCard
          label="Recovery Probability"
          value={detail.recovery_probability !== null ? `${(detail.recovery_probability * 100).toFixed(0)}%` : "—"}
          accent="var(--purple)"
        />
      </div>

      {/* Recovery Journey Timeline */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1.25rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Recovery Journey
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {journeyStages.map((stage, idx) => (
            <div key={idx} style={{ display: "flex", gap: "1rem" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 24, flexShrink: 0 }}>
                <div style={{
                  width: 12, height: 12, borderRadius: "50%",
                  background: stage.color || "var(--border)",
                  boxShadow: stage.active ? `0 0 10px ${stage.color || "var(--border)"}` : "none",
                  flexShrink: 0,
                }} />
                {idx < journeyStages.length - 1 && (
                  <div style={{ width: 2, flex: 1, background: "var(--border)", margin: "0.25rem 0" }} />
                )}
              </div>
              <div style={{ paddingBottom: idx < journeyStages.length - 1 ? "1rem" : 0, flex: 1 }}>
                <div style={{ fontSize: "0.8125rem", fontWeight: stage.active ? 600 : 400, color: stage.active ? "var(--text-primary)" : "var(--text-muted)" }}>
                  {stage.label}
                </div>
                {stage.detail && (
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>{stage.detail}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Two column: Details + AI + Policy */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* Failure Details */}
        <div className="card" style={{ padding: "1.5rem" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Failure Details
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <DetailRow label="Category" value={detail.root_cause || "unknown"} />
            <DetailRow label="Amount" value={fmt(detail.amount_minor)} />
            <DetailRow label="Currency" value={detail.currency} />
            <DetailRow label="Source" value={detail.source_type} />
            <DetailRow label="Created" value={new Date(detail.created_at).toLocaleString()} />
            {(detail.metadata?.error_code as string) && <DetailRow label="Error Code" value={String(detail.metadata.error_code)} />}
            {(detail.metadata?.error_reason as string) && <DetailRow label="Error Reason" value={String(detail.metadata.error_reason)} />}
            {(detail.metadata?.payment_method as string) && <DetailRow label="Payment Method" value={String(detail.metadata.payment_method)} />}
          </div>
        </div>

        {/* AI Recommendation + Policy */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* AI Reasoning */}
          <div className="card" style={{ padding: "1.5rem", borderLeft: `3px solid var(--purple)` }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem", color: "var(--purple)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              AI Recommendation
            </h3>
            {firstDecision ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                  <span style={{
                    background: "var(--purple-subtle)", color: "var(--purple)",
                    padding: "0.25rem 0.75rem", borderRadius: 6, fontSize: "0.8125rem", fontWeight: 600,
                  }}>
                    {(firstDecision.proposed_action || "—").replace(/_/g, " ")}
                  </span>
                  {firstDecision.confidence > 0 && (
                    <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                      {firstDecision.confidence.toFixed(0)}% confidence
                    </span>
                  )}
                </div>
                {firstDecision.reason && (
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    {firstDecision.reason}
                  </div>
                )}
                {firstDecision.model_name && (
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Model: {firstDecision.model_name}
                  </div>
                )}
              </div>
            ) : (
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No AI recommendation recorded.</p>
            )}
          </div>

          {/* Policy Decision */}
          <div className="card" style={{ padding: "1.5rem", borderLeft: `3px solid ${firstDecision ? (firstDecision.policy_allowed ? "var(--success)" : "var(--danger)") : "var(--border)"}` }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Policy Decision
            </h3>
            {firstDecision ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                  <span className={`status-badge ${firstDecision.policy_allowed ? "status-recovered" : "status-escalated"}`}>
                    {firstDecision.policy_allowed ? "ALLOWED" : "DENIED"}
                  </span>
                  {firstDecision.policy_rule && (
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {firstDecision.policy_rule}
                    </span>
                  )}
                </div>
                {firstDecision.policy_reason && (
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                    {firstDecision.policy_reason}
                  </div>
                )}
              </div>
            ) : (
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No policy decision recorded.</p>
            )}
            <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "var(--bg-tertiary)", borderRadius: 6, fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Human approval cannot bypass safety policy. All actions are re-checked by the PolicyEngine.
            </div>
          </div>
        </div>
      </div>

      {/* Execution Details */}
      {detail.attempts.length > 0 && (
        <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Execution Attempts
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {detail.attempts.map((a) => (
              <div key={a.attempt_number} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "0.75rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span style={{
                    width: 24, height: 24, borderRadius: "50%",
                    background: a.outcome === "success" ? "var(--success-subtle)" : "var(--danger-subtle)",
                    color: a.outcome === "success" ? "var(--success)" : "var(--danger)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "0.6875rem", fontWeight: 700,
                  }}>
                    {a.attempt_number}
                  </span>
                  <span style={{ fontSize: "0.8125rem", fontWeight: 500 }}>{a.action}</span>
                </div>
                <span className={`status-badge ${a.outcome === "success" ? "status-recovered" : "status-failed"}`}>
                  {a.outcome}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit Trail */}
      <div className="card" style={{ padding: "1.5rem" }}>
        <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Audit Trail
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {detail.audit_events.map((e, idx) => {
            const actorColor = e.actor === "agent" ? "var(--purple)" : e.actor === "rule" ? "var(--accent)" : "var(--text-muted)";
            const isLast = idx === detail.audit_events.length - 1;
            return (
              <div key={e.id} style={{ display: "flex", gap: "1rem", padding: "0.6rem 0", borderBottom: isLast ? "none" : "1px solid var(--border-subtle)" }}>
                <div style={{ width: 140, flexShrink: 0, fontSize: "0.6875rem", color: "var(--text-muted)", paddingTop: 2 }}>
                  {new Date(e.timestamp).toLocaleTimeString()}
                </div>
                <div style={{ width: 70, flexShrink: 0, fontSize: "0.6875rem", fontWeight: 600, color: actorColor, textTransform: "uppercase", letterSpacing: "0.04em", paddingTop: 2 }}>
                  {e.actor}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "0.8125rem", fontWeight: 500, marginBottom: 2 }}>{e.action}</div>
                  {e.reason && (
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {e.reason}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function buildJourney(detail: CaseDetail, firstDecision: DecisionRow | null) {
  const stages: { label: string; detail?: string; color: string; active: boolean }[] = [
    { label: "Payment Failed", color: "var(--danger)", active: true, detail: `${detail.root_cause || "unknown"} · ₹${(detail.amount_minor / 100).toLocaleString("en-IN")}` },
  ];

  const actions = new Set(detail.audit_events.map((e) => e.action));
  const status = detail.status;

  if (actions.has("failure_classified") || detail.root_cause) {
    stages.push({ label: "Failure Classified", color: "var(--accent)", active: true, detail: detail.root_cause || "unknown" });
  } else {
    stages.push({ label: "Failure Classified", color: "var(--border)", active: false });
  }

  if (firstDecision) {
    stages.push({ label: "AI Analyzed", color: "var(--purple)", active: true, detail: `Proposed: ${(firstDecision.proposed_action || "—").replace(/_/g, " ")}` });
  } else {
    stages.push({ label: "AI Analyzed", color: "var(--border)", active: false });
  }

  if (firstDecision) {
    stages.push({ label: "Policy Gate", color: firstDecision.policy_allowed ? "var(--success)" : "var(--danger)", active: true, detail: firstDecision.policy_allowed ? "Allowed" : "Denied" });
  } else {
    stages.push({ label: "Policy Gate", color: "var(--border)", active: false });
  }

  if (["intervention_pending", "intervention_executed", "recovered", "failed", "escalated"].includes(status)) {
    stages.push({ label: "Recovery Action", color: "var(--accent)", active: true });
  } else {
    stages.push({ label: "Recovery Action", color: "var(--border)", active: false });
  }

  if (status === "recovered") {
    stages.push({ label: "Recovered", color: "var(--success)", active: true, detail: detail.expected_recovery_value ? `₹${(detail.expected_recovery_value / 100).toLocaleString("en-IN")}` : undefined });
  } else if (status === "escalated") {
    stages.push({ label: "Escalated", color: "var(--warning)", active: true, detail: "Requires human review" });
  } else if (status === "stopped") {
    stages.push({ label: "Stopped", color: "var(--text-muted)", active: true, detail: "Recovery stopped" });
  } else if (status === "failed") {
    stages.push({ label: "Failed", color: "var(--danger)", active: true });
  } else {
    stages.push({ label: "Outcome", color: "var(--border)", active: false });
  }

  return stages;
}

function MetricCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="metric-card" style={accent ? { borderLeft: `3px solid ${accent}` } : undefined}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color: accent || "var(--text-primary)", marginTop: 4 }}>{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls = `status-badge status-${status}`;
  return <span className={cls}>{status.replace(/_/g, " ")}</span>;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8125rem" }}>
      <span style={{ color: "var(--text-muted)" }}>{label}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 500, textAlign: "right", maxWidth: "60%" }}>{value}</span>
    </div>
  );
}
