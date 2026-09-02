"use client";

import { useEffect, useState } from "react";

interface FunnelProps {
  detected?: number;
  actionable?: number;
  interventions?: number;
  executed?: number;
  recovered?: number;
  amountAtRisk?: number;
  amountRecovered?: number;
}

export default function RecoveryFunnel({
  detected,
  actionable,
  interventions,
  executed,
  recovered,
  amountAtRisk,
  amountRecovered,
}: FunnelProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/dashboard/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 });

  const d = data || {};
  const det = detected ?? d.total_items ?? 0;
  const act = actionable ?? d.active_recoveries ?? 0;
  const inter = interventions ?? d.executed_count ?? 0;
  const exec = executed ?? d.executed_count ?? 0;
  const rec = recovered ?? d.recovered_cases ?? 0;
  const risk = amountAtRisk ?? d.revenue_at_risk ?? 0;
  const recov = amountRecovered ?? d.actually_recovered ?? 0;

  const hasData = det > 0 || risk > 0 || recov > 0;

  if (loading) {
    return (
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>Loading operational data...</div>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ marginBottom: "1rem" }}>
          <h3 style={{ fontSize: "0.9375rem", fontWeight: 600 }}>Operational Recovery Funnel</h3>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
            Stage-by-stage progression from initial revenue risk detection to verified settlement
          </p>
        </div>
        <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
          No operational recovery data yet. Cases will appear here once live payment failures are detected and processed.
        </div>
      </div>
    );
  }

  const steps = [
    { label: "Detected", count: det, isFinal: false },
    { label: "Eligible", count: act, isFinal: false },
    { label: "Approved", count: inter, isFinal: false },
    { label: "Executed", count: exec, isFinal: false },
    { label: "Verified", count: rec, isFinal: true },
  ];

  return (
    <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h3 style={{ fontSize: "0.9375rem", fontWeight: 600 }}>Operational Recovery Funnel</h3>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
            Stage-by-stage progression from initial revenue risk detection to verified settlement
          </p>
        </div>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Conversion: <strong style={{ color: "var(--success)" }}>{((rec / (det || 1)) * 100).toFixed(1)}%</strong>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem", alignItems: "center" }}>
        {steps.map((step, idx) => (
          <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <div
              style={{
                flex: 1,
                padding: "0.75rem 0.625rem",
                borderRadius: 6,
                background: step.isFinal ? "rgba(16, 185, 129, 0.08)" : "var(--bg-secondary)",
                border: step.isFinal ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid var(--border)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "0.6875rem", color: step.isFinal ? "var(--success)" : "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                {step.label}
              </div>
              <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: 2, color: step.isFinal ? "var(--success)" : "var(--text-primary)" }}>
                {step.count.toLocaleString()}
              </div>
            </div>
            {idx < steps.length - 1 && (
              <span style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>→</span>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
        <span style={{ color: "var(--text-muted)" }}>Total Risk Pool: <strong className="font-mono" style={{ color: "var(--danger)" }}>{fmt(risk)}</strong></span>
        <span style={{ color: "var(--text-muted)" }}>Verified Recovered Money: <strong className="font-mono" style={{ color: "var(--success)" }}>{fmt(recov)}</strong></span>
      </div>
    </div>
  );
}

