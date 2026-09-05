"use client";

import React from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
}

const POLICY_REASON_LABELS: Record<string, string> = {
  terminal_state_block: "The case is already in a terminal state.",
  opt_out_block: "The customer has opted out of automated recovery contact.",
  systemic_incident_suppress: "A systemic incident is active — individual retries are suppressed.",
  retry_limit: "The retry budget has been exhausted.",
  block_hard_failure: "This failure type cannot be automatically retried.",
  contact_frequency_limit: "Contact frequency limit has been reached for this customer.",
  contact_limit: "Contact budget exhausted for this customer.",
  discount_ceiling: "The requested discount exceeds the autonomous limit.",
  fraud_detected: "This case has been flagged for potential fraud.",
  customer_opted_out: "The customer has opted out of automated communication.",
  systemic_incident_active: "A systemic outage is active — retries are suppressed.",
  retry_budget_exhausted: "The retry budget has been exhausted.",
  CONTACT_FREQUENCY_LIMIT: "Contact frequency limit reached within the last 24 hours.",
  policy_blocked: "The action is not permitted under the current recovery policy.",
  policy_allowed: "The action is permitted under the current recovery policy.",
  allow_stop: "Stopping recovery is always permitted.",
  allow_retry: "Retry is within budget and root cause permits it.",
  allow_outbound: "Contact is within budget.",
  default_deny: "Unknown or unsafe action — blocked by default.",
  escalation_required: "Human review is required before recovery can continue.",
  terminal_state: "The case is in a terminal state.",
  fraud_retry_protection: "Fraud protection blocks automated retries.",
};

function getPolicyLabel(
  code: string | null | undefined,
  reason: string | null | undefined
): string {
  if (!code && !reason) return "Policy evaluation not available.";
  if (code && POLICY_REASON_LABELS[code]) return POLICY_REASON_LABELS[code];
  return reason || code?.replace(/_/g, " ") || "Policy constraint applied.";
}

export default function PolicyCard({ trace, detail }: Props) {
  const safetyDec = trace?.safety_decision as Record<string, any> | null | undefined;
  const policyEval = trace?.policy_evaluations as Record<string, any> | null | undefined;

  const status = (trace?.status ?? detail?.status ?? "").toLowerCase();
  const isExecutedOrRecovered =
    status === "recovered" ||
    status === "pending_verification" ||
    status === "intervention_executed" ||
    status === "intervention_pending" ||
    (trace?.execution as any)?.executed === true ||
    (trace?.settlement_evidence as any)?.verified === true;

  const allowed: boolean | null =
    isExecutedOrRecovered ? true : (safetyDec?.allowed ?? policyEval?.allowed ?? null);
  const requiresHuman = !isExecutedOrRecovered && (policyEval?.requires_human_approval ?? false);
  const reasonCode: string | null =
    isExecutedOrRecovered ? "policy_allowed" : (policyEval?.reason_code ?? safetyDec?.reason_code ?? null);
  const reason: string | null =
    isExecutedOrRecovered ? "This intervention passed the deterministic policy and safety checks." : (policyEval?.reason ?? safetyDec?.reason ?? null);
  const rule: string | null =
    isExecutedOrRecovered ? "policy_allowed" : (policyEval?.policy_rule ?? safetyDec?.rule ?? null);

  const sdDecision = isExecutedOrRecovered ? "ALLOWED" : (safetyDec?.decision ?? "");

  let statusLabel = "Not evaluated";
  let statusColor = "var(--text-muted)";
  let statusBg = "var(--bg-secondary)";
  let statusBorder = "var(--border)";
  let headline = "Policy evaluation not available for this case.";
  let statusIcon = "?";

  if (sdDecision === "ESCALATE" || requiresHuman) {
    statusLabel = "Escalation required";
    statusColor = "#6366f1";
    statusBg = "rgba(99,102,241,0.08)";
    statusBorder = "rgba(99,102,241,0.25)";
    statusIcon = "⚑";
    headline = "This case requires human review before recovery can continue.";
  } else if (allowed === true) {
    statusLabel = "Allowed";
    statusColor = "#10b981";
    statusBg = "rgba(16,185,129,0.08)";
    statusBorder = "rgba(16,185,129,0.25)";
    statusIcon = "✓";
    headline = "✓ Allowed — This intervention passed the deterministic policy and safety checks.";
  } else if (allowed === false) {
    statusLabel = "Blocked";
    statusColor = "#ef4444";
    statusBg = "rgba(239,68,68,0.08)";
    statusBorder = "rgba(239,68,68,0.25)";
    statusIcon = "✗";
    headline = "This intervention cannot be executed because the recovery policy prohibits it.";
  }

  const humanLabel = isExecutedOrRecovered
    ? "Passed all deterministic safety bounds, retry budget checks, and contact frequency limits."
    : getPolicyLabel(reasonCode, reason);

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
        Policy check
      </div>

      <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem" }}>
        {/* Status badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            padding: "0.4rem 0.875rem",
            borderRadius: 6,
            background: statusBg,
            border: `1px solid ${statusBorder}`,
            color: statusColor,
            fontWeight: 700,
            fontSize: "0.875rem",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          <span>{statusIcon}</span>
          <span>{statusLabel}</span>
        </div>

        {/* Explanation */}
        <div style={{ flex: 1 }}>
          <div
            style={{
              fontSize: "0.875rem",
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: "0.375rem",
              lineHeight: 1.4,
            }}
          >
            {headline}
          </div>
          {humanLabel && (
            <div
              style={{
                fontSize: "0.8125rem",
                color: "var(--text-secondary)",
                lineHeight: 1.55,
              }}
            >
              {humanLabel}
            </div>
          )}

          {/* Audit: rule code */}
          {rule && (
            <div
              style={{
                marginTop: "0.5rem",
                fontSize: "0.625rem",
                fontFamily: "monospace",
                color: "var(--text-muted)",
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                borderRadius: 4,
                padding: "0.2rem 0.5rem",
                display: "inline-block",
              }}
            >
              rule: {rule}
            </div>
          )}
        </div>
      </div>

      {/* Architectural note */}
      <div
        style={{
          marginTop: "0.875rem",
          padding: "0.625rem 0.875rem",
          background: "var(--bg-primary)",
          borderRadius: 6,
          border: "1px solid var(--border)",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          lineHeight: 1.5,
        }}
      >
        <strong style={{ color: "var(--text-secondary)" }}>
          AI recommends. Policy controls.
        </strong>{" "}
        The AI can propose an action, but the policy engine determines whether it can execute.
        Money never moves without policy clearance.
      </div>
    </div>
  );
}
