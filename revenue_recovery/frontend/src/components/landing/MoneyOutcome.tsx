"use client";

export default function MoneyOutcome() {
  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 720, margin: "0 auto 3.5rem", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--success)",
            marginBottom: "0.75rem",
          }}>
            Financial Accounting
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.5rem)",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            color: "#fff",
            marginBottom: "1rem",
          }}>
            Measure money recovered, not actions taken.
          </h2>
          <p style={{ fontSize: "1.0625rem", color: "var(--text-secondary)", lineHeight: 1.65, margin: 0 }}>
            RecoverOS separates expected economic value from actual verified recovery.
          </p>
        </div>

        {/* 3 Metric Box Comparison */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "1.5rem",
          marginBottom: "2.5rem",
        }}>
          {/* AT RISK */}
          <div style={{
            background: "#0a0e17",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderLeft: "4px solid var(--danger)",
            borderRadius: 8,
            padding: "1.75rem",
          }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--danger)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
              01 · AT RISK
            </div>
            <div style={{ fontSize: "2.25rem", fontWeight: 800, color: "var(--danger)", fontFamily: "monospace", letterSpacing: "-0.03em", marginBottom: 6 }}>
              ₹50,000
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              Raw financial value of failed transactions and overdue accounts prior to intervention.
            </div>
          </div>

          {/* EXPECTED */}
          <div style={{
            background: "#0a0e17",
            border: "1px solid rgba(6, 182, 212, 0.3)",
            borderLeft: "4px solid var(--accent)",
            borderRadius: 8,
            padding: "1.75rem",
          }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
              02 · EXPECTED RECOVERY (EV)
            </div>
            <div style={{ fontSize: "2.25rem", fontWeight: 800, color: "var(--accent)", fontFamily: "monospace", letterSpacing: "-0.03em", marginBottom: 6 }}>
              ₹34,500
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              Deterministic expected value projection (Probabilistic Model × Amount − Intervention Cost).
            </div>
          </div>

          {/* ACTUALLY RECOVERED */}
          <div style={{
            background: "#0a0e17",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderLeft: "4px solid var(--success)",
            borderRadius: 8,
            padding: "1.75rem",
          }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--success)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
              03 · ACTUALLY RECOVERED
            </div>
            <div style={{ fontSize: "2.25rem", fontWeight: 800, color: "var(--success)", fontFamily: "monospace", letterSpacing: "-0.03em", marginBottom: 6 }}>
              ₹34,500
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              Verified financial settlement confirmed independently through gateway transaction state.
            </div>
          </div>
        </div>

        <div style={{
          textAlign: "center",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          fontFamily: "monospace",
        }}>
          [Illustrative Benchmark Comparison — Derived from RecoverOS Evaluation Protocol]
        </div>
      </div>
    </section>
  );
}
