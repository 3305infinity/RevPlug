"use client";

export default function DecisionPipeline() {
  return (
    <div style={{ padding: "3rem 0", borderTop: "1px solid #21262d" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          DECISION PIPELINE
        </div>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.01em" }}>
          From payment signal to verified recovery.
        </h2>
        <p style={{ fontSize: "0.8125rem", color: "#8b949e", marginTop: 4 }}>
          Server-side policy authority and settlement verification bound every recovery action.
        </p>
      </div>

      {/* PIPELINE GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "1px", background: "#21262d", borderRadius: 6, overflow: "hidden" }}>
        {[
          { num: "01", label: "Signal", desc: "Payment failure detected" },
          { num: "02", label: "Diagnose", desc: "Failure cause classified" },
          { num: "03", label: "Propose", desc: "Candidate actions ranked" },
          { num: "04", label: "Decide", desc: "EV + policy authority", highlight: true },
          { num: "05", label: "Execute", desc: "Bounded intervention" },
          { num: "06", label: "Verify", desc: "Settlement confirmed" },
        ].map((stage) => (
          <div key={stage.num} style={{ padding: "1.25rem 1rem", background: stage.highlight ? "#161b22" : "#0d1117" }}>
            <div className="font-mono" style={{ fontSize: "0.625rem", color: stage.highlight ? "#2563eb" : "#6e7681", fontWeight: 700, marginBottom: "0.35rem" }}>
              {stage.num}
            </div>
            <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.25rem" }}>
              {stage.label}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#8b949e", lineHeight: 1.4 }}>
              {stage.desc}
            </div>
          </div>
        ))}
      </div>

      {/* MESSAGE */}
      <div style={{ marginTop: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div style={{ fontSize: "1rem", fontWeight: 700, color: "#f0f6fc" }}>
          AI proposes. Policy decides. Settlement proves.
        </div>
        <div style={{ fontSize: "0.8125rem", color: "#8b949e" }}>
          An attempted action is never counted as recovered revenue.
        </div>
      </div>
    </div>
  );
}
