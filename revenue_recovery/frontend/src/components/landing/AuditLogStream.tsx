"use client";

export default function AuditLogStream() {
  const auditLogs = [
    { time: "14:02:01", event: "EVENT RECEIVED", detail: "Gateway timeout received for pay_demo_1787993826 (₹50,000 INR)", color: "var(--danger)" },
    { time: "14:02:01", event: "DIAGNOSED", detail: "Root cause classified: soft_downtime (Temporary 503 bank error)", color: "var(--orange)" },
    { time: "14:02:01", event: "SCORED", detail: "Expected recovery calculated: ₹34,500 EV (Probability 0.69)", color: "#f8fafc" },
    { time: "14:02:01", event: "POLICY ALLOWED", detail: "DefaultRecoveryGuard cleared: retry budget 1/3 within limits", color: "var(--orange)" },
    { time: "14:02:01", event: "EXECUTED", detail: "Dispatched automated retry_payment action to gateway", color: "#f8fafc" },
    { time: "14:02:01", event: "OUTCOME VERIFIED", detail: "Settlement confirmed with bank truth: ₹34,500 recovered", color: "var(--success)" },
  ];

  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 720, marginBottom: "3rem" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--orange)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.75rem",
          }}>
            Immutable Event Auditability
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            color: "#f8fafc",
            lineHeight: 1.15,
            margin: 0,
          }}>
            Every recovery has a story.
          </h2>
          <p style={{ fontSize: "1rem", color: "var(--text-secondary)", marginTop: "0.5rem" }}>
            Every recovery decision can be reconstructed from the audit trail.
          </p>
        </div>

        {/* Audit Log Terminal Record Instrument */}
        <div style={{
          background: "#0b0f17",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "1.75rem",
          fontFamily: "monospace",
        }}>
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            paddingBottom: "1rem",
            marginBottom: "1rem",
            borderBottom: "1px solid var(--border)",
            fontSize: "0.75rem",
          }}>
            <div style={{ color: "#f8fafc", fontWeight: 700 }}>
              CASE #pay_demo_1787993826 · Payment failure (₹50,000 at risk)
            </div>
            <div style={{ color: "var(--success)", fontWeight: 600 }}>
              ● AUDIT LOG VERIFIED
            </div>
          </div>

          <div style={{ display: "grid", gap: "0.75rem" }}>
            {auditLogs.map((log, index) => (
              <div key={index} style={{
                display: "grid",
                gridTemplateColumns: "80px 170px 1fr",
                gap: "1.25rem",
                alignItems: "baseline",
                padding: "0.4rem 0",
                borderBottom: "1px dashed rgba(255, 255, 255, 0.05)",
                fontSize: "0.8125rem",
              }}>
                <span style={{ color: "var(--text-muted)" }}>{log.time}</span>
                <span style={{ fontWeight: 700, color: log.color }}>{log.event}</span>
                <span style={{ color: "var(--text-secondary)" }}>{log.detail}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
