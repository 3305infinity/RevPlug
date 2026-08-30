"use client";

export default function SafetyControl() {
  const principles = [
    {
      step: "01",
      title: "AI Proposes",
      desc: "The decision agent diagnoses root cause failure modes and suggests optimal recovery proposals from a bounded intervention set.",
      tag: "Recommendation Layer",
    },
    {
      step: "02",
      title: "Policy Decides",
      desc: "Hard financial rules, retry budgets, fraud stopping rules, and customer opt-outs evaluate whether the recommendation is allowed.",
      tag: "Deterministic Enforcement",
    },
    {
      step: "03",
      title: "Verification Proves",
      desc: "An action is never counted as recovered until payment settlement state is independently confirmed with provider truth.",
      tag: "Financial Verification",
    },
  ];

  return (
    <section id="safety" style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 780, margin: "0 auto 3.5rem", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--warning)",
            marginBottom: "0.75rem",
          }}>
            Runtime Safety Architecture
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            color: "#fff",
            marginBottom: "1.25rem",
            lineHeight: 1.15,
          }}>
            Autonomous recovery. Deterministic control.
          </h2>
          <p style={{
            fontSize: "1.0625rem",
            color: "var(--text-secondary)",
            lineHeight: 1.65,
            margin: 0,
          }}>
            RevPlug is designed so that AI can propose actions without receiving unrestricted authority to execute them.
          </p>
        </div>

        {/* 3 Core Principles */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "1.5rem",
          marginBottom: "2.5rem",
        }}>
          {principles.map((p) => (
            <div key={p.title} style={{
              background: "#0a0e17",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "1.75rem",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}>
              <div>
                <div style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "1rem",
                }}>
                  <span style={{ fontSize: "0.875rem", fontWeight: 800, fontFamily: "monospace", color: "var(--accent)" }}>
                    {p.step}
                  </span>
                  <span style={{
                    fontSize: "0.625rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    background: "var(--bg-elevated)",
                    padding: "0.2rem 0.5rem",
                    borderRadius: 4,
                    border: "1px solid var(--border-subtle)",
                  }}>
                    {p.tag}
                  </span>
                </div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#fff", marginBottom: "0.5rem" }}>
                  {p.title}
                </h3>
                <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
                  {p.desc}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Strong Judge-Facing Callout */}
        <div style={{
          background: "rgba(245, 158, 11, 0.05)",
          border: "1px solid rgba(245, 158, 11, 0.25)",
          borderRadius: 8,
          padding: "1.25rem 1.75rem",
          textAlign: "center",
          maxWidth: 780,
          margin: "0 auto",
        }}>
          <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--warning)", letterSpacing: "0.01em" }}>
            🛡️ Core Compliance Guarantee: "Human approval never overrides a mandatory safety rule."
          </span>
          <div style={{ fontSize: "0.78125rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Even if an operator attempts to force an illegal action (e.g. retrying a confirmed fraud case), PolicyEngine rejects the execution.
          </div>
        </div>
      </div>
    </section>
  );
}
