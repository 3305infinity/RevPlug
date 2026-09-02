"use client";

import React, { useEffect, useState } from "react";
import { CaseTrace, CaseDetail, ProductDecisionPayload, TimingEvaluation, api } from "@/lib/api";
import DecisionBadge from "@/components/shared/DecisionBadge";
import TimingBadge from "@/components/recovery/TimingBadge";

interface Props {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
  itemId: string;
  amountAtRiskMinor: number;
  customerId: string;
  customerName: string;
}

function resolveProductDecision(
  trace: CaseTrace | null,
  detail: CaseDetail | null
): ProductDecisionPayload | null {
  if (trace?.product_decision) return trace.product_decision;

  // Fallback: derive from available status
  const status = trace?.status ?? detail?.status ?? "";
  const s = status.toLowerCase();
  if (s === "recovered") {
    return {
      decision: "RECOVER",
      reason_code: "recovered",
      reason: "Payment recovered successfully.",
      selected_action: trace?.ai_recommendation?.selected_action ?? null,
      policy_status: "ALLOWED",
      requires_human_review: false,
      terminal: true,
      scheduled_for: null,
    };
  }
  if (s === "stopped") {
    const stopReason =
      (detail as any)?.stopped_reason ||
      trace?.safety_decision?.reason ||
      "Recovery was stopped by policy.";
    return {
      decision: "STOP",
      reason_code: (detail as any)?.stopped_rule || "policy_stop",
      reason: stopReason,
      selected_action: null,
      policy_status: "BLOCKED",
      requires_human_review: false,
      terminal: true,
      scheduled_for: null,
    };
  }
  if (s === "escalated") {
    return {
      decision: "ESCALATE",
      reason_code: "escalation_required",
      reason: "This case requires human judgment before recovery can continue.",
      selected_action: null,
      policy_status: "ESCALATE",
      requires_human_review: true,
      terminal: false,
      scheduled_for: null,
    };
  }
  if (trace?.safety_decision?.allowed === false && s !== "escalated") {
    return {
      decision: "STOP",
      reason_code: trace.safety_decision.reason_code ?? "policy_blocked",
      reason: trace.safety_decision.reason ?? "Action blocked by recovery policy.",
      selected_action: null,
      policy_status: "BLOCKED",
      requires_human_review: false,
      terminal: false,
      scheduled_for: null,
    };
  }
  if (trace?.ai_recommendation?.selected_action) {
    return {
      decision: "RECOVER",
      reason_code: "actionable",
      reason: trace.ai_recommendation.user_safe_reasoning ?? "Recovery action is ready to execute.",
      selected_action: trace.ai_recommendation.selected_action,
      policy_status: "ALLOWED",
      requires_human_review: false,
      terminal: false,
      scheduled_for: null,
    };
  }
  return null;
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
  wait: "Wait for better window",
};

