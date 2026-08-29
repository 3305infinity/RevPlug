"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type ControlItem = {
  name: string;
  value: string;
  description: string;
  status: "enabled" | "disabled" | "configured";
};

const CONTROLS_KEY = "recovery_controls";

export default function ControlsPage() {
  const [controls, setControls] = useState<ControlItem[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [resetStatus, setResetStatus] = useState<"idle" | "resetting">("idle");
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleReset = async () => {
    if (!confirm("Are you sure you want to reset demo data? This will clear all generated synthetic cases and cannot be undone.")) {
      return;
    }
    setResetStatus("resetting");
    setToast(null);
    try {
      await api.resetDemoData();
      setToast({ type: "success", message: "Demo data reset successfully." });
      // reload after 1 sec
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
          {
            name: "Maximum Payment Retries",
            value: data.max_payment_retries || "3",
            description: "Automated retry attempts per recovery case",
            status: "configured",
          },
          {
            name: "Customer Opt-Out",
            value: data.customer_opt_out || "Enabled",
            description: "Honors customer preference to stop communications",
            status: (data.customer_opt_out || "Enabled") === "Enabled" ? "enabled" : "disabled",
          },
          {
            name: "Fraud Retry Protection",
            value: data.fraud_retry_protection || "Enabled",
            description: "Blocks automated retries for fraud-classified failures",
            status: "enabled",
          },
          {
            name: "Recovery Deadline",
            value: data.recovery_deadline || "24h",
            description: "Maximum time before automated recovery stops",
            status: "configured",
          },
          {
            name: "Promise Expiry Protection",
            value: data.promise_expiry_protection || "Enabled",
            description: "Stops recovery when promise-to-pay expires",
            status: "enabled",
          },
          {
            name: "Policy Enforcement",
            value: data.policy_enforcement || "Mandatory",
            description: "All interventions must pass deterministic policy checks",
            status: "enabled",
          },
          {
            name: "Human Override",
            value: data.human_override || "Disabled",
            description: "Whether human approval can bypass safety policy",
            status: (data.human_override || "Disabled") === "Enabled" ? "enabled" : "disabled",
          },
        ];
        setControls(items);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  const statusColor = (s: ControlItem["status"]) => {
    if (s === "enabled") return "var(--success)";
    if (s === "disabled") return "var(--danger)";
    return "var(--accent)";
  };

  const statusBg = (s: ControlItem["status"]) => {
    if (s === "enabled") return "rgba(16,185,129,0.1)";
    if (s === "disabled") return "rgba(239,68,68,0.1)";
    return "rgba(99,102,241,0.1)";
  };

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load controls</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>Cannot connect to API.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>Safety Controls</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
          Active recovery controls enforced by RecoverOS
        </p>
      </div>

      <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.25rem", background: "var(--warning-subtle)", border: "1px solid rgba(245,158,11,0.15)" }}>
        <div style={{ fontSize: "0.8125rem", color: "var(--warning)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          These controls are enforced deterministically. Human approval cannot override safety policy.
        </div>
      </div>

      <div style={{ display: "grid", gap: "0.75rem" }}>
        {controls.map((ctrl) => (
          <div key={ctrl.name} className="card" style={{ padding: "1.25rem 1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
                  {ctrl.name}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                  {ctrl.description}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexShrink: 0 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, fontFamily: "monospace", color: "var(--text-primary)" }}>
                  {ctrl.value}
                </span>
                <span style={{
                  fontSize: "0.6875rem",
                  fontWeight: 600,
                  padding: "0.25rem 0.625rem",
                  borderRadius: 4,
                  background: statusBg(ctrl.status),
                  color: statusColor(ctrl.status),
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}>
                  {ctrl.status}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {toast && (
        <div style={{
          marginTop: "1.5rem",
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

      <div className="card" style={{ padding: "1.5rem", marginTop: "2rem", border: "1px solid rgba(239,68,68,0.2)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--danger)", marginBottom: "0.5rem" }}>Danger Zone</h3>
        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
          Reset all synthetic demo data. This will clear generated items, promises, and audit logs.
        </p>
        <button
          onClick={handleReset}
          disabled={resetStatus === "resetting"}
          className="btn-secondary"
          style={{
            borderColor: "var(--danger)",
            color: "var(--danger)",
            background: "var(--danger-subtle)",
          }}
        >
          {resetStatus === "resetting" ? "Resetting..." : "Reset Demo Data"}
        </button>
      </div>
    </div>
  );
}
