"use client";

export default function MoneyStorySequence() {
  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        {/* Asymmetric Left Title & Right Narrative */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "2rem",
          alignItems: "baseline",
          marginBottom: "3.5rem",
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
              Financial Flow Protocol
            </div>
            <h2 style={{
              fontSize: "clamp(1.75rem, 3.5vw, 2.5rem)",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              color: "#f8fafc",
              lineHeight: 1.15,
              margin: 0,
            }}>
              From gross leakage to verified cash settlement.
            </h2>
          </div>

          <div>
            <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.65, margin: 0 }}>
              RecoverOS controls every rupee moving through the recovery pipeline. Raw failures are filtered through deterministic economic scoring and safety bounds before execution.
            </p>
          </div>
        </div>

        {/* Large Typographic Money Sequence Instrument */}
        <div style={{
          background: "#0b0f17",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "2.5rem 2rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "2rem",
          alignItems: "center",
        }}>
          {/* Node 1: Revenue at Risk */}
          <div style={{
            borderLeft: "3px solid var(--danger)",
            paddingLeft: "1.25rem",
          }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--danger)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
              01 · REVENUE AT RISK
            </div>
            <div style={{ fontSize: "clamp(2rem, 3.5vw, 2.75rem)", fontWeight: 800, color: "#f8fafc", fontFamily: "monospace", letterSpacing: "-0.03em" }}>
              ₹12.4M
            </div>
            <div style={{ fontSize: "0.78125rem", color: "var(--text-muted)", marginTop: 6 }}>
              Gross payment failures & invoice delinquencies
            </div>
          </div>

          {/* Transition Arrow 1 */}
          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.75rem", fontFamily: "monospace" }}>
            ↓ diagnosis & EV scoring
          </div>

          {/* Node 2: Eligible for Recovery */}
          <div style={{
            borderLeft: "3px solid var(--orange)",
            paddingLeft: "1.25rem",
          }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--orange)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
              02 · ELIGIBLE FOR RECOVERY
            </div>
            <div style={{ fontSize: "clamp(2rem, 3.5vw, 2.75rem)", fontWeight: 800, color: "var(--orange)", fontFamily: "monospace", letterSpacing: "-0.03em" }}>
              ₹8.7M
            </div>
            <div style={{ fontSize: "0.78125rem", color: "var(--text-muted)", marginTop: 6 }}>
              Filtered for positive expected economic value
            </div>
          </div>

          {/* Transition Arrow 2 */}
          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.75rem", fontFamily: "monospace" }}>
            ↓ policy + execution + verification
          </div>

          {/* Node 3: Verified Recovery */}
          <div style={{
            borderLeft: "3px solid var(--success)",
            paddingLeft: "1.25rem",
          }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--success)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
              03 · VERIFIED RECOVERY
            </div>
            <div style={{ fontSize: "clamp(2rem, 3.5vw, 2.75rem)", fontWeight: 800, color: "var(--success)", fontFamily: "monospace", letterSpacing: "-0.03em" }}>
              ₹6.2M
            </div>
            <div style={{ fontSize: "0.78125rem", color: "var(--text-muted)", marginTop: 6 }}>
              Confirmatory settlement in bank gateway truth
            </div>
          </div>
        </div>

        <div style={{
          textAlign: "right",
          fontSize: "0.6875rem",
          color: "var(--text-muted)",
          fontFamily: "monospace",
          marginTop: "0.75rem",
        }}>
          [Illustrative Benchmark Progression — Evaluated on Standard 50-Case Protocol]
        </div>
      </div>
    </section>
  );
}
