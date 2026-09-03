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
  amountAtRisk: number | null;
  expectedRecovery: number | null;
  verifiedRecovery: number | null;
  cost: number | null;
  status: string;
  rootCause: string | null;
}

/**
 * Single point of truth for financial number derivation.
 * NEVER substitutes missing evidence with estimates.
 * null means "not available" — callers must handle this explicitly.
 */
export function resolveCaseData(trace: CaseTrace | null, detail: CaseDetail | null): ResolvedCaseData {
  const amountAtRisk =
    trace?.amount_at_risk_minor != null ? trace.amount_at_risk_minor :
    detail?.amount_minor != null ? detail.amount_minor :
    null;

  // Expected recovery ONLY from backend — never calculated on the frontend
  const expectedRecovery = trace?.expected_recovery_minor ?? null;

  // Verified recovery ONLY from settlement_evidence.verified === true
  const settlement = trace?.settlement_evidence as Record<string, any> | null | undefined;
  const settlementVerified = settlement?.verified === true;
  const verifiedRecovery: number | null = settlementVerified
    ? (settlement?.verified_amount_minor ?? null)
    : null;

  // Cost from execution record only — never a fallback default
  const cost =
    (trace?.execution as Record<string, any> | null)?.cost_minor ?? null;

  const status = trace?.status ?? detail?.status ?? "unknown";
  const rootCause =
    trace?.context_snapshot?.failure_category ??
    detail?.root_cause ??
    null;

  return { amountAtRisk, expectedRecovery, verifiedRecovery, cost, status, rootCause };
}

