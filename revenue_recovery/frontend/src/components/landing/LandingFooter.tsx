"use client";

import Link from "next/link";

export default function LandingFooter() {
  const scrollTo = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <footer style={{
      padding: "3rem 0 2.5rem",
      background: "#04060a",
      fontSize: "0.8125rem",
      color: "var(--text-muted)",
    }}>
      <div style={{
        maxWidth: 1280,
        margin: "0 auto",
        padding: "0 2rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.5rem",
        alignItems: "center",
        textAlign: "center",
      }}>
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
          <div style={{
            width: 24, height: 24, borderRadius: 4,
            background: "var(--orange)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.75rem", fontWeight: 700, color: "#fff",
          }}>
            R
          </div>
          <span style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f8fafc" }}>
            RecoverOS
          </span>
          <span style={{ color: "var(--border)", opacity: 0.5 }}>|</span>
          <span style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>
            Revenue Recovery Infrastructure
          </span>
        </div>

        {/* Minimal Navigation */}
        <div style={{ display: "flex", alignItems: "center", gap: "1.75rem", flexWrap: "wrap" }}>
          <Link href="/" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>Product</Link>
          <Link href="/dashboard" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>Operations</Link>
          <a href="#safety" onClick={scrollTo("safety")} style={{ color: "var(--text-secondary)", textDecoration: "none" }}>Safety</a>
          <Link href="/activity" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>Audit</Link>
          <Link href="/run-recovery" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>Run Recovery</Link>
        </div>

        <div style={{
          paddingTop: "1.25rem",
          borderTop: "1px solid var(--border)",
          width: "100%",
          fontSize: "0.6875rem",
          color: "var(--text-muted)",
        }}>
          RecoverOS Infrastructure · AI Intelligence with Deterministic Economic Guardrails & Financial Payment Verification
        </div>
      </div>
    </footer>
  );
}
