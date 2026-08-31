"use client";

export default function DecisionBoundary() {
  return (
    <section style={{ padding: "3rem 0", borderTop: "1px solid #1e293b" }}>
      {/* LARGE TYPOGRAPHIC STATEMENT */}
      <div style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "clamp(1.5rem, 3vw, 2.25rem)", fontWeight: 700, color: "#f8fafc", lineHeight: 1.25, letterSpacing: "-0.02em" }}>
          AI proposes.<br />
          Policy decides.<br />
          Execution is bounded.<br />
          Settlement is verified.
        </h2>
      </div>

      {/* 4 TEXT COLUMNS SEPARATED BY THIN VERTICAL RULES — NO CARDS */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "0",
          borderTop: "1px solid #1e293b",
          borderBottom: "1px solid #1e293b",
          padding: "1.75rem 0",
        }}
      >
        <div style={{ paddingRight: "1.5rem" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", fontFamily: "monospace", marginBottom: "0.5rem" }}>
            AI
          </div>
          <div style={{ fontSize: "0.8125rem", color: "#94a3b8", lineHeight: 1.6 }}>
            diagnosis<br />
            candidate intervention<br />
            confidence scoring
          </div>
        </div>

        <div style={{ paddingRight: "1.5rem", paddingLeft: "1.5rem", borderLeft: "1px solid #1e293b" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", fontFamily: "monospace", marginBottom: "0.5rem" }}>
            POLICY
          </div>
          <div style={{ fontSize: "0.8125rem", color: "#94a3b8", lineHeight: 1.6 }}>
            eligibility<br />
            fraud signals<br />
            retry budget<br />
            stopping rules
          </div>
        </div>

        <div style={{ paddingRight: "1.5rem", paddingLeft: "1.5rem", borderLeft: "1px solid #1e293b" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", fontFamily: "monospace", marginBottom: "0.5rem" }}>
            EXECUTION
          </div>
          <div style={{ fontSize: "0.8125rem", color: "#94a3b8", lineHeight: 1.6 }}>
            permitted action only<br />
            Razorpay Test Mode API<br />
            idempotency key lock
          </div>
        </div>

        <div style={{ paddingLeft: "1.5rem", borderLeft: "1px solid #1e293b" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", fontFamily: "monospace", marginBottom: "0.5rem" }}>
            SETTLEMENT
          </div>
          <div style={{ fontSize: "0.8125rem", color: "#94a3b8", lineHeight: 1.6 }}>
            evidence-backed recovery<br />
            authoritative webhook<br />
            verified ledger entry
          </div>
        </div>
      </div>

      {/* VISUALLY PROMINENT STATEMENT */}
      <div style={{ marginTop: "2.5rem", fontSize: "1.125rem", fontWeight: 700, color: "#f8fafc", fontFamily: "monospace" }}>
        AI never directly controls financial execution.
      </div>

      {/* INLINE TRUST CONTROLS LIST */}
      <div style={{ marginTop: "1.5rem", fontSize: "0.75rem", color: "#64748b", fontFamily: "monospace" }}>
        TRUST CONTROLS: Verified settlement · Deterministic policy · Idempotent execution · Stopping rules · Audit trail · AI fallback
      </div>
    </section>
  );
}
