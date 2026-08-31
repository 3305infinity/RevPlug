"use client";

export default function DecisionPipeline() {
  return (
    <div style={{ padding: "4rem 0" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          THE DECISION PIPELINE
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
          From payment signal to verified recovery.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
          AI reasoning is one component of the decision pipeline — bounded by server-side policy authority and financial settlement verification.
        </p>
      </div>

      {/* PIPELINE GRID */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          borderTop: "1px solid #21262d",
          borderBottom: "1px solid #21262d",
          background: "#0d1117",
        }}
      >
        {/* STAGE 01 */}
        <div style={{ padding: "1.5rem 1rem", borderRight: "1px solid #21262d" }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", fontWeight: 700 }}>01</div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0" }}>SIGNAL</div>
          <div style={{ fontSize: "0.75rem", color: "#8b949e" }}>Payment failed</div>
        </div>

        {/* STAGE 02 */}
        <div style={{ padding: "1.5rem 1rem", borderRight: "1px solid #21262d" }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", fontWeight: 700 }}>02</div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0" }}>DIAGNOSE</div>
          <div style={{ fontSize: "0.75rem", color: "#8b949e" }}>AI determines cause</div>
        </div>

        {/* STAGE 03 */}
        <div style={{ padding: "1.5rem 1rem", borderRight: "1px solid #21262d" }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", fontWeight: 700 }}>03</div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0" }}>PROPOSE</div>
          <div style={{ fontSize: "0.75rem", color: "#8b949e" }}>Candidate action</div>
        </div>

        {/* STAGE 04 (DECIDE - VISUAL EMPHASIS!) */}
        <div style={{ padding: "1.5rem 1rem", borderRight: "1px solid #21262d", background: "#161b22", outline: "1px solid #2563eb", outlineOffset: -1 }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#2563eb", fontWeight: 700 }}>04 (AUTHORITY)</div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0" }}>DECIDE</div>
          <div style={{ fontSize: "0.75rem", color: "#10b981", fontWeight: 600 }}>EV + Policy Engine</div>
        </div>

        {/* STAGE 05 */}
        <div style={{ padding: "1.5rem 1rem", borderRight: "1px solid #21262d" }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", fontWeight: 700 }}>05</div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0" }}>EXECUTE</div>
          <div style={{ fontSize: "0.75rem", color: "#8b949e" }}>Bounded Razorpay action</div>
        </div>

        {/* STAGE 06 */}
        <div style={{ padding: "1.5rem 1rem" }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", fontWeight: 700 }}>06</div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0" }}>VERIFY</div>
          <div style={{ fontSize: "0.75rem", color: "#8b949e" }}>Settlement evidence</div>
        </div>
      </div>

      {/* ANNOTATIONS */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "1rem", fontSize: "0.75rem", color: "#8b949e", fontFamily: "monospace" }}>
        <span>★ <strong style={{ color: "#f0f6fc" }}>AI proposes. Policy decides.</strong></span>
        <span>★ <strong style={{ color: "#10b981" }}>Settlement proves.</strong></span>
      </div>
    </div>
  );
}
