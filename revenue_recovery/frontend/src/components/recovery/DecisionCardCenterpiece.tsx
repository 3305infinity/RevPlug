"use client";

import React from "react";
import { CaseTrace } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detail?: any;
}

function DataBadge({ type }: { type: "evaluation" | "verified" | "projected" | "pending" }) {
  const cfg = {
    evaluation: { label: "Evaluation Data",   color: "#d97706", border: "rgba(217,119,6,0.25)" },
    verified:   { label: "Provider Verified",  color: "#10b981", border: "rgba(16,185,129,0.25)" },
    projected:  { label: "Expected",           color: "#6366f1", border: "rgba(99,102,241,0.25)" },
    pending:    { label: "Pending Verification", color: "#6b7280", border: "rgba(107,114,128,0.25)" },
  }[type];
  return (
    <span style={{
      fontSize: "0.5rem", fontWeight: 700, color: cfg.color,
      border: `1px solid ${cfg.border}`, padding: "1px 5px",
      borderRadius: 3, letterSpacing: "0.05em", textTransform: "uppercase",
      verticalAlign: "middle", marginLeft: 6,
    }}>{cfg.label}</span>
  );
}

export default function DecisionCardCenterpiece({ trace, detail }: Props) {
  if (!trace && !detail) return null;

  const amountAtRisk   = trace ? trace.amount_at_risk_minor / 100 : (detail?.amount_minor || null);
  const failureCategory = trace?.context_snapshot?.failure_category || detail?.root_cause || null;
  const selectedAction  = trace?.ai_recommendation?.selected_action || detail?.proposed_action || null;
  const policyAllowed   = trace ? (trace.safety_decision?.allowed ?? null) : (detail?.policy_allowed ?? null);

  // Expected recovery: only show if backend provides it
  const expNetRaw  = trace ? trace.expected_recovery_minor : (detail?.expected_recovery_value ?? null);
  const expNet     = expNetRaw != null ? expNetRaw / 100 : null;

  // Cost: only show if backend provides it
  const costRaw    = trace ? trace.intervention_cost_minor : null;
  const cost       = costRaw != null ? costRaw / 100 : null;

  // Actual recovery: only from verified outcomes
  const actualRaw  = trace ? trace.verified_recovery_minor : ((detail as any)?.actual_recovery_value ?? null);
  const actual     = actualRaw != null ? actualRaw / 100 : null;

  const isRecovered = (actual != null && actual > 0) || trace?.status === "RECOVERED" || detail?.status === "recovered";
  const isStopped   = detail?.status === "stopped" || trace?.status === "STOPPED";
  const isNoAction  = selectedAction === "no_action" || selectedAction === "stop" || (isStopped && !isRecovered);

  // Classification method: clean labels only
  const classMethod: string = detail?.classification_method || trace?.classification_method || "RULES";
  let methodLabel: string;
  let methodNote: string;
  let methodColor = "#3b82f6";

  if (classMethod === "LLM_PRIMARY") {
    methodLabel = "AI-ASSISTED";
    methodNote  = "Used because available context was ambiguous.";
    methodColor = "#6366f1";
  } else if (classMethod === "LLM_FALLBACK") {
    methodLabel = "AI-ASSISTED (FALLBACK)";
    methodNote  = "Deterministic rules insufficient; AI resolved ambiguity.";
    methodColor = "#d97706";
  } else {
    methodLabel = "RULES SUFFICIENT";
    methodNote  = "AI not required. Deterministic policy fully resolved this case.";
    methodColor = "#3b82f6";
  }

  const fmtINR = (n: number) =>
    "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  // Alternatives from trace if available
  const alternatives: Array<{ action: string; net: number | null; selected: boolean; blocked?: string }> =
    trace?.alternatives
      ? trace.alternatives.map((a: any) => ({
          action: a.action,
          net: a.net_expected_recovery != null ? a.net_expected_recovery / 100 : null,
          selected: a.action === selectedAction,
          blocked: a.policy_blocked ? a.block_reason : undefined,
        }))
      : [];

  return (
    <div style={{
      borderRadius: 8,
      background: "var(--bg-secondary)",
      border: "1px solid var(--border)",
      color: "var(--text-primary)",
      maxWidth: 680,
      margin: "0 auto 1.5rem auto",
      overflow: "hidden",
    }}>
      {/* Header strip */}
      <div style={{
        background: "var(--bg-primary)",
        borderBottom: "1px solid var(--border)",
        padding: "0.875rem 1.25rem",
        display: "flex", justifyContent: "space-between", alignItems: "flex-start",
      }}>
        <div>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Recovery Decision <DataBadge type="evaluation" />
          </div>
          <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, marginTop: 4, color: "#ef4444" }}>
            {amountAtRisk != null ? fmtINR(amountAtRisk) : "—"}
            <span style={{ fontSize: "0.75rem", fontWeight: 500, color: "var(--text-muted)", marginLeft: 8 }}>revenue at risk</span>
          </div>
          {failureCategory && (
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
              {failureCategory.replace(/_/g, " ")}
            </div>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
          {failureCategory && (
            <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#3b82f6", background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.25)", padding: "3px 8px", borderRadius: 4, textTransform: "uppercase" }}>
              {failureCategory.replace(/_/g, " ")}
            </span>
          )}
          <span style={{ fontSize: "0.5625rem", fontWeight: 700, color: methodColor, background: `${methodColor}18`, border: `1px solid ${methodColor}44`, padding: "3px 7px", borderRadius: 4, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            {methodLabel}
          </span>
        </div>
      </div>

      <div style={{ padding: "1rem 1.25rem" }}>

        {/* NO ACTION state */}
        {isNoAction ? (
          <div style={{ marginBottom: "1rem", background: "rgba(107,114,128,0.08)", border: "1px solid rgba(107,114,128,0.2)", borderRadius: 6, padding: "1rem" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
              NO ACTION
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.875rem" }}>
              {detail?.stopped_reason || trace?.stopped_reason || "Further automated intervention is not justified."}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "0.625rem", fontSize: "0.75rem" }}>
              <div style={{ background: "var(--bg-primary)", borderRadius: 5, border: "1px solid var(--border)", padding: "0.5rem" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.5625rem", textTransform: "uppercase", fontWeight: 600 }}>Attempts prevented</div>
                <div style={{ fontFamily: "monospace", fontWeight: 700, marginTop: 2 }}>0</div>
              </div>
              <div style={{ background: "var(--bg-primary)", borderRadius: 5, border: "1px solid var(--border)", padding: "0.5rem" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.5625rem", textTransform: "uppercase", fontWeight: 600 }}>Customer contacts</div>
                <div style={{ fontFamily: "monospace", fontWeight: 700, marginTop: 2 }}>0</div>
              </div>
              <div style={{ background: "var(--bg-primary)", borderRadius: 5, border: "1px solid var(--border)", padding: "0.5rem" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.5625rem", textTransform: "uppercase", fontWeight: 600 }}>Intervention cost</div>
                <div style={{ fontFamily: "monospace", fontWeight: 700, marginTop: 2 }}>₹0</div>
              </div>
            </div>
          </div>
        ) : (
          /* Recommended action + EV */
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.875rem", marginBottom: "1rem" }}>
            <div style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.75rem" }}>
              <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                Recommended Action
              </div>
              <div style={{ fontSize: "1rem", fontWeight: 700, color: "#3b82f6", fontFamily: "monospace" }}>
                {selectedAction ? selectedAction.replace(/_/g, " ").toUpperCase() : "—"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: 4 }}>
                Policy:{" "}
                <strong style={{ color: policyAllowed === null ? "var(--text-muted)" : policyAllowed ? "#10b981" : "#ef4444" }}>
                  {policyAllowed === null ? "Not evaluated" : policyAllowed ? "ALLOWED" : "BLOCKED"}
                </strong>
              </div>
            </div>

            <div style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.75rem" }}>
              <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                Expected Net Recovery <DataBadge type="projected" />
              </div>
              <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 700, color: expNet != null ? "#10b981" : "var(--text-muted)" }}>
                {expNet != null ? fmtINR(expNet) : "—"}
              </div>
              {cost != null && (
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Intervention cost: {fmtINR(cost)}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Decision method explanation */}
        <div style={{ marginBottom: "1rem", padding: "0.625rem 0.875rem", background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 6, fontSize: "0.75rem" }}>
          <span style={{ fontWeight: 700, color: methodColor }}>{methodLabel}:</span>{" "}
          <span style={{ color: "var(--text-secondary)" }}>{methodNote}</span>
        </div>

        {/* Why this action */}
        {!isNoAction && (
          <div style={{ marginBottom: "1rem", background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.875rem" }}>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
              Why This Action
            </div>
            {trace?.decision_evidence ? (
              <ul style={{ margin: 0, paddingLeft: "1.125rem", fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {(trace.decision_evidence as string[]).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            ) : (
              <ul style={{ margin: 0, paddingLeft: "1.125rem", fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {failureCategory && <li>Failure category: {failureCategory.replace(/_/g, " ")}</li>}
                {policyAllowed !== null && <li>Policy state: {policyAllowed ? "Action permitted" : "Action blocked by policy"}</li>}
                {expNet != null && amountAtRisk != null && <li>Economic case: expected recovery ({fmtINR(expNet)}) vs risk ({fmtINR(amountAtRisk)})</li>}
                {detail?.retry_count != null && <li>Retry budget: {detail.retry_count} / 3 used</li>}
                {!failureCategory && !expNet && <li style={{ color: "var(--text-muted)" }}>Decision evidence not available in trace</li>}
              </ul>
            )}
          </div>
        )}

        {/* Alternatives table */}
        {alternatives.length > 0 && (
          <div style={{ marginBottom: "1rem" }}>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
              Action Alternatives
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th style={{ textAlign: "left", padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.5625rem", textTransform: "uppercase" }}>Action</th>
                  <th style={{ textAlign: "right", padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.5625rem", textTransform: "uppercase" }}>Expected Net</th>
                  <th style={{ textAlign: "right", padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.5625rem", textTransform: "uppercase" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {alternatives.map((alt, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)", background: alt.selected ? "rgba(59,130,246,0.05)" : "transparent" }}>
                    <td style={{ padding: "0.4rem 0.5rem", fontWeight: alt.selected ? 700 : 400, fontFamily: "monospace" }}>
                      {alt.action.replace(/_/g, " ")}
                    </td>
                    <td style={{ padding: "0.4rem 0.5rem", textAlign: "right", fontFamily: "monospace", fontWeight: 700, color: alt.net != null ? "#10b981" : "var(--text-muted)" }}>
                      {alt.net != null ? fmtINR(alt.net) : "—"}
                    </td>
                    <td style={{ padding: "0.4rem 0.5rem", textAlign: "right" }}>
                      {alt.selected ? (
                        <span style={{ fontSize: "0.625rem", fontWeight: 700, color: "#3b82f6", background: "rgba(59,130,246,0.12)", padding: "2px 6px", borderRadius: 4 }}>SELECTED</span>
                      ) : alt.blocked ? (
                        <span style={{ fontSize: "0.625rem", fontWeight: 700, color: "#ef4444", background: "rgba(239,68,68,0.08)", padding: "2px 6px", borderRadius: 4 }}>BLOCKED</span>
                      ) : (
                        <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Alternative</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Outcome strip */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: isRecovered ? "rgba(16,185,129,0.08)" : isStopped ? "rgba(107,114,128,0.08)" : "rgba(59,130,246,0.05)",
          border: `1px solid ${isRecovered ? "rgba(16,185,129,0.25)" : isStopped ? "rgba(107,114,128,0.2)" : "rgba(59,130,246,0.2)"}`,
          padding: "0.625rem 0.875rem", borderRadius: 6,
        }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 700, color: isRecovered ? "#10b981" : isStopped ? "#9ca3af" : "var(--text-secondary)" }}>
            {isRecovered ? "VERIFIED RECOVERED" : isStopped ? "RECOVEROS STOPPED" : "AWAITING OUTCOME"}
          </span>
          <span className="font-mono" style={{ fontSize: "0.9375rem", fontWeight: 700, color: isRecovered ? "#10b981" : "var(--text-muted)" }}>
            {isRecovered && actual != null ? fmtINR(actual) : isStopped ? "₹0 intervention cost" : "—"}
            {isRecovered && <DataBadge type="verified" />}
          </span>
        </div>
      </div>
    </div>
  );
}
