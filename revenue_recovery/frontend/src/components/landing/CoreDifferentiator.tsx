"use client";

export default function CoreDifferentiator() {
  const flowNodes = [
    { title: "AI Recommendation", type: "Intelligence", desc: "LLM/Model diagnoses failure & suggests action", accent: "var(--accent)" },
    { title: "Expected Recovery Value", type: "Economic Scoring", desc: "EV = Probability × Amount - Cost", accent: "var(--text-primary)" },
    { title: "Policy & Safety Guard", type: "Hard Boundaries", desc: "StoppingRules & PolicyEngine evaluate compliance", accent: "var(--warning)" },
    { title: "Bounded Intervention", type: "Authorized Action", desc: "Only permitted execution path dispatches", accent: "var(--text-primary)" },
    { title: "Payment Verification", type: "Financial Truth", desc: "Gateway settlement confirmed before counting", accent: "var(--success)" },
    { title: "Audited Outcome", type: "Accounting Ledger", desc: "Immutable trail recorded for complete compliance", accent: "var(--success)" },
  ];

  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        {/* Editorial Text Block */}
        <div style={{ maxWidth: 780, margin: "0 auto 3.5rem", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--accent)",
            marginBottom: "0.75rem",
          }}>
            The Core Architecture
          </div>

          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            color: "#fff",
            marginBottom: "1.25rem",
            lineHeight: 1.15,
          }}>
            AI doesn't get the final say.
          </h2>

          <p style={{
            fontSize: "1.0625rem",
            color: "var(--text-secondary)",
            lineHeight: 1.7,
            margin: 0,
          }}>
            RecoverOS separates intelligence from authority. The AI can diagnose a failure and propose an intervention, but deterministic economic scoring, policy rules, stopping rules, and payment verification control what actually happens.
          </p>
        </div>

        {/* Linear Flow Architecture */}
        <div style={{
          background: "#0a0e17",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "2rem",
        }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "1rem",
            position: "relative",
          }}>
            {flowNodes.map((node, i) => (
              <div key={node.title} style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "1.25rem 1rem",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}>
                <div>
                  <div style={{
                    fontSize: "0.625rem",
                    fontWeight: 700,
                    color: node.accent,
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    marginBottom: 4,
                  }}>
                    Step 0{i + 1} · {node.type}
                  </div>
                  <div style={{
                    fontSize: "0.9375rem",
                    fontWeight: 700,
                    color: "#fff",
                    marginBottom: 6,
                    lineHeight: 1.3,
                  }}>
                    {node.title}
                  </div>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                  {node.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
