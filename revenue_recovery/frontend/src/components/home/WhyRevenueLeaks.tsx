"use client";

import { useState } from "react";

const LEAKAGE_VECTORS = [
  {
    num: "01",
    title: "Payment degradation",
    desc: "Root cause classification maps temporary gateway downtime to immediate alternative recovery routes.",
    surface: "Gateway Telemetry",
  },
  {
    num: "02",
    title: "Checkout abandonment",
    desc: "High-intent checkout drop-offs receive targeted payment recovery links before cart expiry.",
    surface: "Checkout Events",
  },
  {
    num: "03",
    title: "Failed subscription",
    desc: "Recurring revenue failures are retried intelligently within policy limits and card cycle timing.",
    surface: "Subscriptions",
  },
  {
    num: "04",
    title: "B2B receivables",
    desc: "Overdue commercial invoices trigger structured follow-up without risking customer relationships.",
    surface: "Receivables",
  },
  {
    num: "05",
    title: "Mandate failure",
    desc: "Failed e-mandate and auto-debit payments are retried within compliance and bank rate caps.",
    surface: "Recurring Mandates",
  },
  {
    num: "06",
    title: "Hinglish voice recovery",
    desc: "Customer repayment intent in conversational Hinglish is transcribed and structured into actionable commitments.",
    surface: "Voice & Messaging",
  },
  {
    num: "07",
    title: "Promise-to-pay",
    desc: "Committed repayment dates and amounts are tracked with active policy holds to prevent redundant retries.",
    surface: "PTP Ledger",
  },
];

export default function WhyRevenueLeaks() {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  return (
    <section
      id="how-it-works"
      style={{
        padding: "5rem 0",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "360px 1fr",
          gap: "4.5rem",
          alignItems: "start",
        }}
        className="grid-responsive-2"
      >
        {/* LEFT COLUMN: EDITORIAL HEADING & INTRO (STICKY ON DESKTOP) */}
        <div
          style={{
            position: "sticky",
            top: "6rem",
          }}
        >
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: "0.75rem",
            }}
          >
            REVENUE RISK SURFACES
          </div>
          <h2
            style={{
              fontSize: "clamp(1.875rem, 3.2vw, 2.375rem)",
              fontWeight: 700,
              color: "var(--text-primary)",
              letterSpacing: "-0.03em",
              lineHeight: 1.15,
              marginBottom: "1.25rem",
            }}
          >
            Revenue rarely disappears in one clean step.
          </h2>
          <p
            style={{
              fontSize: "0.9375rem",
              color: "var(--text-secondary)",
              lineHeight: 1.65,
              margin: 0,
            }}
          >
            A payment can fail. A checkout can be abandoned. A subscription can drop. An invoice can stall. The opportunity is not simply detecting these events — it is deciding what should happen next, and knowing when to stop.
          </p>
        </div>

        {/* RIGHT COLUMN: PREMIUM INDEXED CAPABILITY LIST */}
        <div>
          {LEAKAGE_VECTORS.map((vec, idx) => {
            const isHovered = hoveredIdx === idx;

            return (
              <div
                key={vec.title}
                tabIndex={0}
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
                onFocus={() => setHoveredIdx(idx)}
                onBlur={() => setHoveredIdx(null)}
                style={{
                  padding: "1.35rem 1rem",
                  borderBottom: idx === LEAKAGE_VECTORS.length - 1 ? "none" : "1px solid var(--border-subtle)",
                  display: "grid",
                  gridTemplateColumns: "40px 1fr auto",
                  alignItems: "baseline",
                  gap: "1.5rem",
                  background: isHovered ? "rgba(255, 255, 255, 0.018)" : "transparent",
                  borderLeft: isHovered ? "2px solid #2563eb" : "2px solid transparent",
                  marginLeft: "-2px",
                  cursor: "default",
                  transition: "background 0.18s ease, border-color 0.18s ease",
                  outline: "none",
                }}
              >
                {/* SUBTLE NUMBER INDEX */}
                <div
                  className="font-mono"
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: isHovered ? "var(--text-primary)" : "rgba(148, 163, 184, 0.4)",
                    transition: "color 0.18s ease",
                  }}
                >
                  {vec.num}
                </div>

                {/* TITLE & DESCRIPTION */}
                <div>
                  <div
                    style={{
                      fontSize: "0.9375rem",
                      fontWeight: 600,
                      color: isHovered ? "#ffffff" : "var(--text-primary)",
                      letterSpacing: "-0.01em",
                      transition: "color 0.18s ease",
                    }}
                  >
                    {vec.title}
                  </div>
                  <div
                    style={{
                      fontSize: "0.8125rem",
                      color: isHovered ? "var(--text-primary)" : "var(--text-secondary)",
                      lineHeight: 1.55,
                      marginTop: "0.25rem",
                      maxWidth: 480,
                      transition: "color 0.18s ease",
                    }}
                  >
                    {vec.desc}
                  </div>
                </div>

                {/* UNDERSTATED METADATA SOURCE LABEL */}
                <div
                  style={{
                    textAlign: "right",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.35rem",
                    fontSize: "0.75rem",
                    fontFamily: "monospace",
                    color: isHovered ? "var(--text-secondary)" : "var(--text-muted)",
                    transition: "color 0.18s ease",
                    whiteSpace: "nowrap",
                  }}
                  className="hidden-mobile"
                >
                  <span>{vec.surface}</span>
                  <span
                    style={{
                      display: "inline-block",
                      transform: isHovered ? "translateX(3px)" : "translateX(0)",
                      opacity: isHovered ? 1 : 0.4,
                      transition: "transform 0.18s ease, opacity 0.18s ease",
                      color: "#2563eb",
                    }}
                  >
                    →
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
