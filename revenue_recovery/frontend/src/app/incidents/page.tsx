"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, IncidentSummary, Incident } from "@/lib/api";
import DecisionBadge from "@/components/shared/DecisionBadge";

type FilterKey = "all" | "active" | "recovering" | "waiting" | "escalated" | "resolved";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "waiting", label: "Waiting" },
  { key: "recovering", label: "Recovering" },
  { key: "escalated", label: "Escalated" },
  { key: "resolved", label: "Resolved" },
];

const fmt = (minor: number) =>
  "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

const SEVERITY_META: Record<string, { color: string; bg: string; border: string }> = {
  CRITICAL: { color: "#ef4444", bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.4)" },
  HIGH: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.4)" },
  MEDIUM: { color: "#3b82f6", bg: "rgba(59,130,246,0.12)", border: "rgba(59,130,246,0.4)" },
  LOW: { color: "#64748b", bg: "rgba(100,116,139,0.1)", border: "rgba(100,116,139,0.3)" },
};

function IncidentCard({ inc, onResolve }: { inc: Incident; onResolve: (id: string) => void }) {
  const sevMeta = SEVERITY_META[inc.severity] || SEVERITY_META.MEDIUM;
  const isResolving = false;

  return (
    <div className="card" style={{ padding: "1.25rem 1.5rem", borderLeft: `4px solid ${sevMeta.color}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.875rem" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap", marginBottom: "0.35rem" }}>
            <span style={{
              fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
              background: sevMeta.bg, color: sevMeta.color, border: `1px solid ${sevMeta.border}`,
            }}>
              {inc.severity}
            </span>
            <DecisionBadge decision={inc.decision as any} compact />
            <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              {inc.incident_id}
            </span>
          </div>
          <Link href={`/incidents/${inc.incident_id}`} style={{ textDecoration: "none", color: "inherit" }}>
            <h2 style={{ fontSize: "1.0625rem", fontWeight: 700, lineHeight: 1.3, cursor: "pointer" }}>
              {inc.title}
            </h2>
          </Link>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            {inc.payment_method} &middot; {inc.failure_category.replace(/_/g, " ")} &middot; {inc.gateway}
          </div>
        </div>
        <button
          className="btn-primary"
          onClick={() => onResolve(inc.incident_id)}
          disabled={isResolving}
          style={{
            fontSize: "0.75rem", padding: "0.45rem 0.875rem", background: "#10b981", color: "#fff",
            border: "none", cursor: "pointer", borderRadius: 6, fontWeight: 700, whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          {isResolving ? "Resolving..." : "Resolve"}
        </button>
      </div>

      {/* Financial strip */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.875rem",
        background: "var(--bg-primary)", padding: "0.875rem", borderRadius: 8,
        border: "1px solid var(--border)", marginBottom: "0.875rem",
      }}>
        <div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>Revenue at Risk</div>
          <div style={{ fontSize: "1.0625rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", marginTop: 2 }}>
            {fmt(inc.amount_at_risk_minor)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>Expected Recovery</div>
          <div style={{ fontSize: "1.0625rem", fontWeight: 700, color: "#f59e0b", fontFamily: "monospace", marginTop: 2 }}>
            {fmt(inc.estimated_recoverable_minor)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>Protected by Waiting</div>
          <div style={{ fontSize: "1.0625rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace", marginTop: 2 }}>
            {fmt(inc.revenue_protected_by_waiting_minor)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>Affected</div>
          <div style={{ fontSize: "1.0625rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace", marginTop: 2 }}>
            {inc.affected_customers_count} customers
          </div>
        </div>
      </div>

      {/* Evidence */}
      <div style={{
        background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)",
        padding: "0.65rem 0.875rem", borderRadius: 6, fontSize: "0.75rem", color: "var(--text-secondary)",
      }}>
        <strong style={{ color: "#f59e0b" }}>Detection:</strong> {inc.decision_reason || inc.reason}
        {inc.lift_vs_baseline > 0 && (
          <span style={{ marginLeft: "0.5rem", color: "var(--text-muted)" }}>
            ({inc.lift_vs_baseline}x baseline spike)
          </span>
        )}
      </div>
    </div>
  );
}

export default function IncidentsPage() {
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const loadData = useCallback(() => {
    setStatus("loading");
    Promise.all([api.incidents(), api.incidentActive()])
      .then(([s, incs]) => {
        setSummary(s);
        setIncidents(Array.isArray(incs) ? incs : []);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleResolve = async (id: string) => {
    setResolvingId(id);
    try {
      await api.resolveIncident(id);
      loadData();
    } catch {
      // Silent fail — user can retry
    } finally {
      setResolvingId(null);
    }
  };

  const filteredIncidents = incidents.filter((inc) => {
    if (filter === "all") return true;
    if (filter === "active") return inc.status === "ACTIVE";
    if (filter === "waiting") return inc.decision === "WAIT";
    if (filter === "recovering") return inc.decision === "RECOVER";
    if (filter === "escalated") return inc.decision === "ESCALATE";
    if (filter === "resolved") return inc.status === "RESOLVED" || inc.resolved_at;
    return true;
  });

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 90 }} />)}
        </div>
        <div className="skeleton" style={{ height: 200 }} />
      </div>
    );
  }

  if (status === "error" || !summary) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>
          Unable to load revenue incident control plane.
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "flex-end",
        marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem",
      }}>
        <div>
          <div style={{
            fontSize: "0.625rem", fontWeight: 700, color: "#f59e0b",
            textTransform: "uppercase", letterSpacing: "0.08em",
          }}>
            Revenue Incident Control Plane
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Systemic Revenue Incidents
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Detect patterns &middot; Protect the portfolio &middot; Recover safely &middot; Prove the money
          </div>
        </div>
        <Link href="/activity" className="btn-secondary" style={{
          fontSize: "0.75rem", padding: "0.45rem 0.875rem", textDecoration: "none",
          border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-secondary)", fontWeight: 600,
        }}>
          View Decision Stream
        </Link>
      </div>

      {/* KPI METRICS */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem",
      }}>
        <div className="metric-block" style={{ borderLeft: "3px solid #ef4444" }}>
          <div className="metric-label">Active Incidents</div>
          <div className="metric-value" style={{ color: "#ef4444" }}>{summary.active_incidents_count}</div>
        </div>
        <div className="metric-block" style={{ borderLeft: "3px solid #f59e0b" }}>
          <div className="metric-label">Revenue at Risk</div>
          <div className="metric-value" style={{ color: "#f59e0b" }}>{fmt(summary.total_revenue_at_risk_minor)}</div>
        </div>
        <div className="metric-block" style={{ borderLeft: "3px solid #10b981" }}>
          <div className="metric-label">Protected by Waiting</div>
          <div className="metric-value" style={{ color: "#10b981" }}>{fmt(summary.revenue_protected_by_waiting_minor)}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
            {summary.suppressed_actions_count} actions suppressed
          </div>
        </div>
        <div className="metric-block" style={{ borderLeft: "3px solid #6366f1" }}>
          <div className="metric-label">Affected Customers</div>
          <div className="metric-value">{summary.total_affected_customers}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
            {summary.resumed_cases_count} cases resumed
          </div>
        </div>
      </div>

      {/* FILTERS */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              fontSize: "0.6875rem", fontWeight: 600, padding: "0.35rem 0.75px",
              borderRadius: 5, border: `1px solid ${filter === f.key ? "var(--accent)" : "var(--border)"}`,
              background: filter === f.key ? "rgba(99,102,241,0.1)" : "var(--bg-primary)",
              color: filter === f.key ? "var(--accent)" : "var(--text-secondary)",
              cursor: "pointer",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* INCIDENT LIST */}
      {filteredIncidents.length === 0 ? (
        <div style={{
          padding: "3rem 2rem", textAlign: "center", background: "var(--bg-secondary)",
          borderRadius: 10, border: "1px solid var(--border)",
        }}>
          <div style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>✓</div>
          <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
            {incidents.length === 0
              ? "No systemic revenue incidents detected"
              : "No incidents match the current filter"}
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", maxWidth: 500, margin: "0 auto", lineHeight: 1.5 }}>
            {incidents.length === 0
              ? "RevPlug continuously monitors for concentration patterns across payment methods, failure categories, and providers. When a systemic condition is detected, it will appear here with a bounded decision and financial impact assessment."
              : "Try a different filter to see other incidents."}
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {filteredIncidents.map((inc) => (
            <IncidentCard key={inc.incident_id} inc={inc} onResolve={handleResolve} />
          ))}
        </div>
      )}
    </div>
  );
}
