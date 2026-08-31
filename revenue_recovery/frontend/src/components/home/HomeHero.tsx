"use client";

import Link from "next/link";

export default function HomeHero() {
  const scrollToFlow = (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById("visual-flow");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section style={{ padding: "4rem 0 3rem" }}>
      {/* Subheader Badge */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#8b949e", fontFamily: "monospace", marginBottom: "1.5rem" }}>
        <span style={{ color: "#10b981", fontWeight: 600 }}>RevPlug Infrastructure</span>
        <span>/</span>
        <span>Bounded Revenue Recovery Engine</span>
      </div>

      <div style={{ maxWidth: 840 }}>
        <h1
          style={{
            fontSize: "clamp(2.75rem, 5.5vw, 4.25rem)",
            fontWeight: 700,
            letterSpacing: "-0.03em",
            lineHeight: 1.08,
            marginBottom: "1.5rem",
            color: "#f0f6fc",
          }}
        >
          Recover revenue<br />
          before it disappears.
        </h1>

        <p
          style={{
            fontSize: "1.125rem",
            color: "#8b949e",
            lineHeight: 1.6,
            marginBottom: "2.25rem",
            maxWidth: 720,
          }}
        >
          RevPlug turns payment failures into bounded recovery workflows — diagnosing what happened, choosing the right intervention, and counting money only after settlement is verified.
        </p>

        {/* HERO ACTIONS */}
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <Link
            href="/run-recovery"
            style={{
              padding: "0.875rem 1.75rem",
              fontSize: "0.875rem",
              fontWeight: 600,
              background: "#2563eb",
              color: "#ffffff",
              borderRadius: 6,
              textDecoration: "none",
              transition: "background 0.15s ease",
            }}
          >
            Run a recovery →
          </Link>
          <a
            href="#visual-flow"
            onClick={scrollToFlow}
            style={{
              padding: "0.875rem 1.5rem",
              fontSize: "0.875rem",
              fontWeight: 500,
              color: "#8b949e",
              textDecoration: "none",
              border: "1px solid #30363d",
              borderRadius: 6,
              background: "transparent",
            }}
          >
            See how it works ↓
          </a>
        </div>
      </div>
    </section>
  );
}
