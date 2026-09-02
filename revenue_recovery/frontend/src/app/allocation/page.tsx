"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { api, DashboardSummary, OpportunityItem, CapitalProtected } from "@/lib/api";

type Opportunity = OpportunityItem;
type PortfolioSummary = DashboardSummary;

const ACTION_META: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  send_payment_link: { label: "ACT — Payment Link", color: "#10b981", bg: "rgba(16,185,129,0.08)", icon: "→" },
  retry_payment: { label: "ACT — Retry Payment", color: "#3b82f6", bg: "rgba(59,130,246,0.08)", icon: "↻" },
  send_reminder: { label: "ACT — Send Reminder", color: "#f59e0b", bg: "rgba(245,158,11,0.08)", icon: "✉" },
  escalate_human: { label: "ESCALATE", color: "#6366f1", bg: "rgba(99,102,241,0.08)", icon: "⚑" },
  stop_recovery: { label: "SUPPRESS / NO_ACTION", color: "#ef4444", bg: "rgba(239,68,68,0.08)", icon: "■" },
  wait: { label: "WAIT", color: "#64748b", bg: "rgba(100,116,139,0.08)", icon: "◷" },
};

export default function Allocation() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [capital, setCapital] = useState<CapitalProtected | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.portfolioNextBestActions().catch(() => [] as Opportunity[]),
      api.summary().catch(() => null as PortfolioSummary | null),
      api.capitalProtected().catch(() => null as CapitalProtected | null),
    ]).then(([opps, summ, cap]) => {
      setOpportunities(opps || []);
      setSummary(summ);
      setCapital(cap);
      setLoading(false);
    }).catch((e) => {
      setError(e instanceof Error ? e.message : "Failed to load portfolio data");
      setLoading(false);
    });
  }, []);

  const fmt = (n: number) => "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  const fmtPct = (n: number) => `${(n * 100).toFixed(1)}%`;

  const totalAtRisk = useMemo(() => {
    if (summary?.revenue_at_risk) return summary.revenue_at_risk;
    return opportunities.reduce((s, o) => s + o.amount_at_risk_minor, 0);
  }, [summary, opportunities]);

  const totalExpectedNet = useMemo(() => {
    return opportunities.reduce((s, o) => s + o.expected_net_recovery_minor, 0);
  }, [opportunities]);

  const actionCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    opportunities.forEach((o) => {
      counts[o.action] = (counts[o.action] || 0) + 1;
    });
    return counts;
  }, [opportunities]);

  const filtered = useMemo(() => {
    if (filter === "all") return opportunities;
    return opportunities.filter((o) => o.action === filter);
  }, [opportunities, filter]);

  if (loading) {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>Recovery Capital Allocation</h1>
        <div className="card" style={{ padding: "3rem", textAlign: "center", marginTop: "1.5rem" }}>
          <div style={{ fontSize: "0.875rem", fontWeight: 600 }}>Loading portfolio...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>Recovery Capital Allocation</h1>
        <div className="card" style={{ padding: "1rem", marginTop: "1.5rem", background: "var(--danger-subtle)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.8125rem", fontWeight: 600 }}>{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: 4 }}>
          <span className="badge-info" style={{ fontSize: "0.625rem", padding: "0.1rem 0.4rem", borderRadius: 4, textTransform: "uppercase", fontWeight: 700 }}>
            LIVE OPERATIONAL
          </span>
        </div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>Recovery Capital Allocation</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4, maxWidth: 700 }}>
          Given limited intervention capacity, RecoverOS allocates effort to the highest safe expected net recovery opportunities first. Every number is derived from persisted case records.
        </p>
      </div>

      {/* TOP-LEVEL FINANCIAL SUMMARY */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <div className="metric-block" style={{ padding: "1.125rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--danger)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.25rem" }}>Total Revenue at Risk</div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--danger)", lineHeight: 1 }}>{fmt(totalAtRisk)}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>{opportunities.length} open opportunities</div>
        </div>
        <div className="metric-block" style={{ padding: "1.125rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.25rem" }}>Expected Net Recovery</div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--accent)", lineHeight: 1 }}>{fmt(totalExpectedNet)}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>Sum of ranked opportunities</div>
        </div>
        <div className="metric-block" style={{ padding: "1.125rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.25rem" }}>Capital Protected</div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--text-secondary)", lineHeight: 1 }}>{capital ? fmt(capital.total_capital_protected_minor) : "₹0"}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>{capital?.case_count || 0} cases suppressed</div>
        </div>
      </div>

      {/* ACTION FILTERS */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginRight: "0.5rem" }}>Filter:</span>
          <button
            onClick={() => setFilter("all")}
            style={{
              fontSize: "0.75rem", padding: "0.35rem 0.75rem", borderRadius: 6, border: filter === "all" ? "1px solid var(--accent)" : "1px solid var(--border)",
              background: filter === "all" ? "rgba(99,102,241,0.12)" : "var(--bg-secondary)", color: filter === "all" ? "var(--accent)" : "var(--text-primary)", cursor: "pointer", fontWeight: 600
            }}
          >All ({opportunities.length})</button>
          {Object.entries(actionCounts).map(([action, count]) => {
            const meta = ACTION_META[action] || { label: action, color: "var(--text-muted)", bg: "var(--bg-secondary)", icon: "•" };
            return (
              <button
                key={action}
                onClick={() => setFilter(action)}
                style={{
                  fontSize: "0.75rem", padding: "0.35rem 0.75rem", borderRadius: 6,
                  border: filter === action ? `1px solid ${meta.color}` : "1px solid var(--border)",
                  background: filter === action ? meta.bg : "var(--bg-secondary)",
                  color: filter === action ? meta.color : "var(--text-primary)", cursor: "pointer", fontWeight: 600
                }}
              >{meta.label} ({count})</button>
            );
          })}
        </div>
      </div>

      {/* PRIORITIZED OPPORTUNITIES LIST */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
          Prioritized Opportunities — Ranked by Expected Net Recovery
        </div>
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {filtered.length === 0 ? (
            <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
              No open recovery opportunities. Import or create cases to see allocation recommendations.
            </div>
          ) : (
            filtered.map((opp) => {
              const meta = ACTION_META[opp.action] || { label: opp.action, color: "var(--text-muted)", bg: "var(--bg-secondary)", icon: "•" };
              const isExpanded = expandedId === opp.item_id;
              const efficiency = opp.amount_at_risk_minor > 0 ? (opp.expected_net_recovery_minor / opp.amount_at_risk_minor) : 0;
              return (
                <div
                  key={opp.item_id}
                  style={{
                    padding: "0.875rem 1rem", borderRadius: 8, background: "var(--bg-secondary)", border: `1px solid ${isExpanded ? meta.color + "60" : "var(--border)"}`,
                    cursor: "pointer", transition: "border-color 0.15s"
                  }}
                  onClick={() => setExpandedId(isExpanded ? null : opp.item_id)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, minWidth: 0 }}>
                      <span className="font-mono" style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", minWidth: 24 }}>#{opp.rank}</span>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {opp.customer_name || opp.customer_id}
                        </div>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }} className="font-mono">
                          {opp.item_id} · {opp.action_label || opp.action}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>At Risk</div>
                        <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--danger)" }}>{fmt(opp.amount_at_risk_minor)}</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Expected Net</div>
                        <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--accent)" }}>{fmt(opp.expected_net_recovery_minor)}</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Efficiency</div>
                        <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, color: efficiency > 0 ? "var(--success)" : "var(--text-muted)" }}>{fmtPct(efficiency)}</div>
                      </div>
                      <span style={{
                        fontSize: "0.75rem", fontWeight: 700, padding: "0.25rem 0.6rem", borderRadius: 6,
                        background: meta.bg, color: meta.color, border: `1px solid ${meta.color}30`, whiteSpace: "nowrap"
                      }}>
                        {meta.icon} {meta.label}
                      </span>
                      <span style={{
                        fontSize: "0.625rem", fontWeight: 700, padding: "0.15rem 0.4rem", borderRadius: 4,
                        background: opp.urgency === "HIGH" ? "rgba(239,68,68,0.12)" : opp.urgency === "MEDIUM" ? "rgba(245,158,11,0.12)" : "rgba(100,116,139,0.12)",
                        color: opp.urgency === "HIGH" ? "#ef4444" : opp.urgency === "MEDIUM" ? "#f59e0b" : "#64748b",
                        border: `1px solid ${opp.urgency === "HIGH" ? "rgba(239,68,68,0.3)" : opp.urgency === "MEDIUM" ? "rgba(245,158,11,0.3)" : "rgba(100,116,139,0.3)"}`
                      }}>
                        {opp.urgency}
                      </span>
        </div>
      </div>

      {/* CROSS-REFERENCES */}
      <div style={{ padding: "0.875rem 1.25rem", display: "flex", gap: "1rem", alignItems: "center", justifyContent: "space-between", borderLeft: "4px solid var(--accent)", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
          <strong style={{ color: "var(--text-primary)" }}>Related surfaces:</strong> Batch Results shows per-case evaluation outcomes · Proof Lab shows scientific benchmark
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link href="/batch-recovery" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>Batch Results →</Link>
          <Link href="/proof-lab" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>Proof Lab →</Link>
        </div>
      </div>
                  {isExpanded && (
                    <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.5rem" }}>
                        {opp.reason}
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem", fontSize: "0.75rem" }}>
                        <div>
                          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Amount at Risk</div>
                          <div className="font-mono" style={{ fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>{fmt(opp.amount_at_risk_minor)}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Expected Net Recovery</div>
                          <div className="font-mono" style={{ fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>{fmt(opp.expected_net_recovery_minor)}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Recommended Action</div>
                          <div className="font-mono" style={{ fontWeight: 700, color: meta.color, marginTop: 2 }}>{opp.action_label}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* PORTFOLIO INSIGHT */}
      <div className="card" style={{ padding: "1.25rem", borderLeft: "4px solid #6366f1" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>Portfolio Insight</div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          RecoverOS prioritized these {opportunities.length} cases because they offer the highest safe expected net recovery under current intervention constraints. NO_ACTION and SUPPRESS decisions are explicit — they reflect negative expected value or policy blocks, not processing failures.
        </div>
      </div>
    </div>
  );
}
