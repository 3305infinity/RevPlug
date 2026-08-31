"use client";

import Link from "next/link";
import HeroProductVisual from "./HeroProductVisual";

export default function Hero() {
  const scrollTo = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section style={{
      padding: "4rem 0 3rem",
      borderBottom: "1px solid var(--border)",
      background: "#090d16",
    }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        {/* Confident Restrained Hero Header */}
        <div style={{ maxWidth: 840, marginBottom: "2.5rem" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--accent)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "1rem",
          }}>
            Autonomous Revenue Operations Infrastructure
          </div>

          <h1 style={{
            fontSize: "clamp(2.25rem, 4.5vw, 3.75rem)",
            fontWeight: 700,
            letterSpacing: "-0.03em",
            lineHeight: 1.1,
            color: "#f8fafc",
            marginBottom: "1rem",
          }}>
            Autonomous revenue recovery.<br />
            <span style={{ color: "#60a5fa" }}>Precision intervention &amp; verified settlement.</span>
          </h1>

          <p style={{
            fontSize: "1.0625rem",
            color: "var(--text-secondary)",
            lineHeight: 1.6,
            maxWidth: 680,
            margin: "0 0 1.75rem 0",
          }}>
            RevPlug detects revenue leakage, evaluates optimal bounded interventions, enforces non-bypassable policy rules, and verifies recovered money.
          </p>

          {/* Action CTAs */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.875rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
            <Link
              href="/run-recovery"
              className="btn-primary"
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "0.875rem",
              }}
            >
              <span>Run Single Recovery Flow</span>
              <span>→</span>
            </Link>

            <a
              href="#how-it-works"
              onClick={scrollTo("how-it-works")}
              className="btn-secondary"
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "0.875rem",
              }}
            >
              Explore Operations Dashboard
            </a>
          </div>

          {/* Understated Core Principle Statement */}
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--text-muted)",
            letterSpacing: "0.02em",
            fontFamily: "monospace",
          }}>
            AI decides what to try · Policy decides what is allowed · Settlement decides what counts
          </div>
        </div>

        {/* Hero Product Visual Instrument */}
        <HeroProductVisual />
      </div>
    </section>
  );
}
