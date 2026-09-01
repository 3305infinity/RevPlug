"use client";

export default function HeroProductVisual() {
  return (
    <div style={{
      background: "#080c14",
      border: "1px solid var(--border)",
      borderRadius: 4,
      overflow: "hidden",
      fontFamily: "monospace",
    }}>
      {/* Operations Bar */}
      <div style={{
        padding: "0.75rem 1.25rem",
        background: "#0b0f17",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: "0.75rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--orange)" }} />
          <span style={{ fontWeight: 700, color: "#f8fafc" }}>SYSTEM EXECUTION TRACE</span>
          <span style={{ color: "var(--text-muted)" }}>|</span>
          <span style={{ color: "var(--text-secondary)" }}>CASE #pay_demo_1787993826</span>
        </div>
        <div style={{ display: "flex", gap: "1.25rem", color: "var(--text-muted)", fontSize: "0.6875rem" }}>
          <span>CUSTOMER: cust_checkout_101</span>
          <span>CURRENCY: INR</span>
        </div>
      </div>

      {/* Main Financial State Line */}
      <div style={{
        padding: "1.25rem 1.5rem",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "1rem",
        background: "#04060a",
      }}>
        <div>
          <div style={{ fontSize: "0.6875rem", color: "var(--danger)", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>
            REVENUE AT RISK
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginTop: 2 }}>
            ₹50,000
          </div>
        </div>

        <div style={{ fontSize: "0.78125rem", color: "var(--text-secondary)" }}>
          <div><span style={{ color: "var(--text-muted)" }}>Code:</span> Gateway timeout</div>
          <div><span style={{ color: "var(--text-muted)" }}>Mode:</span> soft_downtime</div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--success)", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>
            VERIFIED RECOVERY
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--success)", marginTop: 2 }}>
            ₹34,500
          </div>
        </div>
      </div>

      {/* 6-Stage Execution Trace Nodes */}
      <div style={{
        padding: "1.25rem 1.5rem",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
        gap: "0.75rem",
        background: "#080c14",
      }}>
        {[
          { stage: "01 DETECT", value: "soft", label: "Failure category", color: "var(--danger)" },
          { stage: "02 DIAGNOSE", value: "timeout", label: "Temp 503 error", color: "var(--orange)" },
          { stage: "03 SCORE", value: "₹34,500", label: "EV (Score 0.69)", color: "var(--text-primary)" },
          { stage: "04 GUARD", value: "ALLOWED", label: "Attempt 1/3 budget", color: "var(--orange)" },
          { stage: "05 EXECUTE", value: "retry", label: "Payment retry", color: "var(--text-primary)" },
          { stage: "06 VERIFY", value: "₹34,500", label: "Gateway settled", color: "var(--success)" },
        ].map((s) => (
          <div key={s.stage} style={{
            padding: "0.75rem",
            background: "#0b0f17",
            border: "1px solid var(--border)",
            borderRadius: 4,
          }}>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: 4 }}>
              {s.stage}
            </div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, color: s.color, marginBottom: 2 }}>
              {s.value}
            </div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
