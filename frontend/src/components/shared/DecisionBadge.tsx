"use client";

import { useState } from "react";

type Decision = "RECOVER" | "WAIT" | "ESCALATE" | "STOP";

interface DecisionBadgeProps {
  decision: Decision;
  reason?: string;
  compact?: boolean;
  selectedAction?: string | null;
}

const DECISION_META: Record<Decision, { label: string; color: string; bg: string; border: string; icon: string }> = {
  RECOVER: {
    label: "RECOVER",
    color: "#10b981",
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.25)",
    icon: "→",
  },
  WAIT: {
    label: "WAIT",
    color: "#64748b",
    bg: "rgba(100,116,139,0.08)",
    border: "rgba(100,116,139,0.25)",
    icon: "◷",
  },
  ESCALATE: {
    label: "ESCALATE",
    color: "#6366f1",
    bg: "rgba(99,102,241,0.08)",
    border: "rgba(99,102,241,0.25)",
    icon: "⚑",
  },
  STOP: {
    label: "STOP",
    color: "#ef4444",
    bg: "rgba(239,68,68,0.08)",
    border: "rgba(239,68,68,0.25)",
    icon: "■",
  },
};

export default function DecisionBadge({ decision, reason, compact = false, selectedAction }: DecisionBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const meta = DECISION_META[decision] || DECISION_META.STOP;

  const badge = (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: compact ? 4 : 6,
        padding: compact ? "0.2rem 0.5rem" : "0.3rem 0.65rem",
        borderRadius: 5,
        background: meta.bg,
        border: `1px solid ${meta.border}`,
        color: meta.color,
        fontWeight: 700,
        fontSize: compact ? "0.625rem" : "0.6875rem",
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        cursor: reason ? "help" : "default",
        lineHeight: 1.2,
      }}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span>{meta.icon}</span>
      <span>{meta.label}</span>
      {!compact && selectedAction && selectedAction !== decision.toLowerCase() && (
        <span style={{ fontWeight: 500, color: "var(--text-muted)", fontSize: "0.625rem", textTransform: "none", letterSpacing: "0" }}>
          {selectedAction.replace(/_/g, " ")}
        </span>
      )}
    </span>
  );

  if (!reason) return badge;

  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      {badge}
      {showTooltip && (
        <span
          style={{
            position: "absolute",
            bottom: "100%",
            left: "50%",
            transform: "translateX(-50%)",
            marginBottom: 6,
            padding: "0.4rem 0.6rem",
            borderRadius: 4,
            background: "#1e293b",
            color: "#f1f5f9",
            fontSize: "0.6875rem",
            fontWeight: 500,
            whiteSpace: "nowrap",
            zIndex: 100,
            pointerEvents: "none",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
          }}
        >
          {reason}
        </span>
      )}
    </span>
  );
}
