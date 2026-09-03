"use client";

import React from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
  amountAtRiskMinor: number;
}

function fmtINR(minor: number) {
  return (
    "₹" +
    (minor / 100).toLocaleString("en-IN", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })
  );
}

interface ReasonRow {
  label: string;
  value: string;
  highlight?: boolean;
}

export default function RecoveryWhy({ trace, detail, amountAtRiskMinor }: Props) {
  const diagnosis = trace?.diagnosis as Record<string, any> | null | undefined;
  const aiRec = trace?.ai_recommendation;
  const ctxSnap = trace?.context_snapshot as Record<string, any> | null | undefined;
  const policyEval = trace?.policy_evaluations as Record<string, any> | null | undefined;
  const safetyDec = trace?.safety_decision as Record<string, any> | null | undefined;
  const productDec = trace?.product_decision ?? null;

  // Build the "why" rows from structured data only
  const rows: ReasonRow[] = [];

  // 1. Detected problem
  const failureCategory =
    (ctxSnap?.failure_category ?? ctxSnap?.category ?? (detail as any)?.root_cause ?? null) as string | null;
  if (failureCategory) {
    rows.push({
      label: "Detected problem",
      value: failureCategory.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      highlight: true,
    });
  }

  // 2. Diagnosis / root cause
  const rootCause = (diagnosis?.root_cause as string | null) ?? null;
  const diagRationale = (diagnosis?.rationale as string | null) ?? null;
  const diagSource = (diagnosis?.diagnosis_source as string | null) ?? null;
  if (rootCause && rootCause !== failureCategory) {
    rows.push({ label: "Root cause", value: rootCause.replace(/_/g, " ") });
  }
  if (diagRationale) {
    rows.push({ label: "Diagnosis", value: diagRationale });
  }
  if (diagSource) {
    const diagSourceLabel =
      diagSource === "llm" ? "AI diagnosis (LLM)" : "Deterministic rules";
    rows.push({ label: "Diagnosis method", value: diagSourceLabel });
  }

  // 3. Confidence
  const confidence = aiRec?.confidence != null ? aiRec.confidence : null;
  if (confidence != null) {
    rows.push({
      label: "Confidence",
      value: `${Math.round(Number(confidence) * 100)}%`,
    });
  }

  // 4. Economic rationale — expected recovery only (amount at risk shown in DecisionCard)
  const expectedMinor = trace?.expected_recovery_minor ?? 0;
  if (expectedMinor > 0) {
    rows.push({
      label: "Expected recovery",
      value: `${fmtINR(expectedMinor)} (projected)`,
      highlight: true,
    });
  }

  // 5. Policy constraints
  const policyAllowed = policyEval?.allowed;
  const policyRule = policyEval?.policy_rule ?? safetyDec?.rule ?? null;
  const policyReason = policyEval?.reason ?? safetyDec?.reason ?? null;
  if (policyAllowed != null) {
    rows.push({
      label: "Policy outcome",
      value: policyAllowed ? "Permitted" : "Blocked",
      highlight: !policyAllowed,
    });
  }
  if (!policyAllowed && policyRule) {
    rows.push({
      label: "Policy rule",
      value: String(policyRule).replace(/_/g, " "),
    });
  }
  if (!policyAllowed && policyReason) {
    rows.push({ label: "Policy reason", value: String(policyReason) });
  }

  // 6. Previous attempts
  const attemptCount =
    (ctxSnap?.attempt_count as number | null | undefined) ??
    ((detail?.attempts?.length ?? 0) > 0 ? detail!.attempts.length : null);
  if (attemptCount != null && attemptCount > 0) {
    rows.push({
      label: "Previous attempts",
      value: `${attemptCount}`,
    });
  }

  // 7. Timing/scheduling
  if (productDec?.scheduled_for) {
    rows.push({
      label: "Scheduled for",
      value: new Date(productDec.scheduled_for).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      }),
    });
  }

  // 8. AI evidence bullets (from recommendation)
  const evidenceBullets = Array.isArray(aiRec?.evidence) ? (aiRec!.evidence as string[]) : [];

  // Nothing to show
  if (rows.length === 0 && evidenceBullets.length === 0) {
    return (
      <div
        style={{
          padding: "1.25rem",
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
          Why this decision?
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontStyle: "italic" }}>
          Decision rationale is not available for this case.
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
        Why this decision?
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: "0.75rem",
          marginBottom: evidenceBullets.length > 0 ? "1rem" : 0,
        }}
      >
        {rows.map((row, i) => (
          <div
            key={i}
            style={{
              background: "var(--bg-primary)",
              borderRadius: 6,
              border: `1px solid ${row.highlight ? "rgba(239,68,68,0.2)" : "var(--border)"}`,
              padding: "0.625rem 0.875rem",
            }}
          >
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
              {row.label}
            </div>
            <div
              style={{
                fontSize: "0.8125rem",
                fontWeight: 600,
                color: row.highlight ? "var(--text-primary)" : "var(--text-secondary)",
                lineHeight: 1.4,
              }}
            >
              {row.value}
            </div>
          </div>
        ))}
      </div>

      {/* AI evidence bullets */}
      {evidenceBullets.length > 0 && (
        <div
          style={{
            borderTop: "1px solid var(--border)",
            paddingTop: "0.875rem",
            marginTop: "0.25rem",
          }}
        >
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: "0.5rem",
            }}
          >
            Decision evidence
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: "1.125rem",
              fontSize: "0.8125rem",
              color: "var(--text-secondary)",
              lineHeight: 1.65,
            }}
          >
            {evidenceBullets.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
