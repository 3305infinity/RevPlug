"use client";

export default function WhyAIPanel() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "2rem" }}>
      {/* WHY AI? */}
      <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid var(--accent)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "1.125rem" }}>🤖</span>
          <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--accent)" }}>
            WHY AI? (Context & Interpretation)
          </h3>
        </div>
        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "0.75rem", lineHeight: 1.5 }}>
          AI is used exclusively for ambiguous semantic reasoning where hard rules are inadequate:
        </p>
        <ul style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", paddingLeft: "1.25rem", lineHeight: 1.6, margin: 0 }}>
          <li><strong>Failure Diagnosis:</strong> Distinguishes soft bank timeouts from permanent customer issues</li>
          <li><strong>Customer Reasoning:</strong> Interprets interaction history and payment habits</li>
          <li><strong>Intervention Ranking:</strong> Recommends highest-utility recovery action per context</li>
        </ul>
      </div>

      {/* WHY NOT AI? */}
      <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid var(--success)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "1.125rem" }}>🛡️</span>
          <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--success)" }}>
            WHY NOT AI? (Deterministic Safety & Truth)
          </h3>
        </div>
        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "0.75rem", lineHeight: 1.5 }}>
          Financial ledgers and safety gates remain 100% deterministic and non-bypassable:
        </p>
        <ul style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", paddingLeft: "1.25rem", lineHeight: 1.6, margin: 0 }}>
          <li><strong>Deterministic Policies:</strong> Retry limits, opt-outs, and fraud blocks cannot be overridden</li>
          <li><strong>Expected Value Gate:</strong> Interventions execute only if deterministic EV {">"} 0</li>
          <li><strong>Settlement Verification:</strong> Money is declared recovered ONLY with provider evidence</li>
        </ul>
      </div>
    </div>
  );
}