const DECISION_CONTEXT: Record<string, { headline: string; subtext: string; borderColor: string }> = {
  RECOVER: {
    headline: "Autonomous recovery action is underway.",
    subtext: "RevPlug has identified the highest-value permitted intervention and is executing it.",
    borderColor: "rgba(16,185,129,0.35)",
  },
  WAIT: {
    headline: "Waiting is the optimal decision.",
    subtext:
      "Acting now would reduce expected recovery. RevPlug is holding for a better window.",
    borderColor: "rgba(100,116,139,0.35)",
  },
  ESCALATE: {
    headline: "Human review is required.",
    subtext:
      "This case contains ambiguity or risk that requires human judgment before recovery can proceed.",
    borderColor: "rgba(99,102,241,0.35)",
  },
  STOP: {
    headline: "Recovery is intentionally stopped.",
    subtext:
      "Further automated intervention is not permitted or not economically justified. This is a controlled outcome.",
    borderColor: "rgba(239,68,68,0.3)",
  },
};

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function RecoveryDecisionCard({ trace, detail, itemId, amountAtRiskMinor, customerId, customerName }: Props) {
  const productDecision = resolveProductDecision(trace, detail);
  const decision = productDecision?.decision ?? "STOP";
  const ctx = DECISION_CONTEXT[decision] ?? DECISION_CONTEXT.STOP;
  const [timingEvaluation, setTimingEvaluation] = useState<TimingEvaluation | null>(null);

  useEffect(() => {
    if (decision === "WAIT" && itemId) {
      api.evaluateTiming(itemId)
        .then(setTimingEvaluation)
        .catch(() => setTimingEvaluation(null));
    } else {
      setTimingEvaluation(null);
    }
  }, [decision, itemId]);

  const failureCategory =
    trace?.context_snapshot?.failure_category ??
    (detail as any)?.root_cause ??
    null;

  const createdAt = detail?.created_at ?? null;

  return (
    <div
      style={{
        border: `2px solid ${ctx.borderColor}`,
        borderRadius: 10,
        background: "var(--bg-secondary)",
        padding: "1.5rem 2rem",
        marginBottom: "1rem",
      }}
    >
      {/* Top row: case ID + customer + amount at risk */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          <span
            className="font-mono"
            style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}
          >
            {itemId}
          </span>
          <span style={{ color: "var(--border)" }}>·</span>
          <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--text-primary)" }}>{customerName}</strong>
            <span
              className="font-mono"
              style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginLeft: "0.5rem" }}
            >
              ({customerId})
            </span>
          </span>
          {failureCategory && (
            <>
              <span style={{ color: "var(--border)" }}>·</span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {failureCategory.replace(/_/g, " ")}
              </span>
            </>
          )}
          {createdAt && (
            <>
              <span style={{ color: "var(--border)" }}>·</span>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                {new Date(createdAt).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
              </span>
            </>
          )}
        </div>

        {/* Revenue at risk — dominant number */}
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "#ef4444",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: 4,
            }}
          >
            Revenue at Risk
          </div>
          <div
            className="font-mono"
            style={{ fontSize: "2.5rem", fontWeight: 800, color: "#ef4444", lineHeight: 1 }}
          >
            {fmtINR(amountAtRiskMinor)}
          </div>
        </div>
      </div>

      {/* THE DECISION — dominant */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "1.25rem",
          padding: "1.25rem",
          background: "var(--bg-primary)",
          borderRadius: 8,
          border: `1px solid ${ctx.borderColor}`,
        }}
      >
        <div style={{ flexShrink: 0, paddingTop: 2 }}>
          <DecisionBadge
            decision={decision as any}
            selectedAction={productDecision?.selected_action}
          />
        </div>

        <div style={{ flex: 1 }}>
          <div
            style={{
              fontSize: "1.0625rem",
              fontWeight: 700,
              color: "var(--text-primary)",
              marginBottom: "0.5rem",
              lineHeight: 1.35,
            }}
          >
            {ctx.headline}
          </div>
          {/* Primary reason from backend */}
          {productDecision?.reason && (
            <div
              style={{
                fontSize: "0.875rem",
                color: "var(--text-secondary)",
                lineHeight: 1.55,
                marginBottom: "0.5rem",
              }}
            >
              {productDecision.reason}
            </div>
          )}
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              lineHeight: 1.5,
            }}
          >
            {ctx.subtext}
          </div>

          {/* Selected action if RECOVER */}
          {decision === "RECOVER" && productDecision?.selected_action && (
            <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  color: "#10b981",
                  background: "rgba(16,185,129,0.08)",
                  border: "1px solid rgba(16,185,129,0.2)",
                  padding: "0.25rem 0.6rem",
                  borderRadius: 5,
                }}
              >
                →{" "}
                {ACTION_LABELS[productDecision.selected_action] ??
                  productDecision.selected_action.replace(/_/g, " ")}
              </span>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                selected intervention
              </span>
            </div>
          )}

          {/* Scheduled for WAIT */}
          {decision === "WAIT" && productDecision?.scheduled_for && (
            <div style={{ marginTop: "0.75rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Scheduled reassessment:{" "}
              <strong>
                {new Date(productDecision.scheduled_for).toLocaleString("en-IN", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </strong>
            </div>
          )}

          {/* Timing intelligence for WAIT */}
          {decision === "WAIT" && timingEvaluation && (
            <div style={{ marginTop: "0.75rem" }}>
              <TimingBadge evaluation={timingEvaluation} />
            </div>
          )}

          {decision === "WAIT" && !timingEvaluation && (
            <div style={{ marginTop: "0.75rem", fontSize: "0.6875rem", color: "var(--text-muted)", fontStyle: "italic" }}>
              Loading timing intelligence…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
