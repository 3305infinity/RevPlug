"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, DashboardSummary, RecoveryItem } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";

type Status = "loading" | "error" | "ready";

const STATUS_LABEL: Record<string, { label: string; color: string; bg: string }> = {
  detected:              { label: "Detected",      color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  diagnosed:             { label: "Diagnosed",     color: "#3b82f6", bg: "rgba(59,130,246,0.12)" },
  queued:                { label: "Queued",         color: "#6366f1", bg: "rgba(99,102,241,0.12)" },
  intervention_pending:  { label: "In Flight",     color: "#0ea5e9", bg: "rgba(14,165,233,0.12)" },
  intervention_executed: { label: "Executed",      color: "#10b981", bg: "rgba(16,185,129,0.12)" },
  pending_verification:  { label: "Verifying",     color: "#10b981", bg: "rgba(16,185,129,0.1)"  },
  recovered:             { label: "Verified",       color: "#10b981", bg: "rgba(16,185,129,0.15)" },
  stopped:               { label: "Stopped",       color: "#6b7280", bg: "rgba(107,114,128,0.12)" },
  escalated:             { label: "Needs Review",  color: "#f59e0b", bg: "rgba(245,158,11,0.15)" },
  failed:                { label: "Failed",         color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};

function fmt(n: number) {
  return "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_LABEL[status] || { label: status, color: "var(--text-muted)", bg: "transparent" };
  return (
    <span style={{
      fontSize: "0.6875rem", fontWeight: 700,
      color: s.color, background: s.bg,
      padding: "2px 7px", borderRadius: 4,
      textTransform: "uppercase", letterSpacing: "0.04em",
    }}>{s.label}</span>
  );
}

function DataBadge({ type }: { type: "evaluation" | "verified" | "projected" }) {
  const cfg = {
    evaluation: { label: "Evaluation Data",  color: "#d97706", border: "rgba(217,119,6,0.25)" },
    verified:   { label: "Provider Verified", color: "#10b981", border: "rgba(16,185,129,0.25)" },
    projected:  { label: "Projected",         color: "#6366f1", border: "rgba(99,102,241,0.25)" },
  }[type];
  return (
    <span style={{
      fontSize: "0.5rem", fontWeight: 700, color: cfg.color,
      border: `1px solid ${cfg.border}`, padding: "1px 5px",
      borderRadius: 3, letterSpacing: "0.05em", textTransform: "uppercase",
      verticalAlign: "middle", marginLeft: 6,
    }}>{cfg.label}</span>
  );
}

function PipelineBar({ summary }: { summary: DashboardSummary }) {
  const total = summary.total_items || 1;
  const atRisk = summary.active_recoveries || 0;
  const inFlight = (summary.executed_count || 0);
  const verified = summary.recovered_cases || 0;
  const stopped  = summary.stopped_cases || 0;

  const pct = (n: number) => Math.max(2, Math.round((n / total) * 100));

  const stages = [
    { label: "At Risk",   count: atRisk,   pct: pct(atRisk),   color: "#ef4444" },
    { label: "In Flight", count: inFlight, pct: pct(inFlight), color: "#3b82f6" },
    { label: "Verified",  count: verified, pct: pct(verified), color: "#10b981" },
    { label: "Stopped",   count: stopped,  pct: pct(stopped),  color: "#6b7280" },
  ];

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Recovery Pipeline
        </div>
        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
          {total} total cases
        </div>
      </div>
      {/* bar */}
      <div style={{ display: "flex", height: 8, borderRadius: 4, overflow: "hidden", gap: 1 }}>
        {stages.map(s => (
          <div key={s.label} style={{ flex: s.pct, background: s.color, minWidth: 4 }} title={`${s.label}: ${s.count}`} />
        ))}
      </div>
      {/* labels */}
      <div style={{ display: "flex", marginTop: "0.5rem", gap: "1.25rem" }}>
        {stages.map(s => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
            <span>{s.label}</span>
            <span style={{ fontFamily: "monospace", fontWeight: 700, color: "var(--text-primary)" }}>{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function OperationsDashboard() {
  const [status, setStatus]   = useState<Status>("loading");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [items, setItems]     = useState<RecoveryItem[]>([]);
  const [error, setError]     = useState<string | null>(null);
  const [attribution, setAttribution] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const [s, i, a] = await Promise.all([
        api.summary(),
        api.items(),
        (api as any).recoveryAttribution ? (api as any).recoveryAttribution() : Promise.resolve(null),
      ]);
      setSummary(s);
      setItems(i);
      setAttribution(a);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Attention-required: escalated + intervention_pending, sorted by amount descending
  const attentionItems = useMemo(() =>
    items
      .filter(i => i.status === "escalated" || i.status === "intervention_pending")
      .sort((a, b) => b.amount_minor - a.amount_minor)
      .slice(0, 5),
    [items]
  );

  // Recent verified recoveries
  const recentVerified = useMemo(() =>
    items
      .filter(i => i.status === "recovered")
      .sort((a, b) => b.amount_minor - a.amount_minor)
      .slice(0, 5),
    [items]
  );

  // Top active recovery opportunities
  const topOpportunities = useMemo(() =>
    items
      .filter(i => !["recovered", "stopped"].includes(i.status))
      .sort((a, b) => (b.expected_recovery_value || 0) - (a.expected_recovery_value || 0))
      .slice(0, 8),
    [items]
  );

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

  // Derived: baseline comparison — not computed from frontend.
  // The API does not currently provide a baseline metric; we never fabricate one here.
  // When a baseline endpoint is available, wire it to the "vs Baseline" card.
  // Data integrity fix: removed hard-coded `actually_recovered * 0.64` baseline formula.

  return (
    <div style={{ maxWidth: 1140, margin: "0 auto", paddingBottom: "3rem" }}>

      {/* ── HEADER ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.25rem", borderBottom: "1px solid var(--border)", paddingBottom: "0.875rem" }}>
        <div>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
            RevPlug · Revenue Recovery Control Plane
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.375rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Overview
          </h1>
        </div>
        <div style={{ display: "flex", gap: "0.625rem", alignItems: "center" }}>
          <Link href="/policy-config" className="btn-secondary" style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem" }}>
            Policy
          </Link>
          <Link href="/review" className="btn-primary" style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem" }}>
            Review Queue {attentionItems.length > 0 ? `(${attentionItems.length})` : ""}
          </Link>
        </div>
      </div>

      {/* ── CORE METRICS ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.25rem" }}>

        {/* Revenue at Risk */}
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #ef4444" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            Revenue at Risk
            <DataBadge type="evaluation" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "#ef4444" }}>
            {fmt(summary.revenue_at_risk)}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            {summary.active_recoveries} active cases
          </div>
        </div>

        {/* Verified Recovered */}
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #10b981" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            Verified Recovered
            <DataBadge type="verified" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "#10b981" }}>
            {summary.actually_recovered > 0 ? fmt(summary.actually_recovered) : "—"}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "#10b981", marginTop: 4 }}>
            {summary.actually_recovered > 0
              ? `${(summary.recovery_rate * 100).toFixed(1)}% recovery rate`
              : "No verified recoveries yet"}
          </div>
        </div>

        {/* Vs Baseline */}
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #6366f1" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            vs Baseline
            <DataBadge type="projected" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-muted)" }}>
            —
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            Awaiting verified recoveries
          </div>
        </div>

        {/* Needs Attention */}
        <div className="card" style={{ padding: "1.125rem", borderLeft: `3px solid ${attentionItems.length > 0 ? "#f59e0b" : "var(--border)"}` }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            Needs Attention
          </div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: attentionItems.length > 0 ? "#f59e0b" : "var(--text-muted)" }}>
            {attentionItems.length > 0 ? attentionItems.length : "0"}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            {attentionItems.length > 0
              ? `${attentionItems.length} case${attentionItems.length !== 1 ? "s" : ""} escalated / in-flight`
              : "No cases requiring attention"}
          </div>
        </div>
      </div>

      {/* ── RECOVERY PIPELINE ── */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem" }}>
        <PipelineBar summary={summary} />
      </div>

      {/* ── ATTRIBUTION SUMMARY ── */}
      {attribution && (
        <div className="card" style={{ padding: "1.125rem", marginBottom: "1.25rem", borderLeft: "3px solid #6366f1" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            Recovery Attribution
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Total Verified Recovery</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>{fmt(attribution.total_recovered_minor)}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Agent-Attributed</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#3b82f6", fontFamily: "monospace" }}>{fmt(attribution.agent_attributed_minor)}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>{attribution.direct_agent_pct}% of total</div>
            </div>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Agent-Assisted</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#6366f1", fontFamily: "monospace" }}>{fmt(attribution.agent_assisted_minor)}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Organic</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-secondary)", fontFamily: "monospace" }}>{fmt(attribution.organic_recovered_minor)}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>{attribution.organic_pct}% of total</div>
            </div>
          </div>
        </div>
      )}

      {/* ── ATTENTION REQUIRED ── */}
      {attentionItems.length > 0 && (
        <div className="card" style={{ padding: "1.125rem", marginBottom: "1.25rem", borderLeft: "3px solid #f59e0b" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.875rem" }}>
            <div>
              <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Attention Required
              </div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
                {attentionItems.length} case{attentionItems.length !== 1 ? "s" : ""} escalated or awaiting action
              </div>
            </div>
            <Link href="/review" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
              Open Review Queue →
            </Link>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ padding: "0.5rem 0.625rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.625rem", textTransform: "uppercase", textAlign: "left" }}>Customer</th>
                <th style={{ padding: "0.5rem 0.625rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.625rem", textTransform: "uppercase", textAlign: "right" }}>At Risk</th>
                <th style={{ padding: "0.5rem 0.625rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.625rem", textTransform: "uppercase", textAlign: "right" }}>Expected Net</th>
                <th style={{ padding: "0.5rem 0.625rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.625rem", textTransform: "uppercase", textAlign: "left" }}>Status</th>
                <th style={{ padding: "0.5rem 0.625rem" }}></th>
              </tr>
            </thead>
            <tbody>
              {attentionItems.map(item => (
                <tr key={item.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "0.625rem 0.625rem" }}>
                    <div style={{ fontWeight: 600 }}>{getCustomerDisplayName(item.customer_id, (item as any).customer_name)}</div>
                    <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{item.customer_id}</div>
                  </td>
                  <td style={{ padding: "0.625rem 0.625rem", fontFamily: "monospace", fontWeight: 700, textAlign: "right" }}>{fmt(item.amount_minor)}</td>
                  <td style={{ padding: "0.625rem 0.625rem", fontFamily: "monospace", textAlign: "right", color: item.expected_recovery_value ? "#10b981" : "var(--text-muted)" }}>
                    {item.expected_recovery_value ? fmt(item.expected_recovery_value) : "—"}
                  </td>
                  <td style={{ padding: "0.625rem 0.625rem" }}>
                    <StatusBadge status={item.status} />
                    {item.root_cause && (
                      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 2 }}>{item.root_cause}</div>
                    )}
                  </td>
                  <td style={{ padding: "0.625rem 0.625rem" }}>
                    <Link href={`/recovery/${item.id}`} className="btn-secondary" style={{ fontSize: "0.6875rem", padding: "0.3rem 0.6rem" }}>
                      Review →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── RECOVERY QUEUE: TOP OPPORTUNITIES ── */}
      <div className="card" style={{ padding: "1.125rem", marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.875rem" }}>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Primary Operating Surface
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
              Recovery Queue — Top Opportunities
            </div>
          </div>
          <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
            View All Cases →
          </Link>
        </div>

        {topOpportunities.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            No active recovery opportunities
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                <th style={{ padding: "0.625rem 0.625rem", color: "var(--text-muted)", fontSize: "0.625rem", textTransform: "uppercase", fontWeight: 600 }}>#</th>
                <th style={{ padding: "0.625rem 0.625rem", color: "var(--text-muted)", fontSize: "0.625rem", textTransform: "uppercase", fontWeight: 600 }}>Customer</th>
                <th style={{ padding: "0.625rem 0.625rem", color: "var(--text-muted)", fontSize: "0.625rem", textTransform: "uppercase", fontWeight: 600, textAlign: "right" }}>At Risk</th>
                <th style={{ padding: "0.625rem 0.625rem", color: "var(--text-muted)", fontSize: "0.625rem", textTransform: "uppercase", fontWeight: 600, textAlign: "right" }}>Expected Net</th>
                <th style={{ padding: "0.625rem 0.625rem", color: "var(--text-muted)", fontSize: "0.625rem", textTransform: "uppercase", fontWeight: 600 }}>Evidence</th>
                <th style={{ padding: "0.625rem 0.625rem", color: "var(--text-muted)", fontSize: "0.625rem", textTransform: "uppercase", fontWeight: 600 }}>Status</th>
                <th style={{ padding: "0.625rem 0.625rem" }}></th>
              </tr>
            </thead>
            <tbody>
              {topOpportunities.map((item, idx) => {
                const causeRaw = item.root_cause || "";
                let evidence = "Awaiting diagnosis";
                if (causeRaw.includes("hard") || causeRaw.includes("decline")) evidence = "Hard decline · Stop";
                else if (causeRaw.includes("fraud")) evidence = "Fraud flag · Blocked";
                else if (causeRaw.includes("auth") || causeRaw.includes("transient") || causeRaw.includes("timeout")) evidence = "Transient failure · Retry allowed";
                else if (causeRaw.includes("dispute")) evidence = "Dispute · Policy restricted";
                else if (causeRaw.includes("opt")) evidence = "Opt-out · Blocked";
                else if (causeRaw) evidence = causeRaw.replace(/_/g, " ");

                return (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.625rem 0.625rem", fontWeight: 700, color: "var(--text-muted)", fontFamily: "monospace", fontSize: "0.75rem" }}>
                      {idx + 1}
                    </td>
                    <td style={{ padding: "0.625rem 0.625rem" }}>
                      <div style={{ fontWeight: 600 }}>{getCustomerDisplayName(item.customer_id, (item as any).customer_name)}</div>
                      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{item.customer_id}</div>
                    </td>
                    <td style={{ padding: "0.625rem 0.625rem", fontFamily: "monospace", fontWeight: 700, textAlign: "right" }}>
                      {fmt(item.amount_minor)}
                    </td>
                    <td style={{ padding: "0.625rem 0.625rem", fontFamily: "monospace", textAlign: "right", color: item.expected_recovery_value ? "#10b981" : "var(--text-muted)", fontWeight: 700 }}>
                      {item.expected_recovery_value ? fmt(item.expected_recovery_value) : "—"}
                    </td>
                    <td style={{ padding: "0.625rem 0.625rem", color: "var(--text-secondary)", fontSize: "0.75rem", maxWidth: 200 }}>
                      {evidence}
                    </td>
                    <td style={{ padding: "0.625rem 0.625rem" }}>
                      <StatusBadge status={item.status} />
                    </td>
                    <td style={{ padding: "0.625rem 0.625rem" }}>
                      <Link href={`/recovery/${item.id}`} className="btn-secondary" style={{ fontSize: "0.6875rem", padding: "0.3rem 0.6rem" }}>
                        Case →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* ── BOTTOM ROW: RECENT VERIFIED + SYSTEM METRICS ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>

        {/* Recent Verified Recoveries */}
        <div className="card" style={{ padding: "1.125rem" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Recent Verified Recoveries <DataBadge type="verified" />
          </div>
          {recentVerified.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "1rem 0" }}>
              No verified recoveries yet
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
              {recentVerified.map(item => (
                <div key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.8125rem" }}>{getCustomerDisplayName(item.customer_id, (item as any).customer_name)}</div>
                    <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>{item.root_cause?.replace(/_/g, " ") || "—"}</div>
                  </div>
                  <div style={{ fontFamily: "monospace", fontWeight: 700, color: "#10b981", fontSize: "0.875rem" }}>
                    {fmt(item.amount_minor)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Agent Activity & Policy Summary */}
        <div className="card" style={{ padding: "1.125rem" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Agent Activity Summary
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            {[
              { label: "Analyzed",    value: summary.total_items,     color: "var(--text-primary)" },
              { label: "Recovered",   value: summary.recovered_cases,  color: "#10b981" },
              { label: "Escalated",   value: summary.escalated_cases,  color: "#f59e0b" },
              { label: "Stopped",     value: summary.stopped_cases,    color: "var(--text-muted)" },
              { label: "Policy Allowed", value: summary.policy_allowed ?? "—", color: "#10b981" },
              { label: "Policy Denied",  value: summary.policy_denied  ?? "—", color: "#ef4444" },
            ].map(m => (
              <div key={m.label} style={{ background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)", padding: "0.625rem" }}>
                <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>{m.label}</div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700, fontFamily: "monospace", color: m.color, marginTop: 2 }}>{m.value ?? "—"}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: "0.875rem", paddingTop: "0.875rem", borderTop: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              <Link href="/strategy-analytics" style={{ color: "var(--accent)" }}>Strategy Analytics →</Link>
              <Link href="/batch-recovery" style={{ color: "var(--accent)" }}>Evaluation Report →</Link>
              <Link href="/allocation" style={{ color: "var(--accent)", fontWeight: 700 }}>Recovery Capital Allocation →</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
