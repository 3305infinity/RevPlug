"use client";

export default function RazorpayIntegration() {
  return (
    <section style={{ padding: "4rem 0" }}>
      {/* SECTION HEADER */}
      <div style={{ maxWidth: 640, marginBottom: "2rem" }}>
        <div
          style={{
            fontSize: "0.6875rem",
            fontWeight: 700,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.35rem",
          }}
        >
          INTEGRATION & SETTLEMENT TRUST
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Built around payment event reality.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: 4 }}>
          Native integration with Razorpay APIs and HMAC-SHA256 signed webhook verification.
        </p>
      </div>

      {/* PIPELINE VISUAL */}
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 8,
          background: "var(--bg-primary)",
          padding: "1.5rem",
          marginBottom: "1.5rem",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "1rem",
          }}
          className="grid-responsive-4"
        >
          <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ color: "var(--text-muted)", fontSize: "0.65rem", textTransform: "uppercase", fontWeight: 700 }}>
              1. RAZORPAY SIGNAL
            </div>
            <div style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: "0.875rem", marginTop: 4 }}>
              Payment Failure
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
              payment.failed telemetry
            </div>
          </div>

          <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ color: "var(--text-muted)", fontSize: "0.65rem", textTransform: "uppercase", fontWeight: 700 }}>
              2. REVPLUG POLICY GATE
            </div>
            <div style={{ color: "#2563eb", fontWeight: 700, fontSize: "0.875rem", marginTop: 4 }}>
              Bounded Decision
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
              EV ranking & policy check
            </div>
          </div>

          <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ color: "var(--text-muted)", fontSize: "0.65rem", textTransform: "uppercase", fontWeight: 700 }}>
              3. RAZORPAY API DISPATCH
            </div>
            <div style={{ color: "#6366f1", fontWeight: 700, fontSize: "0.875rem", marginTop: 4 }}>
              Intervention
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
              Payment link creation
            </div>
          </div>

          <div style={{ padding: "1rem", background: "rgba(16, 185, 129, 0.05)", borderRadius: 6, border: "1px solid rgba(16, 185, 129, 0.2)" }}>
            <div style={{ color: "var(--success)", fontSize: "0.65rem", textTransform: "uppercase", fontWeight: 700 }}>
              4. SETTLEMENT VERIFIED
            </div>
            <div style={{ color: "var(--success)", fontWeight: 700, fontSize: "0.875rem", marginTop: 4 }}>
              Ledger Credit
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
              Signed webhook verified
            </div>
          </div>
        </div>
      </div>

      {/* STRONG TRUST STATEMENT */}
      <div style={{ padding: "1.25rem 1.5rem", background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 6 }}>
        <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)" }}>
          “An attempted recovery does not become recovered revenue until settlement is verified.”
        </div>
      </div>
    </section>
  );
}
