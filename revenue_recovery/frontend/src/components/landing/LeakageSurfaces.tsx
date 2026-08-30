"use client";

export default function LeakageSurfaces() {
  const categories = [
    {
      name: "Payment Failures",
      desc: "Point-of-sale and subscription gateway transaction declines caused by downtime, auth errors, or bank limits.",
    },
    {
      name: "Checkout Abandonment",
      desc: "Customer drop-offs occurring right at payment authorization before checkout completion.",
    },
    {
      name: "Failed Subscriptions",
      desc: "Recurring subscription billing drops and recurring payment processing errors.",
    },
    {
      name: "Overdue Receivables",
      desc: "Delinquent B2B invoices and overdue account balances requiring structured recovery.",
    },
    {
      name: "Mandate Failures",
      desc: "Auto-pay and direct debit recurring mandate execution failures.",
    },
    {
      name: "Promise-to-Pay",
      desc: "Customer payment commitments requiring lifecycle tracking through fulfillment, expiry, and break states.",
    },
  ];

  return (
    <section style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 720, margin: "0 auto 3rem", textAlign: "center" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--accent)",
            marginBottom: "0.75rem",
          }}>
            Coverage Scope
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.5rem)",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            color: "#fff",
            marginBottom: "1rem",
          }}>
            One recovery system. Multiple leakage points.
          </h2>
          <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
            Every revenue failure point feeds directly into the same canonical RecoverOS scoring, policy, and verification workflow.
          </p>
        </div>

        {/* Clean Editorial Layout */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "1.25rem",
        }}>
          {categories.map((cat) => (
            <div key={cat.name} style={{
              background: "#0a0e17",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "1.5rem 1.75rem",
            }}>
              <div style={{
                fontSize: "1rem",
                fontWeight: 700,
                color: "#fff",
                marginBottom: "0.5rem",
                letterSpacing: "-0.01em",
              }}>
                {cat.name}
              </div>
              <p style={{
                fontSize: "0.84375rem",
                color: "var(--text-secondary)",
                lineHeight: 1.6,
                margin: 0,
              }}>
                {cat.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
