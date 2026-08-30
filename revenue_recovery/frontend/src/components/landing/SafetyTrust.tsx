"use client";

export default function SafetyTrust() {
  const guarantees = [
    {
      title: "Automated Fraud Halting",
      desc: "Any event identified as risk/fraud is instantly intercepted by StoppingRules with zero retries attempted.",
      icon: "🛑",
      badge: "StoppingRules",
    },
    {
      title: "Strict Retry Budgets",
      desc: "Each item has a hard maximum attempt cap (e.g. 3 retries). Exhausted budgets halt automatically.",
      icon: "⚡",
      badge: "DefaultRetryPolicy",
    },
    {
      title: "Idempotent Webhook Processing",
      desc: "Duplicate payment failure events are detected via unique event keys, preventing double interventions.",
      icon: "🔁",
      badge: "InMemoryIdempotencyStore",
    },
    {
      title: "Fail-Closed Low Confidence",
      desc: "If AI recommendation confidence drops below 0.5, the system automatically escalates for human review.",
      icon: "🛡️",
      badge: "ProposalValidator",
    },
    {
      title: "Policy Engine Overrides Human",
      desc: "Humans cannot manually override hard safety boundaries (e.g. retrying fraud). Policy remains supreme.",
      icon: "🔒",
      badge: "InterventionPolicy",
    },
    {
      title: "Verified Gateway Truth",
      desc: "Recovered balances are only credited after confirming actual provider settlement status.",
      icon: "✓",
      badge: "Outcome Accounting",
    },
    {
      title: "Comprehensive Audit Trail",
      desc: "Every recommendation, policy check, execution, and state change produces an immutable audit record.",
      icon: "📜",
      badge: "InMemoryAuditLog",
    },
    {
      title: "Customer Opt-Out Protection",
      desc: "Customers who opt out of recovery attempts are automatically excluded from all automated interventions.",
      icon: "👤",
      badge: "Customer Preference Guard",
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
          Safety & Compliance
        </div>
        <h2 style={{
          fontSize: "clamp(1.75rem, 3vw, 2.35rem)",
          fontWeight: 700,
          color: "#fff",
          marginBottom: "1rem",
        }}>
          Automation with hard boundaries.
        </h2>
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          RevPlug enforces hard deterministic safety rules at runtime. Autonomous execution operates strictly within policy boundaries.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1.25rem" }}>
        {guarantees.map((g) => (
          <div key={g.title} className="card" style={{
            padding: "1.25rem 1.5rem",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <span style={{ fontSize: "1.25rem" }}>{g.icon}</span>
                <span style={{
                  fontSize: "0.625rem",
                  fontWeight: 600,
                  padding: "0.15rem 0.5rem",
                  borderRadius: 4,
                  background: "var(--accent-subtle)",
                  color: "var(--accent)",
                  fontFamily: "monospace",
                }}>
                  {g.badge}
                </span>
              </div>
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.35rem" }}>
                {g.title}
              </h3>
              <p style={{ fontSize: "0.78125rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
                {g.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
