"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, IncidentDetail, IncidentOpportunity, IncidentTimelineEvent } from "@/lib/api";
import DecisionBadge from "@/components/shared/DecisionBadge";

const fmt = (minor: number) =>
  "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

const SEVERITY_META: Record<string, { color: string; bg: string; border: string }> = {
  CRITICAL: { color: "#ef4444", bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.4)" },
  HIGH: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.4)" },
  MEDIUM: { color: "#3b82f6", bg: "rgba(59,130,246,0.12)", border: "rgba(59,130,246,0.4)" },
  LOW: { color: "#64748b", bg: "rgba(100,116,139,0.1)", border: "rgba(100,116,139,0.3)" },
};

export default function IncidentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const incidentId = params?.id as string;

  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [opportunities, setOpportunities] = useState<IncidentOpportunity[]>([]);
  const [timeline, setTimeline] = useState<IncidentTimelineEvent[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "not-found">("loading");
  const [resolving, setResolving] = useState(false);

  const loadData = useCallback(() => {
    if (!incidentId) return;
    setStatus("loading");
    Promise.all([
      api.incidentDetail(incidentId),
      api.incidentOpportunities(incidentId),
      api.incidentTimeline(incidentId),
    ])
      .then(([d, ops, tl]) => {
        if (!d || (d as any).error) {
          setStatus("not-found");
          return;
        }
        setDetail(d);
        setOpportunities(Array.isArray(ops) ? ops : []);
        setTimeline(Array.isArray(tl) ? tl : []);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [incidentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleResolve = async () => {
    if (!incidentId) return;
    setResolving(true);
    try {
      await api.resolveIncident(incidentId);
      loadData();
    } catch {
      // Silent fail
    } finally {
      setResolving(false);
    }
  };

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 80, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
        </div>
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>
          Unable to load incident details.
        </div>
        <button onClick={() => router.push("/incidents")} className="btn-secondary" style={{ marginTop: "1rem" }}>
          Back to Incidents
        </button>
      </div>
    );
  }

  if (status === "not-found" || !detail) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
          Incident not found
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "1.5rem" }}>
          This incident may have resolved or the ID is invalid.
        </div>
        <button onClick={() => router.push("/incidents")} className="btn-secondary">
          View All Incidents
        </button>
      </div>
    );
  }

  const sevMeta = SEVERITY_META[detail.severity] || SEVERITY_META.MEDIUM;
  const verifiedTotal = opportunities.reduce((sum, o) => sum + (o.verified_recovery_minor || 0), 0);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* BACK LINK */}
      <Link href="/incidents" style={{
        display: "inline-flex", alignItems: "center", gap: "0.35rem",
        fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none",
        marginBottom: "1rem", fontWeight: 600,
      }}>
        ← Back to Incidents
      </Link>

      {/* HEADER */}
      <div style={{
        padding: "1.5rem", background: "var(--bg-secondary)", borderRadius: 10,
        border: `2px solid ${sevMeta.border}`, marginBottom: "1.5rem",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
              <span style={{
                fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
                background: sevMeta.bg, color: sevMeta.color, border: `1px solid ${sevMeta.border}`,
              }}>
                {detail.severity}
              </span>
              <DecisionBadge decision={detail.decision as any} />
              <span style={{ fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
                background: detail.status === "ACTIVE" ? "rgba(239,68,68,0.12)" : "rgba(16,185,129,0.12)",
                color: detail.status === "ACTIVE" ? "#ef4444" : "#10b981",
                border: `1px solid ${detail.status === "ACTIVE" ? "rgba(239,68,68,0.4)" : "rgba(16,185,129,0.4)"}`,
              }}>
                {detail.status}
              </span>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                {detail.incident_id}
              </span>
            </div>
            <h1 style={{ fontSize: "1.375rem", fontWeight: 700, lineHeight: 1.3, marginBottom: "0.35rem" }}>
              {detail.title}
            </h1>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              {detail.payment_method} &middot; {detail.failure_category.replace(/_/g, " ")} &middot; {detail.gateway}
            </div>
          </div>
          {detail.status === "ACTIVE" && (
            <button
              onClick={handleResolve}
              disabled={resolving}
              className="btn-primary"
              style={{
                fontSize: "0.8125rem", padding: "0.5rem 1rem", background: "#10b981", color: "#fff",
                border: "none", cursor: "pointer", borderRadius: 6, fontWeight: 700, whiteSpace: "nowrap",
              }}
            >
              {resolving ? "Resolving..." : "Resolve Incident"}
            </button>
          )}
        </div>
      </div>

      {/* FINANCIAL IMPACT */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", marginBottom: "1.5rem",
      }}>
        <div className="metric-block" style={{ borderLeft: "3px solid #ef4444" }}>
          <div className="metric-label">Revenue at Risk</div>
          <div className="metric-value" style={{ color: "#ef4444" }}>{fmt(detail.amount_at_risk_minor)}</div>
        </div>
        <div className="metric-block" style={{ borderLeft: "3px solid #f59e0b" }}>
          <div className="metric-label">Expected Recovery</div>
          <div className="metric-value" style={{ color: "#f59e0b" }}>{fmt(detail.estimated_recoverable_minor)}</div>
          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 2 }}>projected</div>
        </div>
        <div className="metric-block" style={{ borderLeft: "3px solid #10b981" }}>
          <div className="metric-label">Verified Recovered</div>
          <div className="metric-value" style={{ color: "#10b981" }}>{fmt(verifiedTotal)}</div>
          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 2 }}>settlement confirmed</div>
        </div>
        <div className="metric-block" style={{ borderLeft: "3px solid #6366f1" }}>
          <div className="metric-label">Affected Opportunities</div>
          <div className="metric-value">{detail.affected_opportunity_ids?.length || 0}</div>
        </div>
        <div className="metric-block" style={{ borderLeft: "3px solid #64748b" }}>
          <div className="metric-label">Affected Customers</div>
          <div className="metric-value">{detail.affected_customers_count}</div>
        </div>
      </div>

      {/* SYSTEM DECISION + WHY */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            System Decision
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.625rem" }}>
            <DecisionBadge decision={detail.decision as any} />
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
              Policy constrained &middot; Bounded autonomy
            </span>
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            {detail.decision_reason || detail.reason}
          </div>
        </div>
        <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Resolution Condition
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
            {detail.resolution_condition || "Failure rate returns below 2x baseline for 30+ minutes."}
          </div>
          <div style={{
            fontSize: "0.6875rem", color: "#f59e0b", fontWeight: 600,
            background: "rgba(245,158,11,0.08)", padding: "0.5rem 0.75rem", borderRadius: 5,
            border: "1px solid rgba(245,158,11,0.2)",
          }}>
            Failure rate: {detail.failure_rate_pct}% (baseline: {detail.baseline_failure_rate_pct}%) &middot; {detail.lift_vs_baseline}x spike
          </div>
        </div>
      </div>

      {/* TRUST STRIP */}
      <div style={{
        display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.5rem",
        padding: "0.75rem 1rem", background: "var(--bg-secondary)", borderRadius: 8,
        border: "1px solid var(--border)", fontSize: "0.75rem",
      }}>
        <span style={{ color: "#10b981", fontWeight: 600 }}>✓ Policy constrained</span>
        <span style={{ color: "var(--border)" }}>|</span>
        <span style={{ color: "#10b981", fontWeight: 600 }}>✓ Duplicate-safe</span>
        <span style={{ color: "var(--border)" }}>|</span>
        <span style={{ color: "#10b981", fontWeight: 600 }}>✓ Settlement verified</span>
        <span style={{ color: "var(--border)" }}>|</span>
        <span style={{ color: "#10b981", fontWeight: 600 }}>✓ Auditable</span>
        <span style={{ color: "var(--border)" }}>|</span>
        <span style={{ color: "#10b981", fontWeight: 600 }}>✓ Bounded autonomy</span>
      </div>

      {/* AFFECTED OPPORTUNITIES */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{
          fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)",
          textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem",
        }}>
          Affected Opportunities ({opportunities.length})
        </div>
        {opportunities.length === 0 ? (
          <div style={{
            padding: "2rem", textAlign: "center", background: "var(--bg-secondary)",
            borderRadius: 8, border: "1px solid var(--border)", fontSize: "0.8125rem", color: "var(--text-muted)",
          }}>
            {detail.status === "ACTIVE"
              ? "Opportunities are being suppressed. No new actions are being taken during this systemic condition."
              : "No affected opportunity records available for this incident."}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
              <thead>
                <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>OPPORTUNITY</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>CUSTOMER</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>AT RISK</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>STATUS</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>RELATIONSHIP</th>
                </tr>
              </thead>
              <tbody>
                {opportunities.map((opp) => (
                  <tr key={opp.opportunity_id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.5rem 0.65rem" }}>
                      <Link href={`/recovery/${opp.opportunity_id}`} style={{ color: "var(--accent)", textDecoration: "none", fontFamily: "monospace", fontSize: "0.6875rem" }}>
                        {opp.opportunity_id.slice(0, 16)}
                      </Link>
                    </td>
                    <td style={{ padding: "0.5rem 0.65rem" }}>
                      <Link href={`/customers/${opp.customer_id}`} style={{ color: "var(--accent)", textDecoration: "none", fontSize: "0.6875rem" }}>
                        {opp.customer_name || opp.customer_id}
                      </Link>
                    </td>
                    <td style={{ padding: "0.5rem 0.65rem", fontFamily: "monospace", color: "#ef4444" }}>
                      {fmt(opp.amount_at_risk_minor)}
                    </td>
                    <td style={{ padding: "0.5rem 0.65rem" }}>
                      <span style={{
                        fontSize: "0.625rem", fontWeight: 600, padding: "1px 6px", borderRadius: 3,
                        background: opp.policy_state === "SUPPRESSED_SYSTEMIC" ? "rgba(245,158,11,0.12)" : "rgba(16,185,129,0.1)",
                        color: opp.policy_state === "SUPPRESSED_SYSTEMIC" ? "#f59e0b" : "#10b981",
                      }}>
                        {opp.policy_state === "SUPPRESSED_SYSTEMIC" ? "WAIT" : opp.current_status}
                      </span>
                    </td>
                    <td style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontSize: "0.6875rem" }}>
                      {opp.incident_relationship}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* INCIDENT TIMELINE */}
      {timeline.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div style={{
            fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)",
            textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem",
          }}>
            Incident Timeline
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {timeline.map((evt, idx) => (
              <div key={idx} style={{
                display: "flex", gap: "0.875rem", padding: "0.625rem 0.875rem",
                background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)",
                fontSize: "0.75rem", alignItems: "center",
              }}>
                <span style={{ color: "var(--text-muted)", fontFamily: "monospace", fontSize: "0.625rem", flexShrink: 0, minWidth: 80 }}>
                  {new Date(evt.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{evt.event}</span>
                <span style={{ color: "var(--text-muted)" }}>—</span>
                <span style={{ color: "var(--text-secondary)" }}>{evt.reason || evt.action}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
