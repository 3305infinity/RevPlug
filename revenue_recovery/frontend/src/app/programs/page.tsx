"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

type Status = "loading" | "error" | "ready";

interface ProgramConfig {
  enabled: boolean;
  max_retry_attempts?: number;
  escalation_threshold?: number;
  min_amount_minor?: number;
  allowed_actions?: string[];
}

interface Program {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  status: "Active" | "Paused" | "Coming soon";
  config: { label: string; value: string }[];
  canConfigure: boolean;
  maxRetryAttempts: number;
  escalationThreshold: number;
}

const PROGRAM_META: Record<string, { name: string; description: string; canConfigure: boolean }> = {
  payment_failure: {
    name: "Payment Failure Recovery",
    description: "Automatically recover failed payments within safety constraints. Soft failures are retried, hard failures escalate, fraud is blocked.",
    canConfigure: true,
  },
  checkout_abandonment: {
    name: "Checkout Abandonment",
    description: "Re-engage users who abandoned checkout. Detect drop-off, send timed reminders, and track recovery outcomes.",
    canConfigure: false,
  },
  subscription_failure: {
    name: "Subscription Recovery",
    description: "Recover failed subscription renewals. Dunning campaigns, grace-period strategies, and retry sequencing.",
    canConfigure: false,
  },
  overdue_invoice: {
    name: "Overdue Invoice Recovery",
    description: "Automate B2B receivable follow-up. Payment link dispatch, escalation workflows, and settlement tracking.",
    canConfigure: false,
  },
};

