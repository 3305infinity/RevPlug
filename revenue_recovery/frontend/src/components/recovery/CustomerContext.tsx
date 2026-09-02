"use client";

import React from "react";
import Link from "next/link";
import { Customer360Profile } from "@/lib/api";

interface Props {
  profile: Customer360Profile | null;
  customerId: string;
  customerName?: string;
}

export default function CustomerContext({ profile, customerId, customerName }: Props) {
  if (!profile) {
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
          Customer context
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
          Identifier: <strong style={{ color: "var(--text-primary)" }}>{customerId}</strong>
          {customerName && ` (${customerName})`}
        </div>
      </div>
    );
  }

  const fatigue = profile.contact_fatigue;
  const methods = profile.payment_methods_used || [];
  const tier = profile.customer_value_tier;
  const optOut = profile.previous_opt_outs;
  const rate = profile.historical_recovery_rate;

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
          marginBottom: "0.875rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span>Customer context (Decision-Relevant)</span>
        <Link href={`/customers/${customerId}`} style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--accent)", textDecoration: "none", textTransform: "uppercase", letterSpacing: "0.04em" }}>
          View Profile →
        </Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem" }}>
        <div style={{ background: "var(--bg-primary)", padding: "0.625rem 0.875rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Customer Tier / Value
          </div>
          <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
            {tier || "Standard"}
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.625rem 0.875rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Consent / Opt-Out Status
          </div>
          <div style={{ fontSize: "0.875rem", fontWeight: 700, color: optOut ? "#ef4444" : "#10b981", marginTop: 2 }}>
            {optOut ? "Opted Out (Blocked)" : "Active Consent"}
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.625rem 0.875rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Contact Fatigue Risk
          </div>
          <div style={{ fontSize: "0.875rem", fontWeight: 700, color: fatigue?.fatigue_risk === "HIGH" ? "#ef4444" : "var(--text-primary)", marginTop: 2 }}>
            {fatigue?.fatigue_risk || "Low"} ({fatigue?.contacts_today || 0}/{fatigue?.daily_limit || 2} today)
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.625rem 0.875rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Historical Recovery Rate
          </div>
          <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981", marginTop: 2 }}>
            {Math.round((rate || 0) * 100)}%
          </div>
        </div>

        {methods.length > 0 && (
          <div style={{ background: "var(--bg-primary)", padding: "0.625rem 0.875rem", borderRadius: 6, border: "1px solid var(--border)", gridColumn: "span 2" }}>
            <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
              Available Payment Methods
            </div>
            <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>
              {methods.join(", ")}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
