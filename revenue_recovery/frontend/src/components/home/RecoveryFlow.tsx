"use client";

import { useState } from "react";

interface FlowStep {
  step: string;
  title: string;
  badge: string;
  badgeType: "neutral" | "info" | "success" | "warning" | "danger";
  primaryMeta: string;
  secondaryMeta: string;
  details: {
    eventLabel: string;
    metrics: string;
    explanation: string;
  };
}

const FLOW_STEPS: FlowStep[] = [
  {
    step: "01",
    title: "PAYMENT SIGNAL",
    badge: "₹4,999.00",
    badgeType: "neutral",
    primaryMeta: "payment.failed",
    secondaryMeta: "provider_timeout",
    details: {
      eventLabel: "Event received: payment.failed",
      metrics: "Amount: ₹4,999 · Gateway Error: provider_timeout · Customer: cust_razor_101",
      explanation: "Revenue-risk event detected from real-time gateway telemetry.",
    },
  },
  {
    step: "02",
    title: "DIAGNOSIS",
    badge: "Degradation (91%)",
    badgeType: "info",
    primaryMeta: "Temporary provider degradation",
    secondaryMeta: "Confidence: 0.91",
    details: {
      eventLabel: "AI classification: Temporary provider degradation",
      metrics: "Confidence Score: 0.91 · Signals: gateway_timeout + recent successful payment",
      explanation: "Contextual LLM interprets error context and rules out insufficient funds or customer churn.",
    },
  },
  {
    step: "03",
    title: "PROPOSAL",
    badge: "send_payment_link",
    badgeType: "info",
    primaryMeta: "AI proposed action",
    secondaryMeta: "EV: +₹4,250",
    details: {
      eventLabel: "AI proposed intervention: send_payment_link",
      metrics: "Action: send_payment_link · Cost: ₹0 · Gross EV: ₹4,250",
      explanation: "AI evaluates candidate action matrix and recommends intervention maximizing Expected Value.",
    },
  },
  {
    step: "04",
    title: "POLICY",
    badge: "ALLOW",
    badgeType: "success",
    primaryMeta: "fraud: pass · opt-out: pass",
    secondaryMeta: "budget: pass (1/3)",
    details: {
      eventLabel: "Deterministic policy checks: PASS",
      metrics: "✓ retry budget (1/3) · ✓ opt-out (PASS) · ✓ fraud (PASS) · ✓ EV threshold (PASS)",
      explanation: "Server-side policy engine validates zero-violation safety before authorizing execution.",
    },
  },
  {
    step: "05",
    title: "RAZORPAY",
    badge: "DISPATCHED",
    badgeType: "info",
    primaryMeta: "Test-mode action",
    secondaryMeta: "pay_link_1042 created",
    details: {
      eventLabel: "Razorpay Test Mode API execution",
      metrics: "Action: Payment link created · Link ID: pay_link_1042 · Status: DISPATCHED",
      explanation: "Bounded executor dispatches only the specific action authorized by deterministic policy.",
    },
  },
  {
    step: "06",
    title: "SETTLEMENT",
    badge: "VERIFIED",
    badgeType: "success",
    primaryMeta: "payment.captured",
    secondaryMeta: "HMAC & amount matched",
    details: {
      eventLabel: "Webhook evidence: payment.captured",
      metrics: "Signature: HMAC-SHA256 VERIFIED · Amount: ₹4,999 MATCHED · Payment ID: pay_1042",
      explanation: "Webhook cryptographic evidence is verified before crediting recovery.",
    },
  },
  {
    step: "07",
    title: "RECOVERY LEDGER",
    badge: "₹4,999 VERIFIED",
    badgeType: "success",
    primaryMeta: "Immutable record",
    secondaryMeta: "0 policy violations",
    details: {
      eventLabel: "Financial Truth Ledger updated",
      metrics: "Net Recovered: ₹4,999.00 · Violations: 0 · Audit Entry: #LEDGER-1042",
      explanation: "Authoritative financial record created post-settlement verification.",
    },
  },
];

