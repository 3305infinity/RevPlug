"use client";

export default function AuthoritySplit() {
  const chainStages = [
    { label: "MODEL", title: "AI Agent", detail: "diagnosis + proposal", accent: "var(--orange)" },
    { label: "ECONOMIC SCORE", title: "Scoring Engine", detail: "deterministic EV", accent: "#f8fafc" },
    { label: "POLICY", title: "Intervention Policy", detail: "hard constraints", accent: "var(--warning)" },
    { label: "SAFETY GUARD", title: "Stopping Rules", detail: "budget & fraud checks", accent: "var(--danger)" },
    { label: "EXECUTOR", title: "Action Dispatcher", detail: "bounded actions", accent: "#f8fafc" },
    { label: "VERIFIER", title: "Gateway Truth", detail: "confirmed settlement", accent: "var(--success)" },
  ];

  return (
    <section id="architecture" style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        {/* Editorial Split Layout */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "2.5rem",
          alignItems: "center",
          marginBottom: "3.5rem",
          paddingBottom: "2.5rem",
          borderBottom: "1px solid var(--border)",
        }}>
          <div>
            <div style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              fontFamily: "monospace",
              color: "var(--orange)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: "0.75rem",
            }}>
              Authority & Enforcement
            </div>
            <h2 style={{
              fontSize: "clamp(2.25rem, 4vw, 3rem)",
              fontWeight: 800,
              letterSpacing: "-0.035em",
              color: "#f8fafc",
              lineHeight: 1.1,
              margin: 0,
            }}>
              AI can recommend.
            </h2>
          </div>

          <div>
            <h2 style={{
              fontSize: "clamp(2.25rem, 4vw, 3rem)",
              fontWeight: 800,
              letterSpacing: "-0.035em",
              color: "var(--orange)",
              lineHeight: 1.1,
              marginBottom: "1rem",
            }}>
              It cannot authorize.
            </h2>
            <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.65, margin: 0 }}>
              RevPlug enforces a complete boundary between LLM reasoning and financial execution authority. The model proposes interventions, but deterministic code determines if, when, and how execution proceeds.
            </p>
          </div>
        </div>

        {/* Single Horizontal Technical Control Chain */}
        <div style={{
          background: "#0b0f17",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "1.75rem 1.5rem",
        }}>
          <div style={{
            fontSize: "0.6875rem",
            fontWeight: 700,
            fontFamily: "monospace",
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "1.25rem",
          }}>
            Technical Control Architecture Chain
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
            gap: "0.85rem",
          }}>
            {chainStages.map((stage, idx) => (
              <div key={stage.label} style={{
                background: "#080c14",
                border: "1px solid var(--border)",
                borderRadius: 4,
                padding: "1rem 0.85rem",
              }}>
                <div style={{ fontSize: "0.5625rem", fontWeight: 700, fontFamily: "monospace", color: stage.accent, letterSpacing: "0.05em", marginBottom: 4 }}>
                  0{idx + 1} · {stage.label}
                </div>
                <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f8fafc", marginBottom: 4 }}>
                  {stage.title}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {stage.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
