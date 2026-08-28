"use client";

import { useEffect, useState, useCallback } from "react";
import { api, RecoveryItem } from "@/lib/api";

export default function ReviewsPage() {
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [action, setAction] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try { setItems(await api.pendingReviews()); } catch { } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleApprove(id: string) {
    try {
      const result = await api.approve(id, action[id] || "stop_recovery");
      setToast({ type: result.status === "approved" ? "success" : "error", message: result.message });
      load();
    } catch { setToast({ type: "error", message: "Action failed" }); }
  }

  async function handleReject(id: string) {
    try {
      const result = await api.reject(id);
      setToast({ type: "success", message: result.message });
      load();
    } catch { setToast({ type: "error", message: "Action failed" }); }
  }

  if (toast) {
    setTimeout(() => setToast(null), 4000);
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 1000, margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>Human Review</h1>
      <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "1.5rem" }}>Escalated cases requiring approval</p>

      {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}

      {loading ? <div className="skeleton" style={{ height: 200 }} /> : items.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>No pending reviews</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {items.map((item) => (
            <div key={item.id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{item.id}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{item.root_cause} • ₹{(item.amount_minor / 100).toLocaleString("en-IN")}</div>
                </div>
                <span className={`status-badge status-${item.status}`}>{item.status}</span>
              </div>
              <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "0.75rem", fontSize: "0.75rem" }}>
                <span>AI: <strong style={{ color: "var(--purple)" }}>{item.metadata?.proposed_action as string || "N/A"}</strong></span>
                <span>Policy: <strong>{item.metadata?.policy_allowed !== undefined ? (item.metadata.policy_allowed ? "Allowed" : "Denied") : "N/A"}</strong></span>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select value={action[item.id] || "stop_recovery"} onChange={(e) => setAction({ ...action, [item.id]: e.target.value })}
                  style={{ padding: "0.4rem 0.75rem", background: "var(--bg-tertiary)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text-primary)", fontSize: "0.75rem" }}>
                  <option value="stop_recovery">Stop Recovery</option>
                  <option value="escalate_human">Escalate Human</option>
                  <option value="send_payment_link">Send Payment Link</option>
                </select>
                <button onClick={() => handleApprove(item.id)} className="btn-primary">Approve</button>
                <button onClick={() => handleReject(item.id)} className="btn-secondary" style={{ borderColor: "var(--danger)", color: "var(--danger)" }}>Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card" style={{ marginTop: "1.5rem", background: "var(--warning-subtle)", borderColor: "rgba(245, 158, 11, 0.2)" }}>
        <p style={{ fontSize: "0.75rem", color: "var(--warning)" }}>
          ⚠️ Human approval cannot bypass safety policy. All approved actions are re-checked by the PolicyEngine.
        </p>
      </div>
    </div>
  );
}
