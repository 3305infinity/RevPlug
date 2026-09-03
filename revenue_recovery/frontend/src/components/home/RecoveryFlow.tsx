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
    badge: "Soft decline",
    badgeType: "info",
    primaryMeta: "Temporary provider degradation",
    secondaryMeta: "Confidence: 0.91",
    details: {
      eventLabel: "Failure cause classified",
      metrics: "Category: soft · Retryable: yes · Signals: gateway_timeout + recent successful payment",
      explanation: "Failure context is interpreted and routed to the appropriate recovery path.",
    },
  },
  {
    step: "03",
    title: "PROPOSAL",
    badge: "send_payment_link",
    badgeType: "info",
    primaryMeta: "Send payment link",
    secondaryMeta: "EV: +₹4,250",
    details: {
      eventLabel: "Candidate actions evaluated",
      metrics: "Action: send_payment_link · Cost: ₹0 · Gross EV: ₹4,250 · Net EV: ₹4,250",
      explanation: "Candidate actions are ranked by expected net recovery. Highest-value permitted action is selected.",
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
      eventLabel: "Policy evaluation passed",
      metrics: "✓ retry budget (1/3) · ✓ opt-out (PASS) · ✓ fraud (PASS) · ✓ EV threshold (PASS)",
      explanation: "Server-side policy engine validates safety constraints before authorizing execution.",
    },
  },
  {
    step: "05",
    title: "EXECUTE",
    badge: "DISPATCHED",
    badgeType: "info",
    primaryMeta: "Payment link created",
    secondaryMeta: "pay_link_1042",
    details: {
      eventLabel: "Action dispatched",
      metrics: "Action: Payment link created · Link ID: pay_link_1042 · Status: DISPATCHED",
      explanation: "Bounded executor dispatches only the specific action authorized by policy.",
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
  const [activeIdx, setActiveIdx] = useState<number>(3);

  const activeStep = FLOW_STEPS[activeIdx] || FLOW_STEPS[0];

  return (
    <div id="visual-flow" style={{ padding: "3rem 0" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          HOW IT WORKS
        </div>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.01em" }}>
          From payment signal to verified settlement
        </h2>
        <p style={{ fontSize: "0.8125rem", color: "#8b949e", marginTop: 4, maxWidth: 640, lineHeight: 1.4 }}>
          Every revenue-risk event passes through detection, decision, execution, and verification.
        </p>
      </div>

      {/* OPERATIONAL PIPELINE */}
      <div style={{ borderTop: "1px solid #21262d", borderBottom: "1px solid #21262d" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
          {FLOW_STEPS.map((s, idx) => {
            const isSelected = activeIdx === idx;

            return (
              <button
                key={s.step}
                onClick={() => setActiveIdx(idx)}
                onMouseEnter={() => setActiveIdx(idx)}
                style={{
                  background: isSelected ? "#161b22" : "transparent",
                  border: "none",
                  borderTop: isSelected ? "2px solid #2563eb" : "2px solid transparent",
                  padding: "1rem 0.75rem",
                  textAlign: "left",
                  cursor: "pointer",
                  transition: "background 0.15s ease",
                }}
              >
                <div className="font-mono" style={{ fontSize: "0.625rem", color: isSelected ? "#f0f6fc" : "#6e7681", fontWeight: 700, marginBottom: "0.35rem" }}>
                  {s.step}
                </div>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: isSelected ? "#ffffff" : "#c9d1d9", marginBottom: "0.35rem" }}>
                  {s.title}
                </div>
                <div style={{ fontSize: "0.6875rem", color: isSelected ? "#8b949e" : "#6e7681", lineHeight: 1.4 }}>
                  {s.primaryMeta}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* INSPECTOR */}
      <div style={{ marginTop: "1.25rem", padding: "1rem 1.25rem", background: "#161b22", border: "1px solid #21262d", borderRadius: 6 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div className="font-mono" style={{ fontSize: "0.625rem", color: "#6e7681", fontWeight: 700, textTransform: "uppercase", marginBottom: 4 }}>
              Stage {activeStep.step} — {activeStep.title}
            </div>
            <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#f0f6fc", lineHeight: 1.5 }}>
              {activeStep.details.eventLabel}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#8b949e", marginTop: 4, lineHeight: 1.5 }}>
              {activeStep.details.explanation}
            </div>
          </div>
          <div className="font-mono" style={{ fontSize: "0.75rem", color: "#8b949e", textAlign: "right", lineHeight: 1.6 }}>
            {activeStep.details.metrics}
          </div>
        </div>
      </div>

      {/* PRODUCT MESSAGE */}
      <div style={{ marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px solid #21262d" }}>
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
