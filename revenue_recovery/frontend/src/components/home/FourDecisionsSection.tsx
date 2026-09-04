"use client";

import Link from "next/link";

const DECISIONS = [
  {
    key: "RECOVER",
    label: "RECOVER",
    tagline: "Act when recovery is safe and worthwhile.",
    description: "The failure is retryable, expected net recovery exceeds cost, and all policy bounds pass.",
    badgeBg: "rgba(16, 185, 129, 0.12)",
    badgeColor: "var(--success)",
    examples: "Gateway timeout · Soft decline · Payment link viable",
  },
  {
    key: "WAIT",
    label: "WAIT",
    tagline: "Hold when intervention is premature.",
    description: "Current timing signals indicate higher probability later. Cooldown active or promise pending.",
    badgeBg: "rgba(99, 102, 241, 0.12)",
    badgeColor: "#6366f1",
    examples: "Active promise-to-pay commitment · Retry cooldown period",
  },
  {
    key: "ESCALATE",
    label: "ESCALATE",
    tagline: "Route cases requiring human judgment.",
    description: "Manual review required due to high enterprise value or complex dispute patterns.",
    badgeBg: "rgba(245, 158, 11, 0.12)",
    badgeColor: "var(--warning)",
    examples: "High-value account threshold · Customer dispute flag",
  },
  {
    key: "STOP",
    label: "STOP",
    tagline: "End recovery when unsafe or uneconomic.",
    description: "Policy constraints or financial logic blocks action. Opted-out customer, fraud signal, or negative EV.",
    badgeBg: "rgba(239, 68, 68, 0.12)",
    badgeColor: "var(--danger)",
    examples: "Fraud signal detected · Opted-out customer · Negative EV",
  },
];

export default function FourDecisionsSection() {
  return (
    <section style={{ padding: "4rem 0" }}>
      {/* SECTION HEADER */}
      <div style={{ maxWidth: 640, marginBottom: "2.5rem" }}>
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
          POLICY OUTCOMES
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Every payment failure gets one authoritative outcome.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: 4 }}>
          RevPlug evaluates every candidate action against deterministic policy authority.
        </p>
      </div>

      {/* RESTRAINED 4 OUTCOMES GRID */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "1.25rem",
          marginBottom: "2.5rem",
        }}
        className="grid-responsive-4"
      >
        {DECISIONS.map((d) => (
          <div
            key={d.key}
            style={{
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "1.25rem",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <span
                  style={{
                    fontSize: "0.6875rem",
                    fontWeight: 700,
                    padding: "0.15rem 0.5rem",
                    borderRadius: 4,
                    background: d.badgeBg,
                    color: d.badgeColor,
                    letterSpacing: "0.05em",
                  }}
                >
                  {d.label}
                </span>
              </div>
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem", lineHeight: 1.3 }}>
                {d.tagline}
              </h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                {d.description}
              </p>
            </div>

            <div
              style={{
                marginTop: "1rem",
                paddingTop: "0.75rem",
                borderTop: "1px solid var(--border-subtle)",
                fontSize: "0.6875rem",
                color: "var(--text-muted)",
                fontFamily: "monospace",
              }}
            >
              {d.examples}
            </div>
          </div>
        ))}
      </div>

      {/* NAVIGATION LINKS */}
      <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", fontSize: "0.8125rem" }}>
        <Link href="/dashboard" style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 600 }}>
          View live outcomes in dashboard →
        </Link>
        <Link href="/policy-simulator" style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500 }}>
          Simulate policy constraints →
        </Link>
      </div>
    </section>
  );
}
