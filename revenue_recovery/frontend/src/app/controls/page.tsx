"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type ControlItem = {
  name: string;
  value: string;
  description: string;
  status: "enabled" | "disabled" | "configured";
};

export default function ControlsPage() {
  const [controls, setControls] = useState<ControlItem[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [resetStatus, setResetStatus] = useState<"idle" | "resetting">("idle");
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleReset = async () => {
    if (!confirm("Are you sure you want to reset demo data? This will clear all generated synthetic cases.")) {
      return;
    }
    setResetStatus("resetting");
    setToast(null);
    try {
      await api.resetDemoData();
      setToast({ type: "success", message: "Demo data reset successfully." });
      setTimeout(() => window.location.reload(), 1000);
    } catch {
      setToast({ type: "error", message: "Failed to reset demo data." });
      setResetStatus("idle");
    }
  };

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/controls`)
      .then((r) => r.ok ? r.json() : Promise.reject(new Error("Failed")))
      .then((data: Record<string, string>) => {
        const items: ControlItem[] = [
          { name: "Maximum Payment Retries", value: data.max_payment_retries || "3", description: "Automated retry attempts per recovery case", status: "configured" },
          { name: "Customer Opt-Out", value: data.customer_opt_out || "Enabled", description: "Honors customer preference to stop communications", status: (data.customer_opt_out || "Enabled") === "Enabled" ? "enabled" : "disabled" },
          { name: "Fraud Retry Protection", value: data.fraud_retry_protection || "Enabled", description: "Blocks automated retries for fraud-classified failures", status: "enabled" },
          { name: "Recovery Deadline", value: data.recovery_deadline || "24h", description: "Maximum time before automated recovery stops", status: "configured" },
          { name: "Promise Expiry Protection", value: data.promise_expiry_protection || "Enabled", description: "Stops recovery when promise-to-pay expires", status: "enabled" },
          { name: "Policy Enforcement", value: data.policy_enforcement || "Mandatory", description: "All interventions must pass deterministic policy checks", status: "enabled" },
          { name: "Human Override", value: data.human_override || "Disabled", description: "Whether human approval can bypass safety policy", status: (data.human_override || "Disabled") === "Enabled" ? "enabled" : "disabled" },
        ];
        setControls(items);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1050, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 48, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 60 }} />)}
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load controls</div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>Cannot connect to backend API.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1050, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            RevPlug Policy Guard
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>Deterministic Safety Controls</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
            Server-side non-bypassable policy rules enforced across all AI proposed recovery actions.
          </p>
        </div>

        <button
          onClick={handleReset}
          disabled={resetStatus === "resetting"}
          className="btn-secondary"
          style={{ fontSize: "0.75rem", color: "var(--danger)" }}
        >
          {resetStatus === "resetting" ? "Resetting..." : "Reset Demo Data"}
        </button>
      </div>

      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}

      {/* CONTROLS LIST */}
      <div className="card">
        <table className="ops-table">
          <thead>
            <tr>
              <th>CONTROL RULE</th>
              <th>DESCRIPTION</th>
              <th>CONFIGURED VALUE</th>
              <th>ENFORCEMENT STATUS</th>
            </tr>
          </thead>
          <tbody>
            {controls.map((ctrl, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600 }}>{ctrl.name}</td>
                <td style={{ color: "var(--text-secondary)" }}>{ctrl.description}</td>
                <td className="font-mono" style={{ fontWeight: 600 }}>{ctrl.value}</td>
                <td>
                  <span className={`status-badge status-${ctrl.status === "enabled" ? "recovered" : ctrl.status === "disabled" ? "stopped" : "detected"}`}>
                    {ctrl.status.toUpperCase()}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
