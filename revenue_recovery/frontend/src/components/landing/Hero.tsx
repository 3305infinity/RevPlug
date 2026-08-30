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
      padding: "4.5rem 0 3.5rem",
      borderBottom: "1px solid var(--border)",
      background: "#04060a",
    }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        {/* Confident Restrained Hero Header */}
        <div style={{ maxWidth: 840, marginBottom: "3rem" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--orange)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "1.25rem",
          }}>
            Autonomous Revenue Operations Infrastructure
          </div>

          <h1 style={{
            fontSize: "clamp(2.5rem, 5vw, 4rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            lineHeight: 1.08,
            color: "#f8fafc",
            marginBottom: "1.25rem",
          }}>
            Find revenue that's slipping away.<br />
            <span style={{ color: "var(--orange)" }}>Win it back.</span>
          </h1>

          <p style={{
            fontSize: "1.125rem",
            color: "var(--text-secondary)",
            lineHeight: 1.65,
            maxWidth: 680,
            margin: "0 0 2rem 0",
          }}>
            RecoverOS detects revenue leakage, chooses the safest eligible intervention, and verifies what actually came back.
          </p>

          {/* Action CTAs */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
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
                gap: "0.4rem",
              }}
            >
              <span>Run a Live Recovery</span>
              <span>→</span>
            </Link>

            <a
              href="#how-it-works"
              onClick={scrollTo("how-it-works")}
              style={{
                padding: "0.85rem 1.75rem",
                fontSize: "0.9375rem",
                fontWeight: 500,
                borderRadius: 4,
                background: "#0b0f17",
                border: "1px solid var(--border)",
                color: "#f8fafc",
                textDecoration: "none",
              }}
            >
              Explore the System
            </a>
          </div>

          {/* Understated Core Principle Statement */}
          <div style={{
            fontSize: "0.8125rem",
            fontWeight: 600,
            color: "var(--text-muted)",
            letterSpacing: "0.02em",
          }}>
            AI recommends. Policy decides. Verification proves.
          </div>
        </div>

        {/* Hero Product Visual Instrument */}
        <HeroProductVisual />
      </div>
    </section>
  );
}
