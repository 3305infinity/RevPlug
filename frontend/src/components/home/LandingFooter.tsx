"use client";

import Link from "next/link";

export default function LandingFooter() {
  return (
    <footer
      style={{
        padding: "3.5rem 1.5rem 3rem",
        fontSize: "0.8125rem",
        color: "var(--text-muted)",
        background: "var(--bg-root)",
      }}
    >
      <div
        style={{
          maxWidth: 1140,
          margin: "0 auto",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1.25rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.875rem", letterSpacing: "-0.01em" }}>
            RevPlug
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
            © {new Date().getFullYear()} RevPlug
          </span>
        </div>

        <div style={{ display: "flex", gap: "1.75rem", fontSize: "0.8125rem" }}>
          <Link
            href="/dashboard"
            style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500, transition: "color 0.15s ease" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
          >
            Dashboard
          </Link>
          <Link
            href="/policy-simulator"
            style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500, transition: "color 0.15s ease" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
          >
            Policy Engine
          </Link>
          <Link
            href="/proof-lab"
            style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500, transition: "color 0.15s ease" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
          >
            Proof Lab
          </Link>
          <Link
            href="/recovery"
            style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500, transition: "color 0.15s ease" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
          >
            Recovery Workspace
          </Link>
        </div>
      </div>
    </footer>
  );
}
