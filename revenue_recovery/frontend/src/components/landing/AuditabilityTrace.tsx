"use client";

export default function AuditabilityTrace() {
  const auditLogs = [
    { time: "14:02:01.102", event: "EVENT_RECEIVED", actor: "gateway_webhook", detail: "Payment failure payload pay_demo_1787993826 received (₹50,000 INR)" },
    { time: "14:02:01.145", event: "IDEMPOTENCY_PASS", actor: "idempotency_store", detail: "Event ID evt_demo_10928 verified unique. Inserted to provider_events" },
    { time: "14:02:01.210", event: "DIAGNOSED", actor: "failure_classifier", detail: "Classified root cause: soft_downtime (Temporary 503 from bank issuer)" },
    { time: "14:02:01.290", event: "SCORED", actor: "ev_scorer", detail: "Calculated EV = ₹34,500 (Prob: 0.69, Amount: 50,000, Cost: 100)" },
    { time: "14:02:01.350", event: "RECOMMENDED", actor: "decision_agent", detail: "Proposed action: retry_payment (Confidence: 0.85, Model: mock)" },
    { time: "14:02:01.412", event: "POLICY_ALLOWED", actor: "policy_guard", detail: "DefaultRecoveryGuard evaluated: ALLOWED (Rule: allow_retry_budget_1/3)" },
    { time: "14:02:01.520", event: "INTERVENTION_EXECUTED", actor: "simulated_executor", detail: "Dispatched automated retry payment request to payment gateway" },
    { time: "14:02:01.890", event: "OUTCOME_VERIFIED", actor: "outcome_verifier", detail: "Gateway confirmed status: settlement_succeeded (Verified ₹34,500)" },
  ];

  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 720, margin: "0 auto 3.5rem", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--accent)",
            marginBottom: "0.75rem",
          }}>
            Auditability & Reconstructibility
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.5rem)",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            color: "#fff",
            marginBottom: "1rem",
          }}>
            Every recovery has a story.
          </h2>
          <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
            Every recovery decision can be reconstructed from the audit trail.
          </p>
        </div>

        {/* System Terminal Log Trace Container */}
        <div style={{
          background: "#060911",
          border: "1px solid var(--border)",
          borderRadius: 8,
          overflow: "hidden",
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.4)",
        }}>
          {/* Terminal Window Header */}
          <div style={{
            background: "#0f172a",
            padding: "0.75rem 1.25rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid var(--border-subtle)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444", opacity: 0.7 }} />
              <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b", opacity: 0.7 }} />
              <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#10b981", opacity: 0.7 }} />
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace", marginLeft: 8 }}>
                RevPlug Audit Stream — Event Log Trace [Item: pay_demo_1787993826]
              </span>
            </div>
            <span style={{ fontSize: "0.6875rem", color: "var(--success)", fontWeight: 600, fontFamily: "monospace" }}>
              ● IMMUTABLE
            </span>
          </div>

          {/* Log Lines */}
          <div style={{ padding: "1.25rem 1.5rem", display: "grid", gap: "0.625rem", fontFamily: "monospace", fontSize: "0.8125rem" }}>
            {auditLogs.map((log) => (
              <div key={log.time} style={{
                display: "grid",
                gridTemplateColumns: "110px 180px 160px 1fr",
                gap: "1rem",
                alignItems: "baseline",
                padding: "0.35rem 0",
                borderBottom: "1px dashed rgba(255, 255, 255, 0.05)",
              }}>
                <span style={{ color: "var(--text-muted)" }}>{log.time}</span>
                <span style={{
                  color: log.event.includes("VERIFIED") || log.event.includes("ALLOWED") ? "var(--success)" : log.event.includes("RECEIVED") ? "var(--accent)" : "var(--text-primary)",
                  fontWeight: 700,
                }}>
                  {log.event}
                </span>
                <span style={{ color: "var(--accent)", opacity: 0.9 }}>@{log.actor}</span>
                <span style={{ color: "var(--text-secondary)" }}>{log.detail}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
