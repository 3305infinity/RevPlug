"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function ReviewQueue() {
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [actionMap, setActionMap] = useState<Record<string, string>>({});
  const [processingId, setProcessingId] = useState<string | null>(null);

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
    const action = actionMap[id] || "stop_recovery";
    setProcessingId(id);
    setToast(null);
    try {
      const result = await api.approve(id, action);
      setToast({
        type: result.status === "approved" ? "success" : "error",
        message: result.message,
      });
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

  const fmt = (n: number) => `₹${(n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>Human Review</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
          Cases requiring manual approval before recovery action
        </p>
      </div>

      {toast && (
        <div className={`toast toast-${toast.type}`} style={{ marginBottom: "1rem" }}>
          {toast.message}
        </div>
      )}

      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem", background: "var(--warning-subtle)", border: "1px solid rgba(245,158,11,0.15)" }}>
        <div style={{ fontSize: "0.8125rem", color: "var(--warning)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          Human approval cannot bypass safety policy. All approved actions are re-checked by the PolicyEngine.
        </div>
      </div>

      {status === "error" ? (
        <div style={{ textAlign: "center", padding: "3rem" }}>
          <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>{error}</p>
          <button onClick={load} className="btn-primary">Retry</button>
        </div>
      ) : status === "loading" ? (
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 120 }} />)}
        </div>
      ) : items.length === 0 ? (
        <div className="card" style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "1rem", opacity: 0.6 }}>✅</div>
          <p style={{ fontSize: "0.9375rem", fontWeight: 500, marginBottom: "0.25rem" }}>All caught up</p>
          <p style={{ fontSize: "0.8125rem" }}>No pending reviews right now.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          {items.map((item) => {
            const isProcessing = processingId === item.id;
            const proposedAction = item.metadata?.proposed_action as string | undefined;
            return (
              <div key={item.id} className="card" style={{ padding: "1.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem" }}>
                      <Link href={`/recovery/${item.id}`} style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "monospace", color: "var(--accent)", textDecoration: "none" }}>
                        {item.id}
                      </Link>
                      <StatusBadge status={item.status} />
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                      <span>{item.root_cause || "unknown"}</span>
                      <span>·</span>
                      <span>{fmt(item.amount_minor)}</span>
                      <span>·</span>
                      <span>{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                {/* AI + Policy summary */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
                  <div style={{ padding: "0.75rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8 }}>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                      AI Recommendation
                    </div>
                    <div style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--purple)" }}>
                      {proposedAction?.replace(/_/g, " ") || "—"}
                    </div>
                  </div>
                  <div style={{ padding: "0.75rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8 }}>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>
                      Policy Status
                    </div>
                    <div style={{ fontSize: "0.8125rem", fontWeight: 500 }}>
                      {item.metadata?.policy_allowed !== undefined ? (
                        <span style={{ color: item.metadata.policy_allowed ? "var(--success)" : "var(--danger)" }}>
                          {item.metadata.policy_allowed ? "Allowed" : "Denied"}
                        </span>
                      ) : "—"}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
                  <select
                    value={actionMap[item.id] || "stop_recovery"}
                    onChange={(e) => setActionMap({ ...actionMap, [item.id]: e.target.value })}
                    disabled={isProcessing}
                    className="input"
                    style={{ fontSize: "0.8125rem", minWidth: 180 }}
                  >
                    <option value="stop_recovery">Stop Recovery</option>
                    <option value="escalate_human">Escalate Human</option>
                    <option value="send_payment_link">Send Payment Link</option>
                    <option value="send_customer_message">Send Message</option>
                  </select>
                  <button
                    onClick={() => handleApprove(item.id)}
                    disabled={isProcessing}
                    className="btn-primary"
                    style={{ fontSize: "0.8125rem" }}
                  >
                    {isProcessing ? "Processing..." : "Approve"}
                  </button>
                  <button
                    onClick={() => handleReject(item.id)}
                    disabled={isProcessing}
                    className="btn-secondary"
                    style={{ fontSize: "0.8125rem", borderColor: "var(--danger)", color: "var(--danger)" }}
                  >
                    Reject
                  </button>
                  <Link href={`/recovery/${item.id}`} className="btn-ghost" style={{ fontSize: "0.8125rem", marginLeft: "auto" }}>
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

function StatusBadge({ status }: { status: string }) {
  const cls = `status-badge status-${status}`;
  return <span className={cls}>{status.replace(/_/g, " ")}</span>;
}
