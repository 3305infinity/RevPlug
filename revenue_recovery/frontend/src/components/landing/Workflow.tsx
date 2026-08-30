"use client";

export default function Workflow() {
  const steps = [
    {
      num: "01",
      title: "Detect",
      subtitle: "Revenue Event Arrives",
      desc: "Incoming webhook payload or internal trigger identifies a payment failure, invoice delinquency, or abandoned transaction.",
      tech: "Webhook Service & Idempotency Store",
    },
    {
      num: "02",
      title: "Diagnose",
      subtitle: "Identify Root Cause",
      desc: "Classify failure mode into soft processing errors, hard declines, bank downtime, or potential fraud indicators.",
      tech: "Failure Classifier & Risk Agent",
    },
    {
      num: "03",
      title: "Score",
      subtitle: "Deterministic EV Calculation",
      desc: "Calculate Expected Recovery Value (EV) by combining baseline recovery probability against intervention cost.",
      tech: "ExpectedValueScorer",
    },
    {
      num: "04",
      title: "Recommend",
      subtitle: "Bounded Action Proposal",
      desc: "AI agent or rules engine selects the optimal intervention (e.g. retry_payment, send_payment_link, escalate_human).",
      tech: "RecoveryDecisionAgent",
    },
    {
      num: "05",
      title: "Safety",
      subtitle: "Policy Engine & Guard Evaluation",
      desc: "Mandatory check against stopping rules, max retry budget, customer opt-out list, and intervention policy.",
      tech: "DefaultRecoveryGuard & StoppingRules",
    },
    {
      num: "06",
      title: "Execute",
      subtitle: "Permitted Action Dispatch",
      desc: "If policy grants permission, dispatch the action. If blocked or escalated, execution is cleanly intercepted.",
      tech: "SimulatedRecoveryExecutor",
    },
    {
      num: "07",
      title: "Verify",
      subtitle: "Confirm Payment State",
      desc: "Query provider gateway state to confirm settlement. Never assume success based on action dispatch alone.",
      tech: "Outcome Verification Engine",
    },
    {
      num: "08",
      title: "Outcome",
      subtitle: "Immutable Audit Recording",
      desc: "Log complete audit events, state transitions, decision rationale, and financial recovery metrics for accounting.",
      tech: "InMemoryAuditLog & Postgres Repo",
    },
  ];

  return (
    <section id="workflow" style={{ padding: "4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 3rem" }}>
        <div style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "var(--accent)",
          marginBottom: "0.5rem",
        }}>
          End-to-End Architecture
        </div>
        <h2 style={{
          fontSize: "clamp(1.75rem, 3vw, 2.35rem)",
          fontWeight: 700,
          color: "#fff",
          marginBottom: "1rem",
        }}>
          How RecoverOS Processes a Case
        </h2>
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          Every case flows through an 8-stage pipeline where AI intelligence is continuously validated by strict safety controls.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
        {steps.map((s) => (
          <div key={s.num} className="card" style={{
            padding: "1.5rem",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            position: "relative",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.75rem" }}>
              <span style={{
                fontSize: "1.5rem",
                fontWeight: 800,
                color: "var(--accent)",
                opacity: 0.8,
                letterSpacing: "-0.04em",
              }}>
                {s.num}
              </span>
              <span style={{
                fontSize: "0.625rem",
                fontWeight: 600,
                color: "var(--text-muted)",
                fontFamily: "monospace",
                textTransform: "uppercase",
              }}>
                {s.tech}
              </span>
            </div>

            <h3 style={{ fontSize: "1.0625rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 2 }}>
              {s.title}
            </h3>
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--purple)", marginBottom: "0.75rem" }}>
              {s.subtitle}
            </div>

            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
              {s.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
