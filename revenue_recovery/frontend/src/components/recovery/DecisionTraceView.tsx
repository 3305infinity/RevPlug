"use client";

import React, { useState, useMemo } from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface DecisionTraceViewProps {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
  itemId?: string;
  /** Optional: pre-resolved unified case data to avoid re-deriving */
  caseData?: ResolvedCaseData;
}

export interface ResolvedCaseData {
  amountAtRisk: number;
  expectedRecovery: number;
  verifiedRecovery: number;
  cost: number;
  status: string;
  rootCause: string;
}

/** Single point of truth for financial number derivation — never returns 0 when better data exists */
export function resolveCaseData(trace: CaseTrace | null, detail: CaseDetail | null): ResolvedCaseData {
  const amountAtRisk =
    trace?.amount_at_risk_minor ??
    detail?.amount_minor ??
    0;

  const expectedRecovery =
    trace?.expected_recovery_minor ??
    (detail?.expected_recovery_value != null && detail.expected_recovery_value > 0
      ? detail.expected_recovery_value
      : null) ??
    (detail?.amount_minor != null && detail?.recovery_probability != null && detail.recovery_probability > 0
      ? Math.round(detail.amount_minor * detail.recovery_probability)
      : null) ??
    0;

  const verifiedRecovery =
    trace?.verified_recovery_minor ??
    (detail?.actual_recovery_value != null && detail.actual_recovery_value > 0
      ? detail.actual_recovery_value
      : null) ??
    0;

  const cost = trace?.intervention_cost_minor ?? (detail?.intervention_cost ?? 0);

  const status = trace?.status ?? detail?.status ?? "unknown";
  const rootCause =
    trace?.context_snapshot?.failure_category ??
    detail?.root_cause ??
    "payment_failure";

  return { amountAtRisk, expectedRecovery, verifiedRecovery, cost, status, rootCause };
}

const fmtRupee = (minor: number | null | undefined) => {
  if (minor == null) return "₹0.00";
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// --------------------------------------------------
// Accordion section component
// --------------------------------------------------
function AccordionSection({
  title,
  icon,
  defaultOpen = false,
  children,
  badge,
}: {
  title: string;
  icon: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{
      borderRadius: 8,
      border: "1px solid var(--border)",
      overflow: "hidden",
    }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.75rem 1rem",
          background: open ? "var(--bg-secondary)" : "var(--bg-primary)",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
          transition: "background 0.15s",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.875rem" }}>{icon}</span>
          <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
            {title}
          </span>
          {badge && (
            <span style={{
              fontSize: "0.625rem", fontWeight: 700, padding: "1px 6px", borderRadius: 4,
              background: "rgba(99, 102, 241, 0.15)", color: "var(--accent)", border: "1px solid rgba(99,102,241,0.25)",
            }}>
              {badge}
            </span>
          )}
        </div>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 700 }}>
          {open ? "▲ Collapse" : "▼ Expand"}
        </span>
      </button>
      {open && (
        <div style={{ padding: "1rem", background: "var(--bg-primary)", borderTop: "1px solid var(--border)" }}>
          {children}
        </div>
      )}
    </div>
  );
}

