"use client";

import React from "react";

export default function TrustPanel() {
  return (
    <div style={{ padding: "1.25rem", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)", marginBottom: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
        <div>
          <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            REVPLUG AUTONOMOUS TRUST &amp; SAFETY GUARANTEES
          </h3>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
            Factual implementation safeguards verified by automated test suites
          </div>
        </div>
        <span style={{ fontSize: "0.6875rem", background: "#10b981", color: "#fff", padding: "3px 8px", borderRadius: 4, fontWeight: 700 }}>
          100% AUDITED BOUNDARIES
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", fontSize: "0.8125rem" }}>
        <div style={{ background: "var(--bg-primary)", padding: "0.75rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <strong style={{ color: "#10b981" }}>✓ Independent Policy Gate</strong>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            Every AI recommendation is checked against deterministic code rules before execution.
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.75rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <strong style={{ color: "#10b981" }}>✓ Non-Bypassable Hard Safety</strong>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            Fraud signals and customer opt-outs CANNOT be overridden by LLM proposals or human reviews.
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.75rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <strong style={{ color: "#10b981" }}>✓ Strict Idempotency</strong>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            Duplicate webhooks and worker retries are rejected before financial execution.
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.75rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <strong style={{ color: "#10b981" }}>✓ Immediate Success Stop</strong>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            Verified payment success instantly halts all pending retries and worker jobs.
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.75rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <strong style={{ color: "#10b981" }}>✓ Allowlisted Action Registry</strong>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            Model output strings are validated against a strict action contract allowlist.
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", padding: "0.75rem", borderRadius: 6, border: "1px solid var(--border)" }}>
          <strong style={{ color: "#10b981" }}>✓ Deterministic Fallback</strong>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            LLM timeouts, malformed JSON, or low confidence (&lt;0.5) trigger safe fallbacks or STOP.
          </div>
        </div>
      </div>
    </div>
  );
}
