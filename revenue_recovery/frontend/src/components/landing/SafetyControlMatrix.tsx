"use client";

export default function SafetyControlMatrix() {
  const matrix = [
    {
      category: "AUTOMATIC",
      trigger: "Soft temporary failure",
      action: "Retry within budget (max 3)",
      enforcer: "DefaultRetryPolicy",
      badgeColor: "var(--success)",
    },
    {
      category: "HUMAN REVIEW",
      trigger: "Ambiguous / uncertain confidence (<0.5)",
      action: "Escalation required in Review Queue",
      enforcer: "ProposalValidator",
      badgeColor: "var(--warning)",
    },
    {
      category: "BLOCKED",
      trigger: "Confirmed fraud / opt-out / expired",
      action: "No automated recovery attempt",
      enforcer: "StoppingRules & PolicyEngine",
      badgeColor: "var(--danger)",
    },
  ];

  return (
    <section id="safety" style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 780, marginBottom: "3rem" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--warning)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.75rem",
          }}>
            Governance & Compliance Matrix
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            color: "#f8fafc",
            lineHeight: 1.15,
            margin: 0,
          }}>
            Autonomous where it can be.<br />
            <span style={{ color: "var(--warning)" }}>Controlled where it must be.</span>
          </h2>
        </div>

        {/* Clean Table Structure */}
        <div style={{
          background: "#0b0f17",
          border: "1px solid var(--border)",
          borderRadius: 4,
          overflow: "hidden",
          marginBottom: "2rem",
        }}>
          {/* Header Row */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "180px 1fr 1fr 180px",
            gap: "1rem",
            padding: "0.85rem 1.5rem",
            background: "#080c14",
            borderBottom: "1px solid var(--border)",
            fontSize: "0.6875rem",
            fontWeight: 700,
            fontFamily: "monospace",
            color: "var(--text-muted)",
            textTransform: "uppercase",
          }}>
            <span>EXECUTION MODE</span>
            <span>TRIGGER CONDITION</span>
            <span>ACTION DISPATCH</span>
            <span>RUNTIME ENFORCER</span>
          </div>

          {/* Data Rows */}
          {matrix.map((row) => (
            <div key={row.category} style={{
              display: "grid",
              gridTemplateColumns: "180px 1fr 1fr 180px",
              gap: "1rem",
              alignItems: "center",
              padding: "1.25rem 1.5rem",
              borderBottom: "1px solid var(--border-subtle)",
              fontSize: "0.84375rem",
            }}>
              <div>
                <span style={{
                  fontSize: "0.6875rem",
                  fontWeight: 700,
                  fontFamily: "monospace",
                  padding: "0.25rem 0.5rem",
                  borderRadius: 4,
                  background: `${row.badgeColor}15`,
                  color: row.badgeColor,
                  border: `1px solid ${row.badgeColor}40`,
                }}>
                  {row.category}
                </span>
              </div>
              <div style={{ color: "#f8fafc", fontWeight: 600 }}>{row.trigger}</div>
              <div style={{ color: "var(--text-secondary)" }}>{row.action}</div>
              <div style={{ color: "var(--text-muted)", fontFamily: "monospace", fontSize: "0.75rem" }}>{row.enforcer}</div>
            </div>
          ))}
        </div>

        {/* Clear Compliance Invariant Callout */}
        <div style={{
          background: "rgba(245, 158, 11, 0.05)",
          border: "1px solid rgba(245, 158, 11, 0.25)",
          borderRadius: 4,
          padding: "1.25rem 1.75rem",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          maxWidth: 820,
        }}>
          <span style={{ fontSize: "1.25rem" }}>🛡️</span>
          <div style={{ fontSize: "0.875rem", color: "var(--text-primary)", lineHeight: 1.5 }}>
            <strong style={{ color: "var(--warning)" }}>Compliance Invariant:</strong> "Human approval cannot override a mandatory safety rule." If an operator attempts to approve an unsafe action, PolicyEngine cancels the request.
          </div>
        </div>
      </div>
    </section>
  );
}
