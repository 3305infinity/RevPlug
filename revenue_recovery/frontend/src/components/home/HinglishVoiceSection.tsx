"use client";

import Link from "next/link";

export default function HinglishVoiceSection() {
  return (
    <section id="hinglish-ptp" style={{ padding: "4rem 0" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "3.5rem",
          alignItems: "center",
        }}
        className="grid-responsive-2"
      >
        {/* LEFT COLUMN: EXPLANATION */}
        <div>
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: "0.35rem",
            }}
          >
            SPECIAL CAPABILITY
          </div>
          <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.25rem)", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.025em", marginBottom: "1rem" }}>
            Hinglish Voice-Assisted Promise-to-Pay
          </h2>
          <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "1.5rem" }}>
            Customers in India frequently explain repayment timing in conversational Hinglish. RevPlug extracts structured payment intent, amount, and promised date directly from voice or chat transcripts.
          </p>

          {/* CAPABILITY STEPS */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem", marginBottom: "1.75rem" }}>
            <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
              <span className="font-mono" style={{ fontSize: "0.75rem", color: "#2563eb", fontWeight: 700, marginTop: 2 }}>01</span>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>Customer responds in Hinglish</div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Natural transcript captured via browser audio speech recognition or chat input.</div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
              <span className="font-mono" style={{ fontSize: "0.75rem", color: "#2563eb", fontWeight: 700, marginTop: 2 }}>02</span>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>Intent & date extracted</div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Extracted into structured record: promised amount, target date, and confidence score.</div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
              <span className="font-mono" style={{ fontSize: "0.75rem", color: "#2563eb", fontWeight: 700, marginTop: 2 }}>03</span>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>Promise-to-Pay recorded</div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Policy engine activates a hold to suppress redundant retry attempts until the promised date.</div>
              </div>
            </div>
          </div>

          <Link
            href="/recovery/rec_item_demo_hinglish/voice-call"
            style={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: "var(--accent)",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.35rem",
            }}
          >
            <span>Try Hinglish Voice PTP interactive demo →</span>
          </Link>
        </div>

        {/* RIGHT COLUMN: RESTRAINED PRODUCT ARTIFACT */}
        <div
          style={{
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "1.5rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", paddingBottom: "0.75rem", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
              HINGLISH INTENT EXTRACTOR
            </span>
            <span style={{ fontSize: "0.6875rem", fontFamily: "monospace", color: "var(--success)" }}>
              Endpoint: /api/recovery-items/.../voice-promise
            </span>
          </div>

          {/* TRANSCRIPT CARD */}
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "1rem",
              marginBottom: "1rem",
            }}
          >
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginBottom: 4 }}>
              CUSTOMER TRANSCRIPT (HINGLISH)
            </div>
            <div style={{ fontSize: "0.875rem", color: "var(--text-primary)", fontStyle: "italic", lineHeight: 1.5 }}>
              “Haan, kal shaam tak payment clear kar dunga ₹15,000. Abhi salary nahi aayi hai.”
            </div>
          </div>

          {/* EXTRACTED METRICS GRID */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "0.75rem",
              marginBottom: "1rem",
            }}
          >
            <div style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.75rem" }}>
              <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>PROMISED AMOUNT</div>
              <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
                ₹15,000.00
              </div>
            </div>

            <div style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.75rem" }}>
              <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>PROMISED DATE</div>
              <div className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
                Tomorrow (Kal Shaam)
              </div>
            </div>
          </div>

          {/* RESULT STATUS */}
          <div
            style={{
              background: "rgba(99, 102, 241, 0.08)",
              border: "1px solid rgba(99, 102, 241, 0.2)",
              borderRadius: 6,
              padding: "0.75rem 1rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "0.6875rem", color: "#6366f1", fontWeight: 700, textTransform: "uppercase" }}>
                PTP HOLD ACTIVATED
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                Automated retries suppressed until promised date
              </div>
            </div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#6366f1" }}>
              WAIT (HOLD)
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