const fmtRupee = (minor: number | null | undefined) => {
  if (minor == null) return "—";
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

function EmptyEvidenceNote({ message }: { message: string }) {
  return (
    <div style={{
      padding: "0.625rem 0.875rem",
      background: "var(--bg-secondary)",
      borderRadius: 6,
      border: "1px solid var(--border)",
      fontSize: "0.75rem",
      color: "var(--text-muted)",
      fontStyle: "italic",
    }}>
      {message}
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

  // Settlement is verified ONLY when backend says so
  const settlement = trace?.settlement_evidence as Record<string, any> | null | undefined;
  const settlementVerified = settlement?.verified === true;
  const isVerifiedRecovered = settlementVerified && (verifiedRecovery ?? 0) > 0;

  // Execution evidence from backend only
  const execution = trace?.execution as Record<string, any> | null | undefined;
  const executionRecorded = execution?.executed === true;
  const executionStatus = execution?.status ?? null;
  const actionExecuted: string | null = execution?.action ?? (detail as any)?.action_taken ?? null;

  // Candidates from trace only — never fabricated
  const candidates = trace?.candidate_actions?.length ? trace.candidate_actions : [];
  // selectedCandidate must be explicitly marked by backend — NEVER pick candidates[0] as fallback
  const selectedCandidate = candidates.find((c) => c.selected) ?? null;

  // Classification method from backend
  const classificationMethod: string = (detail as any)?.classification_method ?? trace?.classification_method ?? null;
  const classMethodLabel =
    classificationMethod === "LLM_PRIMARY" ? "🤖 AI-assisted" :
    classificationMethod === "LLM_FALLBACK" ? "⚡ AI fallback" :
    classificationMethod === "RULES" ? "⚙️ Deterministic" :
    "—";
  const classMethodColor =
    classificationMethod === "LLM_PRIMARY" ? "#a78bfa" :
    classificationMethod === "LLM_FALLBACK" ? "#fbbf24" :
    classificationMethod === "RULES" ? "#38bdf8" :
    "var(--text-muted)";

  // Canonical product decision from backend
  const productDecision = trace?.product_decision;
  const canonicalDecision = productDecision?.decision ?? null;

  // AI recommendation from backend — no fallbacks to invented values
  const aiRec = trace?.ai_recommendation as Record<string, any> | null | undefined;
  const aiModel: string | null = aiRec?.model && aiRec.model !== "null" ? aiRec.model : null;
  const aiLatencyMs: number | null = aiRec?.latency_ms ?? null;
  const aiConfidence: number | null = aiRec?.confidence ?? null;
  const aiSelectedAction: string | null = aiRec?.selected_action ?? null;
  const aiRationale: string | null = aiRec?.user_safe_reasoning ?? null;
  const aiEvidence: string[] = Array.isArray(aiRec?.evidence) ? aiRec.evidence : [];
  const aiFallbackUsed = aiRec?.fallback_used === true;

  // Pipeline stage completion — ONLY from actual backend evidence
  const diagnosisRecorded = !!(trace?.diagnosis && Object.keys(trace.diagnosis).length > 0);
  const policyEvaluated = trace?.policy_evaluations != null && Object.keys(trace.policy_evaluations as any).length > 0;
  const policyAllowed = (trace?.safety_decision as any)?.allowed ?? null;

  const pipelineStages = [
    { label: "DETECTED", done: !!(amountAtRisk) },
    { label: "DIAGNOSED", done: diagnosisRecorded },
    { label: "CANDIDATES", done: candidates.length > 0 },
    { label: "AI DECISION", done: !!aiSelectedAction },
    { label: "POLICY CHECK", done: policyEvaluated },
    { label: "EXECUTION", done: executionRecorded },
    { label: "SETTLE", done: settlementVerified },
    { label: "ATTRIBUTED", done: !!(attribution?.attribution_type) },
  ];

  // Net recovery — only when both verified and cost are known
  const netRecovery =
    verifiedRecovery != null && cost != null
      ? verifiedRecovery - cost
      : null;

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
          Architectural Responsibility Boundary
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#60a5fa", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>AI Handles</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.35rem" }}>
              {[
                "Contextual diagnosis",
                "Interpreting ambiguous failure signals",
                "Generating candidate recovery actions",
                "Intervention ranking & selection",
              ].map((item) => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: "#60a5fa", fontSize: "0.875rem" }}>•</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>Deterministic Controls</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.35rem" }}>
              {[
                "Safety policy enforcement",
                "Retry budget & consent checks",
                "Financial arithmetic",
                "Settlement verification",
                "Financial truth boundaries",
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
            <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>
              {rootCause ? rootCause.replace(/_/g, " ") : "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Policy</div>
            <div style={{ fontWeight: 700, color: policyAllowed === true ? "#10b981" : policyAllowed === false ? "#ef4444" : "var(--text-muted)" }}>
              {policyAllowed === true ? "ALLOWED" : policyAllowed === false ? "BLOCKED" : "Not evaluated"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Decision Method</div>
            <div style={{ fontWeight: 700, color: classMethodColor }}>
              {classMethodLabel}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Selected Action</div>
            <div style={{ fontWeight: 700, color: aiSelectedAction ? "var(--accent)" : "var(--text-muted)", fontFamily: aiSelectedAction ? "monospace" : undefined }}>
              {aiSelectedAction ? aiSelectedAction.replace(/_/g, " ").toUpperCase() : "Not available"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Reason</div>
            <div style={{ fontWeight: 600, color: "var(--text-secondary)", fontSize: "0.6875rem" }}>
              {productDecision?.reason_code
                ? productDecision.reason_code.replace(/_/g, " ")
                : "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>Settlement</div>
            <div style={{ fontWeight: 700, color: isVerifiedRecovered ? "#10b981" : "var(--text-muted)" }}>
              {isVerifiedRecovered ? `VERIFIED: ${fmtRupee(verifiedRecovery)}` : "Not verified"}
            </div>
          </div>
        </div>
      </div>

      {/* ── COMPACT SECONDARY STRIP ────────────────────────────────── */}
      <div style={{
        display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap",
        padding: "0.625rem 0.875rem",
        background: "var(--bg-secondary)",
        borderRadius: 8,
        border: "1px solid var(--border)",
        fontSize: "0.75rem",
      }}>
        {/* Recovery Variance — replaces fabricated "Prediction Error" */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.15rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600, fontSize: "0.6875rem" }}>Revenue at Risk</span>
          <span style={{ fontWeight: 700, fontFamily: "monospace", color: "#ef4444" }}>
            {fmtRupee(amountAtRisk)}
          </span>
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.15rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600, fontSize: "0.6875rem" }}>
            Expected Recovery <span style={{ fontWeight: 400 }}>(projected)</span>
          </span>
          <span style={{ fontWeight: 700, fontFamily: "monospace", color: expectedRecovery != null ? "#6366f1" : "var(--text-muted)" }}>
            {fmtRupee(expectedRecovery)}
          </span>
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.15rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600, fontSize: "0.6875rem" }}>
            Verified Recovered <span style={{ fontWeight: 400 }}>(settlement)</span>
          </span>
          <span style={{ fontWeight: 700, fontFamily: "monospace", color: isVerifiedRecovered ? "#10b981" : "var(--text-muted)" }}>
            {isVerifiedRecovered ? fmtRupee(verifiedRecovery) : "Settlement not verified"}
          </span>
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        {/* Action Executed — only from real execution record */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Action:</span>
          {actionExecuted ? (
            <span style={{
              fontFamily: "monospace", fontWeight: 700, color: "var(--text-primary)",
              background: "rgba(99,102,241,0.1)", padding: "2px 7px", borderRadius: 4,
            }}>
              {actionExecuted}
            </span>
          ) : (
            <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>Not available</span>
          )}
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        {/* Outcome */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Outcome:</span>
          <span style={{
            fontWeight: 700,
            color: isVerifiedRecovered ? "#10b981" : status === "stopped" ? "#ef4444" : "#f59e0b",
            background: isVerifiedRecovered ? "rgba(16,185,129,0.1)" : status === "stopped" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)",
            padding: "2px 7px", borderRadius: 4,
          }}>
            {canonicalDecision ?? status.toUpperCase()}
          </span>
        </div>

        <span style={{ color: "var(--border)" }}>|</span>

        {/* Classification Method */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>Method:</span>
          <span style={{ fontWeight: 700, color: classMethodColor, fontSize: "0.6875rem" }}>
            {classMethodLabel}
          </span>
        </div>

        {/* AI Fallback indicator */}
        {aiFallbackUsed && (
          <>
            <span style={{ color: "var(--border)" }}>|</span>
            <span style={{ fontWeight: 700, color: "#fbbf24", fontSize: "0.6875rem", background: "rgba(245,158,11,0.1)", padding: "2px 7px", borderRadius: 4, border: "1px solid rgba(245,158,11,0.25)" }}>
              ⚡ AI fallback used
            </span>
          </>
        )}
      </div>

      {/* ── CASE DETAILS ACCORDION ─────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>

        {/* 1. Detection Context — from backend context_snapshot only */}
        <AccordionSection title="Detection Context" icon="🔍" badge="BACKEND EVIDENCE">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", fontSize: "0.75rem" }}>
            <div style={{ background: "var(--bg-secondary)", padding: "0.65rem", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ color: "var(--text-muted)", fontWeight: 600, marginBottom: 3, fontSize: "0.625rem", textTransform: "uppercase" }}>Opportunity ID</div>
              <div style={{ color: "var(--text-primary)", fontWeight: 700, fontFamily: "monospace", fontSize: "0.6875rem" }}>
                {trace?.context_snapshot?.item_id ?? itemId ?? "—"}
              </div>
            </div>
            <div style={{ background: "var(--bg-secondary)", padding: "0.65rem", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ color: "var(--text-muted)", fontWeight: 600, marginBottom: 3, fontSize: "0.625rem", textTransform: "uppercase" }}>Amount at Risk</div>
              <div style={{ color: amountAtRisk != null ? "#ef4444" : "var(--text-muted)", fontWeight: 700, fontFamily: "monospace" }}>
                {fmtRupee(amountAtRisk)}
              </div>
            </div>
            <div style={{ background: "var(--bg-secondary)", padding: "0.65rem", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ color: "var(--text-muted)", fontWeight: 600, marginBottom: 3, fontSize: "0.625rem", textTransform: "uppercase" }}>Failure Category</div>
              <div style={{ color: rootCause ? "var(--text-primary)" : "var(--text-muted)", fontWeight: 700 }}>
                {rootCause ? rootCause.replace(/_/g, " ") : "—"}
              </div>
            </div>
            <div style={{ background: "var(--bg-secondary)", padding: "0.65rem", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ color: "var(--text-muted)", fontWeight: 600, marginBottom: 3, fontSize: "0.625rem", textTransform: "uppercase" }}>Attempt Count</div>
              <div style={{ color: "var(--text-primary)", fontWeight: 700 }}>
                {trace?.context_snapshot?.attempt_count != null ? String(trace.context_snapshot.attempt_count) : "—"}
              </div>
            </div>
            <div style={{ background: "var(--bg-secondary)", padding: "0.65rem", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ color: "var(--text-muted)", fontWeight: 600, marginBottom: 3, fontSize: "0.625rem", textTransform: "uppercase" }}>Context Hash</div>
              <div style={{ color: "var(--text-muted)", fontWeight: 600, fontFamily: "monospace", fontSize: "0.6875rem" }}>
                {trace?.context_snapshot?.hash ?? "—"}
              </div>
            </div>
            <div style={{ background: "var(--bg-secondary)", padding: "0.65rem", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ color: "var(--text-muted)", fontWeight: 600, marginBottom: 3, fontSize: "0.625rem", textTransform: "uppercase" }}>Decision Method</div>
              <div style={{ color: classMethodColor, fontWeight: 700 }}>
                {classMethodLabel}
              </div>
            </div>
          </div>
        </AccordionSection>

        {/* 2. Decision Trace — Candidates, Reasoning, Architecture, Audit Matrix */}
        <AccordionSection
          title="Decision Trace — Candidate Evaluation & Architecture"
          icon="🧠"
          badge={candidates.length > 0 ? `${candidates.length} candidates` : "No candidates recorded"}
        >
          {/* LLM Inference metadata — only if available from backend */}
          {(aiModel || aiLatencyMs != null) && (
            <div style={{ padding: "0.6rem 0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
                <span style={{ fontSize: "0.625rem", background: "#3b82f6", color: "#fff", padding: "2px 6px", borderRadius: 3, fontWeight: 700 }}>REASONING LAYER</span>
                {aiModel && (
                  <span style={{ fontSize: "0.75rem", color: "var(--text-primary)", fontWeight: 600, fontFamily: "monospace" }}>
                    {aiModel}
                  </span>
                )}
              </div>
              {aiLatencyMs != null && (
                <span style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700, fontFamily: "monospace" }}>
                  Latency: {aiLatencyMs}ms
                </span>
              )}
            </div>
          )}

          {/* AI rationale — only from backend user_safe_reasoning */}
          {aiRationale && (
            <div style={{ marginBottom: "1rem", padding: "0.75rem", background: "rgba(99,102,241,0.05)", borderRadius: 6, border: "1px solid rgba(99,102,241,0.2)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", marginBottom: "0.4rem" }}>AI Rationale (evidence-backed)</div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.55 }}>{aiRationale}</div>
              {aiEvidence.length > 0 && (
                <ul style={{ margin: "0.5rem 0 0 0", paddingLeft: "1rem", fontSize: "0.75rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 3 }}>
                  {aiEvidence.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              )}
            </div>
          )}

          {/* Candidate table */}
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            Candidate Interventions
          </div>

          {candidates.length === 0 ? (
            <EmptyEvidenceNote message="No candidate evidence recorded. The decision may have been made deterministically without generating candidates." />
          ) : (
            <>
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
                          {cand.action} {cand.selected && <span style={{ color: "var(--accent)", fontSize: "0.6875rem" }}>★ selected</span>}
                        </td>
                        <td style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)" }}>
                          {/* Show — if probability not recorded — never default to 75% */}
                          {(cand as any).recovery_probability != null
                            ? `${((cand as any).recovery_probability * 100).toFixed(0)}%`
                            : "—"}
                        </td>
                        <td style={{ padding: "0.5rem 0.65rem", color: "var(--text-muted)" }}>
                          {cand.cost != null ? fmtRupee(cand.cost) : "—"}
                        </td>
                        <td style={{ padding: "0.5rem 0.65rem", fontFamily: "monospace", color: cand.expected_recovery != null && cand.cost != null && (cand.expected_recovery - cand.cost) > 0 ? "#10b981" : "var(--text-muted)" }}>
                          {cand.expected_recovery != null && cand.cost != null
                            ? fmtRupee(cand.expected_recovery - cand.cost)
                            : "—"}
                        </td>
                        <td style={{ padding: "0.5rem 0.65rem" }}>
                          {cand.policy_status ? (
                            <span style={{ fontWeight: 700, fontSize: "0.6875rem", color: cand.policy_status === "ALLOWED" ? "#10b981" : "#ef4444" }}>
                              {cand.policy_status}
                            </span>
                          ) : (
                            <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Selected / not-selected — backed by candidate.selected flag only */}
              {selectedCandidate ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
                  <div style={{ padding: "0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--accent)" }}>
                    <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", marginBottom: "0.5rem" }}>
                      ✓ SELECTED: {selectedCandidate.action?.toUpperCase()}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                      {selectedCandidate.policy_status === "BLOCKED"
                        ? "Note: this candidate was marked selected but also marked BLOCKED by policy."
                        : aiRationale
                          ? aiRationale
                          : "Selected by the decision system based on expected value and policy eligibility."}
                    </div>
                  </div>
                  {candidates.filter(c => !c.selected).length > 0 && (
                    <div style={{ padding: "0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#ef4444", marginBottom: "0.5rem" }}>
                        × NOT SELECTED — {candidates.filter(c => !c.selected).length} candidates
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 5 }}>
                        {candidates.filter(c => !c.selected).map((cand) => {
                          const reason = cand.policy_status === "BLOCKED"
                            ? `Blocked by policy${(cand as any).policy_rule ? ` (${(cand as any).policy_rule})` : ""}`
                            : (cand.expected_recovery != null && cand.cost != null && (cand.expected_recovery - cand.cost) <= 0)
                              ? "Negative expected net value"
                              : "Lower expected net recovery than selected action";
                          return (
                            <div key={cand.action}>
                              <strong style={{ color: "var(--text-primary)" }}>× {cand.action.replace(/_/g, " ").toUpperCase()}:</strong>{" "}
                              {reason}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <EmptyEvidenceNote message="No candidate is marked as selected. The system may have used a deterministic decision path." />
              )}

              {/* Narrative: Why this action, not the others */}
              {selectedCandidate && (
                <div style={{ marginTop: "0.75rem", padding: "0.875rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)", fontSize: "0.8125rem" }}>
                  <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
                    Why This Action, Not the Others
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", color: "var(--text-secondary)" }}>
                    <div>
                      <span style={{ fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>
                        {selectedCandidate.action.replace(/_/g, " ").toUpperCase()}
                      </span>
                      {" — selected"}
                      <div style={{ marginTop: 2 }}>
                        Expected Net Recovery {fmtRupee((selectedCandidate.expected_recovery != null && selectedCandidate.cost != null) ? selectedCandidate.expected_recovery - selectedCandidate.cost : selectedCandidate.expected_recovery)}
                        {aiConfidence != null && <> · Confidence {(aiConfidence * 100).toFixed(0)}%</>}
                      </div>
                      {selectedCandidate.reason && (
                        <ul style={{ margin: "0.35rem 0 0 0", paddingLeft: "1.125rem", lineHeight: 1.6 }}>
                          {selectedCandidate.reason.split("; ").map((r, i) => <li key={i}>{r}</li>)}
                        </ul>
                      )}
                    </div>
                    {(() => {
                      const rejected = candidates.filter((c) => !c.selected);
                      if (rejected.length === 0) return null;
                      return (
                        <div>
                          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 3 }}>
                            Considered and rejected:
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            {rejected.map((cand) => {
                              const net = (cand.expected_recovery != null && cand.cost != null)
                                ? cand.expected_recovery - cand.cost
                                : cand.expected_recovery;
                              const label = cand.policy_status === "BLOCKED"
                                ? `Blocked by policy${cand.policy_rule ? ` (${cand.policy_rule.replace(/_/g, " ")})` : ""}`
                                : cand.reason || "Lower expected net recovery than selected action";
                              return (
                                <div key={cand.action}>
                                  <strong style={{ color: "var(--text-primary)", fontFamily: "monospace" }}>
                                    {cand.action.replace(/_/g, " ").toUpperCase()}
                                  </strong>
                                  {" — "}
                                  {net != null ? `EV ${fmtRupee(net)}` : "EV —"}
                                  {" "}
                                  <span style={{ color: "var(--text-muted)" }}>({label})</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Architecture: AI → Policy → Executor */}
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem", marginTop: "1rem" }}>
            Architecture Bounds: AI Proposes → Policy Controls → Execution Acts → Settlement Proves
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr auto 1fr", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            {/* AI Agent box */}
            <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.5625rem", color: "#60a5fa", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>1. AI Agent</div>
              <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700 }}>
                {aiSelectedAction ?? "—"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                {aiConfidence != null ? `Confidence: ${(aiConfidence * 100).toFixed(0)}%` : "Confidence: —"}
              </div>
            </div>
            <div style={{ fontSize: "1.125rem", color: "var(--text-muted)" }}>→</div>
            {/* Policy Engine box */}
            <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: `1px solid ${policyAllowed === true ? "#10b981" : policyAllowed === false ? "#ef4444" : "var(--border)"}` }}>
              <div style={{ fontSize: "0.5625rem", color: policyAllowed === true ? "#10b981" : policyAllowed === false ? "#ef4444" : "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>2. Policy Engine</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 700, color: policyAllowed === true ? "#10b981" : policyAllowed === false ? "#ef4444" : "var(--text-muted)" }}>
                {policyAllowed === true ? "ALLOWED" : policyAllowed === false ? "BLOCKED" : "Not evaluated"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                {(trace?.safety_decision as any)?.reason_code ?? "—"}
              </div>
            </div>
            <div style={{ fontSize: "1.125rem", color: "var(--text-muted)" }}>→</div>
            {/* Executor box */}
            <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>3. Executor</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 700, color: executionRecorded ? "var(--text-primary)" : "var(--text-muted)" }}>
                {executionRecorded
                  ? (executionStatus === "EXECUTED" ? "EXECUTED" : executionStatus ?? "EXECUTED")
                  : "No execution recorded"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                {executionRecorded ? (execution?.action ?? "—") : "—"}
              </div>
            </div>
            <div style={{ fontSize: "1.125rem", color: "var(--text-muted)" }}>→</div>
            {/* Settlement box */}
            <div style={{ padding: "0.75rem", background: settlementVerified ? "rgba(16,185,129,0.06)" : "var(--bg-secondary)", borderRadius: 6, border: `1px solid ${settlementVerified ? "rgba(16,185,129,0.3)" : "var(--border)"}` }}>
              <div style={{ fontSize: "0.5625rem", color: settlementVerified ? "#10b981" : "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>4. Settlement</div>
              <div style={{ fontSize: "0.875rem", fontWeight: 700, color: settlementVerified ? "#10b981" : "var(--text-muted)" }}>
                {settlementVerified ? "VERIFIED" : "Not verified"}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                {settlementVerified ? fmtRupee(verifiedRecovery) : "Settlement not verified"}
              </div>
            </div>
          </div>

          {/* Agent vs Policy matrix */}
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            Evidence Audit Matrix
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)", textAlign: "left" }}>
                <th style={{ padding: "0.4rem" }}>Layer</th>
                <th style={{ padding: "0.4rem" }}>Decision / Action</th>
                <th style={{ padding: "0.4rem" }}>Expected / Cost</th>
                <th style={{ padding: "0.4rem" }}>Status</th>
                <th style={{ padding: "0.4rem" }}>Evidence Source</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.4rem", fontWeight: 700, color: "#60a5fa" }}>AI Agent</td>
                <td style={{ padding: "0.4rem" }} className="font-mono">{aiSelectedAction ?? "—"}</td>
                <td style={{ padding: "0.4rem" }}>{selectedCandidate?.expected_recovery != null ? fmtRupee(selectedCandidate.expected_recovery) : "—"}</td>
                <td style={{ padding: "0.4rem", color: "#f59e0b", fontWeight: 600 }}>PROPOSED</td>
                <td style={{ padding: "0.4rem", color: "var(--text-muted)" }}>
                  {aiModel ? `${aiModel}` : classMethodLabel}
                </td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.4rem", fontWeight: 700, color: "#10b981" }}>Policy Engine</td>
                <td style={{ padding: "0.4rem" }}>Guard check</td>
                <td style={{ padding: "0.4rem", color: "var(--text-muted)" }}>Cost: {fmtRupee(cost)}</td>
                <td style={{ padding: "0.4rem", fontWeight: 600, color: policyAllowed === true ? "#10b981" : policyAllowed === false ? "#ef4444" : "var(--text-muted)" }}>
                  {policyAllowed === true ? "ALLOWED" : policyAllowed === false ? "BLOCKED" : "—"}
                </td>
                <td style={{ padding: "0.4rem", color: "var(--text-muted)" }}>
                  {policyEvaluated ? "policy_evaluations" : "Not evaluated"}
                </td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.4rem", fontWeight: 700 }}>Executor</td>
                <td style={{ padding: "0.4rem", fontFamily: "monospace" }}>{actionExecuted ?? "—"}</td>
                <td style={{ padding: "0.4rem" }}>Cost: {fmtRupee(cost)}</td>
                <td style={{ padding: "0.4rem", fontWeight: 600, color: executionRecorded ? "var(--text-primary)" : "var(--text-muted)" }}>
                  {executionRecorded ? (executionStatus ?? "EXECUTED") : "No execution recorded"}
                </td>
                <td style={{ padding: "0.4rem", color: "var(--text-muted)" }}>
                  {executionRecorded ? "execution record" : "None"}
                </td>
              </tr>
              <tr>
                <td style={{ padding: "0.4rem", fontWeight: 700 }}>Settlement</td>
                <td style={{ padding: "0.4rem" }}>Verify & attribute</td>
                <td style={{ padding: "0.4rem", fontFamily: "monospace", color: isVerifiedRecovered ? "#10b981" : "var(--text-muted)" }}>
                  {isVerifiedRecovered ? fmtRupee(verifiedRecovery) : "₹0"}
                </td>
                <td style={{ padding: "0.4rem", color: isVerifiedRecovered ? "#10b981" : "var(--text-muted)", fontWeight: 600 }}>
                  {settlementVerified ? "SETTLEMENT VERIFIED" : "Not verified"}
                </td>
                <td style={{ padding: "0.4rem", color: "var(--text-muted)" }}>
                  {settlementVerified ? "settlement_evidence" : "None"}
                </td>
              </tr>
            </tbody>
          </table>
        </AccordionSection>

        {/* 3. Attribution — only if settlement verified */}
        <AccordionSection title="Recovery Attribution" icon="🏷" badge={isVerifiedRecovered ? "SETTLEMENT VERIFIED" : "NOT ATTRIBUTED"} defaultOpen={isVerifiedRecovered}>
          {isVerifiedRecovered ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.8125rem" }}>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Verified Recovery</div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>
                  {fmtRupee(verifiedRecovery)}
                </div>
                {netRecovery != null && (
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                    Net (after cost): {fmtRupee(netRecovery)}
                  </div>
                )}
              </div>
              <div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", marginBottom: 3 }}>Attribution Type</div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--accent)", fontFamily: "monospace" }}>
                  {attributionLoading
                    ? "Loading..."
                    : attribution?.attribution_type ?? "Not attributed"}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {attribution?.attribution_reason ?? "Attribution not yet determined."}
                </div>
              </div>
              <div style={{ gridColumn: "1 / -1", marginTop: "0.25rem", padding: "0.625rem 0.875rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Attribution rules: DIRECT_AGENT = recovery via agent-executed action. AGENT_ASSISTED = recovery following agent communication. ORGANIC = recovery without agent intervention. UNKNOWN = attribution not determinable. Agent recovery is never claimed for organic or unverified money.
              </div>
            </div>
          ) : (
            <div>
              <EmptyEvidenceNote message="Settlement not verified — no verified money to attribute. Attribution is only recorded when settlement evidence confirms realized recovery." />
              {settlement && !settlementVerified && (
                <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  Settlement evidence exists but is not yet verified.
                </div>
              )}
            </div>
          )}
        </AccordionSection>

      </div>
    </div>
  );
}
