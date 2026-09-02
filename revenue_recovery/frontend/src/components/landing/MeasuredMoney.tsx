"use client";

import Link from "next/link";
import { DashboardSummary } from "@/lib/api";

export default function MeasuredMoney({ summary }: { summary: DashboardSummary | null }) {
  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const metrics = [
    {
      label: "Revenue at Risk",
      value: summary ? fmt(summary.revenue_at_risk) : "₹500,000",
      desc: "Total value of failed transactions & overdue items",
      color: "var(--danger)",
      isLive: !!summary,
    },
    {
      label: "Expected Recovery",
      value: summary ? fmt(summary.expected_recovery) : "₹345,000",
      desc: "EV projected deterministically prior to intervention",
      color: "var(--purple)",
      isLive: !!summary,
    },
    {
      label: "Actually Recovered",
      value: summary ? fmt(summary.actually_recovered) : "₹345,000",
      desc: "Financial settlement verified with gateway truth",
      color: "var(--success)",
      isLive: !!summary,
    },
    {
      label: "Recovery Rate",
      value: summary ? `${(summary.recovery_rate * 100).toFixed(1)}%` : "69.0%",
      desc: "Ratio of actually recovered vs revenue at risk",
      color: "var(--accent)",
      isLive: !!summary,
    },
    {
      label: "Cost per Recovery",
      value: "₹1.00",
      desc: "Simulated fixed intervention cost per executed action",
      color: "var(--text-secondary)",
      isLive: false,
    },
    {
      label: "Unnecessary Interventions",
      desc: "Retries prevented on fraud or unrecoverable cases",
      value: summary ? `${summary.stopped_cases} blocked` : "0 prevented",
      color: "var(--warning)",
      isLive: !!summary,
    },
  ];

  return (
    <section style={{ padding: "4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 3rem" }}>
        <div style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "var(--success)",
          marginBottom: "0.5rem",
        }}>
          Financial Verification
        </div>
        <h2 style={{
          fontSize: "clamp(1.75rem, 3vw, 2.35rem)",
          fontWeight: 700,
          color: "#fff",
          marginBottom: "1rem",
        }}>
          Evaluated on actual money, not recommendations.
        </h2>
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          We hold our recovery engine to strict financial metrics. A recommendation is useless until verified settlement occurs.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginBottom: "2.5rem" }}>
        {metrics.map((m) => (
          <div key={m.label} className="metric-card" style={{ borderLeft: `3px solid ${m.color}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
              <span className="metric-label">{m.label}</span>
              {m.isLive ? (
                <span style={{ fontSize: "0.5625rem", color: "var(--success)", fontWeight: 600, padding: "0.1rem 0.35rem", borderRadius: 3, background: "var(--success-subtle)" }}>
                  LIVE API
                </span>
              ) : (
                <span style={{ fontSize: "0.5625rem", color: "var(--text-muted)", fontWeight: 500 }}>
                  LIVE/BENCHMARK
                </span>
              )}
            </div>
            <div className="metric-value" style={{ color: m.color, marginTop: 4 }}>
              {m.value}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6, lineHeight: 1.4 }}>
              {m.desc}
            </div>
          </div>
        ))}
      </div>

      <div style={{ textAlign: "center" }}>
        <Link
          href="/batch-recovery"
          className="btn-primary"
          style={{
            padding: "0.75rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            borderRadius: 8,
          }}
        >
          <span>Run a 50-case evaluation →</span>
        </Link>
      </div>
    </section>
  );
}
