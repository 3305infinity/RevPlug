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
    // Check if detail outcome has settlement
    const outcome = detail?.outcome as Record<string, any> | null | undefined;
    const outcomeVerified = outcome?.verified === true || detail?.status === "recovered";
    
    if (!outcomeVerified) {
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
            <span style={{ color: "#f59e0b" }}>⏳</span>
            <span>Settlement pending</span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            Settlement verification has not been confirmed for this opportunity yet.
          </div>
        </div>
      );
    }
  }

  const verifiedAmountMinor =
    settlement?.verified_amount_minor ??
    (detail as any)?.actual_recovery_value ??
    trace?.verified_recovery_minor ??
    0;

  const paymentId = settlement?.payment_id || (detail as any)?.metadata?.razorpay_payment_id || "N/A";
  const eventId = settlement?.provider_event_id || (detail as any)?.metadata?.provider_event_id || "N/A";
  const timestamp = settlement?.settlement_timestamp || trace?.timeline?.find(t => t.event_type === "SETTLEMENT_RECEIVED")?.timestamp || null;
  const provider = settlement?.provider || "Razorpay";
  const method = settlement?.method || "webhook_hmac";

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
            Recovered {fmtINR(verifiedAmountMinor)}
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
          <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {paymentId}
          </div>
        </div>

        <div>
          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Provider Event Reference
          </div>
          <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {eventId}
          </div>
        </div>

        <div>
          <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Verification Provider & Method
          </div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {provider} ({method})
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
