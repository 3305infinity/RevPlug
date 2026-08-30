"use client";

export default function MoneyStory() {
  const pipelineNodes = [
    {
      title: "Revenue at Risk",
      desc: "Webhooks signal failed charges, abandoned carts, or overdue invoices.",
      tag: "Input",
      color: "var(--danger)",
    },
    {
      title: "Diagnose Root Cause",
      desc: "Categorize failure mode into soft downtime, card decline, or fraud risk.",
      tag: "AI Diagnosis",
      color: "var(--warning)",
    },
    {
      title: "Estimate Recovery Value",
      desc: "Calculate ROI dynamically based on expected value minus intervention cost.",
      tag: "Scoring Engine",
      color: "var(--purple)",
    },
    {
      title: "Check Policy & Safety",
      desc: "Evaluate hard stopping rules, retry budgets, and customer opt-out status.",
      tag: "Policy Guard",
      color: "var(--accent)",
    },
    {
      title: "Execute Intervention",
      desc: "Trigger permitted action: automated retry, payment link, or human escalation.",
      tag: "Bounded Execution",
      color: "var(--accent)",
    },
    {
      title: "Verify Payment",
      desc: "Reconcile with gateway truth to confirm actual settlement before marking success.",
      tag: "Financial Verification",
      color: "var(--success)",
    },
    {
      title: "Record Outcome",
      desc: "Persist immutable audit trail, decision trace, and outcome accounting.",
      tag: "Audit Ledger",
      color: "var(--success)",
    },
  ];

  return (
    <section style={{ padding: "4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      {/* Section Header */}
      <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 3rem" }}>
        <div style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "var(--accent)",
          marginBottom: "0.5rem",
        }}>
          The Core Paradigm
        </div>
        <h2 style={{
          fontSize: "clamp(1.75rem, 3vw, 2.35rem)",
          fontWeight: 700,
          color: "#fff",
          marginBottom: "1rem",
        }}>
          Revenue recovery is more than sending another retry.
        </h2>
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          Blindly retrying failed payments causes customer friction, processor penalties, and unnecessary cost. RecoverOS governs the full lifecycle through strict financial control.
        </p>
      </div>

      {/* Visual Progression Pipeline */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem", marginBottom: "3rem" }}>
        {pipelineNodes.map((node, index) => (
          <div key={node.title} className="card" style={{
            padding: "1.25rem 1.25rem",
            position: "relative",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <span style={{
                  fontSize: "0.6875rem",
                  fontFamily: "monospace",
                  fontWeight: 700,
                  color: "var(--text-muted)",
                }}>
                  0{index + 1}
                </span>
                <span style={{
                  fontSize: "0.625rem",
                  fontWeight: 600,
                  padding: "0.15rem 0.45rem",
                  borderRadius: 4,
                  background: `rgba(255, 255, 255, 0.05)`,
                  color: node.color,
                  border: `1px solid ${node.color}33`,
                }}>
                  {node.tag}
                </span>
              </div>
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                {node.title}
              </h3>
              <p style={{ fontSize: "0.78125rem", color: "var(--text-secondary)", lineHeight: 1.55 }}>
                {node.desc}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Distinction Bar */}
      <div style={{
        background: "linear-gradient(90deg, rgba(6, 182, 212, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "1.5rem 2rem",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "1.5rem",
        textAlign: "center",
      }}>
        <div>
          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
            Intelligence
          </div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--accent)" }}>
            AI Recommends
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
            Control
          </div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--purple)" }}>
            Deterministic Engine Decides
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
            Safety
          </div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--warning)" }}>
            Execution is Bounded
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
            Financial Truth
          </div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--success)" }}>
            Recovery is Verified
          </div>
        </div>
      </div>
    </section>
  );
}
