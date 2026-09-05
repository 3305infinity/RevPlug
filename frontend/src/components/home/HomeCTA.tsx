"use client";

import Link from "next/link";

export default function HomeCTA() {
  return (
    <section style={{ padding: "4rem 0 5rem", textAlign: "center" }}>
      <div
        style={{
          fontSize: "0.6875rem",
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: "0.5rem",
        }}
      >
        REVPLUG CONTROL PLANE
      </div>
      <h2 style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em", marginBottom: "0.75rem" }}>
        Explore the full recovery engine.
      </h2>
      <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", marginBottom: "2rem", maxWidth: 540, margin: "0 auto 2rem", lineHeight: 1.6 }}>
        From customer recovery profiles to policy simulation, examine every layer of the revenue recovery control plane.
      </p>

      <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center", alignItems: "center", flexWrap: "wrap" }}>
        <Link
          href="/dashboard"
          style={{
            padding: "0.75rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            background: "#2563eb",
            color: "#ffffff",
            borderRadius: 6,
            textDecoration: "none",
          }}
        >
          Open Dashboard →
        </Link>

        <Link
          href="/customers"
          style={{
            padding: "0.75rem 1.25rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "var(--text-primary)",
            textDecoration: "none",
            border: "1px solid var(--border)",
            borderRadius: 6,
            background: "var(--bg-secondary)",
          }}
        >
          Customer Profiles
        </Link>

        <Link
          href="/strategy-analytics"
          style={{
            padding: "0.75rem 1.25rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "var(--text-primary)",
            textDecoration: "none",
            border: "1px solid var(--border)",
            borderRadius: 6,
            background: "var(--bg-secondary)",
          }}
        >
          Strategy Analytics
        </Link>

        <Link
          href="/policy-simulator"
          style={{
            padding: "0.75rem 1.25rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "var(--text-primary)",
            textDecoration: "none",
            border: "1px solid var(--border)",
            borderRadius: 6,
            background: "var(--bg-secondary)",
          }}
        >
          Policy Simulator
        </Link>
      </div>
    </section>
  );
}
