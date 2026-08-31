"use client";

import { useEffect, useState, useRef } from "react";

export default function WhyNotRetry() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visibleRows, setVisibleRows] = useState<number>(0);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          let count = 0;
          const interval = setInterval(() => {
            count++;
            setVisibleRows(count);
            if (count >= 5) {
              clearInterval(interval);
            }
          }, 400);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.15 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section ref={containerRef} style={{ padding: "3.5rem 0 2.5rem" }}>
      {/* SECTION HEADER & BREADCRUMB */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace", marginBottom: "1rem" }}>
        <span>RevPlug</span>
        <span>/</span>
        <span style={{ color: "#8b949e" }}>Decision Logic</span>
      </div>

      <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", marginBottom: "1rem", letterSpacing: "-0.02em" }}>
        This wasn&apos;t another retry.
      </h2>

      <p style={{ fontSize: "0.9375rem", color: "#8b949e", lineHeight: 1.6, marginBottom: "2.5rem", maxWidth: 640 }}>
        RevPlug did three things before touching the payment: diagnosed the failure telemetry, verified policy safety bounds, and executed only the permitted action.
      </p>

      {/* REAL TERMINAL LOG STREAM STRUCTURE WITH 400MS STAGGERED REVEAL & TRANSLUCENT CHIPS */}
      <div
        className="glow-box"
        style={{
          background: "rgba(13, 17, 23, 0.95)",
          border: "1px solid #21262d",
          borderRadius: 6,
          padding: "1.25rem 1.5rem",
          fontFamily: "monospace",
          fontSize: "0.8125rem",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* LOG ROW 1: INGESTION */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "110px 140px 1fr",
              gap: "1.25rem",
              alignItems: "baseline",
              opacity: visibleRows >= 1 ? 1 : 0,
              transform: visibleRows >= 1 ? "translateY(0)" : "translateY(8px)",
              transition: "opacity 0.4s ease, transform 0.4s ease",
            }}
          >
            <span style={{ color: "#6e7681" }}>14:02:31.041</span>
            <span
              style={{
                color: "#f59e0b",
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.25)",
                backdropFilter: "blur(4px)",
                padding: "0.15rem 0.4rem",
                borderRadius: 4,
                textAlign: "center",
                fontSize: "0.75rem",
                fontWeight: 600,
              }}
            >
              [INGESTION]
            </span>
            <span style={{ color: "#8b949e" }}>
              Webhook <code style={{ color: "#ef4444" }}>payment.failed</code> ingested (Error: provider_timeout, Risk Amount: <strong style={{ color: "#f0f6fc" }} className="font-mono">₹4,999</strong>)
            </span>
          </div>

          {/* LOG ROW 2: AI DIAGNOSIS */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "110px 140px 1fr",
              gap: "1.25rem",
              alignItems: "baseline",
              opacity: visibleRows >= 2 ? 1 : 0,
              transform: visibleRows >= 2 ? "translateY(0)" : "translateY(8px)",
              transition: "opacity 0.4s ease, transform 0.4s ease",
            }}
          >
            <span style={{ color: "#6e7681" }}>14:02:32.102</span>
            <span
              style={{
                color: "#2563eb",
                background: "rgba(37, 99, 235, 0.08)",
                border: "1px solid rgba(37, 99, 235, 0.25)",
                backdropFilter: "blur(4px)",
                padding: "0.15rem 0.4rem",
                borderRadius: 4,
                textAlign: "center",
                fontSize: "0.75rem",
                fontWeight: 600,
              }}
            >
              [AI_DIAGNOSIS]
            </span>
            <span style={{ color: "#8b949e" }}>
              Groq LLM identified temporary 3DS degradation (Confidence: 91%, Proposed Action: <code style={{ color: "#2563eb" }}>send_payment_link</code>)
            </span>
          </div>

          {/* LOG ROW 3: POLICY GATE — WITH VERDICT HIGHLIGHT FLASH */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "110px 140px 1fr",
              gap: "1.25rem",
              alignItems: "baseline",
              opacity: visibleRows >= 3 ? 1 : 0,
              transform: visibleRows >= 3 ? "translateY(0)" : "translateY(8px)",
              transition: "opacity 0.4s ease, transform 0.4s ease",
            }}
          >
            <span style={{ color: "#6e7681" }}>14:02:32.418</span>
            <span
              className={visibleRows >= 3 ? "verdict-flash" : ""}
              style={{
                color: "#10b981",
                background: "rgba(16, 185, 129, 0.12)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                backdropFilter: "blur(4px)",
                padding: "0.15rem 0.4rem",
                borderRadius: 4,
                textAlign: "center",
                fontSize: "0.75rem",
                fontWeight: 700,
              }}
            >
              [POLICY_GATE]
            </span>
            <span style={{ color: "#8b949e" }}>
              Fail-closed policy engine verified 0 fraud flags, customer consent OK, Net Expected Value &gt; 0. Verdict: <strong style={{ color: "#10b981" }}>ALLOW</strong>
            </span>
          </div>

          {/* LOG ROW 4: EXECUTION */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "110px 140px 1fr",
              gap: "1.25rem",
              alignItems: "baseline",
              opacity: visibleRows >= 4 ? 1 : 0,
              transform: visibleRows >= 4 ? "translateY(0)" : "translateY(8px)",
              transition: "opacity 0.4s ease, transform 0.4s ease",
            }}
          >
            <span style={{ color: "#6e7681" }}>14:02:33.002</span>
            <span
              style={{
                color: "#2563eb",
                background: "rgba(37, 99, 235, 0.08)",
                border: "1px solid rgba(37, 99, 235, 0.25)",
                backdropFilter: "blur(4px)",
                padding: "0.15rem 0.4rem",
                borderRadius: 4,
                textAlign: "center",
                fontSize: "0.75rem",
                fontWeight: 600,
              }}
            >
              [EXECUTION]
            </span>
            <span style={{ color: "#8b949e" }}>
              Dispatched Razorpay Test Mode Payment Link API (<code style={{ color: "#8b949e" }}>plink_demo_9021</code>)
            </span>
          </div>

          {/* LOG ROW 5: SETTLEMENT VERIFIED — WITH VERDICT HIGHLIGHT FLASH */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "110px 140px 1fr",
              gap: "1.25rem",
              alignItems: "baseline",
              opacity: visibleRows >= 5 ? 1 : 0,
              transform: visibleRows >= 5 ? "translateY(0)" : "translateY(8px)",
              transition: "opacity 0.4s ease, transform 0.4s ease",
            }}
          >
            <span style={{ color: "#6e7681" }}>14:03:17.890</span>
            <span
              className={visibleRows >= 5 ? "verdict-flash" : ""}
              style={{
                color: "#10b981",
                background: "rgba(16, 185, 129, 0.12)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                backdropFilter: "blur(4px)",
                padding: "0.15rem 0.4rem",
                borderRadius: 4,
                textAlign: "center",
                fontSize: "0.75rem",
                fontWeight: 700,
              }}
            >
              [SETTLEMENT]
            </span>
            <span style={{ color: "#10b981" }}>
              Authoritative <code style={{ color: "#10b981" }}>payment.authorized</code> webhook received. Credited <strong className="font-mono">₹4,999.00</strong> to verified ledger.
            </span>
          </div>
        </div>
      </div>

      {/* CORE PHILOSOPHICAL STATEMENT */}
      <div style={{ marginTop: "2.5rem", fontSize: "1rem", fontWeight: 600, color: "#f0f6fc", fontFamily: "monospace" }}>
        AI proposes the recovery path. Deterministic policy decides whether it is allowed.
      </div>
    </section>
  );
}
