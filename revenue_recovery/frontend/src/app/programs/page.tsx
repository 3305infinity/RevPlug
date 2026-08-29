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

const PROGRAM_META: Record<string, { name: string; description: string; workflow: string[] }> = {
  payment_failure: {
    name: "Payment Failure Recovery",
    description: "Automatically recovers failed payments within safety constraints. Soft failures are retried, hard failures escalate, fraud is blocked.",
    workflow: ["Detect", "Classify", "Score", "Recommend", "Guard", "Execute", "Verify"],
  },
};

export default function Programs() {
  const [status, setStatus] = useState<Status>("loading");
  const [programs, setPrograms] = useState<Record<string, ProgramConfig>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const config = await api.getProgramsConfig();
      const built: Record<string, ProgramConfig> = {};
      for (const [id, cfg] of Object.entries(config)) {
        const c = cfg as Record<string, unknown>;
        built[id] = {
          enabled: Boolean(c.enabled),
          max_retry_attempts: c.max_retry_attempts as number | undefined,
          escalation_threshold: c.escalation_threshold as number | undefined,
          min_amount_minor: c.min_amount_minor as number | undefined,
          allowed_actions: c.allowed_actions as string[] | undefined,
        };
      }
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

  const paymentFailure = programs.payment_failure;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>Recovery Programs</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Configure and monitor recovery workflows. All programs respect deterministic safety controls.
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

      {status === "loading" ? (
        <div style={{ display: "grid", gap: "1rem" }}>
          {[...Array(2)].map((_, i) => <div key={i} className="skeleton" style={{ height: 300 }} />)}
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1.25rem" }}>
          {Object.entries(PROGRAM_META).map(([id, meta]) => {
            const cfg = programs[id] || { enabled: false, max_retry_attempts: 3, escalation_threshold: 0.5 };
            const isActive = cfg.enabled;
            return (
              <div key={id} className="card" style={{ overflow: "hidden" }}>
                <div style={{ padding: "1.5rem" }}>
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem", flexWrap: "wrap" }}>
                        <span style={{ fontWeight: 600, fontSize: "1rem" }}>{meta.name}</span>
                        <span
                          className="status-badge"
                          style={{
                            background: isActive ? "var(--success-subtle)" : "var(--bg-tertiary)",
                            color: isActive ? "var(--success)" : "var(--text-muted)",
                          }}
                        >
                          {isActive ? "Active" : "Paused"}
                        </span>
                      </div>
                      <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", maxWidth: 600, lineHeight: 1.6 }}>{meta.description}</p>
                    </div>
                    <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", flexShrink: 0 }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Enable</span>
                      <button
                        onClick={() => handleToggle(id, !isActive)}
                        disabled={saving === id}
                        style={{
                          width: 44,
                          height: 24,
                          borderRadius: 12,
                          border: "none",
                          cursor: "pointer",
                          position: "relative",
                          transition: "background 0.2s",
                          background: isActive ? "var(--success)" : "var(--bg-tertiary)",
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
                          left: isActive ? 23 : 3,
                        }} />
                      </button>
                    </label>
                  </div>

                  {/* Workflow visualization */}
                  <div style={{ marginBottom: "1.25rem" }}>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
                      Recovery Workflow
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", flexWrap: "wrap" }}>
                      {meta.workflow.map((step, i) => (
                        <div key={step} style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                          <div style={{
                            padding: "0.35rem 0.65rem",
                            borderRadius: 6,
                            fontSize: "0.6875rem",
                            fontWeight: 600,
                            background: isActive ? "var(--accent-subtle)" : "var(--bg-tertiary)",
                            color: isActive ? "var(--accent)" : "var(--text-muted)",
                            textTransform: "uppercase",
                            letterSpacing: "0.04em",
                          }}>
                            {step}
                          </div>
                          {i < meta.workflow.length - 1 && (
                            <span style={{ color: "var(--text-muted)", fontSize: "0.625rem" }}>→</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Safety config */}
                  <div style={{ padding: "1rem 1.25rem", background: "var(--bg-tertiary)", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                        Safety Configuration
                      </div>
                      <div style={{ fontSize: "0.625rem", color: "var(--accent)" }}>
                        Managed by backend policy.
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
                      <div>
                        <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Max Retries</div>
                        <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", fontFamily: "monospace" }}>{cfg.max_retry_attempts ?? 3}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Escalation Threshold</div>
                        <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", fontFamily: "monospace" }}>{(cfg.escalation_threshold ?? 0.5).toFixed(2)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Min Amount</div>
                        <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", fontFamily: "monospace" }}>
                          {cfg.min_amount_minor ? `₹${(cfg.min_amount_minor / 100).toFixed(0)}` : "Any"}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Allowed Actions</div>
                        <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
                          {cfg.allowed_actions?.length ?? "—"}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="card" style={{ marginTop: "1.5rem", padding: "1.25rem 1.5rem", background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.7 }}>
          <strong style={{ color: "var(--text-primary)" }}>PolicyEngine always has final authority.</strong> Even when a program is enabled, every proposed action is validated against the policy engine before execution. Unsafe actions are blocked regardless of program settings.
        </div>
      </div>
    </div>
  );
}
