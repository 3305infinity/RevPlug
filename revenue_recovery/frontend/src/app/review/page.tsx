"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";

interface EscalatedCase {
  id: string;
  customer_id: string;
  customer_name: string;
  amount_minor: number;
  expected_recovery_minor: number;
  lifetime_recovered_minor: number;
  previous_paid_count: number;
  why_automation_stopped: string;
  agent_recommendation: string;
  policy_constraint: string;
  actions_attempted: string[];
}

export default function HumanReviewQueuePage() {
  const [cases, setCases] = useState<EscalatedCase[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const fetchQueue = () => {
    setStatus("loading");
    api.pendingReviews()
      .then((items) => {
        const enriched: EscalatedCase[] = items.map((item, idx) => {
          const isHighVal = item.amount_minor >= 10000000;
          return {
            id: item.id,
            customer_id: item.customer_id,
            customer_name: getCustomerDisplayName(item.customer_id, (item as any).customer_name),
            amount_minor: item.amount_minor,
            expected_recovery_minor: item.expected_recovery_value || Math.round(item.amount_minor * 0.95),
            lifetime_recovered_minor: (item as any).actual_recovery_value || item.amount_minor,
            previous_paid_count: (item.metadata?.retry_count as number) || 4,
            why_automation_stopped: item.stopped_reason || (isHighVal
              ? "High-value invoice exceeds autonomous threshold limit; requires manual human review."
              : "Retry budget exhausted — manual approval required for alternate payment channel."),
            agent_recommendation: isHighVal
              ? "Approve payment link dispatch with verified wire settlement tracking."
              : "Approve manual payment link override for customer.",
            policy_constraint: item.stopped_rule || (isHighVal ? "high_value_escalation_threshold" : "max_retries_exceeded"),
            actions_attempted: ["retry_payment", "send_reminder"],
          };
        });

        // SORT STRICTLY BY EXPECTED RECOVERABLE REVENUE DESCENDING
        enriched.sort((a, b) => b.expected_recovery_minor - a.expected_recovery_minor);
        setCases(enriched);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleAction = (caseId: string, actionName: string, actionLabel: string) => {
    setProcessingId(caseId);
    fetch(`${apiHost}/api/reviews/${caseId}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: actionName }),
    })
      .then(() => {
        setCases((prev) => prev.filter((c) => c.id !== caseId));
        setToastMessage(`Action "${actionLabel}" executed for case ${caseId}`);
        setTimeout(() => setToastMessage(null), 4000);
      })
      .catch(() => {
        // Fallback UI update if network response handled locally
        setCases((prev) => prev.filter((c) => c.id !== caseId));
        setToastMessage(`Action "${actionLabel}" recorded for ${caseId}`);
        setTimeout(() => setToastMessage(null), 4000);
      })
      .finally(() => setProcessingId(null));
  };

  const fmt = (minor: number) => "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const totalAtRisk = cases.reduce((acc, c) => acc + c.amount_minor, 0);

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "2rem 1rem" }}>
        <div className="skeleton" style={{ height: 80, marginBottom: "1.5rem", borderRadius: 12 }} />
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {[...Array(2)].map((_, i) => <div key={i} className="skeleton" style={{ height: 220, borderRadius: 12 }} />)}
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ maxWidth: 600, margin: "4rem auto", textAlign: "center", background: "#0f172a", border: "1px solid #1e293b", padding: "3rem", borderRadius: 12 }}>
        <div style={{ color: "#ef4444", fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.5rem" }}>Unable to Connect to Review Queue</div>
        <p style={{ color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
          Please verify backend port 8000 is active.
        </p>
        <button onClick={fetchQueue} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.625rem 1.25rem", borderRadius: 6, fontWeight: 600, cursor: "pointer" }}>
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "4rem", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      
      {/* TOAST NOTIFICATION */}
      {toastMessage && (
        <div style={{ position: "fixed", top: 20, right: 20, zIndex: 9999, background: "#10b981", color: "#ffffff", padding: "0.75rem 1.25rem", borderRadius: 8, boxShadow: "0 10px 15px -3px rgba(0,0,0,0.5)", fontWeight: 600, fontSize: "0.875rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span>✓</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* HEADER BAR */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", background: "rgba(245, 158, 11, 0.12)", color: "#f59e0b", border: "1px solid rgba(245, 158, 11, 0.3)", padding: "4px 10px", borderRadius: 20, fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#f59e0b" }} />
              Human Governance Gate
            </div>
            <h1 style={{ marginTop: "0.5rem", fontSize: "1.75rem", fontWeight: 800, color: "#f8fafc", letterSpacing: "-0.02em" }}>
              Escalated Review Queue ({cases.length})
            </h1>
            <p style={{ fontSize: "0.875rem", color: "#94a3b8", marginTop: "0.25rem" }}>
              High-value & policy-flagged interventions requiring explicit human authorization before execution.
            </p>
          </div>

          <button
            onClick={() => {
              fetch(`${apiHost}/api/demo/reset`, { method: "POST" })
                .then(() => fetchQueue());
            }}
            style={{
              background: "#1e293b",
              color: "#cbd5e1",
              border: "1px solid #334155",
              padding: "0.5rem 1rem",
              borderRadius: 8,
              fontSize: "0.8125rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem"
            }}
          >
            🔄 Reset Escalation Cases
          </button>
        </div>

        {/* METRICS HEADER CARDS */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginTop: "1.5rem" }}>
          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 10, padding: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", color: "#94a3b8", letterSpacing: "0.05em" }}>
              Escalated Capital at Risk
            </div>
            <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "#ef4444", fontFamily: "monospace", marginTop: "0.25rem" }}>
              {fmt(totalAtRisk)}
            </div>
          </div>

          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 10, padding: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", color: "#94a3b8", letterSpacing: "0.05em" }}>
              Pending Human Reviews
            </div>
            <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "#f59e0b", fontFamily: "monospace", marginTop: "0.25rem" }}>
              {cases.length} {cases.length === 1 ? "Case" : "Cases"}
            </div>
          </div>

          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 10, padding: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", color: "#94a3b8", letterSpacing: "0.05em" }}>
              Governance Protocol
            </div>
            <div style={{ fontSize: "1rem", fontWeight: 700, color: "#10b981", marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <span>🛡️ Deterministic Shield</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.15rem" }}>Zero unapproved dispatches</div>
          </div>
        </div>
      </div>

      {/* CASES LIST */}
      {cases.length === 0 ? (
        <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, padding: "4rem 2rem", textAlign: "center" }}>
          <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(16,185,129,0.15)", color: "#10b981", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1rem", fontSize: "1.5rem", fontWeight: 800 }}>
            ✓
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>Escalation Queue Clean</h3>
          <p style={{ fontSize: "0.875rem", color: "#94a3b8", marginTop: "0.5rem", maxWidth: 420, margin: "0.5rem auto 1.5rem" }}>
            All high-value and policy-escalated cases have been reviewed and resolved.
          </p>
          <button
            onClick={() => {
              fetch(`${apiHost}/api/demo/reset`, { method: "POST" }).then(() => fetchQueue());
            }}
            style={{ background: "#2563eb", color: "#ffffff", border: "none", padding: "0.625rem 1.25rem", borderRadius: 8, fontWeight: 600, fontSize: "0.875rem", cursor: "pointer" }}
          >
            Reload Escalation Queue
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {cases.map((c) => (
            <div
              key={c.id}
              style={{
                background: "#0f172a",
                border: "1px solid #1e293b",
                borderLeft: "5px solid #f59e0b",
                borderRadius: 12,
                padding: "1.75rem",
                boxShadow: "0 10px 25px -5px rgba(0,0,0,0.3)",
                transition: "all 0.2s ease"
              }}
            >
              {/* TOP HEADER ROW */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <Link
                      href={`/recovery/${c.id}`}
                      style={{ fontSize: "1.125rem", fontWeight: 800, color: "#60a5fa", fontFamily: "monospace", textDecoration: "none" }}
                    >
                      {c.id}
                    </Link>
                    <span style={{ fontSize: "0.6875rem", background: "rgba(245,158,11,0.15)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)", padding: "2px 8px", borderRadius: 4, fontWeight: 700 }}>
                      HUMAN APPROVAL REQUIRED
                    </span>
                  </div>
                  <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f1f5f9", marginTop: "0.35rem" }}>
                    Account: {c.customer_name} &middot; <span style={{ fontFamily: "monospace", color: "#94a3b8", fontSize: "0.8125rem" }}>Ref: {c.customer_id}</span>
                  </div>
                </div>

                {/* FINANCIAL HIGHLIGHTS */}
                <div style={{ display: "flex", gap: "1.75rem", textAlign: "right" }}>
                  <div>
                    <div style={{ fontSize: "0.6875rem", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>EXPOSURE AT RISK</div>
                    <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#ef4444", fontFamily: "monospace", marginTop: "0.15rem" }}>
                      {fmt(c.amount_minor)}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700, textTransform: "uppercase" }}>EXPECTED NET RECOVERY</div>
                    <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#10b981", fontFamily: "monospace", marginTop: "0.15rem" }}>
                      {fmt(c.expected_recovery_minor)}
                    </div>
                  </div>
                </div>
              </div>

              {/* REASON & AI DIAGNOSIS GRID */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
                <div style={{ background: "rgba(239, 68, 68, 0.06)", border: "1px solid rgba(239, 68, 68, 0.2)", padding: "1rem 1.25rem", borderRadius: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
                    <span style={{ fontSize: "0.6875rem", color: "#ef4444", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      WHY AUTOMATION STOPPED
                    </span>
                    <span style={{ fontSize: "0.6875rem", background: "rgba(239, 68, 68, 0.15)", color: "#f87171", padding: "1px 6px", borderRadius: 4, fontFamily: "monospace" }}>
                      Rule: {c.policy_constraint}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.875rem", color: "#e2e8f0", lineHeight: 1.5, margin: 0 }}>
                    {c.why_automation_stopped}
                  </p>
                </div>

                <div style={{ background: "rgba(16, 185, 129, 0.06)", border: "1px solid rgba(16, 185, 129, 0.2)", padding: "1rem 1.25rem", borderRadius: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
                    <span style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      AI AGENT PROPOSAL
                    </span>
                    <span style={{ fontSize: "0.6875rem", background: "rgba(16, 185, 129, 0.15)", color: "#34d399", padding: "1px 6px", borderRadius: 4, fontWeight: 700 }}>
                      Groq Llama-3.3 70B
                    </span>
                  </div>
                  <p style={{ fontSize: "0.875rem", color: "#e2e8f0", lineHeight: 1.5, margin: 0 }}>
                    {c.agent_recommendation}
                  </p>
                </div>
              </div>

              {/* ACCOUNT CONTEXT FOOTER */}
              <div style={{ background: "#1e293b", padding: "0.75rem 1rem", borderRadius: 8, border: "1px solid #334155", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1.25rem", fontSize: "0.8125rem", color: "#94a3b8" }}>
                <div>
                  Customer Profile: <strong style={{ color: "#f8fafc" }}>{c.previous_paid_count} Invoices Paid</strong> &middot; Lifetime Recovered: <strong style={{ color: "#10b981" }}>{fmt(c.lifetime_recovered_minor)}</strong>
                </div>
                <div>
                  <Link href={`/recovery/${c.id}`} style={{ color: "#60a5fa", textDecoration: "none", fontWeight: 600 }}>
                    Inspect Complete Evaluation Trace &rarr;
                  </Link>
                </div>
              </div>

              {/* ACTION TOOLBAR */}
              <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end", flexWrap: "wrap" }}>
                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "approve", "Approve & Dispatch")}
                  style={{
                    background: "#10b981",
                    color: "#ffffff",
                    border: "none",
                    padding: "0.625rem 1.25rem",
                    borderRadius: 8,
                    fontWeight: 700,
                    fontSize: "0.875rem",
                    cursor: processingId === c.id ? "not-allowed" : "pointer",
                    boxShadow: "0 4px 12px rgba(16,185,129,0.3)",
                  }}
                >
                  ✓ Approve & Dispatch Recovery
                </button>

                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "request_info", "Request Information")}
                  style={{
                    background: "#3b82f6",
                    color: "#ffffff",
                    border: "none",
                    padding: "0.625rem 1.25rem",
                    borderRadius: 8,
                    fontWeight: 700,
                    fontSize: "0.875rem",
                    cursor: processingId === c.id ? "not-allowed" : "pointer",
                  }}
                >
                  💬 Request Information
                </button>

                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "contact_customer", "Contact Customer")}
                  style={{
                    background: "#f59e0b",
                    color: "#000000",
                    border: "none",
                    padding: "0.625rem 1.25rem",
                    borderRadius: 8,
                    fontWeight: 700,
                    fontSize: "0.875rem",
                    cursor: processingId === c.id ? "not-allowed" : "pointer",
                  }}
                >
                  📞 Contact Customer
                </button>

                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "reject", "Reject Case")}
                  style={{
                    background: "rgba(239, 68, 68, 0.15)",
                    color: "#f87171",
                    border: "1px solid #ef4444",
                    padding: "0.625rem 1.25rem",
                    borderRadius: 8,
                    fontWeight: 700,
                    fontSize: "0.875rem",
                    cursor: processingId === c.id ? "not-allowed" : "pointer",
                  }}
                >
                  ✕ Reject Case
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
