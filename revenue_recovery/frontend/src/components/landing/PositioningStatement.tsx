"use client";

export default function PositioningStatement() {
  const notList = [
    { title: "NOT a chatbot", desc: "No conversational prompts or unconstrained natural-language chat interfaces." },
    { title: "NOT an unrestricted agent", desc: "AI models cannot self-authorize financial execution without guard approval." },
    { title: "NOT action-counting marketing", desc: "An action attempt is never credited as revenue until settlement is proven." },
  ];

  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 780, margin: "0 auto", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--danger)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.75rem",
          }}>
            Clear Product Positioning
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            color: "#f8fafc",
            marginBottom: "2.5rem",
            lineHeight: 1.15,
          }}>
            What RecoverOS is not.
          </h2>
        </div>

        {/* 3 Not Cards */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "1.5rem",
          marginBottom: "2.5rem",
        }}>
          {notList.map((item) => (
            <div key={item.title} style={{
              background: "#0b0f17",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              borderTop: "3px solid var(--danger)",
              borderRadius: 4,
              padding: "1.5rem",
            }}>
              <div style={{ fontSize: "1.0625rem", fontWeight: 700, color: "var(--danger)", marginBottom: "0.5rem" }}>
                🚫 {item.title}
              </div>
              <div style={{ fontSize: "0.84375rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                {item.desc}
              </div>
            </div>
          ))}
        </div>

        {/* Definition Summary Banner */}
        <div style={{
          background: "#0b0f17",
          border: "1px solid var(--orange)",
          borderRadius: 4,
          padding: "1.75rem 2rem",
          textAlign: "center",
          maxWidth: 900,
          margin: "0 auto",
        }}>
          <div style={{ fontSize: "1.0625rem", fontWeight: 700, color: "#f8fafc", lineHeight: 1.6 }}>
            "RecoverOS is a bounded recovery control plane where AI proposes, deterministic systems constrain execution, and verification establishes financial truth."
          </div>
        </div>
      </div>
    </section>
  );
}
