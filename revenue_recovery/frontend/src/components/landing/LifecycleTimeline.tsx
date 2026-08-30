"use client";

export default function LifecycleTimeline() {
  const steps = [
    {
      num: "01",
      title: "Detect",
      desc: "Revenue-risk event enters RevPlug via webhook or system trigger.",
      tech: "Webhook Service & Idempotency",
    },
    {
      num: "02",
      title: "Diagnose",
      desc: "Rules classify known failure modes; ambiguous cases can use AI decision agents.",
      tech: "Failure Classifier & AI Agent",
    },
    {
      num: "03",
      title: "Score",
      desc: "Expected Recovery Value (EV) is calculated deterministically from recovery probability.",
      tech: "ExpectedValueScorer",
    },
    {
      num: "04",
      title: "Guard",
      desc: "Policy and stopping rules determine whether the proposed action is allowed.",
      tech: "DefaultRecoveryGuard & StoppingRules",
    },
    {
      num: "05",
      title: "Execute",
      desc: "Only bounded, policy-approved interventions can dispatch.",
      tech: "SimulatedRecoveryExecutor",
    },
    {
      num: "06",
      title: "Verify",
      desc: "Recovery is only counted after settlement payment state is confirmed.",
      tech: "Outcome Accounting",
    },
    {
      num: "07",
      title: "Audit",
      desc: "Every decision, state transition, and financial outcome is recorded.",
      tech: "InMemoryAuditLog & Postgres",
    },
  ];

  return (
    <section id="how-it-works" style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 720, margin: "0 auto 3.5rem", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--accent)",
            marginBottom: "0.75rem",
          }}>
            Case Execution Lifecycle
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.5rem)",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            color: "#fff",
            marginBottom: "1rem",
          }}>
            From failure to verified recovery.
          </h2>
          <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
            Every recovery case follows an auditable 7-step lifecycle with strict state progression.
          </p>
        </div>

        {/* Clean Process Timeline Layout */}
        <div style={{
          display: "grid",
          gap: "0.75rem",
        }}>
          {steps.map((s) => (
            <div key={s.num} style={{
              background: "#0a0e17",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "1.125rem 1.5rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "1.5rem",
              flexWrap: "wrap",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", flex: 1, minWidth: 280 }}>
                <span style={{
                  fontSize: "1rem",
                  fontWeight: 800,
                  fontFamily: "monospace",
                  color: "var(--accent)",
                  minWidth: 32,
                }}>
                  {s.num}
                </span>
                <div>
                  <div style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", marginBottom: 2 }}>
                    {s.title}
                  </div>
                  <div style={{ fontSize: "0.84375rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                    {s.desc}
                  </div>
                </div>
              </div>

              <div style={{
                fontSize: "0.6875rem",
                fontWeight: 600,
                fontFamily: "monospace",
                color: "var(--text-muted)",
                background: "var(--bg-elevated)",
                padding: "0.25rem 0.6rem",
                borderRadius: 4,
                border: "1px solid var(--border-subtle)",
              }}>
                {s.tech}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
