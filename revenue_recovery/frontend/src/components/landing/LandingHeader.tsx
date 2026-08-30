"use client";

import Link from "next/link";

export default function LandingHeader() {
  const scrollTo = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <header style={{
      position: "sticky",
      top: 0,
      zIndex: 100,
      background: "rgba(4, 6, 10, 0.95)",
      backdropFilter: "blur(8px)",
      borderBottom: "1px solid var(--border)",
      width: "100%",
    }}>
      <div style={{
        maxWidth: 1280,
        margin: "0 auto",
        padding: "0.75rem 2rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        {/* Brand Logo & Descriptor */}
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: "0.65rem", textDecoration: "none" }}>
          <div style={{
            width: 24, height: 24, borderRadius: 4,
            background: "var(--orange)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.75rem", fontWeight: 700, color: "#fff",
          }}>
            R
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.4rem" }}>
            <span style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f8fafc", letterSpacing: "-0.01em" }}>
              RevPlug
            </span>
            <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>·</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 500 }}>
              Revenue Recovery Infrastructure
            </span>
          </div>
        </Link>

        {/* Minimal Navigation Links */}
        <nav style={{ display: "flex", alignItems: "center", gap: "1.75rem" }}>
          <a
            href="#architecture"
            onClick={scrollTo("architecture")}
            style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500 }}
          >
            Architecture
          </a>
          <a
            href="#control-plane"
            onClick={scrollTo("control-plane")}
            style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500 }}
          >
            Control Plane
          </a>
          <a
            href="#how-it-works"
            onClick={scrollTo("how-it-works")}
            style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500 }}
          >
            Workflow
          </a>
          <a
            href="#safety"
            onClick={scrollTo("safety")}
            style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500 }}
          >
            Safety
          </a>
        </nav>

        {/* Auth CTAs */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Link
            href="/login"
            style={{
              padding: "0.45rem 0.85rem",
              fontSize: "0.8125rem",
              fontWeight: 500,
              color: "#a1a1aa",
              textDecoration: "none",
              transition: "color 0.15s",
            }}
          >
            Log In
          </Link>
          <Link
            href="/signup"
            style={{
              padding: "0.45rem 0.95rem",
              fontSize: "0.8125rem",
              fontWeight: 600,
              borderRadius: 4,
              background: "var(--orange)",
              color: "#fff",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              transition: "background 0.15s",
            }}
          >
            <span>Sign Up</span>
            <span>→</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
