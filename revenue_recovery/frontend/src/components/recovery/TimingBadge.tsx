"use client";

import React, { useState } from "react";
import { TimingEvaluation, TimingSignal } from "@/lib/api";

interface TimingBadgeProps {
  evaluation: TimingEvaluation;
  compact?: boolean;
}

const SIGNAL_ICONS: Record<string, string> = {
  ACTIVE_PROMISE: "⏳",
  RECENT_ATTEMPT: "🔄",
  CONTACT_LIMIT_WINDOW: "📵",
  SYSTEMIC_INCIDENT: "⚠",
  HISTORICAL_SUCCESS_WINDOW: "🕐",
  PAYMENT_PATTERN: "📊",
  RETRY_COOLDOWN: "⏱",
  NO_TIMING_ADVANTAGE: "✓",
  INSUFFICIENT_TIMING_DATA: "❓",
};

function formatScheduledFor(isoString: string | null): string {
  if (!isoString) return "Not scheduled";
  try {
    return new Date(isoString).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return isoString;
  }
}

function SignalIndicator({ signal }: { signal: TimingSignal }) {
  const icon = SIGNAL_ICONS[signal.signal_type] || "•";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "0.5rem",
        padding: "0.375rem 0.5rem",
        background: signal.active ? "rgba(100,116,139,0.06)" : "transparent",
        borderRadius: 4,
        border: signal.active ? "1px solid rgba(100,116,139,0.15)" : "1px solid transparent",
      }}
    >
      <span style={{ fontSize: "0.75rem", flexShrink: 0 }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.375rem", flexWrap: "wrap" }}>
          <span
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: signal.active ? "var(--text-secondary)" : "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            {signal.signal_type.replace(/_/g, " ")}
          </span>
          {signal.active && (
            <span
              style={{
                fontSize: "0.5rem",
                fontWeight: 700,
                color: "#fff",
                background: "rgba(100,116,139,0.5)",
                padding: "0.1rem 0.35rem",
                borderRadius: 3,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              ACTIVE
            </span>
          )}
        </div>
        <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: 2, lineHeight: 1.4 }}>
          {signal.reason}
        </div>
        {signal.evidence.length > 0 && (
          <div style={{ marginTop: "0.25rem" }}>
            {signal.evidence.slice(0, 2).map((e, i) => (
              <div key={i} style={{ fontSize: "0.5625rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                • {e}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function TimingBadge({ evaluation, compact = false }: TimingBadgeProps) {
  const [expanded, setExpanded] = useState(false);
  const activeSignals = evaluation.signals.filter((s) => s.active);
  const inactiveSignals = evaluation.signals.filter((s) => !s.active);

  if (compact) {
    return (
      <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
        <span
          style={{
            fontSize: "0.5625rem",
            fontWeight: 700,
            color: "#64748b",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
          }}
        >
          WAIT
        </span>
        {evaluation.scheduled_for && (
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
            until {formatScheduledFor(evaluation.scheduled_for)}
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        borderRadius: 8,
        border: "1px solid rgba(100,116,139,0.2)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "0.75rem 1rem",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          <span
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "#64748b",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Timing Intelligence
          </span>
          <span
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: evaluation.timing_decision === "WAIT" ? "#64748b" : evaluation.timing_decision === "RECOVER" ? "#10b981" : "#ef4444",
              background: evaluation.timing_decision === "WAIT" ? "rgba(100,116,139,0.1)" : evaluation.timing_decision === "RECOVER" ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
              padding: "0.2rem 0.5rem",
              borderRadius: 4,
              border: "1px solid",
              borderColor: evaluation.timing_decision === "WAIT" ? "rgba(100,116,139,0.2)" : evaluation.timing_decision === "RECOVER" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)",
            }}
          >
            {evaluation.timing_decision}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.6875rem" }}>
          <span style={{ color: "var(--text-muted)" }}>
            Waits: <strong style={{ color: "var(--text-secondary)" }}>{evaluation.wait_count}/{evaluation.max_wait_count}</strong>
          </span>
          {evaluation.wait_remaining > 0 && (
            <span style={{ color: "var(--text-muted)" }}>
              · <strong style={{ color: "var(--text-secondary)" }}>{evaluation.wait_remaining}</strong> remaining
            </span>
          )}
        </div>
      </div>

      <div style={{ padding: "0.75rem 1rem" }}>
        <div style={{ marginBottom: "0.5rem" }}>
          <span
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Reason
          </span>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: 2, lineHeight: 1.45 }}>
            {evaluation.reason}
          </div>
        </div>

        {evaluation.scheduled_for && (
          <div style={{ marginBottom: "0.5rem" }}>
            <span
              style={{
                fontSize: "0.5625rem",
                fontWeight: 700,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Scheduled For
            </span>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-primary)", marginTop: 2 }}>
              {formatScheduledFor(evaluation.scheduled_for)}
            </div>
          </div>
        )}

        <div style={{ marginBottom: "0.5rem" }}>
          <span
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Policy Basis
          </span>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: 2 }}>
            {evaluation.policy_status.replace(/_/g, " ")} · Confidence: {Math.round(evaluation.confidence * 100)}%
          </div>
        </div>
      </div>

      {activeSignals.length > 0 && (
        <div
          style={{
            borderTop: "1px solid var(--border)",
            padding: "0.75rem 1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.375rem",
          }}
        >
          <span
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: "0.125rem",
            }}
          >
            Active Timing Signals
          </span>
          {activeSignals.map((signal, i) => (
            <SignalIndicator key={i} signal={signal} />
          ))}
        </div>
      )}

      {expanded && inactiveSignals.length > 0 && (
        <div
          style={{
            borderTop: "1px solid var(--border)",
            padding: "0.75rem 1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.375rem",
          }}
        >
          <span
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: "0.125rem",
            }}
          >
            Inactive Signals
          </span>
          {inactiveSignals.map((signal, i) => (
            <SignalIndicator key={i} signal={signal} />
          ))}
        </div>
      )}

      {inactiveSignals.length > 0 && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            width: "100%",
            border: "none",
            borderTop: "1px solid var(--border)",
            background: "transparent",
            padding: "0.5rem",
            fontSize: "0.6875rem",
            color: "var(--text-muted)",
            cursor: "pointer",
            textAlign: "center",
          }}
        >
          {expanded ? "Hide inactive signals" : `Show ${inactiveSignals.length} inactive signal${inactiveSignals.length > 1 ? "s" : ""}`}
        </button>
      )}
    </div>
  );
}