export default function RecoveryFlow() {
  const [activeIdx, setActiveIdx] = useState<number>(3); // Default focus on Policy node

  const activeStep = FLOW_STEPS[activeIdx] || FLOW_STEPS[0];

  return (
    <div id="visual-flow" style={{ padding: "2.5rem 0 3rem" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          END-TO-END RECOVERY FLOW
        </div>
        <h2 style={{ fontSize: "1.375rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.01em" }}>
          From payment signal to verified settlement
        </h2>
        <p style={{ fontSize: "0.8125rem", color: "#8b949e", marginTop: 4, maxWidth: 680, lineHeight: 1.4 }}>
          Follow a revenue-risk event through RevPlug's operational transaction trace — from gateway failure signal to policy authorization and verified settlement truth.
        </p>
      </div>

      {/* CONTINUOUS HORIZONTAL OPERATIONAL PIPELINE (DESKTOP) */}
      <div style={{ position: "relative", borderTop: "1px solid #21262d", borderBottom: "1px solid #21262d", padding: "1.5rem 0", background: "#0d1117" }}>
        {/* CONTINUOUS CONNECTING LINE */}
        <div
          style={{
            position: "absolute",
            top: "2.75rem",
            left: "5%",
            right: "5%",
            height: "1px",
            background: "#21262d",
            zIndex: 1,
          }}
        />

        {/* ACTIVE HIGHLIGHT SEGMENT */}
        <div
          style={{
            position: "absolute",
            top: "2.75rem",
            left: "5%",
            width: `${((activeIdx + 1) / FLOW_STEPS.length) * 90}%`,
            height: "1px",
            background: "#2563eb",
            zIndex: 2,
            transition: "width 0.25s ease",
          }}
        />

        {/* 7 OPERATIONAL NODES */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", position: "relative", zIndex: 3, gap: "0.5rem" }}>
          {FLOW_STEPS.map((s, idx) => {
            const isSelected = activeIdx === idx;
            const isPolicyNode = idx === 3;

            let badgeBg = "rgba(110, 118, 129, 0.15)";
            let badgeColor = "#8b949e";

            if (s.badgeType === "success") {
              badgeBg = "rgba(16, 185, 129, 0.15)";
              badgeColor = "#10b981";
            } else if (s.badgeType === "info") {
              badgeBg = "rgba(99, 102, 241, 0.15)";
              badgeColor = "#6366f1";
            }

            return (
              <button
                key={s.step}
                onClick={() => setActiveIdx(idx)}
                onMouseEnter={() => setActiveIdx(idx)}
                style={{
                  background: isSelected ? "#161b22" : "transparent",
                  border: "none",
                  borderTop: isSelected ? "2px solid #2563eb" : "2px solid transparent",
                  padding: "0.75rem 0.5rem",
                  textAlign: "left",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  borderRadius: "0 0 4px 4px",
                }}
              >
                {/* STEP NUMBER & INDICATOR NODE */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", marginBottom: "0.5rem" }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: isSelected ? "#2563eb" : isPolicyNode ? "#10b981" : "#30363d",
                      display: "inline-block",
                    }}
                  />
                  <span className="font-mono" style={{ fontSize: "0.625rem", color: isSelected ? "#f0f6fc" : "#6e7681", fontWeight: 700 }}>
                    {s.step}
                  </span>
                </div>

                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: isSelected ? "#ffffff" : "#c9d1d9", marginBottom: "0.25rem" }}>
                  {s.title}
                </div>

                <div
                  className="font-mono"
                  style={{
                    fontSize: "0.625rem",
                    color: isSelected ? "#f0f6fc" : "#8b949e",
                    marginBottom: "0.25rem",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {s.primaryMeta}
                </div>

                <div
                  className="font-mono"
                  style={{
                    display: "inline-block",
                    fontSize: "0.625rem",
                    fontWeight: 600,
                    padding: "0.15rem 0.35rem",
                    borderRadius: 3,
                    background: badgeBg,
                    color: badgeColor,
                  }}
                >
                  {s.badge}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* COMPACT OPERATIONAL INSPECTOR PANEL */}
      <div
        style={{
          marginTop: "1rem",
          padding: "1rem 1.25rem",
          background: "#161b22",
          border: "1px solid #21262d",
          borderRadius: 6,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <div style={{ fontSize: "0.625rem", color: "#6e7681", fontFamily: "monospace", fontWeight: 700, textTransform: "uppercase" }}>
            STAGE {activeStep.step} TRACE SPECIFICATION
          </div>
          <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#f0f6fc", marginTop: 2 }}>
            {activeStep.details.eventLabel}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#8b949e", marginTop: 4 }}>
            “{activeStep.details.explanation}”
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div className="font-mono" style={{ fontSize: "0.75rem", color: "#2563eb", fontWeight: 600 }}>
            {activeStep.details.metrics}
          </div>
          <div style={{ fontSize: "0.625rem", color: "#6e7681", fontFamily: "monospace", marginTop: 4 }}>
            Hover or click any node to inspect
          </div>
        </div>
      </div>

      {/* KEY PRODUCT MESSAGE (PLAIN TYPOGRAPHY - NOT A CARD) */}
      <div style={{ marginTop: "1.5rem", borderTop: "1px solid #21262d", paddingTop: "1.25rem" }}>
        <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.01em" }}>
          AI proposes. Policy decides. Settlement proves.
        </div>
        <div style={{ fontSize: "0.8125rem", color: "#8b949e", marginTop: 4 }}>
          RevPlug never counts an attempted action as recovered revenue.
        </div>
      </div>
    </div>
  );
}
