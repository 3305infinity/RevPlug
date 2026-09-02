"use client";

import Link from "next/link";

export default function HomeCTA() {
  return (
    <div style={{ padding: "4rem 0 5rem", textAlign: "center", borderTop: "1px solid #21262d" }}>
      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
        REVPLUG CONTROL PLANE
      </div>
      <h2 style={{ fontSize: "2rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em", marginBottom: "0.75rem" }}>
        Explore the full recovery engine.
      </h2>
      <p style={{ fontSize: "0.9375rem", color: "#8b949e", marginBottom: "2rem", maxWidth: 540, margin: "0 auto 2rem" }}>
        From live customer intelligence to policy simulation, see every layer of the revenue-recovery control plane.
      </p>

      <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center", alignItems: "center", flexWrap: "wrap" }}>
        <Link
          href="/dashboard"
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
          Dashboard →
        </Link>

        <Link
          href="/customers"
          style={{
            padding: "0.875rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "#f0f6fc",
            textDecoration: "none",
            border: "1px solid #30363d",
            borderRadius: 6,
            background: "transparent",
          }}
        >
          Customer Profiles
        </Link>

        <Link
          href="/strategy-analytics"
          style={{
            padding: "0.875rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "#f0f6fc",
            textDecoration: "none",
            border: "1px solid #30363d",
            borderRadius: 6,
            background: "transparent",
          }}
        >
          Strategy Analytics
        </Link>

        <Link
          href="/policy-simulator"
          style={{
            padding: "0.875rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            color: "#f0f6fc",
            textDecoration: "none",
            border: "1px solid #30363d",
            borderRadius: 6,
            background: "transparent",
          }}
        >
          Policy Simulator
        </Link>
      </div>
    </div>
  );
}
