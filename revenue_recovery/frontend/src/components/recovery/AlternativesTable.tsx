"use client";

import React from "react";
import { CaseTrace, CandidateAction } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
}

const ACTION_LABELS: Record<string, string> = {
  send_payment_link: "Send payment link",
  retry_payment: "Retry payment",
  send_reminder: "Send reminder",
  send_customer_message: "Send customer message",
  alternate_channel: "Alternate payment channel",
  promise_to_pay: "Promise-to-pay workflow",
  send_discount: "Send discount offer",
  escalate_human: "Escalate to human review",
  stop_recovery: "Stop recovery",
  no_action: "No action",
  wait: "Wait",
};

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function AlternativesTable({ trace }: Props) {
  const candidates: CandidateAction[] = trace?.candidate_actions ?? [];

  if (candidates.length === 0) {
    return (
      <div
        style={{
          padding: "1.25rem 1.5rem",
          background: "var(--bg-secondary)",
          borderRadius: 8,
          border: "1px solid var(--border)",
          marginBottom: "1rem",
        }}
      >
        <div
          style={{
            fontSize: "0.6875rem",
            fontWeight: 700,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.07em",
            marginBottom: "0.5rem",
          }}
        >
          Other options considered
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontStyle: "italic" }}>
          Candidate evaluation data is not available for this case.
        </div>
      </div>
    );
  }

  const selectedAction = trace?.product_decision?.selected_action ?? trace?.ai_recommendation?.selected_action;

  // Sort: selected first, then by net expected recovery descending
  const sorted = [...candidates].sort((a, b) => {
    const aSelected = a.action === selectedAction || (a as any).selected;
    const bSelected = b.action === selectedAction || (b as any).selected;
    if (aSelected && !bSelected) return -1;
    if (!aSelected && bSelected) return 1;
    return (b.net_expected_recovery ?? 0) - (a.net_expected_recovery ?? 0);
  });

  return (
    <div
      style={{
        padding: "1.25rem 1.5rem",
        background: "var(--bg-secondary)",
        borderRadius: 8,
        border: "1px solid var(--border)",
        marginBottom: "1rem",
      }}
    >
      <div
        style={{
          fontSize: "0.6875rem",
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.07em",
          marginBottom: "0.875rem",
        }}
      >
        Other options considered
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th
              style={{
                textAlign: "left",
                padding: "0.4rem 0.5rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                fontSize: "0.5625rem",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              Intervention
            </th>
            <th
              style={{
                textAlign: "right",
                padding: "0.4rem 0.5rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                fontSize: "0.5625rem",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              Expected recovery
            </th>
            <th
              style={{
                textAlign: "right",
                padding: "0.4rem 0.5rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                fontSize: "0.5625rem",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              Cost
            </th>
            <th
              style={{
                textAlign: "right",
                padding: "0.4rem 0.5rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                fontSize: "0.5625rem",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              Policy
            </th>
            <th
              style={{
                textAlign: "right",
                padding: "0.4rem 0.5rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                fontSize: "0.5625rem",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              Outcome
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((cand, i) => {
            const isSelected = cand.action === selectedAction || (cand as any).selected;
            const isBlocked = cand.policy_status === "BLOCKED";
            const label = ACTION_LABELS[cand.action] ?? cand.action.replace(/_/g, " ");
            const netMinor = cand.net_expected_recovery ?? 0;
            const costMinor = cand.intervention_cost ?? 0;
            const policyRule = cand.policy_rule;

            let outcomeLabel = "Not selected — lower expected value";
            let outcomeColor = "var(--text-muted)";
            if (isSelected) {
              outcomeLabel = "Selected";
              outcomeColor = "#3b82f6";
            } else if (isBlocked) {
              outcomeLabel = policyRule
                ? `Blocked — ${policyRule.replace(/_/g, " ")}`
                : "Blocked by policy";
              outcomeColor = "#ef4444";
            }

            return (
              <tr
                key={i}
                style={{
                  borderBottom: "1px solid var(--border)",
                  background: isSelected ? "rgba(59,130,246,0.04)" : "transparent",
                  opacity: isBlocked && !isSelected ? 0.7 : 1,
                }}
              >
                <td
                  style={{
                    padding: "0.5rem 0.5rem",
                    fontWeight: isSelected ? 700 : 400,
                    color: isBlocked && !isSelected ? "var(--text-muted)" : "var(--text-primary)",
                  }}
                >
                  {label}
                  {isBlocked && (
                    <span
                      style={{
                        fontSize: "0.5625rem",
                        color: "#ef4444",
                        marginLeft: 6,
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                      }}
                    >
                      BLOCKED
                    </span>
                  )}
                </td>
                <td
                  style={{
                    padding: "0.5rem 0.5rem",
                    textAlign: "right",
                    fontFamily: "monospace",
                    fontWeight: 600,
                    color: isBlocked ? "var(--text-muted)" : netMinor > 0 ? "#10b981" : "var(--text-muted)",
                  }}
                >
                  {netMinor > 0 ? fmtINR(netMinor) : "—"}
                </td>
                <td
                  style={{
                    padding: "0.5rem 0.5rem",
                    textAlign: "right",
                    fontFamily: "monospace",
                    color: "var(--text-muted)",
                    fontSize: "0.75rem",
                  }}
                >
                  {costMinor > 0 ? fmtINR(costMinor) : "—"}
                </td>
                <td style={{ padding: "0.5rem 0.5rem", textAlign: "right" }}>
                  <span
                    style={{
                      fontSize: "0.625rem",
                      fontWeight: 700,
                      color: isBlocked ? "#ef4444" : "#10b981",
                      background: isBlocked ? "rgba(239,68,68,0.08)" : "rgba(16,185,129,0.08)",
                      border: `1px solid ${isBlocked ? "rgba(239,68,68,0.25)" : "rgba(16,185,129,0.25)"}`,
                      padding: "1px 5px",
                      borderRadius: 4,
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                    }}
                  >
                    {isBlocked ? "Blocked" : "Allowed"}
                  </span>
                </td>
                <td
                  style={{
                    padding: "0.5rem 0.5rem",
                    textAlign: "right",
                    fontSize: "0.75rem",
                    color: outcomeColor,
                    fontWeight: isSelected ? 700 : 400,
                  }}
                >
                  {isSelected ? (
                    <span
                      style={{
                        fontSize: "0.625rem",
                        fontWeight: 700,
                        color: "#3b82f6",
                        background: "rgba(59,130,246,0.1)",
                        border: "1px solid rgba(59,130,246,0.3)",
                        padding: "1px 6px",
                        borderRadius: 4,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                      }}
                    >
                      ✓ Selected
                    </span>
                  ) : (
                    <span style={{ color: outcomeColor, fontSize: "0.75rem" }}>{outcomeLabel}</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div
        style={{
          marginTop: "0.75rem",
          fontSize: "0.6875rem",
          color: "var(--text-muted)",
          lineHeight: 1.5,
        }}
      >
        AI proposed candidates; policy determined what was permitted; expected value determined the selection.
      </div>
    </div>
  );
}
