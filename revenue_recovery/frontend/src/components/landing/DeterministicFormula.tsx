"use client";

export default function DeterministicFormula() {
  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--orange)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.75rem",
          }}>
            Economic Rigor
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            color: "#f8fafc",
            marginBottom: "1.25rem",
            lineHeight: 1.15,
          }}>
            The Deterministic Economic Formula
          </h2>
          <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "2.5rem" }}>
            Recovery decisions are mathematically grounded in positive expected economic value (EV).
          </p>
        </div>

        {/* Financial Calculation Instrument Box */}
        <div style={{
          maxWidth: 740,
          margin: "0 auto",
          background: "#0b0f17",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "2rem",
          fontFamily: "monospace",
        }}>
          <div style={{
            fontSize: "0.6875rem",
            fontWeight: 700,
            color: "var(--text-muted)",
            letterSpacing: "0.08em",
            marginBottom: "1.25rem",
            textTransform: "uppercase",
          }}>
            FORMULA · EXPECTED RECOVERY VALUE (EV)
          </div>

          {/* Mathematical Expression */}
          <div style={{
            fontSize: "clamp(1.125rem, 2.5vw, 1.35rem)",
            fontWeight: 700,
            color: "var(--orange)",
            marginBottom: "1.5rem",
            padding: "1rem",
            background: "#080c14",
            borderRadius: 4,
            border: "1px solid var(--border)",
            textAlign: "center",
          }}>
            EV = (Amount × Recovery Probability) − Intervention Cost
          </div>

          {/* Concrete Sample Calculation */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "1rem",
            alignItems: "center",
            marginBottom: "1.5rem",
            textAlign: "center",
          }}>
            <div style={{ background: "#080c14", padding: "0.85rem", borderRadius: 4, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>AMOUNT AT RISK</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#f8fafc", marginTop: 2 }}>₹50,000</div>
            </div>

            <div style={{ fontSize: "1.125rem", color: "var(--text-muted)" }}>×</div>

            <div style={{ background: "#080c14", padding: "0.85rem", borderRadius: 4, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>PROBABILITY</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--orange)", marginTop: 2 }}>69%</div>
            </div>

            <div style={{ fontSize: "1.125rem", color: "var(--text-muted)" }}>−</div>

            <div style={{ background: "#080c14", padding: "0.85rem", borderRadius: 4, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>ACTION COST</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--danger)", marginTop: 2 }}>₹100</div>
            </div>
          </div>

          {/* Result Line */}
          <div style={{
            background: "rgba(16, 185, 129, 0.08)",
            border: "1px solid var(--success)",
            borderRadius: 4,
            padding: "1rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}>
            <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f8fafc" }}>
              DETERMINISTIC EXPECTED VALUE =
            </span>
            <span style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--success)" }}>
              ₹34,400
            </span>
          </div>

          {/* Verification Badges */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "1.5rem",
            marginTop: "1.5rem",
            fontSize: "0.75rem",
            color: "var(--text-secondary)",
            borderTop: "1px solid var(--border)",
            paddingTop: "1rem",
          }}>
            <span style={{ color: "var(--success)", fontWeight: 700 }}>✓ Calculated deterministically</span>
            <span style={{ color: "var(--text-muted)" }}>|</span>
            <span style={{ color: "var(--warning)", fontWeight: 700 }}>🚫 Not generated by the LLM</span>
          </div>
        </div>
      </div>
    </section>
  );
}
