"use client";

export default function ArchitectureComparison() {
  const aiCapabilities = [
    { title: "Handling Ambiguity", detail: "Interpreting vague failure reasons & qualitative customer behavior patterns." },
    { title: "Contextual Diagnosis", detail: "Diagnosing complex root causes where simple static rules are insufficient." },
    { title: "Bounded Action Recommendations", detail: "Selecting optimal intervention proposals from a strictly allowed set." },
    { title: "Natural Language Reasoning", detail: "Synthesizing rationale for human review when cases are escalated." },
  ];

  const deterministicControls = [
    { title: "Expected Recovery Value (EV)", detail: "Calculated deterministically via EV = Prob × Amount - Cost." },
    { title: "Mandatory Policy Limits", detail: "Enforces max retry attempts, confidence thresholds, and action restrictions." },
    { title: "Hard Stopping Rules", detail: "Automated instant shutdown on fraud risk, customer opt-out, or expired deadline." },
    { title: "Idempotency & Duplicate Safety", detail: "Guarantees duplicate webhooks execute zero additional interventions." },
    { title: "Execution Authorization", detail: "Interventions are only dispatched if cleared by DefaultRecoveryGuard." },
    { title: "Financial Outcome Accounting", detail: "Verifies settlement state before recording recovered balance in ledger." },
  ];

  return (
    <section style={{ padding: "4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 3rem" }}>
        <div style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "var(--purple)",
          marginBottom: "0.5rem",
        }}>
          System Architecture
        </div>
        <h2 style={{
          fontSize: "clamp(1.75rem, 3vw, 2.35rem)",
          fontWeight: 700,
          color: "#fff",
          marginBottom: "1rem",
        }}>
          AI recommends. RecoverOS decides.
        </h2>
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          We never allow unconstrained LLM outputs to execute financial transactions. Intelligence handles reasoning, while deterministic code enforces truth and safety.
        </p>
      </div>

      {/* Side-by-side Visual Boundary Card */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
        gap: "1.5rem",
      }}>
        {/* AI Column */}
        <div className="card" style={{
          padding: "2rem",
          background: "linear-gradient(180deg, rgba(139, 92, 246, 0.05) 0%, var(--bg-card) 100%)",
          border: "1px solid var(--border)",
          position: "relative",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.25rem", paddingBottom: "1rem", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: "var(--purple-subtle)",
              color: "var(--purple)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1rem", fontWeight: 700,
            }}>
              AI
            </div>
            <div>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                AI Decision Agent
              </h3>
              <div style={{ fontSize: "0.75rem", color: "var(--purple)", fontWeight: 500 }}>
                Reasoning & Recommendation Subsystem
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gap: "1rem" }}>
            {aiCapabilities.map((cap) => (
              <div key={cap.title} style={{
                background: "var(--bg-elevated)",
                padding: "0.85rem 1rem",
                borderRadius: 8,
                border: "1px solid var(--border-subtle)",
              }}>
                <div style={{ fontSize: "0.84375rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
                  ✦ {cap.title}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {cap.detail}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Deterministic Column */}
        <div className="card" style={{
          padding: "2rem",
          background: "linear-gradient(180deg, rgba(6, 182, 212, 0.05) 0%, var(--bg-card) 100%)",
          border: "1px solid var(--border)",
          position: "relative",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.25rem", paddingBottom: "1rem", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: "var(--accent-subtle)",
              color: "var(--accent)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1rem", fontWeight: 700,
            }}>
              ⚙
            </div>
            <div>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                Deterministic Guardrails
              </h3>
              <div style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 500 }}>
                Control, Safety & Financial Truth
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gap: "1rem" }}>
            {deterministicControls.map((ctrl) => (
              <div key={ctrl.title} style={{
                background: "var(--bg-elevated)",
                padding: "0.85rem 1rem",
                borderRadius: 8,
                border: "1px solid var(--border-subtle)",
              }}>
                <div style={{ fontSize: "0.84375rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
                  ✓ {ctrl.title}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {ctrl.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
