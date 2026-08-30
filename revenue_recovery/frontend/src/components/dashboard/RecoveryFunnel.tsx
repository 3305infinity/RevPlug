"use client";

interface FunnelProps {
  detected: number;
  actionable: number;
  interventions: number;
  executed: number;
  recovered: number;
  amountAtRisk: number;
  amountRecovered: number;
}

export default function RecoveryFunnel({
  detected = 1000,
  actionable = 742,
  interventions = 531,
  executed = 317,
  recovered = 204,
  amountAtRisk = 4820000,
  amountRecovered = 1370000,
}: FunnelProps) {
  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 });

  const stages = [
    { label: "Revenue-Risk Events", count: detected, pct: 100, color: "var(--text-secondary)" },
    { label: "Actionable Cases", count: actionable, pct: Math.round((actionable / (detected || 1)) * 100), color: "var(--accent)" },
    { label: "Interventions Planned", count: interventions, pct: Math.round((interventions / (detected || 1)) * 100), color: "var(--purple)" },
    { label: "Interventions Executed", count: executed, pct: Math.round((executed / (detected || 1)) * 100), color: "var(--warning)" },
    { label: "Verified Recoveries", count: recovered, pct: Math.round((recovered / (detected || 1)) * 100), color: "var(--success)" },
  ];

  return (
    <div className="card" style={{ padding: "1.5rem", marginBottom: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <div>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 700, letterSpacing: "-0.01em" }}>
            Proof of Recovery Funnel
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 2 }}>
            Measured progression from detected revenue risk to settlement-verified recovered money
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Verified Recovery Rate</div>
          <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--success)" }}>
            {((recovered / (detected || 1)) * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gap: "0.75rem" }}>
        {stages.map((stage, idx) => (
          <div key={idx} style={{ display: "grid", gridTemplateColumns: "180px 1fr 100px", alignItems: "center", gap: "1rem" }}>
            <div style={{ fontSize: "0.8125rem", fontWeight: 500, color: stage.color }}>
              {stage.label}
            </div>
            <div style={{ background: "rgba(255, 255, 255, 0.05)", borderRadius: 4, height: 24, overflow: "hidden", position: "relative" }}>
              <div
                style={{
                  width: `${Math.max(stage.pct, 4)}%`,
                  height: "100%",
                  background: stage.color,
                  opacity: 0.85,
                  transition: "width 0.5s ease",
                  borderRadius: 4,
                }}
              />
            </div>
            <div style={{ fontSize: "0.8125rem", fontWeight: 600, textAlign: "right", color: "var(--text-primary)" }}>
              {stage.count.toLocaleString()} <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 400 }}>({stage.pct}%)</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "1.25rem", paddingTop: "1rem", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", fontSize: "0.8125rem" }}>
        <span>Total Risk: <strong style={{ color: "var(--danger)" }}>{fmt(amountAtRisk)}</strong></span>
        <span>Verified Money Recovered: <strong style={{ color: "var(--success)" }}>{fmt(amountRecovered)}</strong></span>
      </div>
    </div>
  );
}
