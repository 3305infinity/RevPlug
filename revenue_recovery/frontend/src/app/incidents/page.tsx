"use client";

import { useEffect, useState } from "react";

interface IncidentSummary {
  active_incidents_count: number;
  total_revenue_at_risk_minor: number;
  revenue_protected_by_waiting_minor: number;
  total_affected_customers: number;
  suppressed_actions_count: number;
  resumed_cases_count: number;
}

interface IncidentCluster {
  incident_id: string;
  gateway: string;
  payment_method: string;
  issuer_bank: string;
  failure_category: string;
  title: string;
  failure_rate_pct: number;
  baseline_failure_rate_pct: number;
  lift_vs_baseline: number;
  amount_at_risk_minor: number;
  affected_customers_count: number;
  estimated_recoverable_minor: number;
  revenue_protected_by_waiting_minor: number;
  status: string;
  recommendation: string;
  reason: string;
  created_at: string;
}

export default function IncidentsPage() {
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [incidents, setIncidents] = useState<IncidentCluster[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const loadData = () => {
    Promise.all([
      fetch(`${apiHost}/api/incidents/summary`).then((r) => r.json()),
      fetch(`${apiHost}/api/incidents/active`).then((r) => r.json()),
    ])
      .then(([s, incs]) => {
        setSummary(s);
        setIncidents(Array.isArray(incs) ? incs : (incs?.incidents || []));
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleResolve = (id: string) => {
    setResolvingId(id);
    fetch(`${apiHost}/api/incidents/${id}/resolve`, { method: "POST" })
      .then((r) => r.json())
      .then(() => {
        loadData();
      })
      .finally(() => setResolvingId(null));
  };

  const fmt = (minor: number) => "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 90 }} />)}
        </div>
      </div>
    );
  }

  if (status === "error" || !summary) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load incident control manager</div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            PORTFOLIO REVENUE INCIDENT CONTROL SYSTEM
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Systemic Payment Outage Incidents
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Automated cluster detection & policy suppression (RETRY → WAIT / HOLD) protecting customer trust and gateway EV
          </div>
        </div>
      </div>

      {/* KPI METRICS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="metric-block" style={{ borderLeft: "3px solid #ef4444" }}>
          <div className="metric-label">ACTIVE INCIDENTS</div>
          <div className="metric-value" style={{ color: "#ef4444" }}>{summary.active_incidents_count}</div>
        </div>

        <div className="metric-block" style={{ borderLeft: "3px solid #f59e0b" }}>
          <div className="metric-label">AFFECTED REVENUE</div>
          <div className="metric-value" style={{ color: "#f59e0b" }}>{fmt(summary.total_revenue_at_risk_minor)}</div>
        </div>

        <div className="metric-block" style={{ borderLeft: "3px solid #3b82f6" }}>
          <div className="metric-label">AFFECTED CUSTOMERS</div>
          <div className="metric-value">{summary.total_affected_customers}</div>
        </div>

        <div className="metric-block" style={{ borderLeft: "3px solid #10b981" }}>
          <div className="metric-label">ACTION SUPPRESSED</div>
          <div className="metric-value" style={{ color: "#10b981" }}>{summary.suppressed_actions_count}</div>
          <div style={{ fontSize: "0.75rem", color: "#10b981", marginTop: 2 }}>{fmt(summary.revenue_protected_by_waiting_minor)} protected</div>
        </div>

        <div className="metric-block" style={{ borderLeft: "3px solid var(--purple)" }}>
          <div className="metric-label">RECOVERY RESUMED</div>
          <div className="metric-value">{summary.resumed_cases_count}</div>
        </div>
      </div>

      {/* ACTIVE INCIDENTS LIST */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {(Array.isArray(incidents) ? incidents : []).map((inc) => (
          <div key={inc.incident_id} className="card" style={{ padding: "1.5rem", borderLeft: "4px solid #ef4444" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span style={{ fontSize: "0.6875rem", background: "rgba(239, 68, 68, 0.2)", color: "#ef4444", padding: "2px 8px", borderRadius: 4, fontWeight: 700, border: "1px solid rgba(239, 68, 68, 0.4)" }}>
                    SYSTEMIC INCIDENT DETECTED
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                    ID: {inc.incident_id}
                  </span>
                </div>
                <h2 style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: 4, color: "var(--text-primary)" }}>
                  {inc.title} ({inc.gateway} / {inc.payment_method})
                </h2>
              </div>
              <button
                className="btn-primary"
                onClick={() => handleResolve(inc.incident_id)}
                disabled={resolvingId === inc.incident_id}
                style={{ fontSize: "0.8125rem", padding: "0.5rem 1rem", background: "#10b981", color: "#fff", border: "none", cursor: "pointer", borderRadius: 6, fontWeight: 700 }}
              >
                {resolvingId === inc.incident_id ? "Resuming..." : "✓ Resolve & Resume Playbooks"}
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", background: "var(--bg-primary)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)", marginBottom: "1rem" }}>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>FAILURE RATE</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", marginTop: 2 }}>
                  {inc.failure_rate_pct}% <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>(Baseline: {inc.baseline_failure_rate_pct}%)</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>FAILURE LIFT</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f59e0b", fontFamily: "monospace", marginTop: 2 }}>
                  {inc.lift_vs_baseline}x Baseline Spike
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>AFFECTED CUSTOMERS</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace", marginTop: 2 }}>
                  {inc.affected_customers_count} customers
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>REVENUE AT RISK</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", marginTop: 2 }}>
                  {fmt(inc.amount_at_risk_minor)}
                </div>
              </div>
            </div>

            <div style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", padding: "0.85rem", borderRadius: 6 }}>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f59e0b" }}>
                RECOMMENDATION: {inc.recommendation}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                Reason: {inc.reason}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
