"use client";

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

  const steps = [
    { label: "Detected", count: detected, isFinal: false },
    { label: "Eligible", count: actionable, isFinal: false },
    { label: "Approved", count: interventions, isFinal: false },
    { label: "Executed", count: executed, isFinal: false },
    { label: "Verified", count: recovered, isFinal: true },
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
          Conversion: <strong style={{ color: "var(--success)" }}>{((recovered / (detected || 1)) * 100).toFixed(1)}%</strong>
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
        <span style={{ color: "var(--text-muted)" }}>Total Risk Pool: <strong className="font-mono" style={{ color: "var(--danger)" }}>{fmt(amountAtRisk)}</strong></span>
        <span style={{ color: "var(--text-muted)" }}>Verified Recovered Money: <strong className="font-mono" style={{ color: "var(--success)" }}>{fmt(amountRecovered)}</strong></span>
      </div>
    </div>
  );
}
