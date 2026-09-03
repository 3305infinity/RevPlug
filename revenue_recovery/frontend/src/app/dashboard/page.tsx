"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, DashboardSummary, RecoveryItem, DecisionStreamEvent, DecisionDistribution, IncidentSummary, PromiseSummary } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import DecisionBadge from "@/components/shared/DecisionBadge";

type Status = "loading" | "error" | "ready";

function fmt(n: number) {
  return "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtDate(iso: string) {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function fmtTime(iso: string) {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

const ACTIVITY_ACTION_LABELS: Record<string, string> = {
  failure_classified: "Failure classified",
  recovery_item_created: "Opportunity created",
  recovery_scored: "Recovery scored",
  guard_evaluate: "Policy gate evaluated",
  execution_requested: "Action executed",
  recovery_stopped: "Recovery stopped",
  escalation_created: "Escalation created",
  settlement_verified: "Settlement verified",
  case_cleared: "Case cleared",
  agent_proposal_created: "Agent proposal created",
  immediate_success_termination: "Payment succeeded",
};

function ActivityActionLabel(action: string): string {
  return ACTIVITY_ACTION_LABELS[action] || action.replace(/_/g, " ");
}

export default function OperationsDashboard() {
  const [status, setStatus] = useState<Status>("loading");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [attribution, setAttribution] = useState<any>(null);
  const [activity, setActivity] = useState<DecisionStreamEvent[]>([]);
  const [decisions, setDecisions] = useState<Record<string, DecisionDistribution> | null>(null);
  const [incidents, setIncidents] = useState<IncidentSummary | null>(null);
  const [promiseSummary, setPromiseSummary] = useState<PromiseSummary | null>(null);
  const [strategyReport, setStrategyReport] = useState<{ strategies: Array<{ label: string; verified_recovered_minor: number; verified_recovery_rate_pct: number; evidence_level: string; explanation: string }>; what_works: Array<{ label: string; explanation: string }> } | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const [s, i, a, act, dec, inc, ps, strat] = await Promise.all([
        api.summary(),
        api.items(),
        (api as any).recoveryAttribution ? (api as any).recoveryAttribution() : Promise.resolve(null),
        api.decisionStream().catch(() => ({ events: [] as DecisionStreamEvent[], summary: null })),
        api.dashboardDecisions().catch(() => null as Record<string, DecisionDistribution> | null),
        api.incidents().catch(() => null as IncidentSummary | null),
        api.promiseSummary().catch(() => null as PromiseSummary | null),
        fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/strategy-analytics`).then(r => r.json()).catch(() => null),
      ]);
      setSummary(s);
      setItems(i);
      setAttribution(a);
      setActivity(act?.events?.slice(0, 8) || []);
      setDecisions(dec);
      setIncidents(inc);
      setPromiseSummary(ps);
      setStrategyReport(strat);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Escalated items for Needs Attention
  const attentionItems = useMemo(() =>
    items
      .filter(i => i.status === "escalated" || i.status === "intervention_pending")
      .sort((a, b) => b.amount_minor - a.amount_minor)
      .slice(0, 5),
    [items]
  );

  // Next best recovery: highest expected net from actionable items
  const nextBestRecovery = useMemo(() => {
    const actionable = items.filter(i =>
      !["recovered", "stopped"].includes(i.status) &&
      i.expected_recovery_value && i.expected_recovery_value > 0
    );
    if (actionable.length === 0) return null;
    return actionable.sort((a, b) => (b.expected_recovery_value || 0) - (a.expected_recovery_value || 0))[0];
  }, [items]);

  if (status === "error") {
    return (
      <div style={{ padding: "3rem 1.5rem", maxWidth: 600, margin: "0 auto", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          RECOVERY ENGINE UNREACHABLE
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1rem" }}>
          {error || "API server is offline."}
        </p>
        <button onClick={load} className="btn-primary">Retry Connection</button>
      </div>
    );
  }

  if (status === "loading" || !summary) {
    return (
      <div style={{ maxWidth: 1140, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 56, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 88 }} />)}
        </div>
        <div className="skeleton" style={{ height: 36, marginBottom: "1.5rem" }} />
        <div className="skeleton" style={{ height: 280 }} />
      </div>
    );
  }

  const totalAtRisk = summary.revenue_at_risk || 0;
  const expectedRecovery = summary.expected_recovery || 0;
  const verifiedRecovered = summary.actually_recovered || 0;
  const needsAttentionCount = attentionItems.length;
  const waitingCount = decisions?.WAIT?.count || 0;
  const waitingValue = decisions?.WAIT?.total_at_risk || 0;
  const stoppedCount = decisions?.STOP?.count || 0;
  const stoppedValue = decisions?.STOP?.total_at_risk || 0;
  const actionableOpportunities = items.filter((i) => !["recovered", "stopped"].includes(i.status)).length;

  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", paddingBottom: "3rem" }}>

      {/* ── HEADER ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "0.875rem" }}>
        <div>
          <h1 style={{ fontSize: "1.375rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Revenue Recovery Command Center
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
            Policy-bounded recovery · Settlement-verified
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.625rem", alignItems: "center" }}>
          <Link href="/review" className="btn-primary" style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem" }}>
            Review Queue {needsAttentionCount > 0 ? `(${needsAttentionCount})` : ""}
          </Link>
        </div>
      </div>

      {/* ── PRIMARY FINANCIAL SUMMARY ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #ef4444" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
            Revenue at Risk
          </div>
          <div className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 800, color: "#ef4444", letterSpacing: "-0.02em" }}>
            {fmt(totalAtRisk)}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            {actionableOpportunities} actionable opportunities
          </div>
        </div>

        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #6366f1" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
            Expected Recovery
          </div>
          <div className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 800, color: "#6366f1", letterSpacing: "-0.02em" }}>
            {expectedRecovery > 0 ? fmt(expectedRecovery) : "—"}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            Projected from Net EV scoring
          </div>
        </div>

        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #10b981" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
            Verified Recovered
          </div>
          <div className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 800, color: "#10b981", letterSpacing: "-0.02em" }}>
            {verifiedRecovered > 0 ? fmt(verifiedRecovered) : "—"}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            Settlement-confirmed funds
          </div>
        </div>

        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #f59e0b" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
            Cases Needing Attention
          </div>
          <div className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 800, color: "#f59e0b", letterSpacing: "-0.02em" }}>
            {needsAttentionCount}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            Escalated or pending review
          </div>
        </div>
      </div>

      {/* ── INCIDENT SUMMARY ── */}
      {incidents && incidents.active_incidents_count > 0 && (
        <div style={{
          display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap",
          padding: "0.875rem 1.25rem", background: "var(--bg-secondary)", borderRadius: 8,
          border: "1px solid rgba(245,158,11,0.3)", marginBottom: "1.5rem",
        }}>
          <span style={{
            fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
            background: "rgba(245,158,11,0.15)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.4)",
          }}>
            {incidents.active_incidents_count} ACTIVE INCIDENT{incidents.active_incidents_count > 1 ? "S" : ""}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", flex: 1 }}>
            <strong style={{ color: "#f59e0b" }}>{fmt(incidents.total_revenue_at_risk_minor)}</strong> at risk across {incidents.total_affected_customers} customers &middot; {fmt(incidents.revenue_protected_by_waiting_minor)} protected by waiting
          </span>
          <Link href="/incidents" style={{
            fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b",
            textDecoration: "none", padding: "0.3rem 0.65rem", borderRadius: 4,
            border: "1px solid rgba(245,158,11,0.4)", background: "rgba(245,158,11,0.08)",
          }}>
            View Incidents →
          </Link>
        </div>
      )}

      {/* ── PROMISE SUMMARY ── */}
      {promiseSummary && promiseSummary.active_count > 0 && (
        <div style={{
          display: "flex", alignItems: "center", gap: "1.5rem", flexWrap: "wrap",
          padding: "0.875rem 1.25rem", background: "rgba(59,130,246,0.04)", borderRadius: 8,
          border: "1px solid rgba(59,130,246,0.15)", marginBottom: "1.5rem",
        }}>
          <span style={{
            fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
            background: "rgba(59,130,246,0.12)", color: "#3b82f6", border: "1px solid rgba(59,130,246,0.3)",
          }}>
            {promiseSummary.active_count} ACTIVE COMMITMENT{promiseSummary.active_count > 1 ? "S" : ""}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            <strong style={{ color: "#3b82f6" }}>{fmt(promiseSummary.committed_amount_minor)}</strong> committed
          </span>
          {promiseSummary.due_soon_count > 0 && (
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              &middot; <strong style={{ color: "#f59e0b" }}>{promiseSummary.due_soon_count}</strong> due soon
            </span>
          )}
          {promiseSummary.fulfilled_count > 0 && (
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              &middot; <strong style={{ color: "#10b981" }}>{promiseSummary.fulfilled_count}</strong> fulfilled ({fmt(promiseSummary.fulfilled_amount_minor)} settled)
            </span>
          )}
          <Link href="/recovery" style={{
            fontSize: "0.6875rem", fontWeight: 700, color: "#3b82f6",
            textDecoration: "none", padding: "0.3rem 0.65rem", borderRadius: 4,
            border: "1px solid rgba(59,130,246,0.3)", background: "rgba(59,130,246,0.06)",
          }}>
            View Cases →
          </Link>
        </div>
      )}

      {/* ── NEXT BEST RECOVERY ── */}
      {nextBestRecovery && (
        <div style={{ padding: "1.25rem 1.5rem", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
            <div style={{ flex: 1, minWidth: 280 }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
                Next Recovery
              </div>
              <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
                {getCustomerDisplayName(nextBestRecovery.customer_id, (nextBestRecovery as any).customer_name)}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: 12 }}>
                {nextBestRecovery.root_cause?.replace(/_/g, " ") || "Revenue at risk"}
              </div>
              <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>At Risk</div>
                  <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "#ef4444" }}>{fmt(nextBestRecovery.amount_minor)}</div>
                </div>
                <div>
                  <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Expected Net</div>
                  <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "#10b981" }}>{fmt(nextBestRecovery.expected_recovery_value || 0)}</div>
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <Link href={`/recovery/${nextBestRecovery.id}`} className="btn-primary" style={{ fontSize: "0.8125rem", padding: "0.5rem 1rem" }}>
                Review case →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ── RECOVERY DECISIONS + MONEY FLOW ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>

        {/* Recovery Decisions Distribution */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem" }}>
            Decisions
          </div>
          {decisions ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {(["RECOVER", "WAIT", "ESCALATE", "STOP"] as const).map((d) => {
                const data = decisions[d];
                if (!data || data.count === 0) return null;
                return (
                  <div key={d} style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <div style={{ width: 90 }}>
                      <DecisionBadge decision={d} compact />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
                        {data.count} {data.count === 1 ? "case" : "cases"}
                      </div>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                        {fmt(data.total_at_risk)} at risk
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                        {fmt(data.total_expected)}
                      </div>
                      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>expected</div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>No decision data available</div>
          )}
        </div>

        {/* Money Flow Funnel */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem" }}>
            Money Flow
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <FunnelStage label="At Risk" value={totalAtRisk} color="#ef4444" />
            <FunnelArrow />
            <FunnelStage label="Expected Recovery" value={expectedRecovery} color="#6366f1" sublabel="Projected" />
            <FunnelArrow />
            <FunnelStage label="Verified Recovered" value={verifiedRecovered} color="#10b981" sublabel="Settlement confirmed" />
          </div>
          <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border)", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Waiting</div>
              <div className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 700, color: "#64748b" }}>{waitingCount} ({fmt(waitingValue)})</div>
            </div>
            <div>
              <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Stopped</div>
              <div className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 700, color: "#ef4444" }}>{stoppedCount} ({fmt(stoppedValue)})</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── NEEDS ATTENTION + ACTIVITY ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>

        {/* Needs Attention */}
        <div className="card" style={{ padding: "1.25rem", borderLeft: `3px solid ${needsAttentionCount > 0 ? "#f59e0b" : "var(--border)"}` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.875rem" }}>
            <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Needs Attention
            </div>
            <Link href="/review" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
              Review Queue →
            </Link>
          </div>
          {attentionItems.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "1rem 0" }}>
              No cases require human review
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {attentionItems.map(item => (
                <div key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.625rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {getCustomerDisplayName(item.customer_id, (item as any).customer_name)}
                    </div>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                      {item.root_cause?.replace(/_/g, " ") || "Requires review"}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginLeft: "0.75rem" }}>
                    <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#ef4444" }}>{fmt(item.amount_minor)}</div>
                    <Link href={`/recovery/${item.id}`} className="btn-secondary" style={{ fontSize: "0.6875rem", padding: "0.3rem 0.6rem" }}>
                      Review →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.875rem" }}>
            <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Recent Activity
            </div>
            <Link href="/activity" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
              View all activity →
            </Link>
          </div>
          {activity.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "1rem 0" }}>
              No recent activity
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem", maxHeight: 320, overflowY: "auto" }}>
              {activity.map(evt => (
                <Link key={evt.event_id} href={`/recovery/${evt.opportunity_id}`} style={{ textDecoration: "none" }}>
                  <div style={{ display: "flex", gap: "0.625rem", padding: "0.5rem 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: getActivityColor(evt.event_action), flexShrink: 0, marginTop: 5 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-primary)", fontWeight: 500 }}>
                        {evt.event_label}
                      </div>
                      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 1 }}>
                        {evt.opportunity_id.slice(0, 12)} · {fmt(evt.amount_at_risk_minor)}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <DecisionBadge decision={evt.decision as any} compact />
                      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", flexShrink: 0 }}>
                        {fmtDate(evt.timestamp)}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── TRUST STRIP ── */}
      <div style={{ padding: "0.75rem 0", marginBottom: "1.5rem", display: "flex", gap: "2rem", flexWrap: "wrap", fontSize: "0.75rem", color: "var(--text-secondary)", borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)" }}>
        <span><strong style={{ color: "#10b981" }}>Settlement-verified</strong> — money counted only after evidence</span>
        <span><strong style={{ color: "#6366f1" }}>Policy-bounded</strong> — server-side authority, not frontend state</span>
        <span><strong style={{ color: "#3b82f6" }}>Duplicate-safe</strong> — idempotent execution</span>
        <span><strong style={{ color: "#f59e0b" }}>Auditable</strong> — every decision produces a traceable record</span>
      </div>

      {/* ── ATTRIBUTION SUMMARY ── */}
      {attribution && attribution.total_recovered_minor > 0 && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid #6366f1" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Recovery Attribution
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Total Verified</div>
              <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "#10b981" }}>{fmt(attribution.total_recovered_minor)}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Agent-Attributed</div>
              <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "#3b82f6" }}>{fmt(attribution.agent_attributed_minor)}</div>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>{attribution.direct_agent_pct}%</div>
            </div>
            <div>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Agent-Assisted</div>
              <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "#6366f1" }}>{fmt(attribution.agent_assisted_minor)}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Organic</div>
              <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-secondary)" }}>{fmt(attribution.organic_recovered_minor)}</div>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>{attribution.organic_pct}%</div>
            </div>
          </div>
        </div>
      )}

      {/* ── QUICK LINKS ── */}
      <div style={{ display: "flex", justifyContent: "center", gap: "1.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
        <Link href="/batch-recovery" style={{ color: "var(--accent)" }}>Batch Results →</Link>
        <Link href="/proof-lab" style={{ color: "var(--accent)" }}>Benchmark →</Link>
      </div>
    </div>
  );
}

function FunnelStage({ label, value, color, sublabel }: { label: string; value: number; color: string; sublabel?: string }) {
  return (
    <div style={{ padding: "0.75rem 1rem", borderRadius: 6, background: `${color}08`, border: `1px solid ${color}25` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>{label}</span>
        <span className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color }}>{fmt(value)}</span>
      </div>
      {sublabel && <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 2 }}>{sublabel}</div>}
    </div>
  );
}

function FunnelArrow() {
  return (
    <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.75rem", lineHeight: 1 }}>↓</div>
  );
}

function getActivityColor(action: string): string {
  if (action.includes("verified") || action.includes("success") || action.includes("recovered")) return "#10b981";
  if (action.includes("stopped") || action.includes("block") || action.includes("denied")) return "#ef4444";
  if (action.includes("escalat")) return "#f59e0b";
  if (action.includes("execut") || action.includes("requested")) return "#3b82f6";
  return "#64748b";
}

function TrustItem({ icon, label, sublabel, color }: { icon: string; label: string; sublabel: string; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 140 }}>
      <span style={{ color, fontSize: "1rem" }}>{icon}</span>
      <div>
        <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-primary)" }}>{label}</div>
        <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)" }}>{sublabel}</div>
      </div>
    </div>
  );
}
