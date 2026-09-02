"use client";

import React from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
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

const EXECUTION_STATUS_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  EXECUTED: { label: "Completed", color: "#10b981", bg: "rgba(16,185,129,0.08)", border: "rgba(16,185,129,0.25)" },
  NOT_EXECUTED: { label: "Ready", color: "#6366f1", bg: "rgba(99,102,241,0.08)", border: "rgba(99,102,241,0.25)" },
  PENDING: { label: "In progress", color: "#f59e0b", bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.25)" },
  WAITING: { label: "Waiting", color: "#64748b", bg: "rgba(100,116,139,0.08)", border: "rgba(100,116,139,0.25)" },
  BLOCKED: { label: "Blocked", color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.25)" },
  FAILED: { label: "Failed", color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.25)" },
  SKIPPED_BY_POLICY: { label: "Blocked", color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.25)" },
};

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function SelectedIntervention({ trace, detail }: Props) {
  const productDecision = trace?.product_decision;
  const decision = productDecision?.decision ?? null;

  // Only show this section for RECOVER
  if (decision && decision !== "RECOVER") {
    // For STOP/WAIT/ESCALATE — show a different panel
    if (decision === "STOP") {
      const reason = productDecision?.reason || (detail as any)?.stopped_reason || trace?.safety_decision?.reason || "No further automated recovery will be attempted.";
      const ruleCode = productDecision?.reason_code || (detail as any)?.stopped_rule || null;
      return (
        <div
          style={{
            padding: "1.25rem 1.5rem",
            background: "rgba(239,68,68,0.04)",
            borderRadius: 8,
            border: "1px solid rgba(239,68,68,0.2)",
            marginBottom: "1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "#ef4444",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: "0.625rem",
            }}
          >
            ■ Recovery stopped
          </div>
          <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
            No further automated recovery will be attempted.
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.55, marginBottom: ruleCode ? "0.625rem" : 0 }}>
            {reason}
          </div>
          {ruleCode && (
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              Rule: {ruleCode}
            </div>
          )}
        </div>
      );
    }

    if (decision === "WAIT") {
      const reason = productDecision?.reason || "Waiting preserves recovery value — the current moment is not optimal for intervention.";
      const scheduled = productDecision?.scheduled_for;
      return (
        <div
          style={{
            padding: "1.25rem 1.5rem",
            background: "rgba(100,116,139,0.05)",
            borderRadius: 8,
            border: "1px solid rgba(100,116,139,0.2)",
            marginBottom: "1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "#64748b",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: "0.625rem",
            }}
          >
            ◷ Waiting is the decision
          </div>
          <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
            Recovery is paused — acting now would reduce expected value.
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.55 }}>
            {reason}
          </div>
          {scheduled && (
            <div style={{ marginTop: "0.625rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Reassess after:{" "}
              <strong>{new Date(scheduled).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</strong>
            </div>
          )}
        </div>
      );
    }

    if (decision === "ESCALATE") {
      const reason = productDecision?.reason || "This case requires human judgment before recovery can continue.";
      return (
        <div
          style={{
            padding: "1.25rem 1.5rem",
            background: "rgba(99,102,241,0.04)",
            borderRadius: 8,
            border: "1px solid rgba(99,102,241,0.2)",
            marginBottom: "1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "#6366f1",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: "0.625rem",
            }}
          >
            ⚑ Human review required
          </div>
          <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
            A human operator must review this case before recovery continues.
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.55 }}>
            {reason}
          </div>
        </div>
      );
    }
  }

  const selectedAction =
    productDecision?.selected_action ??
    trace?.ai_recommendation?.selected_action ??
    trace?.execution?.action ??
    null;

  if (!selectedAction) return null;

  const actionLabel = ACTION_LABELS[selectedAction] ?? selectedAction.replace(/_/g, " ");
  const policyAllowed = trace?.safety_decision?.allowed ?? trace?.policy_evaluations?.allowed ?? null;

  const execStatusRaw = trace?.execution?.status ?? "NOT_EXECUTED";
  const statusMeta =
    EXECUTION_STATUS_META[execStatusRaw] ?? EXECUTION_STATUS_META.NOT_EXECUTED;

  const expectedMinor = trace?.expected_recovery_minor ?? 0;
  const costMinor = trace?.intervention_cost_minor ?? 0;

  const confidence = trace?.ai_recommendation?.confidence;
  const userSafeReasoning = trace?.ai_recommendation?.user_safe_reasoning;

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
          marginBottom: "1rem",
        }}
      >
        Selected intervention
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", gap: "1rem", alignItems: "start" }}>
        {/* Action */}
        <div>
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 4,
            }}
          >
            Action
          </div>
          <div
            style={{
              fontSize: "1.0625rem",
              fontWeight: 700,
              color: "#3b82f6",
            }}
          >
            {actionLabel}
          </div>
          {userSafeReasoning && (
            <div
              style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.45 }}
            >
              {userSafeReasoning}
            </div>
          )}
          {confidence != null && (
            <div
              style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}
            >
              Confidence: {Math.round(Number(confidence) * 100)}%
            </div>
          )}
        </div>

        {/* Expected recovery */}
        <div>
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 4,
            }}
          >
            Expected recovery
          </div>
          <div
            className="font-mono"
            style={{
              fontSize: "1rem",
              fontWeight: 700,
              color: expectedMinor > 0 ? "#10b981" : "var(--text-muted)",
            }}
          >
            {expectedMinor > 0 ? fmtINR(expectedMinor) : "—"}
          </div>
          {expectedMinor > 0 && (
            <div
              style={{
                fontSize: "0.5rem",
                fontWeight: 700,
                color: "#6366f1",
                border: "1px solid rgba(99,102,241,0.25)",
                padding: "1px 5px",
                borderRadius: 3,
                display: "inline-block",
                marginTop: 3,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Projected
            </div>
          )}
          {costMinor > 0 && (
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 3 }}>
              Cost: {fmtINR(costMinor)}
            </div>
          )}
        </div>

        {/* Policy status */}
        <div>
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 4,
            }}
          >
            Policy
          </div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: policyAllowed === null ? "var(--text-muted)" : policyAllowed ? "#10b981" : "#ef4444",
              background: policyAllowed === null ? "transparent" : policyAllowed ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
              border: `1px solid ${policyAllowed === null ? "var(--border)" : policyAllowed ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}`,
              padding: "0.2rem 0.5rem",
              borderRadius: 4,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            {policyAllowed === null ? "Not evaluated" : policyAllowed ? "✓ Allowed" : "✗ Blocked"}
          </div>
        </div>

        {/* Execution status */}
        <div>
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 4,
            }}
          >
            Status
          </div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: statusMeta.color,
              background: statusMeta.bg,
              border: `1px solid ${statusMeta.border}`,
              padding: "0.2rem 0.5rem",
              borderRadius: 4,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            {statusMeta.label}
          </div>
        </div>
      </div>
    </div>
  );
}
