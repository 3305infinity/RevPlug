"use client";

import Link from "next/link";

export default function HomeHero() {
  const scrollToHowItWorks = (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById("how-it-works");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section style={{ padding: "4rem 0 3.5rem" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.1fr 0.9fr",
          gap: "3.5rem",
          alignItems: "center",
        }}
        className="grid-responsive-2"
      >
        {/* LEFT: HERO COPY & CTAS */}
        <div>

          {/* HEADLINE */}
          <h1
            style={{
              fontSize: "clamp(2.5rem, 4.5vw, 3.75rem)",
              fontWeight: 700,
              letterSpacing: "-0.035em",
              lineHeight: 1.1,
              marginBottom: "1.25rem",
              color: "var(--text-primary)",
            }}
          >
            Turn failed payments into recovered revenue.
          </h1>

          {/* SUPPORTING COPY */}
          <p
            style={{
              fontSize: "1.0625rem",
              color: "var(--text-secondary)",
              lineHeight: 1.6,
              marginBottom: "2rem",
              maxWidth: 580,
            }}
          >
            RevPlug finds revenue at risk, chooses the next recovery action within policy, and counts the money only after settlement is verified.
          </p>

          {/* MAXIMUM 2 CTAS */}
          <div style={{ display: "flex", gap: "0.875rem", alignItems: "center", flexWrap: "wrap" }}>
            <Link
              href="/dashboard"
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "0.875rem",
                fontWeight: 600,
                background: "#2563eb",
                color: "#ffffff",
                borderRadius: 6,
                textDecoration: "none",
                transition: "background 0.15s ease",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              <span>Open Dashboard</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>

            <a
              href="#how-it-works"
              onClick={scrollToHowItWorks}
              style={{
                padding: "0.75rem 1.35rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "var(--text-secondary)",
                textDecoration: "none",
                border: "1px solid var(--border)",
                borderRadius: 6,
                background: "var(--bg-secondary)",
                transition: "border-color 0.15s ease, color 0.15s ease",
              }}
            >
              See how it works ↓
            </a>
          </div>
        </div>

        {/* RIGHT: HERO VISUAL — REFINED PRODUCT ARTIFACT */}
        <div
          style={{
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            padding: "1.5rem",
            boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.5)",
          }}
        >
          {/* ARTIFACT HEADER WITH PROVENANCE BADGE */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              paddingBottom: "1rem",
              borderBottom: "1px solid var(--border)",
              marginBottom: "1.25rem",
            }}
          >
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              RECOVERY DECISION TRACE
            </div>

            {/* HONEST DATA PROVENANCE LABEL */}
            <div
              style={{
                fontSize: "0.6875rem",
                color: "var(--text-muted)",
                fontFamily: "monospace",
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                background: "var(--bg-secondary)",
                padding: "0.2rem 0.5rem",
                borderRadius: 4,
                border: "1px solid var(--border)",
              }}
            >
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#f59e0b" }} />
              <span>Illustrative case · Razorpay Test Mode</span>
            </div>
          </div>

          {/* PRODUCT STEP 1: PAYMENT FAILED */}
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "0.875rem 1rem",
              marginBottom: "0.875rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--danger)", fontWeight: 700, textTransform: "uppercase" }}>
                PAYMENT FAILED
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                cust_razor_101 · Gateway Timeout
              </div>
            </div>
            <div className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
              ₹4,999
            </div>
          </div>

          {/* PRODUCT STEP 2: RECOMMENDED ACTION & POLICY */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "0.75rem",
              marginBottom: "0.875rem",
            }}
          >
            <div style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.875rem" }}>
              <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
                RECOMMENDED ACTION
              </div>
              <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--accent)", marginTop: 4 }}>
                Send payment link
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: 2 }}>
                Expected recovery: <span className="font-mono" style={{ color: "var(--success)", fontWeight: 600 }}>₹4,799</span>
              </div>
            </div>

            <div style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.875rem" }}>
              <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
                POLICY AUTHORITY
              </div>
              <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--success)", marginTop: 4 }}>
                ALLOWED
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: 2 }}>
                Retry budget: 1/3 (Pass)
              </div>
            </div>
          </div>

          {/* PRODUCT STEP 3: SETTLEMENT VERIFIED */}
          <div
            style={{
              background: "rgba(16, 185, 129, 0.06)",
              border: "1px solid rgba(16, 185, 129, 0.2)",
              borderRadius: 6,
              padding: "0.875rem 1rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--success)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                SETTLEMENT VERIFIED
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                HMAC-SHA256 Signed Webhook Matched
              </div>
            </div>
            <div className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--success)" }}>
              +₹4,999
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
