"use client";

import Link from "next/link";

export default function FinalCTA() {
  return (
    <section id="demo" style={{
      padding: "5rem 0",
      borderBottom: "1px solid var(--border)",
      background: "#04060a",
      textAlign: "center",
    }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 740, margin: "0 auto" }}>
          <h2 style={{
            fontSize: "clamp(2rem, 4vw, 3rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            color: "#f8fafc",
            marginBottom: "2rem",
            lineHeight: 1.15,
          }}>
            See what happens when revenue recovery<br />
            becomes an engineered system.
          </h2>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "1.25rem", flexWrap: "wrap" }}>
            <Link
              href="/run-recovery"
              style={{
                padding: "0.85rem 1.75rem",
                fontSize: "0.9375rem",
                fontWeight: 600,
                borderRadius: 4,
                background: "var(--orange)",
                color: "#fff",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span>Run a Live Recovery</span>
              <span>→</span>
            </Link>

            <Link
              href="/dashboard"
              style={{
                padding: "0.85rem 1.75rem",
                fontSize: "0.9375rem",
                fontWeight: 500,
                borderRadius: 4,
                background: "#0b0f17",
                border: "1px solid var(--border)",
                color: "#f8fafc",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span>Open Operations</span>
              <span>→</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
