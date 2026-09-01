"use client";

import { useEffect, useState } from "react";

interface PolicyConfigData {
  version: string;
  max_retries: number;
  max_contacts_per_24h: number;
  min_expected_net_ev_minor: number;
  max_intervention_cost_minor: number;
  cooldown_retry_minutes: number;
  allowed_channels: string[];
  allowed_payment_methods: string[];
  escalation_thresholds_minor: number;
  failure_categories_blocked: string[];
  systemic_suppression_threshold_pct: number;
  updated_at: string;
  updated_by: string;
  preview_summary: {
    max_retries: number;
    max_contacts: string;
    min_net_ev: string;
    hard_decline: string;
    fraud_recovery: string;
    dispute_collection: string;
  };
}

export default function PolicyConfigPage() {
  const [config, setConfig] = useState<PolicyConfigData | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const loadConfig = () => {
    fetch(`${apiHost}/api/policy-config`)
      .then((r) => r.json())
      .then((data) => {
        setConfig(data);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setSaving(true);
    fetch(`${apiHost}/api/policy-config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        max_retries: config.max_retries,
        max_contacts_per_24h: config.max_contacts_per_24h,
        min_expected_net_ev_minor: config.min_expected_net_ev_minor,
        max_intervention_cost_minor: config.max_intervention_cost_minor,
        cooldown_retry_minutes: config.cooldown_retry_minutes,
        systemic_suppression_threshold_pct: config.systemic_suppression_threshold_pct,
      }),
    })
      .then((r) => r.json())
      .then((updated) => {
        setConfig(updated);
        setSaveSuccess(`Policy version ${updated.version} published successfully!`);
        setTimeout(() => setSaveSuccess(null), 4000);
      })
      .finally(() => setSaving(false));
  };

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div className="skeleton" style={{ height: 400 }} />
      </div>
    );
  }

  if (status === "error" || !config) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load policy configuration</div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            BUSINESS OPERATOR POLICY GOVERNANCE
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Recovery Policy Configuration
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Deterministic Policy Engine Rules. Versioned on every change. AI agents cannot bypass or alter policy rules.
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <span style={{ fontSize: "0.75rem", background: "rgba(59, 130, 246, 0.2)", color: "#60a5fa", border: "1px solid #3b82f6", padding: "4px 10px", borderRadius: 6, fontWeight: 700 }}>
            CURRENT POLICY VERSION: {config.version}
          </span>
        </div>
      </div>

      {saveSuccess && (
        <div style={{ background: "rgba(16, 185, 129, 0.15)", border: "1px solid #10b981", color: "#10b981", padding: "0.85rem 1rem", borderRadius: 8, marginBottom: "1.5rem", fontSize: "0.875rem", fontWeight: 700 }}>
          ✓ {saveSuccess}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem" }}>
        {/* FORM CONFIGURATION */}
        <form onSubmit={handleSave} className="card" style={{ padding: "1.5rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1.25rem", color: "var(--text-primary)" }}>
            POLICY CONSTRAINTS
          </h2>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                MAXIMUM RETRY ATTEMPTS
              </label>
              <input
                type="number"
                value={config.max_retries}
                onChange={(e) => setConfig({ ...config, max_retries: parseInt(e.target.value) || 0 })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontFamily: "monospace" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                MAX CUSTOMER CONTACTS / 24H
              </label>
              <input
                type="number"
                value={config.max_contacts_per_24h}
                onChange={(e) => setConfig({ ...config, max_contacts_per_24h: parseInt(e.target.value) || 0 })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontFamily: "monospace" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                MINIMUM EXPECTED NET EV (PAISE)
              </label>
              <input
                type="number"
                value={config.min_expected_net_ev_minor}
                onChange={(e) => setConfig({ ...config, min_expected_net_ev_minor: parseInt(e.target.value) || 0 })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontFamily: "monospace" }}
              />
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>₹{config.min_expected_net_ev_minor / 100} min threshold</span>
            </div>

            <div>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                COOLDOWN RETRY (MINUTES)
              </label>
              <input
                type="number"
                value={config.cooldown_retry_minutes}
                onChange={(e) => setConfig({ ...config, cooldown_retry_minutes: parseInt(e.target.value) || 0 })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontFamily: "monospace" }}
              />
            </div>
          </div>

          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
              SYSTEMIC INCIDENT SUPPRESSION THRESHOLD (%)
            </label>
            <input
              type="number"
              value={config.systemic_suppression_threshold_pct}
              onChange={(e) => setConfig({ ...config, systemic_suppression_threshold_pct: parseFloat(e.target.value) || 0 })}
              style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontFamily: "monospace" }}
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            style={{ background: "#3b82f6", color: "#fff", border: "none", padding: "0.65rem 1.25rem", borderRadius: 6, fontWeight: 700, fontSize: "0.875rem", cursor: "pointer" }}
          >
            {saving ? "Publishing New Version..." : `Publish & Version Policy (${config.version})`}
          </button>
        </form>

        {/* LIVE POLICY PREVIEW CARD */}
        <div className="card" style={{ padding: "1.5rem", borderLeft: "3px solid #3b82f6" }}>
          <div style={{ fontSize: "0.6875rem", color: "#3b82f6", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            LIVE POLICY PREVIEW
          </div>

          <h3 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "1rem", color: "var(--text-primary)" }}>
            CURRENT POLICY ({config.version})
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.8125rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: 4 }}>
              <span style={{ color: "var(--text-muted)" }}>Max retries:</span>
              <strong style={{ fontFamily: "monospace" }}>{config.preview_summary?.max_retries ?? config.max_retries ?? 2}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: 4 }}>
              <span style={{ color: "var(--text-muted)" }}>Max contacts / 24h:</span>
              <strong style={{ fontFamily: "monospace" }}>{config.preview_summary?.max_contacts ?? `${config.max_contacts_per_24h ?? 2}/24h`}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: 4 }}>
              <span style={{ color: "var(--text-muted)" }}>Minimum net EV:</span>
              <strong style={{ fontFamily: "monospace", color: "#10b981" }}>{config.preview_summary?.min_net_ev ?? `₹${(config.min_expected_net_ev_minor ?? 10000) / 100}`}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: 4 }}>
              <span style={{ color: "var(--text-muted)" }}>Hard decline retry:</span>
              <strong style={{ color: "#ef4444" }}>{config.preview_summary?.hard_decline ?? "BLOCKED"}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: 4 }}>
              <span style={{ color: "var(--text-muted)" }}>Fraud recovery:</span>
              <strong style={{ color: "#ef4444" }}>{config.preview_summary?.fraud_recovery ?? "BLOCKED"}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: 4 }}>
              <span style={{ color: "var(--text-muted)" }}>Dispute collection:</span>
              <strong style={{ color: "#f59e0b" }}>{config.preview_summary?.dispute_collection ?? "HUMAN ONLY"}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
