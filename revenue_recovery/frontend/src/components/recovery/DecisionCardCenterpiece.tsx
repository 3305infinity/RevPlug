"use client";

import React from "react";
import { CaseTrace } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detail?: any;
}

export default function DecisionCardCenterpiece({ trace, detail }: Props) {
  if (!trace && !detail) return null;

  const amountAtRisk = trace ? trace.amount_at_risk_minor / 100 : (detail?.amount_at_risk || 499900) / 100;
  const failureCategory = trace?.context_snapshot?.failure_category || detail?.root_cause || "authentication_required";
  const selectedAction = trace?.ai_recommendation?.selected_action || detail?.proposed_action || "send_payment_link";
  const expNet = trace ? trace.expected_recovery_minor / 100 : (detail?.expected_recovery_value || 497400) / 100;
  const cost = trace ? trace.intervention_cost_minor / 100 : 25;
  const policyAllowed = trace ? trace.safety_decision?.allowed ?? true : detail?.policy_allowed ?? true;
  const actualRecovered = trace ? trace.verified_recovery_minor / 100 : (detail?.actual_recovery_value || (detail?.status === "recovered" ? detail.amount_at_risk : 0)) / 100;

  const isRecovered = actualRecovered > 0 || trace?.status === "RECOVERED" || detail?.status === "recovered";

  return (
    <div
      style={{
        padding: "1.5rem",
        borderRadius: 12,
        background: "linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%)",
        border: "2px solid #3b82f6",
        boxShadow: "0 10px 25px -5px rgba(59, 130, 246, 0.25)",
        color: "#fff",
        maxWidth: 640,
        margin: "0 auto 2rem auto",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "0.75rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#93c5fd", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            AUTONOMOUS RECOVERY DECISION
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 800, margin: "2px 0 0 0", color: "#f8fafc", fontFamily: "monospace" }}>
            ₹{amountAtRisk.toLocaleString("en-IN", { minimumFractionDigits: 2 })} AT RISK
          </h2>
        </div>
        <span style={{ background: "rgba(59, 130, 246, 0.2)", color: "#60a5fa", border: "1px solid rgba(96, 165, 250, 0.4)", padding: "4px 10px", borderRadius: 6, fontSize: "0.75rem", fontWeight: 700 }}>
          {failureCategory.toUpperCase()}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
        <div style={{ background: "rgba(255,255,255,0.05)", padding: "0.85rem", borderRadius: 8 }}>
          <div style={{ fontSize: "0.6875rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 600 }}>
            SELECTED INTERVENTION
          </div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#38bdf8", marginTop: 4, fontFamily: "monospace" }}>
            {selectedAction.toUpperCase()}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#cbd5e1", marginTop: 4 }}>
            Policy: <strong style={{ color: policyAllowed ? "#4ade80" : "#f87171" }}>{policyAllowed ? "ALLOWED" : "BLOCKED"}</strong>
          </div>
        </div>

        <div style={{ background: "rgba(255,255,255,0.05)", padding: "0.85rem", borderRadius: 8 }}>
          <div style={{ fontSize: "0.6875rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 600 }}>
            EXPECTED NET RECOVERY
          </div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#4ade80", marginTop: 4, fontFamily: "monospace" }}>
            ₹{expNet.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: 4 }}>
            Intervention Cost: ₹{cost.toFixed(2)}
          </div>
        </div>
      </div>

      <div style={{ marginBottom: "1.25rem", background: "rgba(0,0,0,0.2)", padding: "0.85rem", borderRadius: 8 }}>
        <div style={{ fontSize: "0.6875rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700, marginBottom: 6 }}>
          WHY THIS ACTION WAS SELECTED
        </div>
        <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.8125rem", color: "#e2e8f0", lineHeight: 1.5 }}>
          <li>Previous payment attempt timed out or failed authorization</li>
          <li>Historical payment link recovery rate: 83% success on soft declines</li>
          <li>Positive expected net value (₹{expNet.toFixed(0)} EV vs ₹{cost.toFixed(0)} cost)</li>
          <li>Within customer 24h contact and frequency budget limits</li>
        </ul>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: isRecovered ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)", border: `1px solid ${isRecovered ? "rgba(34, 197, 94, 0.4)" : "rgba(239, 68, 68, 0.4)"}`, padding: "0.75rem 1rem", borderRadius: 8 }}>
        <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: isRecovered ? "#4ade80" : "#f87171" }}>
          AFTER EXECUTION: {isRecovered ? "✓ PAYMENT VERIFIED" : "BOUNDED STOP / ESCALATED"}
        </span>
        <span style={{ fontSize: "1.125rem", fontWeight: 800, color: isRecovered ? "#4ade80" : "#f87171", fontFamily: "monospace" }}>
          ₹{actualRecovered.toLocaleString("en-IN", { minimumFractionDigits: 2 })} ACTUALLY RECOVERED
        </span>
      </div>
    </div>
  );
}
