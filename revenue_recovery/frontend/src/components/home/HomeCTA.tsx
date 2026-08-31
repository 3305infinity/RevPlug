"use client";

import Link from "next/link";

export default function HomeCTA() {
  return (
    <div style={{ padding: "4rem 0 5rem", textAlign: "center", borderTop: "1px solid #21262d" }}>
      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
        REVPLUG PRODUCT LAUNCH
      </div>
      <h2 style={{ fontSize: "2rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em", marginBottom: "0.75rem" }}>
        See the recovery engine make a decision.
      </h2>
      <p style={{ fontSize: "0.9375rem", color: "#8b949e", marginBottom: "2rem", maxWidth: 540, margin: "0 auto 2rem" }}>
        Run a single payment failure recovery case or evaluate performance across a 100-case synthetic benchmark batch.
      </p>

      <div style={{ display: "flex", gap: "1rem", justifyContent: "center", alignItems: "center" }}>
        <Link
          href="/run-recovery"
          style={{
            padding: "0.875rem 1.75rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            background: "#2563eb",
            color: "#ffffff",
            borderRadius: 6,
            textDecoration: "none",
          }}
        >
          Run a recovery →
        </Link>

        <Link
          href="/batch-recovery"
          style={{
            padding: "0.875rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "#8b949e",
            textDecoration: "none",
            border: "1px solid #30363d",
            borderRadius: 6,
          }}
        >
          View the benchmark
        </Link>
      </div>
    </div>
  );
}
