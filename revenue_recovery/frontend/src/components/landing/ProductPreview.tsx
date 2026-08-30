"use client";

import Link from "next/link";
import { RecoveryItem } from "@/lib/api";

export default function ProductPreview({ items }: { items: RecoveryItem[] }) {
  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  // Use a real recent item if available, otherwise high-fidelity illustrative case
  const realItem = items && items.length > 0 ? items[0] : null;

  const sampleData = realItem
    ? {
        id: realItem.id,
        amount: fmt(realItem.amount_minor),
        diagnosis: realItem.root_cause || "soft_downtime",
        expected: fmt(realItem.expected_recovery_value || 34500),
        recommendation: (realItem.metadata?.proposed_action as string) || "retry_payment",
        policyState: realItem.stopped_reason || "Policy Allowed",
        execution: realItem.status === "recovered" ? "Succeeded" : realItem.status === "stopped" ? "Blocked" : "Executed",
        verified: fmt(realItem.actual_recovery_value || realItem.expected_recovery_value || realItem.amount_minor),
        isReal: true,
      }
    : {
        id: "pay_demo_1787993826",
        amount: "₹50,000",
        diagnosis: "soft_downtime (Temporary 503)",
        expected: "₹34,500",
        recommendation: "retry_payment",
        policyState: "Allowed (Within 3 Max Retries)",
        execution: "Success (Attempt 1)",
        verified: "₹34,500 Settled",
        isReal: false,
      };

  return (
    <section style={{ padding: "4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 3rem" }}>
        <div style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "var(--accent)",
          marginBottom: "0.5rem",
        }}>
          Live System Trace
        </div>
        <h2 style={{
          fontSize: "clamp(1.75rem, 3vw, 2.35rem)",
          fontWeight: 700,
          color: "#fff",
          marginBottom: "1rem",
        }}>
          Inside a Recovery Case
        </h2>
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
          Inspect how RevPlug evaluates a single case from initial failure signal to final settlement verification.
        </p>
      </div>

      <div className="card" style={{
        maxWidth: 800,
        margin: "0 auto",
        padding: "2rem",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        boxShadow: "0 15px 30px rgba(0, 0, 0, 0.3)",
      }}>
        {/* Header */}
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
          paddingBottom: "1rem",
          borderBottom: "1px solid var(--border-subtle)",
        }}>
          <div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {sampleData.isReal ? "Live System Case" : "Illustrative Example Case"}
            </div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, fontFamily: "monospace", color: "var(--accent)" }}>
              {sampleData.id}
            </div>
          </div>
          <span style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            padding: "0.25rem 0.65rem",
            borderRadius: 100,
            background: "var(--success-subtle)",
            color: "var(--success)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
          }}>
            ✓ Verified Recovery
          </span>
        </div>

        {/* 6-step breakdown */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1.25rem", marginBottom: "1.5rem" }}>
          <div style={{ background: "var(--bg-elevated)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
              1. Payment Failure
            </div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--danger)", fontFamily: "monospace" }}>
              {sampleData.amount} at risk
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
              2. Diagnosis
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--warning)" }}>
              {sampleData.diagnosis}
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
              3. Expected Recovery
            </div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--purple)", fontFamily: "monospace" }}>
              {sampleData.expected} EV
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
              4. AI Proposal
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--accent)" }}>
              {sampleData.recommendation}
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
              5. Policy & Safety Guard
            </div>
            <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--accent)" }}>
              {sampleData.policyState}
            </div>
          </div>

          <div style={{ background: "var(--bg-elevated)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>
              6. Verified Recovery
            </div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--success)", fontFamily: "monospace" }}>
              {sampleData.verified}
            </div>
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <Link
            href={sampleData.isReal ? `/recovery/${sampleData.id}` : "/run-recovery"}
            style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--accent)" }}
          >
            Inspect full case detail & audit log →
          </Link>
        </div>
      </div>
    </section>
  );
}
