"use client";

import Link from "next/link";

const DECISIONS = [
  {
    key: "RECOVER",
    label: "RECOVER",
    tagline: "Act now within policy.",
    description: "The opportunity is viable, the intervention is safe, and the expected value exceeds cost. Execute bounded recovery action.",
    color: "#10b981",
    bg: "rgba(16, 185, 129, 0.08)",
    border: "rgba(16, 185, 129, 0.2)",
    examples: ["Gateway timeout · Retry allowed · Budget available", "Soft decline · Payment link viable", "Declined card · Alternate method available"],
  },
  {
    key: "WAIT",
    label: "WAIT",
    tagline: "A better recovery window exists later.",
    description: "Current timing signals indicate higher probability later. Cooldown active, promise pending, or contact limits reached.",
    color: "#6366f1",
    bg: "rgba(99, 102, 241, 0.08)",
    border: "rgba(99, 102, 241, 0.2)",
    examples: ["Active promise-to-pay commitment", "Retry cooldown period active", "Systemic incident suppression active"],
  },
  {
    key: "ESCALATE",
    label: "ESCALATE",
    tagline: "Human judgment is required.",
    description: "The case requires manual review. High value, edge case, unusual pattern, or ambiguous signals that automation cannot resolve.",
    color: "#f59e0b",
    bg: "rgba(245, 158, 11, 0.08)",
    border: "rgba(245, 158, 11, 0.2)",
    examples: ["High-value opportunity above threshold", "Unusual failure pattern detected", "Customer disputes prior recovery attempt"],
  },
  {
    key: "STOP",
    label: "STOP",
    tagline: "Recovery is unsafe, uneconomic, or prohibited.",
    description: "Policy constraints or financial logic blocks action. Opted-out customer, fraud signal, uneconomic EV, or terminal status.",
    color: "#ef4444",
    bg: "rgba(239, 68, 68, 0.08)",
    border: "rgba(239, 68, 68, 0.2)",
    examples: ["Fraud risk signal detected", "Customer opted out of recovery", "Expected value below intervention cost"],
  },
];

export default function FourDecisionsSection() {
  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "2.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          THE FOUR DECISIONS
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
          Every payment failure gets one answer.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
          RevPlug diagnoses, evaluates, and produces a canonical recovery decision — bounded by policy authority.
        </p>
      </div>

      {/* DECISION CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        {DECISIONS.map((d) => (
          <div
            key={d.key}
            style={{
              border: `1px solid ${d.border}`,
              borderRadius: 8,
              background: d.bg,
              padding: "1.25rem",
            }}
          >
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: d.color, letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
              {d.label}
            </div>
            <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#f0f6fc", marginBottom: "0.5rem", lineHeight: 1.3 }}>
              {d.tagline}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#8b949e", lineHeight: 1.5 }}>
              {d.description}
            </div>
            <div style={{ marginTop: "0.875rem", paddingTop: "0.75rem", borderTop: `1px solid ${d.border}` }}>
              <div style={{ fontSize: "0.625rem", color: "#6e7681", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.4rem" }}>
                Examples
              </div>
              {d.examples.map((ex, i) => (
                <div key={i} style={{ fontSize: "0.6875rem", color: "#8b949e", lineHeight: 1.4, marginBottom: "0.2rem" }}>
                  · {ex}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* PRODUCT LINK STRIP */}
      <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
        <Link
          href="/dashboard"
          style={{ fontSize: "0.8125rem", color: "#2563eb", textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.35rem" }}
        >
          See live decisions in the dashboard →
        </Link>
        <Link
          href="/customers"
          style={{ fontSize: "0.8125rem", color: "#8b949e", textDecoration: "none", fontWeight: 500, display: "flex", alignItems: "center", gap: "0.35rem" }}
        >
          Customer recovery profiles →
        </Link>
        <Link
          href="/policy-simulator"
          style={{ fontSize: "0.8125rem", color: "#8b949e", textDecoration: "none", fontWeight: 500, display: "flex", alignItems: "center", gap: "0.35rem" }}
        >
          Preview policy impact →
        </Link>
      </div>
    </div>
  );
}
