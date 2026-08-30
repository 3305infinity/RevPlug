"use client";

export default function ControlPlaneSurfaces() {
  const leakageCategories = [
    { num: "01", title: "PAYMENT FAILURE", detail: "Gateway decline / timeout / authentication failure" },
    { num: "02", title: "CHECKOUT ABANDONMENT", detail: "Customer exits transaction before final authorization" },
    { num: "03", title: "SUBSCRIPTION FAILURE", detail: "Recurring billing cycle & payment token interruption" },
    { num: "04", title: "RECEIVABLE", detail: "Delinquent B2B invoice & overdue account balance" },
    { num: "05", title: "MANDATE FAILURE", detail: "Auto-pay debit & direct debit mandate rejection" },
    { num: "06", title: "PROMISE TO PAY", detail: "Customer payment commitment requiring fulfillment tracking" },
  ];

  return (
    <section id="control-plane" style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 800, marginBottom: "3rem" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--orange)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.75rem",
          }}>
            Multi-Surface Ingestion
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            color: "#f8fafc",
            lineHeight: 1.15,
            margin: 0,
          }}>
            Revenue leaks in different places.<br />
            <span style={{ color: "var(--orange)" }}>The recovery control plane stays the same.</span>
          </h2>
        </div>

        {/* Asymmetric 2-Column Split */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "2.5rem",
          alignItems: "start",
        }}>
          {/* LEFT: Vertical List */}
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {leakageCategories.map((item) => (
              <div key={item.num} style={{
                background: "#0b0f17",
                border: "1px solid var(--border)",
                borderRadius: 4,
                padding: "1rem 1.25rem",
                display: "flex",
                alignItems: "baseline",
                gap: "1rem",
              }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 700, fontFamily: "monospace", color: "var(--orange)" }}>
                  {item.num}
                </span>
                <div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: "0.78125rem", color: "var(--text-muted)", marginTop: 2 }}>
                    {item.detail}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* RIGHT: Connected Control Plane Diagram */}
          <div style={{
            background: "#0b0f17",
            border: "1px solid var(--border)",
            borderRadius: 4,
            padding: "2rem",
            textAlign: "center",
          }}>
            <div style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              fontFamily: "monospace",
              color: "var(--text-muted)",
              letterSpacing: "0.08em",
              marginBottom: "1.5rem",
            }}>
              UNIFIED CANONICAL RECOVERY CONTROL PLANE
            </div>

            <div style={{
              background: "#080c14",
              border: "1px solid var(--orange)",
              borderRadius: 4,
              padding: "1.25rem",
              fontSize: "1.125rem",
              fontWeight: 800,
              color: "#f8fafc",
              fontFamily: "monospace",
              marginBottom: "1.5rem",
            }}>
              RECOVEROS ENGINE
            </div>

            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace", marginBottom: "1.5rem" }}>
              ↓ Canonical Ingestion Pipeline ↓
            </div>

            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "0.75rem",
              marginBottom: "1.5rem",
            }}>
              <div style={{ background: "#080c14", border: "1px solid var(--border)", padding: "0.85rem", borderRadius: 4 }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontFamily: "monospace" }}>01</div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#f8fafc" }}>SCORE</div>
                <div style={{ fontSize: "0.625rem", color: "var(--text-secondary)" }}>EV Analysis</div>
              </div>

              <div style={{ background: "#080c14", border: "1px solid var(--border)", padding: "0.85rem", borderRadius: 4 }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontFamily: "monospace" }}>02</div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--warning)" }}>POLICY</div>
                <div style={{ fontSize: "0.625rem", color: "var(--text-secondary)" }}>Hard Guards</div>
              </div>

              <div style={{ background: "#080c14", border: "1px solid var(--border)", padding: "0.85rem", borderRadius: 4 }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontFamily: "monospace" }}>03</div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--success)" }}>VERIFY</div>
                <div style={{ fontSize: "0.625rem", color: "var(--text-secondary)" }}>Bank Truth</div>
              </div>
            </div>

            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace", marginBottom: "1.5rem" }}>
              ↓ Verified Financial Settlement ↓
            </div>

            <div style={{
              background: "rgba(16, 185, 129, 0.08)",
              border: "1px solid var(--success)",
              borderRadius: 4,
              padding: "1rem",
              fontSize: "0.9375rem",
              fontWeight: 700,
              color: "var(--success)",
              fontFamily: "monospace",
            }}>
              AUDITED FINANCIAL OUTCOME
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
