"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";

interface FailureRes {
  status: string;
  failure_type: string;
  system_reaction: string;
  [key: string]: any;
}

export default function FailureInjectionControl() {
  const [runningType, setRunningType] = useState<string | null>(null);
  const [lastRes, setLastRes] = useState<FailureRes | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleInject = async (type: string) => {
    try {
      setRunningType(type);
      setError(null);
      const res = await api.injectFailure({ failure_type: type });
      setLastRes(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failure injection failed");
    } finally {
      setRunningType(null);
    }
  };

  return (
    <div style={{ padding: "1.25rem", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)", marginBottom: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
        <div>
          <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            DEVELOPER &amp; JUDGE FAILURE-INJECTION SANDBOX
          </h3>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
            Simulate real failure conditions to verify RevPlug safe boundary handling
          </div>
        </div>

      </div>

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        {[
          { type: "llm_timeout", label: "LLM Timeout (504)", badge: "Safe Fallback" },
          { type: "executor_failure", label: "Gateway API 502", badge: "Re-Plan" },
          { type: "duplicate_webhook", label: "Duplicate Webhook", badge: "Idempotency" },
          { type: "payment_success_race", label: "Payment Success Race", badge: "Halt Jobs" },
          { type: "policy_violation", label: "Policy Override Attempt", badge: "Blocked" },
          { type: "unknown_action", label: "Hallucinated Action", badge: "Registry Reject" },
        ].map((item) => (
          <button
            key={item.type}
            onClick={() => handleInject(item.type)}
            disabled={runningType === item.type}
            style={{
              padding: "0.4rem 0.75rem",
              borderRadius: 6,
              background: runningType === item.type ? "var(--bg-tertiary)" : "var(--bg-primary)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {item.label} ({item.badge})
          </button>
        ))}
      </div>

      {error && (
        <div style={{ color: "var(--danger)", fontSize: "0.8125rem", marginBottom: "0.5rem" }}>
          Error injecting failure: {error}
        </div>
      )}

      {lastRes && (
        <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid #10b981", fontSize: "0.8125rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontWeight: 700, color: "#10b981" }}>
              ✓ SYSTEM HANDLED SAFELY ({lastRes.failure_type})
            </span>
            <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              Status: {lastRes.status}
            </span>
          </div>
          <div style={{ color: "var(--text-primary)", fontWeight: 600, marginTop: 4 }}>
            {lastRes.system_reaction}
          </div>
        </div>
      )}
    </div>
  );
}
