"use client";

import React, { useState } from "react";
import { api, SimulationResult } from "@/lib/api";

interface ScenarioDef {
  id: string;
  title: string;
  badge: string;
  description: string;
  payload: Record<string, unknown>;
}

const PRESET_SCENARIOS: ScenarioDef[] = [
  {
    id: "scen_1",
    title: "Scenario 1: Soft Auth Failure → Dynamic Pivot → Recovered",
    badge: "CLOSED-LOOP PIVOT",
    description: "Gateway authentication error. Retry payment fails; agent dynamically pivots to Payment Link.",
    payload: {
      amount_minor: 499900,
      currency: "INR",
      error_reason: "authentication_required",
      method: "card",
      customer_id: "cust_demo_pivot_101",
      customer_name: "Evaluation Customer #101",
      metadata: { failure_category: "authentication_required" },
    },
  },
  {
    id: "scen_2",
    title: "Scenario 2: Hard Card Decline → Multi-Step → Bounded Stop",
    badge: "BOUNDED STOP",
    description: "Expired card decline. Multi-step payment link attempt fails; agent stops automatically without budget waste.",
    payload: {
      amount_minor: 1250000,
      currency: "INR",
      error_reason: "expired_card",
      method: "card",
      customer_id: "cust_demo_hard_202",
      customer_name: "Evaluation Customer #202",
      metadata: { failure_category: "hard", attempt_count: 2 },
    },
  },
  {
    id: "scen_3",
    title: "Scenario 3: Disputed Invoice → Policy Engine Blocks → Human Escalation",
    badge: "POLICY SHIELD",
    description: "Customer filed invoice dispute. Agent proposes collection; Policy Engine blocks automated collection.",
    payload: {
      amount_minor: 850000,
      currency: "INR",
      error_reason: "disputed_invoice",
      method: "upi",
      customer_id: "cust_demo_dispute_303",
      customer_name: "Evaluation Customer #303",
      metadata: { disputed: true, failure_category: "soft" },
    },
  },
  {
    id: "scen_4",
    title: "Scenario 4: Fraud Flag → Automated Prohibited → Policy Stop",
    badge: "FRAUD GUARD",
    description: "Fraud risk flag active on account. Policy engine halts recovery with 0 retries and 0 policy violations.",
    payload: {
      amount_minor: 2500000,
      currency: "INR",
      error_reason: "fraud_detected",
      method: "card",
      customer_id: "cust_demo_fraud_404",
      customer_name: "Evaluation Customer #404",
      metadata: { fraud_flag: true, failure_category: "fraud" },
    },
  },
  {
    id: "scen_5",
    title: "Scenario 5: Hinglish Voice/Chat Recovery → Intent Extraction → Promise Active",
    badge: "HINGLISH VOICE/CHAT",
    description: "Customer responds in Hinglish: 'Haan kal tak payment clear kar dunga ₹15,000'. Intent extracted, promise recorded.",
    payload: {
      amount_minor: 1500000,
      currency: "INR",
      error_reason: "hinglish_promise_active",
      method: "upi",
      customer_id: "cust_hinglish_505",
      customer_name: "Evaluation Customer #505",
      metadata: { text: "Haan kal tak payment clear kar dunga ₹15,000" },
    },
  },
  {
    id: "scen_6",
    title: "Scenario 6: B2B Overdue Invoice → Promise-to-Pay Tracker → Grace Period",
    badge: "B2B PROMISE-TO-PAY",
    description: "₹2,50,000 B2B invoice overdue by 14 days. AP team promises wire transfer by Dec 31. Status updated to AWAITING_PAYMENT.",
    payload: {
      amount_minor: 25000000,
      currency: "INR",
      error_reason: "overdue_receivable",
      method: "wire",
      customer_id: "cust_corp_acme",
      customer_name: "Evaluation Customer #606",
      metadata: { invoice_number: "INV-2026-884", promise_date: "2026-12-31" },
    },
  },
  {
    id: "scen_7",
    title: "Scenario 7: Ambiguous Gateway Timeout → LLM Primary Reasoning",
    badge: "🤖 LLM REASONING",
    description: "3DS v2 challenge server timed out after 30000ms on secondary gateway node. Ambiguous error forces Groq LLM reasoning path.",
    payload: {
      amount_minor: 1850000,
      currency: "INR",
      error_reason: "unknown_gateway_timeout_3ds_challenge_failed",
      method: "card",
      customer_id: "cust_ambig_707",
      customer_name: "Evaluation Customer #707",
      metadata: {
        ambiguous: true,
        unstructured_error: "3DS v2 challenge server timed out after 30000ms on secondary gateway node #42",
      },
    },
  },
];

export default function ScenarioWalkthroughSection() {
  const [runningId, setRunningId] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, SimulationResult>>({});
  const [error, setError] = useState<string | null>(null);

  const handleRunScenario = async (scen: ScenarioDef) => {
    try {
      setRunningId(scen.id);
      setError(null);
      const res = await api.triggerDemo(scen.payload);
      setResults((prev) => ({ ...prev, [scen.id]: res }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run scenario");
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
            DETERMINISTIC JUDGING SCENARIOS
          </h3>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Execute end-to-end backend recovery flows to verify AI judgment, policy compliance, and closed-loop behavior
          </div>
        </div>
        <span style={{ fontSize: "0.6875rem", background: "#2563eb", color: "#fff", padding: "3px 8px", borderRadius: 4, fontWeight: 700 }}>
          REAL BACKEND SIMULATION
        </span>
      </div>

      {error && (
        <div style={{ color: "var(--danger)", fontSize: "0.8125rem", marginBottom: "1rem" }}>
          Error executing scenario: {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        {PRESET_SCENARIOS.map((scen) => {
          const res = results[scen.id];
          const isRunning = runningId === scen.id;

          return (
            <div
              key={scen.id}
              style={{
                padding: "1rem",
                borderRadius: 8,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {scen.title}
                  </div>
                  <span style={{ fontSize: "0.625rem", background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b", padding: "2px 6px", borderRadius: 4, fontWeight: 700 }}>
                    {scen.badge}
                  </span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: 12 }}>
                  {scen.description}
                </div>

                {res && (
                  <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, fontSize: "0.75rem", marginBottom: 12, border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span>Proposed Action: <strong className="font-mono">{res.proposed_action || "None"}</strong></span>
                      <span style={{ color: res.policy_allowed ? "#10b981" : "#ef4444", fontWeight: 700 }}>
                        Policy: {res.policy_allowed ? "ALLOWED" : "BLOCKED"}
                      </span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
                      <span>Status: <strong style={{ color: "var(--text-primary)" }}>{res.recovery_status || res.status}</strong></span>
                      <span>Verified: <strong style={{ color: "#10b981" }}>₹{((res.actual_recovery_value || 0) / 100).toFixed(2)}</strong></span>
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={() => handleRunScenario(scen)}
                disabled={isRunning}
                style={{
                  padding: "0.5rem 0.85rem",
                  borderRadius: 6,
                  background: isRunning ? "var(--bg-tertiary)" : "#2563eb",
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  border: "none",
                  cursor: isRunning ? "not-allowed" : "pointer",
                }}
              >
                {isRunning ? "Running Backend Orchestrator..." : "Trigger Backend Scenario →"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
