"use client";

import React from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface Props {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
}

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function RecoveryReceipt({ trace, detail }: Props) {
  const settlement = trace?.settlement_evidence as Record<string, any> | null | undefined;
  const isVerified = settlement?.verified === true;

  if (!isVerified) {
    // Settlement is ONLY confirmed by settlement_evidence.verified — never inferred from item status
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
          Recovery receipt
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.875rem",
            color: "var(--text-secondary)",
            fontWeight: 600,
          }}
        >
          <span style={{ color: "#64748b" }}>⊘</span>
          <span>Settlement not verified</span>
        </div>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
          No authoritative settlement evidence has been recorded for this opportunity. Verified recovered amount: ₹0.
        </div>
      </div>
    );
  }

  const verifiedAmountMinor =
    settlement?.verified_amount_minor ??
    trace?.verified_recovery_minor ??
    null;

  const paymentId = settlement?.payment_id ?? null;
  const eventId = settlement?.provider_event_id ?? null;
  const timestamp = settlement?.settlement_timestamp ?? trace?.timeline?.find((t: any) => t.event_type === "SETTLEMENT_RECEIVED")?.timestamp ?? null;
  // Provider and method come from settlement evidence only — never hardcoded defaults
  const provider = settlement?.provider ?? null;
  const method = settlement?.method ?? null;

  return (
    <div
      style={{
        padding: "1.25rem 1.5rem",
        background: "rgba(16, 185, 129, 0.04)",
        borderRadius: 8,
        border: "1px solid rgba(16, 185, 129, 0.3)",
        marginBottom: "1rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
          borderBottom: "1px solid rgba(16, 185, 129, 0.15)",
          paddingBottom: "0.75rem",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "#10b981",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
            }}
          >
            ✓ RECOVERY RECEIPT & SETTLEMENT PROOF
          </div>
          <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "#10b981", marginTop: 2 }}>
            Verified Recovered {verifiedAmountMinor != null ? fmtINR(verifiedAmountMinor) : "—"}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <span
            style={{
              fontSize: "0.625rem",
              fontWeight: 700,
              color: "#10b981",
              background: "rgba(16, 185, 129, 0.12)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              padding: "2px 8px",
              borderRadius: 4,
              textTransform: "uppercase",
            }}
          >
            SETTLEMENT VERIFIED
          </span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem" }}>
        <div>
          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Payment / Reference ID
          </div>
          <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 600, color: paymentId ? "var(--text-primary)" : "var(--text-muted)" }}>
            {paymentId ?? "—"}
          </div>
        </div>

        <div>
          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Provider Event Reference
          </div>
          <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 600, color: eventId ? "var(--text-primary)" : "var(--text-muted)" }}>
            {eventId ?? "—"}
          </div>
        </div>

        <div>
          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Verification Provider & Method
          </div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {provider && method ? `${provider} (${method})` : provider ?? method ?? "—"}
          </div>
        </div>

        {timestamp && (
          <div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Settlement Timestamp
            </div>
            <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
              {new Date(timestamp).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
