"use client";

import React from "react";
import { CaseTrace, AuditEvent } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detailAuditEvents?: AuditEvent[];
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  CASE_CREATED: "Opportunity detected",
  CONTEXT_CAPTURED: "Context & telemetry captured",
  DIAGNOSIS_CREATED: "AI Diagnosis generated",
  CANDIDATES_GENERATED: "Candidates evaluated",
  AI_RECOMMENDATION_CREATED: "AI Proposal created",
  POLICY_EVALUATED: "Policy check",
  SAFETY_EVALUATED: "Safety check passed",
  DECISION_MADE: "Decision finalized",
  APPROVAL_GRANTED: "Approval granted",
  APPROVAL_REJECTED: "Approval rejected",
  EXECUTION_STARTED: "Intervention dispatched",
  EXECUTION_ACCEPTED: "Intervention accepted",
  EXECUTION_FAILED: "Intervention failed",
  VERIFICATION_PENDING: "Settlement verification pending",
  SETTLEMENT_RECEIVED: "Settlement verified",
  RECOVERY_CONFIRMED: "Recovery confirmed",
  RECOVERY_FAILED: "Recovery failed",
  STOPPED: "Recovery stopped",
  ESCALATED: "Human review escalation",
  FALLBACK_USED: "Fallback triggered",
  DUPLICATE_WEBHOOK_SKIPPED: "Duplicate webhook skipped",
};

export default function CaseTimeline({ trace, detailAuditEvents }: Props) {
  // Use trace timeline or detail audit events
  const timeline = trace?.timeline?.length
    ? trace.timeline
    : (detailAuditEvents || []).map((e) => ({
        id: e.id,
        event_type: e.action ? e.action.toUpperCase() : "EVENT",
        actor: e.actor,
        action: e.action,
        reason: e.reason,
        timestamp: e.timestamp,
        metadata: e.metadata || {},
      }));

  if (!timeline || timeline.length === 0) {
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
          Recovery timeline
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontStyle: "italic" }}>
          No audit timeline events recorded yet.
        </div>
      </div>
    );
  }

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
        Recovery timeline ({timeline.length} events)
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", position: "relative" }}>
        {timeline.map((ev, idx) => {
          const label = EVENT_TYPE_LABELS[ev.event_type] || ev.event_type.replace(/_/g, " ");
          const isStop = ev.event_type === "STOPPED" || ev.action === "stop_recovery";
          const isSettled = ev.event_type === "SETTLEMENT_RECEIVED" || ev.event_type === "RECOVERY_CONFIRMED";
          const isEscalated = ev.event_type === "ESCALATED";

          let dotColor = "var(--accent)";
          if (isSettled) dotColor = "#10b981";
          if (isStop) dotColor = "#ef4444";
          if (isEscalated) dotColor = "#6366f1";

          return (
            <div key={ev.id || idx} style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}>
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: dotColor,
                  marginTop: 4,
                  flexShrink: 0,
                }}
              />
              <div style={{ flex: 1, background: "var(--bg-primary)", padding: "0.625rem 0.875rem", borderRadius: 6, border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {label}
                  </div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                    {ev.timestamp ? new Date(ev.timestamp).toLocaleString("en-IN", { timeStyle: "short", dateStyle: "short" }) : ""}
                  </div>
                </div>
                {ev.reason && (
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                    {ev.reason}
                  </div>
                )}
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4, display: "flex", gap: "0.75rem" }}>
                  <span>Actor: {ev.actor}</span>
                  {ev.action && <span>Action: {ev.action}</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
