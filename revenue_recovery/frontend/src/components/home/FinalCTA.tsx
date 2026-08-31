"use client";

import Link from "next/link";

export default function FinalCTA() {
  return (
    <section style={{ textAlign: "center", padding: "3rem 0 2rem", borderTop: "1px solid #1e293b" }}>
      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
        READY TO RECOVER?
      </div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginBottom: "0.5rem" }}>
        Run a recovery workflow against a real case.
      </h2>
      <p style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "1.5rem", maxWidth: 500, margin: "0 auto 1.5rem" }}>
        Inspect real-time telemetry diagnosis, fail-closed policy checks, and Razorpay Test Mode settlement verification.
      </p>

      <Link
        href="/run-recovery"
        style={{
          padding: "0.75rem 1.75rem",
          fontSize: "0.875rem",
          fontWeight: 600,
          background: "#2563eb",
          color: "#ffffff",
          borderRadius: 6,
          textDecoration: "none",
          display: "inline-block",
        }}
      >
        Run Recovery →
      </Link>
    </section>
  );
}
