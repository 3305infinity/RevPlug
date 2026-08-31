"use client";

export default function RazorpayConnectionSection() {
  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d" }}>
      {/* SECTION HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
            <span style={{ fontSize: "0.625rem", padding: "0.1rem 0.4rem", borderRadius: 4, background: "rgba(16, 185, 129, 0.15)", color: "#10b981", fontWeight: 700, textTransform: "uppercase" }}>
              RAZORPAY TEST MODE
            </span>
            <span style={{ fontSize: "0.6875rem", color: "#6e7681", fontFamily: "monospace" }}>
              HMAC-SHA256 Verification Enabled
            </span>
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
            Built around real payment events.
          </h2>
          <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
            Direct integration with Razorpay Test Mode APIs and webhook event handlers.
          </p>
        </div>
      </div>

      {/* RAZORPAY FLOW PIPELINE */}
      <div
        style={{
          border: "1px solid #21262d",
          borderRadius: 8,
          background: "#0d1117",
          padding: "1.5rem",
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", textTransform: "uppercase", fontSize: "0.75rem", fontFamily: "monospace" }}>
          <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>RAZORPAY TELEMETRY</div>
            <div style={{ color: "#f0f6fc", fontWeight: 700, marginTop: 4 }}>Payment signal</div>
            <div style={{ color: "#8b949e", fontSize: "0.7rem", textTransform: "none", marginTop: 4 }}>Authorization failure event</div>
          </div>

          <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>REVPLUG ENGINE</div>
            <div style={{ color: "#2563eb", fontWeight: 700, marginTop: 4 }}>RevPlug decision</div>
            <div style={{ color: "#8b949e", fontSize: "0.7rem", textTransform: "none", marginTop: 4 }}>AI diagnosis + Policy gate</div>
          </div>

          <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>RAZORPAY API</div>
            <div style={{ color: "#6366f1", fontWeight: 700, marginTop: 4 }}>Bounded action</div>
            <div style={{ color: "#8b949e", fontSize: "0.7rem", textTransform: "none", marginTop: 4 }}>Payment link creation</div>
          </div>

          <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>WEBHOOK RECEIVER</div>
            <div style={{ color: "#f59e0b", fontWeight: 700, marginTop: 4 }}>Signed webhook</div>
            <div style={{ color: "#8b949e", fontSize: "0.7rem", textTransform: "none", marginTop: 4 }}>payment_link.paid event</div>
          </div>

          <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>SETTLEMENT VERIFIER</div>
            <div style={{ color: "#10b981", fontWeight: 700, marginTop: 4 }}>Verified settlement</div>
            <div style={{ color: "#8b949e", fontSize: "0.7rem", textTransform: "none", marginTop: 4 }}>Money settled to ledger</div>
          </div>
        </div>
      </div>
    </div>
  );
}