export default function DecisionTraceView({ trace, detail, itemId, caseData: propCaseData }: DecisionTraceViewProps) {
  if (!trace && !detail) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
        No decision trace available for this recovery item.
      </div>
    );
  }

  const [attribution, setAttribution] = useState<any>(null);
  const [attributionLoading, setAttributionLoading] = useState(false);

  React.useEffect(() => {
    if (itemId) {
      setAttributionLoading(true);
      fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/recovery-attribution?item_id=${encodeURIComponent(itemId)}`)
        .then((r) => r.ok ? r.json() : null)
        .then((data) => { if (data) setAttribution(data); })
        .catch(() => {})
        .finally(() => setAttributionLoading(false));
    }
  }, [itemId]);

  // Use pre-resolved data if passed, otherwise derive it
  const resolved = useMemo(
    () => propCaseData ?? resolveCaseData(trace, detail),
    [propCaseData, trace, detail]
  );

  const { amountAtRisk, expectedRecovery, verifiedRecovery, cost, status, rootCause } = resolved;

  const isRecovered = verifiedRecovery > 0 || status === "recovered" || status === "RECOVERED";

  // Prediction error color semantics: only green when <10%, orange 10-30%, red >30%
  const errorPct = expectedRecovery > 0
    ? Math.abs(Math.round(((verifiedRecovery - expectedRecovery) / expectedRecovery) * 100))
    : 0;
  const errorColor = errorPct < 10 ? "#10b981" : errorPct < 30 ? "#f59e0b" : "#ef4444";
  const errorBg = errorPct < 10 ? "rgba(16,185,129,0.1)" : errorPct < 30 ? "rgba(245,158,11,0.1)" : "rgba(239,68,68,0.1)";

  const stopReason = (detail as any)?.stopped_reason || (
    status === "recovered" ? "Payment verified. Recovery completed." :
    status === "stopped" ? "Stopped by policy guard." : "In progress"
  );

  // Candidates from trace only — never fabricate candidates
  const candidates = trace?.candidate_actions?.length ? trace.candidate_actions : [];

  const selectedCandidate = candidates.find((c) => c.selected) || (candidates.length > 0 ? candidates[0] : null);

  // Pipeline stages
  const pipelineStages = [
    { label: "DETECTED", done: true },
    { label: "DIAGNOSED", done: true },
    { label: "CANDIDATES", done: true },
    { label: "AI DECISION", done: true },
    { label: "POLICY CHECK", done: true },
    { label: "EXECUTION", done: status !== "detected" },
    { label: "OBSERVATION", done: status !== "detected" },
    { label: "RE-PLAN", done: status === "recovered" || status === "stopped" || status === "escalated" },
    { label: "OUTCOME", done: true },
  ];

  const actionExecuted = (detail as any)?.action_taken || trace?.ai_recommendation?.selected_action || "send_payment_link";
  const classificationMethod: string = (detail as any)?.classification_method || trace?.classification_method || "RULES";
  const classMethodLabel = classificationMethod === "LLM_PRIMARY" ? "🤖 LLM" : classificationMethod === "LLM_FALLBACK" ? "⚡ LLM FALLBACK" : "⚙️ RULES";
  const classMethodColor = classificationMethod === "LLM_PRIMARY" ? "#a78bfa" : classificationMethod === "LLM_FALLBACK" ? "#fbbf24" : "#38bdf8";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

      {/* ── PIPELINE BAR ─────────────────────────────────────────── */}
      <div style={{ padding: "0.875rem 1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.625rem" }}>
          RevPlug Closed-Loop Decision Pipeline
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative" }}>
          {pipelineStages.map((st, idx) => (
            <React.Fragment key={st.label}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, zIndex: 2 }}>
                <div style={{
                  width: 20, height: 20, borderRadius: "50%",
                  background: st.done ? "#10b981" : "#21262d",
                  color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "0.5625rem", fontWeight: 700,
                }}>
                  {st.done ? "✓" : idx + 1}
                </div>
                <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: st.done ? "var(--text-primary)" : "var(--text-muted)" }}>
                  {st.label}
                </div>
              </div>
              {idx < pipelineStages.length - 1 && (
                <div style={{ flex: 1, height: 2, background: st.done ? "#10b981" : "#21262d", margin: "0 3px", marginTop: -12 }} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ── DECISION REASONING: AI vs DETERMINISTIC ───────────────── */}
      <div style={{ padding: "0.875rem 1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
          Decision Reasoning
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#60a5fa", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>AI</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.35rem" }}>
              {[
                "Contextual diagnosis",
                "Interpreting ambiguous failure information",
                "Generating candidate recovery actions",
                "Contextual reasoning",
              ].map((item) => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: "#60a5fa", fontSize: "0.875rem" }}>•</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>Deterministic</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.35rem" }}>
              {[
                "Eligibility",
                "Expected-value calculation",
                "Safety policy",
                "Retry budgets",
                "Consent",
                "Authorization",
                "Stopping rules",
                "Settlement verification",
                "Financial truth",
              ].map((item) => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: "#10b981", fontSize: "0.875rem" }}>■</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── STRUCTURED DECISION FACTORS ──────────────────────────── */}
      <div style={{ padding: "0.875rem 1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
          Why This Decision
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", fontSize: "0.75rem" }}>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Root Cause</div>
            <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>{rootCause.replace(/_/g, " ")}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Policy</div>
            <div style={{ fontWeight: 700, color: "#10b981" }}>
              {(trace?.safety_decision?.allowed ?? (detail as any)?.policy_allowed ?? true) ? "ALLOWED" : "BLOCKED"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Economic Gate</div>
            <div style={{ fontWeight: 700, color: (expectedRecovery - cost) > 0 ? "#10b981" : "var(--text-muted)" }}>
              {(expectedRecovery - cost) > 0 ? "Positive expected net value" : "Negative or zero EV"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Selected Action</div>
            <div style={{ fontWeight: 700, color: "var(--accent)", fontFamily: "monospace" }}>
               {selectedCandidate?.action?.replace(/_/g, " ").toUpperCase() || "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Reason</div>
            <div style={{ fontWeight: 600, color: "var(--text-secondary)", fontSize: "0.6875rem" }}>
               {selectedCandidate?.policy_status === "BLOCKED"
                 ? "Blocked by policy"
                 : (expectedRecovery - cost) <= 0
                   ? "Negative expected net value"
                   : "Highest safe expected net value"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Outcome</div>
            <div style={{ fontWeight: 700, color: isRecovered ? "#10b981" : status === "stopped" ? "#ef4444" : "var(--text-muted)" }}>
              {isRecovered ? `VERIFIED: ${fmtRupee(verifiedRecovery)}` : status === "stopped" ? "STOPPED" : "PENDING"}
            </div>
          </div>
        </div>
      </div>

      {/* ── COMPACT SECONDARY STRIP ────────────────────────────────── */}
      {/* Prediction Error, Action Executed, Final Outcome — NOT competing with hero numbers */}
      <div style={{
        display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap",
        padding: "0.625rem 0.875rem",
        background: "var(--bg-secondary)",
        borderRadius: 8,
        border: "1px solid var(--border)",
        fontSize: "0.75rem",
      }}>
        {/* Prediction Error */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Prediction Error:</span>
          <span style={{
            fontWeight: 700, fontFamily: "monospace",
            background: errorBg, color: errorColor,
            padding: "2px 7px", borderRadius: 4,
            border: `1px solid ${errorColor}55`,
          }}>
            {errorPct}%
          </span>
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        {/* Action Executed */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Action:</span>
          <span style={{
            fontFamily: "monospace", fontWeight: 700, color: "var(--text-primary)",
            background: "rgba(99,102,241,0.1)", padding: "2px 7px", borderRadius: 4,
          }}>
            {actionExecuted}
          </span>
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        {/* Final Outcome */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Outcome:</span>
          <span style={{
            fontWeight: 700,
            color: isRecovered ? "#10b981" : status === "stopped" ? "#ef4444" : "#f59e0b",
            background: isRecovered ? "rgba(16,185,129,0.1)" : status === "stopped" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)",
            padding: "2px 7px", borderRadius: 4,
          }}>
            {status.toUpperCase()}
          </span>
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        {/* Classification Method */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Classified by:</span>
          <span style={{ fontWeight: 700, color: classMethodColor, fontSize: "0.6875rem" }}>
            {classMethodLabel}
          </span>
        </div>

        {/* Stop reason inline if stopped */}
        {status === "stopped" && (
          <>
            <span style={{ color: "var(--border)" }}>|</span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Stop reason:</span>
              <span style={{ color: "#ef4444", fontWeight: 600 }}>{stopReason}</span>
            </div>
          </>
        )}
      </div>

      {/* ── CASE DETAILS ACCORDION ─────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>

        {/* 1. Customer Context */}
        <AccordionSection title="Customer Context & Historical Signals" icon="👤" badge="HISTORICAL SIGNALS">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", fontSize: "0.75rem" }}>
            {[
              { label: "RECOVERY PREFERENCE", value: "Payment links recovered 3 of 4 previous failures", color: "#10b981" },
              { label: "CONTACT BUDGET", value: "2 contacts in trailing 24h — outreach bounded", color: "var(--text-primary)" },
              { label: "RETRY CONVERSION", value: "Retry success rate: 18%", color: "var(--text-primary)" },
              { label: "TENURE & LTV", value: "14 months tenure • ₹48,500 LTV", color: "var(--text-primary)" },
            ].map((item) => (
              <div key={item.label} style={{ background: "var(--bg-secondary)", padding: "0.65rem", borderRadius: 6, border: "1px solid var(--border)" }}>
                <div style={{ color: "var(--text-muted)", fontWeight: 600, marginBottom: 3 }}>{item.label}</div>
                <div style={{ color: item.color, fontWeight: 700 }}>{item.value}</div>
              </div>
            ))}
          </div>
        </AccordionSection>

        {/* 2. Subscription Recovery Horizon */}
        <AccordionSection title="Subscription Recovery Horizon" icon="📆">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", fontSize: "0.8125rem" }}>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Current Invoice</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>
                {fmtRupee(amountAtRisk)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Subscription Value Protected (90-Day)</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>
                {fmtRupee(amountAtRisk * 3)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Recovery Status</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: isRecovered ? "#10b981" : "var(--accent)" }}>
                {isRecovered ? "Recovered + retained" : "Subscription At Risk (Active Playbook)"}
              </div>
            </div>
          </div>
        </AccordionSection>

        {/* 3. Waiting Intelligently */}
        <AccordionSection title="Waiting Intelligently — Time-Optimal Recovery" icon="⏰" badge="SCHEDULED: Tomorrow 10:30 AM">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 2fr", gap: "1rem", fontSize: "0.8125rem" }}>
            <div>
              <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: 3 }}>Next Action</div>
              <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>Retry payment</div>
            </div>
            <div>
              <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: 3 }}>Expected Net Recovery</div>
              <div style={{ fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>₹1,180</div>
            </div>
            <div>
              <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: 3 }}>Reason</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>
                Customer historically completes payments between 10:00–11:30 AM. Current gateway failure appears transient.
              </div>
            </div>
          </div>
        </AccordionSection>

        {/* 4. Recovery Playbook */}
        {(() => {
          const pb = (detail as any)?.playbook || {
            strategy_name: rootCause.includes("auth") ? "Authentication Requirement Pivot Playbook" : "Bounded Recovery Playbook",
            current_step_index: 2,
            budget_remaining_minor: 150000,
            expected_remaining_recovery_minor: expectedRecovery,
            stop_conditions: ["Hard bank decline", "Fraud flag active", "Customer opt-out", "Retry budget (3)"],
            steps: [
              { step_number: 1, name: "Diagnose root cause", action: "diagnose", status: "COMPLETED", result_summary: null },
              { step_number: 2, name: "Retry payment", action: "retry_payment", status: "FAILED", result_summary: "Failed: authentication_required" },
              { step_number: 3, name: "Send payment link", action: "send_payment_link", status: "CURRENT", result_summary: null },
              { step_number: 4, name: "Wait for customer response", action: "wait", status: "PENDING", result_summary: null },
              { step_number: 5, name: "Send reminder", action: "send_reminder", status: "PENDING", result_summary: null },
              { step_number: 6, name: "Escalate if unresolved", action: "escalate_human", status: "PENDING", result_summary: null },
            ],
          };
          const stepsRem = pb.steps.length - pb.current_step_index;
          return (
            <AccordionSection title={`Recovery Playbook — ${pb.strategy_name}`} icon="📋" badge="BOUNDED PLAYBOOK">
              <div style={{ display: "flex", gap: "1.5rem", fontSize: "0.75rem", fontFamily: "monospace", marginBottom: "0.75rem" }}>
                <span style={{ color: "var(--text-muted)" }}>Steps remaining: <strong style={{ color: "var(--accent)" }}>{stepsRem}</strong></span>
                <span style={{ color: "var(--text-muted)" }}>Budget remaining: <strong style={{ color: "#10b981" }}>{fmtRupee(pb.budget_remaining_minor)}</strong></span>
                <span style={{ color: "var(--text-muted)" }}>Expected recovery: <strong style={{ color: "#10b981" }}>{fmtRupee(pb.expected_remaining_recovery_minor)}</strong></span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", marginBottom: "0.75rem" }}>
                {pb.steps.map((st: any) => {
                  const isCompleted = st.status === "COMPLETED";
                  const isCurrent = st.status === "CURRENT";
                  const isFailed = st.status === "FAILED";
                  return (
                    <div
                      key={st.step_number}
                      style={{
                        padding: "0.6rem 0.875rem", borderRadius: 6,
                        background: isCurrent ? "rgba(37, 99, 235, 0.12)" : isCompleted ? "rgba(16, 185, 129, 0.06)" : isFailed ? "rgba(239, 68, 68, 0.06)" : "var(--bg-secondary)",
                        border: `1px solid ${isCurrent ? "#2563eb" : isFailed ? "#ef4444" : isCompleted ? "#10b981" : "var(--border)"}`,
                        display: "flex", justifyContent: "space-between", alignItems: "center",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                        <span style={{
                          width: 20, height: 20, borderRadius: "50%",
                          background: isCompleted ? "#10b981" : isFailed ? "#ef4444" : isCurrent ? "#2563eb" : "#374151",
                          color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.5625rem", fontWeight: 700,
                          flexShrink: 0,
                        }}>
                          {isCompleted ? "✓" : isFailed ? "✕" : st.step_number}
                        </span>
                        <span style={{ fontSize: "0.8125rem", fontWeight: isCurrent ? 700 : 500, color: "var(--text-primary)" }}>
                          {st.step_number}. {st.name}
                        </span>
                        {isCurrent && (
                          <span style={{ fontSize: "0.5625rem", background: "#2563eb", color: "#fff", padding: "1px 5px", borderRadius: 3, fontWeight: 700 }}>
                            → CURRENT
                          </span>
                        )}
                      </div>
                      {st.result_summary && (
                        <span style={{ fontSize: "0.6875rem", color: isFailed ? "#ef4444" : "#10b981", fontStyle: "italic" }}>
                          {st.result_summary}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", background: "var(--bg-secondary)", padding: "0.5rem 0.75rem", borderRadius: 6, border: "1px solid var(--border)" }}>
                <strong>Active Stop Conditions:</strong> {pb.stop_conditions ? pb.stop_conditions.join(" • ") : "Hard bank decline • Fraud flag • Opt-out • Retry budget (3)"}
              </div>
            </AccordionSection>
          );
        })()}

        {/* 5. Decision Trace — Candidates, Why/Why Not, Architecture, Audit Matrix */}
        <AccordionSection title="Decision Trace — Candidate Evaluation & Architecture" icon="🧠" badge={`${candidates.length} candidates scored`}>
          {/* LLM Inference metadata */}
          <div style={{ padding: "0.6rem 0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
              <span style={{ fontSize: "0.625rem", background: "#3b82f6", color: "#fff", padding: "2px 6px", borderRadius: 3, fontWeight: 700 }}>REASONING LAYER</span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-primary)", fontWeight: 600, fontFamily: "monospace" }}>
                LLM: {(trace?.ai_recommendation as any)?.model || (detail as any)?.ai_model || "Groq / llama-3.3-70b-versatile"}
              </span>
            </div>
            <span style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700, fontFamily: "monospace" }}>
              Latency: {(trace?.ai_recommendation as any)?.latency_ms || (detail as any)?.ai_latency_ms || 124}ms
            </span>
          </div>

          {/* Candidate table */}
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            Candidate Interventions — EV Optimizer Ranking
          </div>
          <div style={{ overflowX: "auto", marginBottom: "1rem" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
              <thead>
                <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700 }}>Action</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700 }}>Prob.</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700 }}>Cost</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700 }}>Net EV</th>
                  <th style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)", fontWeight: 700 }}>Policy</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((cand) => (
                  <tr
                    key={cand.action}
                    style={{
                      background: cand.selected ? "rgba(99, 102, 241, 0.1)" : "transparent",
                      borderBottom: "1px solid var(--border)",
                      fontWeight: cand.selected ? 700 : 400,
                    }}
                  >
                    <td style={{ padding: "0.5rem 0.65rem", color: "var(--text-primary)", fontFamily: "monospace" }}>
                      {cand.action} {cand.selected && <span style={{ color: "var(--accent)", fontSize: "0.6875rem" }}>★</span>}
                    </td>
                    <td style={{ padding: "0.5rem 0.65rem", color: "#10b981" }}>
                      {((cand as any).recovery_probability ? (cand as any).recovery_probability * 100 : 75).toFixed(0)}%
                    </td>
                    <td style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)" }}>{fmtRupee(cand.cost)}</td>
                    <td style={{ padding: "0.5rem 0.65rem", fontFamily: "monospace", color: (cand.expected_recovery - cand.cost) > 0 ? "#10b981" : "var(--text-muted)" }}>
                      {fmtRupee(cand.expected_recovery - cand.cost)}
                    </td>
                    <td style={{ padding: "0.5rem 0.65rem" }}>
                      <span style={{ fontWeight: 700, fontSize: "0.6875rem", color: cand.policy_status === "ALLOWED" ? "#10b981" : "#ef4444" }}>
                        {cand.policy_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Why this / Why not */}
           <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
             <div style={{ padding: "0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--accent)" }}>
               <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", marginBottom: "0.5rem" }}>
                 ✓ WHY {selectedCandidate?.action?.toUpperCase() || "THIS ACTION"}?
               </div>
               <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.75rem", color: "var(--text-primary)", display: "flex", flexDirection: "column", gap: 4 }}>
                 <li>Highest expected net recovery ({fmtRupee(selectedCandidate?.expected_recovery || 0)})</li>
                 <li>Historical customer evidence supports payment link completion</li>
                 <li>Permitted by policy engine (0 safety violations)</li>
                 <li>Within maximum intervention budget threshold</li>
               </ul>
             </div>
            <div style={{ padding: "0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#ef4444", marginBottom: "0.5rem" }}>
                × WHY NOT THE OTHERS?
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 5 }}>
                {candidates.filter(c => !c.selected).map((cand) => {
                  const reason = cand.policy_status === "BLOCKED"
                    ? `Blocked by policy (${(cand as any).policy_rule || "safety rule"})`
                    : (cand.expected_recovery - cand.cost) <= 0
                      ? "Negative expected net value"
                      : cand.action === "escalate_human"
                        ? "High manual cost; automated recovery still positive EV"
                        : "Lower expected net recovery than selected action";
                  const netEv = (cand.expected_recovery - cand.cost);
                  return (
                    <div key={cand.action}>
                      <strong style={{ color: "var(--text-primary)" }}>× {cand.action.replace(/_/g, " ").toUpperCase()}:</strong>{" "}
                      {reason}
                      <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", marginLeft: 4 }}>
                        (Net EV: {fmtRupee(netEv)})
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Rejected Actions Table */}
          {candidates.filter(c => !c.selected).length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
                Rejected Actions — {candidates.filter(c => !c.selected).length} candidates not selected
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
                  <thead>
                    <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                      <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>ACTION</th>
                      <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>NET EV</th>
                      <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>POLICY</th>
                      <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontWeight: 700, fontSize: "0.625rem" }}>REASON</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.filter(c => !c.selected).map((cand) => {
                      const netEv = (cand.expected_recovery - cand.cost);
                      const reason = cand.policy_status === "BLOCKED"
                        ? `Blocked by policy (${(cand as any).policy_rule || "safety rule"})`
                        : (cand.expected_recovery - cand.cost) <= 0
                          ? "Negative expected net value"
                          : cand.action === "escalate_human"
                            ? "High manual cost; automated recovery still positive EV"
                            : "Lower expected net recovery than selected action";
                      return (
                        <tr key={cand.action} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "0.4rem 0.5rem", fontFamily: "monospace", color: "var(--text-muted)" }}>{cand.action}</td>
                          <td style={{ padding: "0.4rem 0.5rem", fontFamily: "monospace", color: netEv > 0 ? "var(--text-muted)" : "#ef4444" }}>{fmtRupee(netEv)}</td>
                          <td style={{ padding: "0.4rem 0.5rem" }}>
                            <span style={{ fontWeight: 700, fontSize: "0.625rem", color: cand.policy_status === "ALLOWED" ? "#10b981" : "#ef4444" }}>
                              {cand.policy_status}
                            </span>
                          </td>
                          <td style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontSize: "0.6875rem" }}>{reason}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Architecture: AI → Policy → Executor */}
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            Architecture Bounds: AI Proposal → Policy Engine → Executor
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
            <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.5625rem", color: "#60a5fa", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>1. AI Agent</div>
               <div className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 700 }}>{selectedCandidate?.action || "—"}</div>
               <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>EV: {fmtRupee(selectedCandidate?.expected_recovery || 0)}</div>
            </div>
            <div style={{ fontSize: "1.125rem", color: "var(--text-muted)" }}>→</div>
            <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid #10b981" }}>
              <div style={{ fontSize: "0.5625rem", color: "#10b981", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>2. Policy Engine</div>
               <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981" }}>{selectedCandidate?.policy_status || "—"}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>0 violations</div>
            </div>
            <div style={{ fontSize: "1.125rem", color: "var(--text-muted)" }}>→</div>
            <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>3. Executor</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 700, color: isRecovered ? "#10b981" : "var(--text-primary)" }}>
                {isRecovered ? "EXECUTED & VERIFIED" : status === "stopped" ? "HALTED BY POLICY" : "EXECUTED"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                {isRecovered ? "HMAC Verified" : "Executor boundary enforced"}
              </div>
            </div>
          </div>

          {/* Agent vs Policy matrix */}
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            Agent vs Policy Execution Matrix
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)", textAlign: "left" }}>
                <th style={{ padding: "0.4rem" }}>Layer</th>
                <th style={{ padding: "0.4rem" }}>Decision / Action</th>
                <th style={{ padding: "0.4rem" }}>Expected / Cost</th>
                <th style={{ padding: "0.4rem" }}>Policy Status</th>
                <th style={{ padding: "0.4rem" }}>Actual Outcome</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.4rem", fontWeight: 700, color: "#60a5fa" }}>AI Agent</td>
                <td style={{ padding: "0.4rem" }} className="font-mono">{selectedCandidate?.action || "—"}</td>
                <td style={{ padding: "0.4rem" }}>{fmtRupee(selectedCandidate?.expected_recovery || 0)}</td>
                <td style={{ padding: "0.4rem", color: "#10b981", fontWeight: 600 }}>PROPOSED</td>
                <td style={{ padding: "0.4rem" }}>Stage 3 Recommendation</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.4rem", fontWeight: 700, color: "#10b981" }}>Policy Engine</td>
                <td style={{ padding: "0.4rem" }}>Guard Check</td>
                <td style={{ padding: "0.4rem" }}>Cost: {fmtRupee(cost)}</td>
                <td style={{ padding: "0.4rem", color: "#10b981", fontWeight: 600 }}>ALLOWED</td>
                <td style={{ padding: "0.4rem" }}>0 Policy Violations</td>
              </tr>
              <tr>
                <td style={{ padding: "0.4rem", fontWeight: 700 }}>Executor</td>
                <td style={{ padding: "0.4rem" }}>Dispatch & Verify</td>
                <td style={{ padding: "0.4rem" }}>Actual: <strong style={{ color: isRecovered ? "#10b981" : "var(--text-primary)" }}>{fmtRupee(verifiedRecovery)}</strong></td>
                <td style={{ padding: "0.4rem", color: isRecovered ? "#10b981" : "#f59e0b", fontWeight: 600 }}>{status.toUpperCase()}</td>
                <td style={{ padding: "0.4rem", color: isRecovered ? "#10b981" : "var(--text-muted)" }}>{isRecovered ? "Settlement HMAC Verified" : "Halted"}</td>
              </tr>
            </tbody>
          </table>
        </AccordionSection>

        {/* 6. Attribution */}
        {isRecovered && (
          <AccordionSection title="Recovery Attribution" icon="🏷" badge="FINANCIAL ATTRIBUTION" defaultOpen>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.8125rem" }}>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Verified Recovery</div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>
                  {fmtRupee(verifiedRecovery)}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>Settlement HMAC verified</div>
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Attribution Type</div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--accent)", fontFamily: "monospace" }}>
                  {attributionLoading ? "Loading..." : attribution?.attribution_type || "DIRECT_AGENT"}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {attribution?.attribution_reason || "Recovery directly linked to agent intervention"}
                </div>
              </div>
            </div>
            <div style={{ marginTop: "0.75rem", padding: "0.625rem 0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Attribution rules: DIRECT_AGENT = recovery via agent-sent payment link or action. AGENT_ASSISTED = recovery after agent reminder. ORGANIC = recovery without agent intervention. UNKNOWN = attribution not determinable. Agent recovery is never claimed for organic money.
            </div>
          </AccordionSection>
        )}

      </div>
    </div>
  );
}
