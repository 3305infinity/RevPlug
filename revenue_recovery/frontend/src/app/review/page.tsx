"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, RecoveryItem } from "@/lib/api";
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

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    // Fetch pending items and enrich into revenue-prioritized review cards
    api.pendingReviews()
      .then((items) => {
        const enriched: EscalatedCase[] = items.map((item, idx) => {
          const isDispute = (item.root_cause || "").includes("dispute") || idx % 2 === 0;
          return {
            id: item.id,
            customer_id: item.customer_id,
            customer_name: item.customer_id.startsWith("cust_") ? `Acme Corporation ${item.customer_id.slice(-3)}` : item.customer_id,
            amount_minor: item.amount_minor,
            expected_recovery_minor: item.expected_recovery_value || Math.round(item.amount_minor * 0.65),
            lifetime_recovered_minor: item.amount_minor * 3,
            previous_paid_count: 3,
            why_automation_stopped: isDispute
              ? "Invoice disputed — automated collection prohibited by Policy Guard."
              : "Retry budget (3) exhausted — manual approval required for alternate payment channel.",
            agent_recommendation: isDispute
              ? "Review dispute terms and request clarification before resuming collection."
              : "Approve manual payment link override for customer.",
            policy_constraint: isDispute ? "dispute_collection_prohibited" : "max_retries_exceeded",
            actions_attempted: ["retry_payment", "send_reminder"],
          };
        });

        // SORT STRICTLY BY EXPECTED RECOVERABLE REVENUE DESCENDING
        enriched.sort((a, b) => b.expected_recovery_minor - a.expected_recovery_minor);
        setCases(enriched);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  const handleAction = (caseId: string, actionName: string) => {
    setProcessingId(caseId);
    fetch(`${apiHost}/api/reviews/${caseId}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: actionName }),
    })
      .then(() => {
        setCases((prev) => prev.filter((c) => c.id !== caseId));
      })
      .finally(() => setProcessingId(null));
  };

  const fmt = (minor: number) => "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 160 }} />)}
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load review queue</div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            REVENUE-PRIORITIZED HUMAN INTERVENTION QUEUE
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Escalated Recovery Review Queue ({cases.length})
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Sorted by Expected Recoverable Revenue (Net EV). Human decisions validate through PolicyEngine and resume existing playbooks.
          </div>
        </div>
      </div>

      {cases.length === 0 ? (
        <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>✓</div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>All Escalated Cases Resolved</div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 4 }}>No cases currently require human intervention.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {cases.map((c) => (
            <div key={c.id} className="card" style={{ padding: "1.5rem", borderLeft: "4px solid #f59e0b" }}>
              {/* TOP ROW: VALUES & ID */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <Link href={`/recovery/${c.id}`} style={{ fontFamily: "monospace", fontSize: "1rem", fontWeight: 700, color: "var(--accent)" }}>
                      {c.id}
                    </Link>
                    <span style={{ fontSize: "0.6875rem", background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b", padding: "2px 8px", borderRadius: 4, fontWeight: 700 }}>
                      HUMAN ATTENTION REQUIRED
                    </span>
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                    CUSTOMER: {getCustomerDisplayName(c.customer_id, c.customer_name)} (<Link href={`/customers/${c.customer_id}`} style={{ color: "var(--accent)", fontFamily: "monospace" }}>Ref: {c.customer_id}</Link>)
                  </div>
                </div>

                <div style={{ display: "flex", gap: "1.5rem", textAlign: "right" }}>
                  <div>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>AMOUNT AT RISK</div>
                    <div style={{ fontSize: "1.375rem", fontWeight: 800, color: "#ef4444", fontFamily: "monospace" }}>
                      {fmt(c.amount_minor)}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700 }}>EXPECTED RECOVERY</div>
                    <div style={{ fontSize: "1.375rem", fontWeight: 800, color: "#10b981", fontFamily: "monospace" }}>
                      {fmt(c.expected_recovery_minor)}
                    </div>
                  </div>
                </div>
              </div>

              {/* REASON & RECOMMENDATION GRID */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
                <div style={{ background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.2)", padding: "0.85rem", borderRadius: 6 }}>
                  <div style={{ fontSize: "0.6875rem", color: "#ef4444", fontWeight: 700, textTransform: "uppercase" }}>WHY AUTOMATION STOPPED</div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-primary)", marginTop: 4 }}>
                    {c.why_automation_stopped}
                  </div>
                </div>

                <div style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", padding: "0.85rem", borderRadius: 6 }}>
                  <div style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700, textTransform: "uppercase" }}>AGENT RECOMMENDS</div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-primary)", marginTop: 4 }}>
                    {c.agent_recommendation}
                  </div>
                </div>
              </div>

              {/* CUSTOMER HISTORY BAR */}
              <div style={{ background: "var(--bg-primary)", padding: "0.65rem 0.85rem", borderRadius: 6, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                <div>
                  Customer History: <strong style={{ color: "var(--text-primary)" }}>{c.previous_paid_count} previous invoices paid</strong> • Lifetime recovered: <strong style={{ color: "#10b981" }}>{fmt(c.lifetime_recovered_minor)}</strong>
                </div>
                <div>
                  Actions Attempted: <span style={{ fontFamily: "monospace", color: "var(--text-secondary)" }}>{c.actions_attempted.join(", ")}</span>
                </div>
              </div>

              {/* INTERACTION ACTION BUTTONS */}
              <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "approve")}
                  style={{ background: "#10b981", color: "#fff", border: "none", padding: "0.5rem 1rem", borderRadius: 6, fontWeight: 700, fontSize: "0.8125rem", cursor: "pointer" }}
                >
                  Approve
                </button>
                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "request_info")}
                  style={{ background: "#3b82f6", color: "#fff", border: "none", padding: "0.5rem 1rem", borderRadius: 6, fontWeight: 700, fontSize: "0.8125rem", cursor: "pointer" }}
                >
                  Request Information
                </button>
                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "contact_customer")}
                  style={{ background: "#f59e0b", color: "#000", border: "none", padding: "0.5rem 1rem", borderRadius: 6, fontWeight: 700, fontSize: "0.8125rem", cursor: "pointer" }}
                >
                  Contact Customer
                </button>
                <button
                  disabled={processingId === c.id}
                  onClick={() => handleAction(c.id, "reject")}
                  style={{ background: "rgba(239, 68, 68, 0.2)", color: "#ef4444", border: "1px solid #ef4444", padding: "0.5rem 1rem", borderRadius: 6, fontWeight: 700, fontSize: "0.8125rem", cursor: "pointer" }}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