export default function Programs() {
  const [status, setStatus] = useState<Status>("loading");
  const [programs, setPrograms] = useState<Program[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const config = await api.getProgramsConfig();
      const built = Object.entries(config).map(([id, cfg]) => buildProgram(id, cfg as unknown as ProgramConfig));
      setPrograms(built);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load programs");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleToggle(id: string, enabled: boolean) {
    setSaving(id);
    setToast(null);
    try {
      const updates = { [id]: { enabled } };
      await api.updateProgramsConfig(updates);
      setToast({ type: "success", message: `${PROGRAM_META[id]?.name || id} ${enabled ? "enabled" : "paused"}` });
      await load();
    } catch {
      setToast({ type: "error", message: "Failed to update program" });
    } finally {
      setSaving(null);
    }
  }

  async function handleSaveMaxRetries(id: string, value: number) {
    setSaving(id);
    setToast(null);
    try {
      await api.updateProgramsConfig({ [id]: { max_retry_attempts: value } });
      setToast({ type: "success", message: "Configuration saved" });
      await load();
    } catch {
      setToast({ type: "error", message: "Failed to save" });
    } finally {
      setSaving(null);
    }
  }

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load programs</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={load} className="btn-primary">Retry</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>Recovery Programs</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
          Configure and monitor recovery workflows. All programs respect PolicyEngine safety rules.
        </p>
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

      <div style={{ display: "grid", gap: "1.25rem" }}>
        {programs.map((program) => (
          <div key={program.id} className="card" style={{ overflow: "hidden" }}>
            <div style={{ padding: "1.5rem" }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.75rem" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem", flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, fontSize: "1rem" }}>{program.name}</span>
                    <span
                      className="status-badge"
                      style={{
                        background: program.status === "Active" ? "var(--success-subtle)" : program.status === "Paused" ? "var(--warning-subtle)" : "var(--bg-tertiary)",
                        color: program.status === "Active" ? "var(--success)" : program.status === "Paused" ? "var(--warning)" : "var(--text-muted)",
                      }}
                    >
                      {program.status}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", maxWidth: 600 }}>{program.description}</p>
                </div>
                {program.canConfigure && (
                  <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", flexShrink: 0 }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Enable</span>
                    <button
                      onClick={() => handleToggle(program.id, !program.enabled)}
                      disabled={saving === program.id}
                      style={{
                        width: 44,
                        height: 24,
                        borderRadius: 12,
                        border: "none",
                        cursor: "pointer",
                        position: "relative",
                        transition: "background 0.2s",
                        background: program.enabled ? "var(--success)" : "var(--bg-tertiary)",
                        padding: 0,
                      }}
                    >
                      <div style={{
                        width: 18,
                        height: 18,
                        borderRadius: "50%",
                        background: "#fff",
                        position: "absolute",
                        top: 3,
                        transition: "left 0.2s",
                        left: program.enabled ? 23 : 3,
                      }} />
                    </button>
                  </label>
                )}
              </div>

              {program.canConfigure && program.enabled && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", marginTop: "1rem" }}>
                  <ConfigItem
                    label="Max Retry Attempts"
                    value={String(program.maxRetryAttempts)}
                    onSave={(v) => handleSaveMaxRetries(program.id, v)}
                    saving={saving === program.id}
                  />
                  <ConfigItem label="Escalation Threshold" value={String(program.escalationThreshold)} readOnly />
                  <ConfigItem label="Min Amount" value={program.id === "payment_failure" ? "₹1" : "—"} readOnly />
                  <ConfigItem
                    label="Allowed Actions"
                    value={String(program.config.find((c) => c.label === "Allowed Actions")?.value || "6 actions")}
                    readOnly
                  />
                </div>
              )}

              {!program.canConfigure && (
                <div style={{ marginTop: "1rem", padding: "0.875rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  Not yet implemented — backend integration pending.
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: "1.5rem", padding: "1.25rem 1.5rem", background: "var(--accent-subtle)", border: "1px solid rgba(6,182,212,0.15)" }}>
        <div style={{ fontSize: "0.8125rem", color: "var(--accent)", lineHeight: 1.6 }}>
          <strong>PolicyEngine always has final authority.</strong> Even when a program is enabled, every proposed action is validated against the policy engine before execution. Unsafe actions are blocked regardless of program settings.
        </div>
      </div>
    </div>
  );
}

function ConfigItem({ label, value, readOnly, onSave, saving }: {
  label: string;
  value: string;
  readOnly?: boolean;
  onSave?: (value: number) => void;
  saving?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [numValue, setNumValue] = useState(Number(value) || 0);

  return (
    <div style={{ padding: "0.875rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8 }}>
      <div style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.35rem" }}>{label}</div>
      {readOnly || !onSave ? (
        <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>{value}</div>
      ) : editing ? (
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            type="number"
            value={numValue}
            onChange={(e) => setNumValue(Math.max(1, Number(e.target.value)))}
            className="input"
            style={{ width: 60, padding: "0.35rem 0.5rem", fontSize: "0.8125rem" }}
            min={1}
            max={10}
          />
          <button
            onClick={() => { onSave(numValue); setEditing(false); }}
            disabled={saving}
            className="btn-primary"
            style={{ padding: "0.35rem 0.6rem", fontSize: "0.6875rem" }}
          >
            Save
          </button>
          <button onClick={() => setEditing(false)} className="btn-ghost" style={{ padding: "0.35rem 0.5rem", fontSize: "0.6875rem" }}>
            Cancel
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>{value}</div>
          <button onClick={() => setEditing(true)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--accent)", fontSize: "0.6875rem", padding: 0 }}>
            Edit
          </button>
        </div>
      )}
    </div>
  );
}

function buildProgram(id: string, cfg: ProgramConfig): Program {
  const meta = PROGRAM_META[id] || { name: id, description: "", canConfigure: false };
  const isActive = cfg.enabled;
  return {
    id,
    name: meta.name,
    description: meta.description,
    enabled: isActive,
    status: isActive ? "Active" : (meta.canConfigure ? "Paused" : "Coming soon"),
    canConfigure: meta.canConfigure,
    config: [
      { label: "Max Retry Attempts", value: String(cfg.max_retry_attempts ?? "—") },
      { label: "Escalation Threshold", value: String(cfg.escalation_threshold ?? "—") },
      { label: "Min Amount", value: cfg.min_amount_minor ? `₹${cfg.min_amount_minor / 100}` : "—" },
      { label: "Allowed Actions", value: cfg.allowed_actions ? `${cfg.allowed_actions.length} actions` : "—" },
    ],
    maxRetryAttempts: cfg.max_retry_attempts ?? 3,
    escalationThreshold: cfg.escalation_threshold ?? 0.5,
  };
}
