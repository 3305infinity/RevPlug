"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function ReviewQueue() {
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [approvedIds, setApprovedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const data = await api.pendingReviews();
      setItems(data);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleApprove(id: string) {
    if (approvedIds.has(id)) return;
    setProcessingId(id);
    setToast(null);
    try {
      const result = await api.approve(id, "retry_payment");
      if (result.status === "denied_by_policy") {
        setToast({
          type: "error",
          message: `Approval blocked: ${result.message}. Human approval cannot override mandatory safety controls.`,
        });
      } else {
        setToast({ type: "success", message: result.message });
        setApprovedIds((prev) => new Set(prev).add(id));
      }
      await load();
    } catch {
      setToast({ type: "error", message: "Action failed. Please try again." });
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReject(id: string) {
    setProcessingId(id);
    setToast(null);
    try {
      const result = await api.reject(id);
      setToast({ type: "success", message: result.message });
      await load();
    } catch {
      setToast({ type: "error", message: "Action failed. Please try again." });
    } finally {
      setProcessingId(null);
    }
  }

  const fmt = (n: number) => "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>Review Queue</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Cases awaiting human review before any recovery action can proceed.
        </p>
      </div>

      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem", background: "var(--warning-subtle)", border: "1px solid rgba(245,158,11,0.15)" }}>
        <div style={{ fontSize: "0.8125rem", color: "var(--warning)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          Human approval cannot override mandatory safety policy. Blocked actions remain blocked.
        </div>
      </div>

      {toast && (
        <div style={{
          marginBottom: "1rem",
          padding: "0.875rem 1.25rem",
          borderRadius: 8,
          fontSize: "0.8125rem",
          fontWeight: 500,
          background: toast.type === "success" ? "var(--success-subtle)" : "var(--danger-subtle)",
          color: toast.type === "success" ? "var(--success)" : "var(--danger)",
          border: `1px solid ${toast.type === "success" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
        }}>
          {toast.message}
        </div>
      )}

      {status === "error" ? (
        <div style={{ textAlign: "center", padding: "3rem" }}>
          <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>{error}</p>
          <button onClick={load} className="btn-primary">Retry</button>
        </div>
      ) : status === "loading" ? (
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 180 }} />)}
        </div>
      ) : items.length === 0 ? (
        <div className="card" style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ fontSize: "0.9375rem", fontWeight: 500, marginBottom: "0.25rem" }}>All caught up</p>
          <p style={{ fontSize: "0.8125rem" }}>No pending reviews right now.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          {items.map((item) => {
            const isProcessing = processingId === item.id;
            const proposedAction = (item.metadata?.proposed_action as string | undefined) || "retry_payment";
            const policyRule = item.stopped_reason || (item.metadata?.policy_rule as string | undefined) || "Policy denied";
            const isBlocked = item.status === "stopped" || item.status === "escalated";
            const isApproved = approvedIds.has(item.id);

            return (
              <div key={item.id} className="card" style={{ padding: "1.5rem", opacity: isApproved ? 0.6 : 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem", flexWrap: "wrap" }}>
                      <Link href={`/recovery/${item.id}`} style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "monospace", color: "var(--accent)", textDecoration: "none" }}>
                        {item.id}
                      </Link>
                      <span className={`status-badge status-${item.status}`}>{item.status.replace(/_/g, " ")}</span>
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                      <span>{item.customer_id || "Unknown"}</span>
                      <span style={{ opacity: 0.4 }}>|</span>
                      <span>{item.root_cause || "unknown"}</span>
                      <span style={{ opacity: 0.4 }}>|</span>
                      <span style={{ fontFamily: "monospace" }}>{fmt(item.amount_minor)}</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
                  <div style={{ padding: "0.75rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8 }}>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                      AI Recommendation
                    </div>
                    <div style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--purple)", textTransform: "capitalize" }}>
                      {proposedAction.replace(/_/g, " ")}
                    </div>
                  </div>
                  <div style={{ padding: "0.75rem 1rem", background: isBlocked ? "var(--danger-subtle)" : "var(--bg-tertiary)", borderRadius: 8, border: isBlocked ? "1px solid rgba(239,68,68,0.15)" : undefined }}>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                      Policy Decision
                    </div>
                    <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: isBlocked ? "var(--danger)" : "var(--text-primary)", textTransform: "capitalize" }}>
                      {isBlocked ? "Blocked" : "Allowed"}
                    </div>
                    {isBlocked && (
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                        {policyRule.replace(/_/g, " ")}
                      </div>
                    )}
                  </div>
                </div>

                {item.expected_recovery_value && (
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Expected recovery:</span>{" "}
                    <span style={{ fontWeight: 600, color: "var(--purple)", fontFamily: "monospace" }}>{fmt(item.expected_recovery_value)}</span>
                  </div>
                )}

                <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                  {!isApproved && (
                    <>
                      <button
                        onClick={() => handleApprove(item.id)}
                        disabled={isProcessing}
                        className="btn-primary"
                        style={{ fontSize: "0.8125rem" }}
                      >
                        {isProcessing ? "Processing..." : "Approve Action"}
                      </button>
                      <button
                        onClick={() => handleReject(item.id)}
                        disabled={isProcessing}
                        className="btn-secondary"
                        style={{ fontSize: "0.8125rem", borderColor: "var(--danger)", color: "var(--danger)" }}
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {isApproved && (
                    <span style={{ fontSize: "0.8125rem", color: "var(--success)", fontWeight: 500 }}>✓ Approved</span>
                  )}
                  <Link href={`/recovery/${item.id}`} style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", textDecoration: "none", marginLeft: "auto" }}>
                    View Case →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
