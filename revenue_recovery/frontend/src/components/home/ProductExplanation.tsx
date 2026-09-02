"use client";

import Link from "next/link";

export default function ProductExplanation() {
  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d", borderBottom: "1px solid #21262d" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "2.5rem" }}>
        {/* COLUMN 1 */}
        <div style={{ borderRight: "1px solid #21262d", paddingRight: "2.5rem" }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
            01 / TELEMETRY
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.75rem" }}>
            Find what is slipping
          </h3>
          <p style={{ fontSize: "0.875rem", color: "#8b949e", lineHeight: 1.6, margin: 0 }}>
            Payment failures, degraded gateway authorization signals, and overdue receivables automatically become structured recovery cases.
          </p>
          <div style={{ marginTop: "1rem" }}>
            <Link href="/incidents" style={{ fontSize: "0.75rem", color: "#2563eb", textDecoration: "none", fontWeight: 600 }}>
              View Incidents →
            </Link>
          </div>
        </div>

        {/* COLUMN 2 */}
        <div style={{ borderRight: "1px solid #21262d", paddingRight: "2.5rem" }}>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
            02 / DECISION
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.75rem" }}>
            Decide what is worth doing
          </h3>
          <p style={{ fontSize: "0.875rem", color: "#8b949e", lineHeight: 1.6, margin: 0 }}>
            RevPlug combines Groq LLM failure diagnosis with deterministic server-side policy constraints and expected-value net recovery scoring.
          </p>
          <div style={{ marginTop: "1rem" }}>
            <Link href="/policy-simulator" style={{ fontSize: "0.75rem", color: "#2563eb", textDecoration: "none", fontWeight: 600 }}>
              Preview Policy Impact →
            </Link>
          </div>
        </div>

        {/* COLUMN 3 */}
        <div>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
            03 / TRUTH
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.75rem" }}>
            Count what actually came back
          </h3>
          <p style={{ fontSize: "0.875rem", color: "#8b949e", lineHeight: 1.6, margin: 0 }}>
            A dispatched action is not revenue recovered. Money is counted strictly when authoritative webhook settlement evidence matches expected amounts.
          </p>
          <div style={{ marginTop: "1rem" }}>
            <Link href="/proof-lab" style={{ fontSize: "0.75rem", color: "#2563eb", textDecoration: "none", fontWeight: 600 }}>
              View Performance Proof →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
