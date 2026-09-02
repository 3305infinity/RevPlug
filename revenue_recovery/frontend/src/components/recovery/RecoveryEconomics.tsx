"use client";

import React from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
}

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function DataProvenanceBadge({ label, color }: { label: string; color: string }) {
  return (
    <span
      style={{
        fontSize: "0.5rem",
        fontWeight: 700,
        color: color,
        border: `1px solid ${color}44`,
        background: `${color}14`,
        padding: "1px 5px",
        borderRadius: 3,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        verticalAlign: "middle",
        marginLeft: 6,
      }}
    >
      {label}
    </span>
  );
}

export default function RecoveryEconomics({ trace, detail }: Props) {
  // Revenue at risk — from item, authoritative
  const amountAtRiskMinor =
    trace?.amount_at_risk_minor ??
    (detail as any)?.amount_minor ??
    null;

  // Expected recovery — ONLY from backend trace, never calculated on frontend
  const expectedMinor = trace?.expected_recovery_minor ?? null;
  const hasExpected = expectedMinor != null && expectedMinor > 0;

  // Verified recovery — ONLY from settlement_evidence.verified === true
  const settlement = trace?.settlement_evidence as Record<string, any> | null | undefined;
  const settlementVerified = settlement?.verified === true;
  const verifiedMinor: number | null = settlementVerified
    ? (settlement?.verified_amount_minor ?? null)
    : null;

  // Intervention cost — from execution.cost_minor or trace.intervention_cost_minor
  const costMinor =
    (trace?.execution as Record<string, any> | null)?.cost_minor ??
    trace?.intervention_cost_minor ??
    null;

  // Net recovery — only when verified
  const netMinor =
    verifiedMinor != null && costMinor != null
      ? verifiedMinor - costMinor
      : null;

  const recoveryRate =
    amountAtRiskMinor && verifiedMinor != null && amountAtRiskMinor > 0
      ? Math.round((verifiedMinor / amountAtRiskMinor) * 100)
      : null;

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
        Recovery economics
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "1rem",
        }}
      >
        {/* Revenue at risk */}
        <div
          style={{
            background: "var(--bg-primary)",
            borderRadius: 7,
            border: "1px solid rgba(239,68,68,0.18)",
            padding: "0.875rem 1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "#ef4444",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 5,
            }}
          >
            Revenue at risk
          </div>
          <div
            className="font-mono"
            style={{
              fontSize: "1.5rem",
              fontWeight: 800,
              color: "#ef4444",
              lineHeight: 1,
            }}
          >
            {amountAtRiskMinor != null ? fmtINR(amountAtRiskMinor) : "—"}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            Authoritative
          </div>
        </div>

        {/* Expected recovery */}
        <div
          style={{
            background: "var(--bg-primary)",
            borderRadius: 7,
            border: "1px solid rgba(99,102,241,0.15)",
            padding: "0.875rem 1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: "#6366f1",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 5,
            }}
          >
            Expected recovery
            <DataProvenanceBadge label="Projected" color="#6366f1" />
          </div>
          <div
            className="font-mono"
            style={{
              fontSize: "1.5rem",
              fontWeight: 800,
              color: hasExpected ? "#6366f1" : "var(--text-muted)",
              lineHeight: 1,
            }}
          >
            {hasExpected ? fmtINR(expectedMinor!) : "—"}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            {hasExpected ? "Pre-execution estimate" : "Not available"}
          </div>
        </div>

        {/* Verified recovered */}
        <div
          style={{
            background: settlementVerified ? "rgba(16,185,129,0.06)" : "var(--bg-primary)",
            borderRadius: 7,
            border: settlementVerified
              ? "1px solid rgba(16,185,129,0.3)"
              : "1px solid var(--border)",
            padding: "0.875rem 1rem",
          }}
        >
          <div
            style={{
              fontSize: "0.5625rem",
              fontWeight: 700,
              color: settlementVerified ? "#10b981" : "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: 5,
            }}
          >
            {settlementVerified ? (
              <>
                Verified recovered
                <DataProvenanceBadge label="Settlement confirmed" color="#10b981" />
              </>
            ) : (
              "Actual recovery"
            )}
          </div>
          <div
            className="font-mono"
            style={{
              fontSize: "1.5rem",
              fontWeight: 800,
              color: settlementVerified ? "#10b981" : "var(--text-muted)",
              lineHeight: 1,
            }}
          >
            {settlementVerified && verifiedMinor != null ? fmtINR(verifiedMinor) : "—"}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
            {settlementVerified ? "Settlement verified" : "No verified recovery yet"}
          </div>
        </div>

        {/* Intervention cost */}
        {costMinor != null && (
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 7,
              border: "1px solid var(--border)",
              padding: "0.875rem 1rem",
            }}
          >
            <div
              style={{
                fontSize: "0.5625rem",
                fontWeight: 700,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: 5,
              }}
            >
              Intervention cost
            </div>
            <div
              className="font-mono"
              style={{
                fontSize: "1.5rem",
                fontWeight: 800,
                color: costMinor > 0 ? "var(--text-secondary)" : "var(--text-muted)",
                lineHeight: 1,
              }}
            >
              {fmtINR(costMinor)}
            </div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
              Execution cost
            </div>
          </div>
        )}

        {/* Net recovery */}
        {netMinor != null && (
          <div
            style={{
              background: netMinor >= 0 ? "rgba(16,185,129,0.04)" : "rgba(239,68,68,0.04)",
              borderRadius: 7,
              border: `1px solid ${netMinor >= 0 ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
              padding: "0.875rem 1rem",
            }}
          >
            <div
              style={{
                fontSize: "0.5625rem",
                fontWeight: 700,
                color: netMinor >= 0 ? "#10b981" : "#ef4444",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: 5,
              }}
            >
              Net recovery
            </div>
            <div
              className="font-mono"
              style={{
                fontSize: "1.5rem",
                fontWeight: 800,
                color: netMinor >= 0 ? "#10b981" : "#ef4444",
                lineHeight: 1,
              }}
            >
              {fmtINR(netMinor)}
            </div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
              After cost · {recoveryRate != null ? `${recoveryRate}% recovery rate` : ""}
            </div>
          </div>
        )}
      </div>

      {/* Strict provenance note */}
      <div
        style={{
          marginTop: "0.875rem",
          fontSize: "0.6875rem",
          color: "var(--text-muted)",
          lineHeight: 1.5,
          borderTop: "1px solid var(--border)",
          paddingTop: "0.625rem",
        }}
      >
        <strong style={{ color: "var(--text-secondary)" }}>Financial truth rule:</strong> Expected recovery is a pre-execution projection.
        Verified recovery is recognized only after authoritative settlement confirmation.
        These are never interchangeable.
      </div>
    </div>
  );
}
