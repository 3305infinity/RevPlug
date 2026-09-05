"use client";

import Link from "next/link";
import NavbarAuth from "@/components/home/NavbarAuth";

export default function HomeHeader() {
  return (
    <header
      style={{
        borderBottom: "1px solid var(--border)",
        background: "rgba(10, 13, 20, 0.85)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      <div
        style={{
          maxWidth: 1140,
          margin: "0 auto",
          padding: "0.85rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        {/* BRAND & FEATURE LINKS */}
        <div style={{ display: "flex", alignItems: "center", gap: "2.5rem" }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.55rem" }}>
              <div
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 5,
                  background: "#2563eb",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#ffffff",
                  fontSize: "0.75rem",
                  fontWeight: 800,
                  fontFamily: "monospace",
                }}
              >
                R
              </div>
              <span style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                RevPlug
              </span>
            </div>
          </Link>

          {/* REFINED NAVBAR FEATURE OPTIONS */}
          <nav style={{ display: "flex", gap: "1.75rem", fontSize: "0.8125rem" }}>
            <a
              href="#how-it-works"
              style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500, transition: "color 0.15s ease" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
            >
              Risk Surfaces
            </a>
            <a
              href="#control-loop"
              style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500, transition: "color 0.15s ease" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
            >
              Control Loop
            </a>
            <a
              href="#hinglish-ptp"
              style={{ color: "var(--text-secondary)", textDecoration: "none", fontWeight: 500, transition: "color 0.15s ease" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
            >
              Hinglish PTP
            </a>
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
          </nav>
        </div>

        {/* AUTH & DASHBOARD CTA */}
        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
          <NavbarAuth />

          <Link
            href="/dashboard"
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              padding: "0.45rem 0.9rem",
              borderRadius: 6,
              background: "#2563eb",
              color: "#ffffff",
              textDecoration: "none",
              transition: "background 0.15s ease",
            }}
          >
            Open Dashboard
          </Link>
        </div>
      </div>
    </header>
  );
}
