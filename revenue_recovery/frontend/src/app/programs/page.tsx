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

const PROGRAM_META: Record<string, { name: string; description: string; workflow: string[]; status: string }> = {
  payment_failure: {
    name: "Payment Failure Recovery",
    description: "Automatically recovers failed payments within safety constraints. Soft failures are retried, hard failures escalate, fraud is blocked.",
    workflow: ["Detect", "Classify", "Score", "Recommend", "Guard", "Execute", "Verify"],
    status: "ACTIVE",
  },
  checkout_abandonment: {
    name: "Checkout Abandonment Recovery",
    description: "Recovers abandoned shopping carts and checkout sessions with bounded payment links and reminder workflows.",
    workflow: ["Detect", "Stage Check", "Contactability", "Link Dispatch", "Conversion Verify"],
    status: "ACTIVE",
  },
  subscription_failure: {
    name: "Subscription Failure Recovery",
    description: "Handles recurring billing and token failures with automated retry sequencing and hosted payment links.",
    workflow: ["Ingest Cycle", "Token Check", "EV Scoring", "Smart Retry", "Settlement Confirm"],
    status: "ACTIVE",
  },
  overdue_receivable: {
    name: "Receivables Escalation Ladder",
    description: "Deterministic B2B receivables escalation ladder (Day 1 Gentle → Day 3 Link → Day 7 Alternate → Day 14 Human Escalation).",
    workflow: ["Overdue Calc", "Ladder Schedule", "Promise Check", "Dispatch", "Settlement Audit"],
    status: "ACTIVE",
  },
  mandate_failure: {
    name: "Mandate Failure Sequencer",
    description: "Manages direct debit and auto-pay mandate rejections with delayed retry scheduling and fallback payment links.",
    workflow: ["Mandate Check", "Eligibility Evaluation", "Delayed Retry", "Payment Link Fallback"],
    status: "ACTIVE",
  },
};

export default function Programs() {
  const [status, setStatus] = useState<Status>("loading");
  const [programs, setPrograms] = useState<Record<string, ProgramConfig>>({});
  const [error, setError] = useState<string | null>(null);

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
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>Recovery Programs</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Canonical revenue recovery control plane workflows. All 5 program surfaces respect deterministic safety bounds.
        </p>
      </div>

      <div style={{ display: "grid", gap: "1.25rem" }}>
        {Object.entries(PROGRAM_META).map(([key, meta]) => (
          <div key={key} className="card" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <h2 style={{ fontSize: "1.125rem", fontWeight: 700, color: "#fff" }}>{meta.name}</h2>
              <span style={{
                fontSize: "0.625rem",
                fontWeight: 700,
                fontFamily: "monospace",
                padding: "0.2rem 0.6rem",
                borderRadius: 4,
                background: "rgba(16, 185, 129, 0.1)",
                color: "var(--success)",
                border: "1px solid var(--success)",
              }}>
                {meta.status}
              </span>
            </div>
            <p style={{ fontSize: "0.84375rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
              {meta.description}
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>WORKFLOW:</span>
              {meta.workflow.map((w, idx) => (
                <span key={w} style={{ fontSize: "0.75rem", color: "var(--orange)", fontFamily: "monospace" }}>
                  {w} {idx < meta.workflow.length - 1 ? "→" : ""}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
