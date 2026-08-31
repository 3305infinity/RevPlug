"use client";

import Link from "next/link";
import { CountUpNumber } from "./motion";

export default function HomeHero() {
  const scrollToCase = (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById("central-case");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section style={{ minHeight: "42vh", display: "flex", flexDirection: "column", justifyContent: "center", padding: "2rem 0 2.5rem" }}>
      {/* Breadcrumb Navigation Path */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace", marginBottom: "1.25rem" }}>
        <span>RevPlug</span>
        <span>/</span>
        <span style={{ color: "#8b949e" }}>Case Workspace</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "3rem", alignItems: "end" }}>
        <div>
          <h1
            style={{
              fontSize: "clamp(2.5rem, 5vw, 3.75rem)",
              fontWeight: 700,
              letterSpacing: "-0.035em",
              lineHeight: 1.08,
              marginBottom: "1.25rem",
              color: "#f0f6fc",
            }}
          >
            Recover revenue<br />
            before it becomes lost revenue.
          </h1>

          <p
            style={{
              fontSize: "1rem",
              color: "#8b949e",
              lineHeight: 1.6,
              marginBottom: "2rem",
              maxWidth: 580,
            }}
          >
            RevPlug finds failed payments, determines why they failed, chooses the safest recovery path, and only counts money after settlement is actually verified.
          </p>

          {/* HERO ACTIONS */}
          <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            <Link
              href="/run-recovery"
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
              Run a recovery →
            </Link>
            <a
              href="#central-case"
              onClick={scrollToCase}
              style={{
                padding: "0.75rem 1.25rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "#8b949e",
                textDecoration: "none",
              }}
            >
              See an example ↓
            </a>
          </div>
        </div>

        {/* UNCONVENTIONAL LAYOUT BREAKOUT: MASSIVE ASYMMETRIC NUMERAL ANCHOR WITH COUNT-UP & SOFT GLOW */}
        <div style={{ textAlign: "right", borderLeft: "1px solid #21262d", paddingLeft: "2.5rem" }}>
          <div style={{ fontSize: "0.6875rem", color: "#6e7681", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            TOTAL PORTFOLIO AT RISK
          </div>
          <div
            className="font-mono glow-red"
            style={{
              fontSize: "clamp(3.5rem, 8vw, 5.5rem)",
              fontWeight: 800,
              color: "#ef4444",
              letterSpacing: "-0.05em",
              lineHeight: 0.95,
              marginTop: "0.5rem",
            }}
          >
            ₹<CountUpNumber value={84} duration={800} />.6K
          </div>
          <div style={{ fontSize: "0.75rem", color: "#8b949e", marginTop: "0.75rem", fontFamily: "monospace" }}>
            100 counterfactual cases
          </div>
        </div>
      </div>
    </section>
  );
}
