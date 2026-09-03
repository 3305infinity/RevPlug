"use client";

import Link from "next/link";

export default function ProductExplanation() {
  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "3rem" }}>
        {/* COLUMN 1 */}
        <div>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
            01 / Detect
          </div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.5rem" }}>
            Find what is slipping
          </h3>
          <p style={{ fontSize: "0.8125rem", color: "#8b949e", lineHeight: 1.6, margin: 0 }}>
            Payment failures, degraded gateway signals, and overdue receivables automatically become structured recovery cases.
          </p>
        </div>

        {/* COLUMN 2 */}
        <div>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
            02 / Decide
          </div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.5rem" }}>
            Choose the safest, highest-value action
          </h3>
          <p style={{ fontSize: "0.8125rem", color: "#8b949e", lineHeight: 1.6, margin: 0 }}>
            Expected-value scoring ranks interventions. Server-side policy enforces retry budgets, opt-out protection, fraud rules, and contact limits before any action executes.
          </p>
        </div>

        {/* COLUMN 3 */}
        <div>
          <div className="font-mono" style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
            03 / Verify
          </div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.5rem" }}>
            Count only what actually came back
          </h3>
          <p style={{ fontSize: "0.8125rem", color: "#8b949e", lineHeight: 1.6, margin: 0 }}>
            A dispatched action is not recovered revenue. Money is counted only after signed webhook settlement evidence matches the expected amount.
          </p>
        </div>
      </div>
    </div>
  );
}
