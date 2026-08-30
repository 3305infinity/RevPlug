"use client";

import Link from "next/link";

export default function RecoverySurfaces() {
  const surfaces = [
    {
      title: "Payment Failures",
      tagline: "Point-of-Sale & Subscription Recovery",
      desc: "Detect degradation from gateway timeouts, card declines, or auth errors and select bounded recovery actions (smart retry, hosted payment link).",
      features: ["Gateway downtime classification", "Smart retry scheduling", "Payment link generation"],
      cta: "Run Recovery",
      href: "/run-recovery",
      status: "Active Feature",
      color: "var(--accent)",
    },
    {
      title: "Overdue Receivables",
      tagline: "B2B Invoice & Account Collection",
      desc: "Track overdue receivables, calculate expected recovery based on days overdue, and trigger controlled escalation workflows.",
      features: ["Days-overdue risk scoring", "Automated customer outreach", "Human review escalation"],
      cta: "View Recovery Cases",
      href: "/recovery",
      status: "Active Feature",
      color: "var(--purple)",
    },
    {
      title: "Promise-to-Pay Engine",
      tagline: "Commitment Lifecycle Management",
      desc: "Record customer payment promises, monitor commitment deadlines, and handle break/expiry transitions deterministically.",
      features: ["Promise fulfillment tracking", "Expiry state transitions", "Audit log recording"],
      cta: "View Customers",
      href: "/customers",
      status: "Active Feature",
      color: "var(--success)",
    },
  ];

  return (
    <section style={{ padding: "4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 3rem" }}>
        <div style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "var(--accent)",
          marginBottom: "0.5rem",
        }}>
          Recovery Capabilities
        </div>
        <h2 style={{
          fontSize: "clamp(1.75rem, 3vw, 2.35rem)",
          fontWeight: 700,
          color: "#fff",
          marginBottom: "1rem",
        }}>
          Supported Revenue Surfaces
        </h2>
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          RevPlug handles diverse revenue failure modes through dedicated domain handlers.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
        {surfaces.map((s) => (
          <div key={s.title} className="card" style={{
            padding: "1.75rem",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <span style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: s.color }}>
                  {s.tagline}
                </span>
                <span style={{
                  fontSize: "0.625rem",
                  fontWeight: 600,
                  padding: "0.15rem 0.45rem",
                  borderRadius: 4,
                  background: `${s.color}15`,
                  color: s.color,
                }}>
                  {s.status}
                </span>
              </div>

              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                {s.title}
              </h3>

              <p style={{ fontSize: "0.84375rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "1.25rem" }}>
                {s.desc}
              </p>

              <div style={{ display: "grid", gap: "0.5rem", marginBottom: "1.75rem" }}>
                {s.features.map((feat) => (
                  <div key={feat} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.78125rem", color: "var(--text-primary)" }}>
                    <span style={{ color: s.color, fontWeight: 700 }}>✓</span>
                    {feat}
                  </div>
                ))}
              </div>
            </div>

            <Link
              href={s.href}
              className="btn-secondary"
              style={{
                textAlign: "center",
                fontSize: "0.8125rem",
                padding: "0.65rem 1rem",
                borderRadius: 6,
                width: "100%",
                display: "block",
              }}
            >
              {s.cta} →
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
