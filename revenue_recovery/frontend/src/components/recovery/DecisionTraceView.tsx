"use client";

import React, { useState, useMemo } from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface DecisionTraceViewProps {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
  itemId?: string;
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

export function resolveCaseData(trace: CaseTrace | null, detail: CaseDetail | null): ResolvedCaseData {
  const amountAtRisk =
    trace?.amount_at_risk_minor != null ? trace.amount_at_risk_minor :
    detail?.amount_minor != null ? detail.amount_minor :
    null;

  const expectedRecovery = trace?.expected_recovery_minor ?? null;

  const settlement = trace?.settlement_evidence as Record<string, any> | null | undefined;
  const settlementVerified = settlement?.verified === true;
  const verifiedRecovery: number | null = settlementVerified
    ? (settlement?.verified_amount_minor ?? null)
    : null;

  const cost = (trace?.execution as Record<string, any> | null)?.cost_minor ?? null;

  const status = trace?.status ?? detail?.status ?? "unknown";
  const rootCause =
    trace?.context_snapshot?.failure_category ??
    detail?.root_cause ??
    null;

  return { amountAtRisk, expectedRecovery, verifiedRecovery, cost, status, rootCause };
}

const fmtRupee = (minor: number | null | undefined) => {
  if (minor == null) return "Not available";
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const fmtPct = (val: number | null | undefined) => {
  if (val == null) return "—";
  return `${(val * 100).toFixed(0)}%`;
};

const actionLabel = (action: string | null | undefined) => {
  if (!action) return "Not available";
  return action.replace(/_/g, " ").toUpperCase();
};

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
    <div style={{ borderRadius: 8, border: "1px solid var(--border)", overflow: "hidden" }}>
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

  const resolved = useMemo(
    () => propCaseData ?? resolveCaseData(trace, detail),
    [propCaseData, trace, detail]
  );

  const { amountAtRisk, expectedRecovery, verifiedRecovery, cost, status, rootCause } = resolved;

  const settlement = trace?.settlement_evidence as Record<string, any> | null | undefined;
  const settlementVerified = settlement?.verified === true;
  const isVerifiedRecovered = settlementVerified && (verifiedRecovery ?? 0) > 0;

  const execution = trace?.execution as Record<string, any> | null | undefined;
  const executionRecorded = execution?.executed === true;
  const executionStatus = execution?.status ?? null;
  const actionExecuted: string | null = execution?.action ?? (detail as any)?.action_taken ?? null;

  const candidates = trace?.candidate_actions?.length ? trace.candidate_actions : [];
  const selectedCandidate = candidates.find((c) => c.selected) ?? null;

  const classificationMethod: string = (detail as any)?.classification_method ?? trace?.classification_method ?? null;
  const classMethodLabel =
    classificationMethod === "LLM_PRIMARY" ? "AI-assisted" :
    classificationMethod === "LLM_FALLBACK" ? "AI fallback" :
    classificationMethod === "RULES" ? "Deterministic" :
    "—";
  const classMethodColor =
    classificationMethod === "LLM_PRIMARY" ? "#a78bfa" :
    classificationMethod === "LLM_FALLBACK" ? "#fbbf24" :
    classificationMethod === "RULES" ? "#38bdf8" :
    "var(--text-muted)";

  const productDecision = trace?.product_decision;
  const canonicalDecision = productDecision?.decision ?? null;

  const aiRec = trace?.ai_recommendation as Record<string, any> | null | undefined;
  const aiModel: string | null = aiRec?.model && aiRec.model !== "null" ? aiRec.model : null;
  const aiLatencyMs: number | null = aiRec?.latency_ms ?? null;
  const aiConfidence: number | null = aiRec?.confidence ?? null;
  const aiSelectedAction: string | null = aiRec?.selected_action ?? null;
  const aiRationale: string | null = aiRec?.user_safe_reasoning ?? null;
  const aiEvidence: string[] = Array.isArray(aiRec?.evidence) ? aiRec.evidence : [];
  const aiFallbackUsed = aiRec?.fallback_used === true;

  const policyAllowed = (trace?.safety_decision as any)?.allowed ?? null;
  const policyReasonCode = (trace?.safety_decision as any)?.reason_code ?? null;
  const policyEvaluated = trace?.policy_evaluations != null && Object.keys(trace.policy_evaluations as any).length > 0;

  const netRecovery =
    verifiedRecovery != null && cost != null
      ? verifiedRecovery - cost
      : null;

  const finalAction = selectedCandidate?.action ?? aiSelectedAction;
  const finalActionDisplay = actionExecuted ?? finalAction;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* 1. WHAT WE CHOSE — Most prominent section                     */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <div style={{
        padding: "1.25rem",
        background: "var(--bg-secondary)",
        borderRadius: 12,
        border: "1px solid var(--border)",
      }}>
        <div style={{
          fontSize: "0.625rem",
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: "0.75rem",
        }}>
          Final Action
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "1rem" }}>
          <span style={{
            fontSize: "1.5rem",
            fontWeight: 800,
            color: "var(--accent)",
            fontFamily: "monospace",
          }}>
            {actionLabel(finalActionDisplay)}
          </span>
          {actionExecuted && actionExecuted !== finalAction && (
            <span style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              fontStyle: "italic",
            }}>
              (executed: {actionLabel(actionExecuted)})
            </span>
          )}
        </div>

        {/* Key metrics row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Expected Net Recovery
            </div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: selectedCandidate?.net_expected_recovery != null && selectedCandidate.net_expected_recovery > 0 ? "#10b981" : "var(--text-muted)", fontFamily: "monospace" }}>
              {selectedCandidate?.net_expected_recovery != null
                ? fmtRupee(selectedCandidate.net_expected_recovery)
                : expectedRecovery != null
                  ? fmtRupee(expectedRecovery)
                  : "Not available"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Recovery Probability
            </div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>
              {selectedCandidate?.recovery_probability != null
                ? fmtPct(selectedCandidate.recovery_probability)
                : "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Policy Status
            </div>
            <div style={{
              fontSize: "1.125rem",
              fontWeight: 700,
              fontFamily: "monospace",
              color: policyAllowed === true ? "#10b981" : policyAllowed === false ? "#ef4444" : "var(--text-muted)",
            }}>
              {policyAllowed === true ? "ALLOWED" : policyAllowed === false ? "BLOCKED" : "—"}
            </div>
          </div>
        </div>

        {/* Revenue at risk strip */}
        <div style={{
          display: "flex",
          gap: "1.5rem",
          alignItems: "center",
          padding: "0.75rem 1rem",
          background: "var(--bg-primary)",
          borderRadius: 8,
          border: "1px solid var(--border)",
        }}>
          <div>
            <span style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Revenue at Risk </span>
            <span style={{ fontWeight: 700, color: "#ef4444", fontFamily: "monospace" }}>{fmtRupee(amountAtRisk)}</span>
          </div>
          {cost != null && (
            <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: "1.5rem" }}>
              <span style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Intervention Cost </span>
              <span style={{ fontWeight: 700, color: "var(--text-secondary)", fontFamily: "monospace" }}>{fmtRupee(cost)}</span>
            </div>
          )}
          {isVerifiedRecovered && (
            <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: "1.5rem" }}>
              <span style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Verified Recovery </span>
              <span style={{ fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>{fmtRupee(verifiedRecovery)}</span>
            </div>
          )}
          {netRecovery != null && (
            <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: "1.5rem" }}>
              <span style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Net Recovery </span>
              <span style={{ fontWeight: 700, color: netRecovery >= 0 ? "#10b981" : "#ef4444", fontFamily: "monospace" }}>{fmtRupee(netRecovery)}</span>
            </div>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* 2. WHY THIS ACTION                                            */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <div style={{
        padding: "1rem",
        background: "var(--bg-secondary)",
        borderRadius: 12,
        border: "1px solid var(--border)",
      }}>
        <div style={{
          fontSize: "0.625rem",
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: "0.75rem",
        }}>
          Why This Action
        </div>

        {aiRationale ? (
          <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "0.75rem" }}>
            {aiRationale}
          </div>
        ) : selectedCandidate?.reason ? (
          <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "0.75rem" }}>
            {selectedCandidate.reason}
          </div>
        ) : productDecision?.reason ? (
          <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "0.75rem" }}>
            {productDecision.reason}
          </div>
        ) : (
          <div style={{ fontSize: "0.875rem", color: "var(--text-muted)", fontStyle: "italic" }}>
            No reasoning recorded
          </div>
        )}

        {aiEvidence.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            {aiEvidence.map((e, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                <span style={{ color: "#10b981", marginTop: 2 }}>•</span>
                <span>{e}</span>
              </div>
            ))}
          </div>
        )}

        {/* Method badge */}
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", alignItems: "center" }}>
          <span style={{
            fontSize: "0.625rem",
            fontWeight: 700,
            padding: "2px 8px",
            borderRadius: 4,
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            color: classMethodColor,
          }}>
            {classMethodLabel}
          </span>
          {aiModel && (
            <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              {aiModel}
            </span>
          )}
          {aiLatencyMs != null && (
            <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              {aiLatencyMs}ms
            </span>
          )}
          {aiFallbackUsed && (
            <span style={{
              fontSize: "0.625rem",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: 4,
              background: "rgba(245,158,11,0.1)",
              border: "1px solid rgba(245,158,11,0.25)",
              color: "#fbbf24",
            }}>
              Fallback used
            </span>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* 3. WHAT ELSE WE CONSIDERED — Alternatives                    */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      {candidates.length > 0 && (
        <div style={{
          padding: "1rem",
          background: "var(--bg-secondary)",
          borderRadius: 12,
          border: "1px solid var(--border)",
        }}>
          <div style={{
            fontSize: "0.625rem",
            fontWeight: 700,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            marginBottom: "0.75rem",
          }}>
            Alternatives Considered
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {candidates.map((cand) => (
              <div
                key={cand.action}
                style={{
                  padding: "0.75rem 1rem",
                  background: cand.selected ? "rgba(99, 102, 241, 0.1)" : "var(--bg-primary)",
                  borderRadius: 8,
                  border: `1px solid ${cand.selected ? "var(--accent)" : "var(--border)"}`,
                  display: "grid",
                  gridTemplateColumns: "auto 1fr auto",
                  gap: "1rem",
                  alignItems: "center",
                }}
              >
                {/* Action name */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {cand.selected ? (
                    <span style={{ color: "var(--accent)", fontWeight: 700, fontSize: "0.875rem" }}>✓</span>
                  ) : (
                    <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>○</span>
                  )}
                  <span style={{
                    fontWeight: 700,
                    fontSize: "0.8125rem",
                    color: cand.selected ? "var(--accent)" : "var(--text-primary)",
                    fontFamily: "monospace",
                  }}>
                    {actionLabel(cand.action)}
                  </span>
                </div>

                {/* Metrics */}
                <div style={{ display: "flex", gap: "1rem", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                  <span>
                    <span style={{ color: "var(--text-secondary)" }}>Prob: </span>
                    {cand.recovery_probability != null ? fmtPct(cand.recovery_probability) : "—"}
                  </span>
                  <span>
                    <span style={{ color: "var(--text-secondary)" }}>Gross EV: </span>
                    {cand.gross_expected_recovery != null ? fmtRupee(cand.gross_expected_recovery) : "—"}
                  </span>
                  <span>
                    <span style={{ color: "var(--text-secondary)" }}>Cost: </span>
                    {cand.intervention_cost != null ? fmtRupee(cand.intervention_cost) : "—"}
                  </span>
                  <span>
                    <span style={{ color: "var(--text-secondary)" }}>Net EV: </span>
                    <span style={{
                      fontWeight: 700,
                      color: cand.net_expected_recovery != null && cand.net_expected_recovery > 0 ? "#10b981" : "var(--text-muted)",
                    }}>
                      {cand.net_expected_recovery != null ? fmtRupee(cand.net_expected_recovery) : "—"}
                    </span>
                  </span>
                </div>

                {/* Policy status */}
                <div style={{ textAlign: "right" }}>
                  <span style={{
                    fontSize: "0.6875rem",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: 4,
                    background: cand.policy_status === "ALLOWED" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                    color: cand.policy_status === "ALLOWED" ? "#10b981" : "#ef4444",
                    border: `1px solid ${cand.policy_status === "ALLOWED" ? "rgba(16, 185, 129, 0.25)" : "rgba(239, 68, 68, 0.25)"}`,
                  }}>
                    {cand.policy_status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* 4. POLICY / SAFETY CHECK                                    */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <div style={{
        padding: "1rem",
        background: "var(--bg-secondary)",
        borderRadius: 12,
        border: "1px solid var(--border)",
      }}>
        <div style={{
          fontSize: "0.625rem",
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: "0.75rem",
        }}>
          Policy / Safety Check
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Safety Decision
            </div>
            <div style={{
              fontSize: "0.875rem",
              fontWeight: 700,
              color: policyAllowed === true ? "#10b981" : policyAllowed === false ? "#ef4444" : "var(--text-muted)",
            }}>
              {policyAllowed === true ? "ALLOWED" : policyAllowed === false ? "BLOCKED" : "Not evaluated"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Rule
            </div>
            <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
              {policyReasonCode ? policyReasonCode.replace(/_/g, " ") : "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Execution Status
            </div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, color: executionRecorded ? "#10b981" : "var(--text-muted)" }}>
              {executionRecorded ? (executionStatus ?? "EXECUTED") : "Not executed"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Settlement
            </div>
            <div style={{
              fontSize: "0.875rem",
              fontWeight: 700,
              color: isVerifiedRecovered ? "#10b981" : "var(--text-muted)",
            }}>
              {isVerifiedRecovered ? "VERIFIED" : "Not verified"}
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* 5. CASE DETAILS — Collapsible technical details              */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>

        <AccordionSection
          title="Detection Context"
          icon="🔍"
          badge="Backend Evidence"
        >
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

        <AccordionSection
          title="Recovery Attribution"
          icon="🏷"
          badge={isVerifiedRecovered ? "Settlement Verified" : "Not Attributed"}
          defaultOpen={isVerifiedRecovered}
        >
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
                  {attributionLoading ? "Loading..." : attribution?.attribution_type ?? "Not attributed"}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {attribution?.attribution_reason ?? "Attribution not yet determined."}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
              Settlement not verified — no verified money to attribute.
            </div>
          )}
        </AccordionSection>

        <AccordionSection
          title="Audit Timeline"
          icon="📋"
          badge={trace?.timeline?.length ? `${trace.timeline.length} events` : "No events"}
        >
          {trace?.timeline && trace.timeline.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", fontSize: "0.75rem", maxHeight: 400, overflowY: "auto" }}>
              {trace.timeline.map((event: any, idx: number) => (
                <div key={event.id ?? idx} style={{
                  display: "grid",
                  gridTemplateColumns: "100px 80px 1fr",
                  gap: "0.5rem",
                  padding: "0.5rem",
                  background: idx % 2 === 0 ? "var(--bg-secondary)" : "var(--bg-primary)",
                  borderRadius: 4,
                  alignItems: "start",
                }}>
                  <span style={{ color: "var(--text-muted)", fontFamily: "monospace", fontSize: "0.6875rem" }}>
                    {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "—"}
                  </span>
                  <span style={{ fontWeight: 700, color: "var(--accent)" }}>
                    {event.actor}
                  </span>
                  <span style={{ color: "var(--text-secondary)" }}>
                    {event.action}: {event.reason ?? "—"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
              No audit events recorded.
            </div>
          )}
        </AccordionSection>

      </div>
    </div>
  );
}
