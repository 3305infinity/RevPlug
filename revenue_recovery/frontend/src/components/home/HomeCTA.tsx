"use client";

import Link from "next/link";

export default function HomeCTA() {
  return (
    <section style={{ textAlign: "left", padding: "3.5rem 0 2.5rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace", marginBottom: "0.5rem" }}>
        <span>RevPlug</span>
        <span>/</span>
        <span style={{ color: "#8b949e" }}>Action</span>
      </div>
      <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "0.5rem", letterSpacing: "-0.02em" }}>
        Run a recovery workflow against a real case.
      </h2>
      <p style={{ fontSize: "1rem", color: "#8b949e", marginBottom: "2rem", maxWidth: 540, lineHeight: 1.6 }}>
        Inspect real-time telemetry diagnosis, fail-closed policy checks, and Razorpay Test Mode settlement verification.
      </p>

      <Link
        href="/run-recovery"
        style={{
          padding: "0.85rem 2rem",
          fontSize: "0.9375rem",
          fontWeight: 600,
          background: "#2563eb",
          color: "#ffffff",
          borderRadius: 6,
          textDecoration: "none",
          display: "inline-block",
        }}
      >
        Run a recovery →
      </Link>
    </section>
  );
}
