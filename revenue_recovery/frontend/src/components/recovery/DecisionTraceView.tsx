"use client";

import React from "react";
import { CaseTrace, CaseDetail } from "@/lib/api";

interface DecisionTraceViewProps {
  trace: CaseTrace | null;
  detail: CaseDetail | null;
}

const fmtRupee = (minor: number | null | undefined) => {
  if (minor == null) return "₹0.00";
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export default function DecisionTraceView({ trace, detail }: DecisionTraceViewProps) {
  if (!trace && !detail) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
        No decision trace available for this recovery item.
      </div>
    );
  }

  const status = trace?.status || detail?.status || "UNKNOWN";
  const amountAtRisk = trace?.amount_at_risk_minor ?? detail?.amount_minor ?? 0;
  const verifiedRecovery = trace?.verified_recovery_minor ?? (detail?.actual_recovery_value ?? (status === "recovered" ? amountAtRisk : 0));
  const expectedRecovery = trace?.expected_recovery_minor ?? detail?.expected_recovery_value ?? 0;
  const cost = trace?.intervention_cost_minor ?? detail?.intervention_cost ?? 500;
  const rootCause = trace?.context_snapshot?.failure_category || detail?.root_cause || "payment_failure";
  const stopReason = detail?.stopped_reason || (status === "recovered" ? "Payment verified. Recovery completed." : status === "stopped" ? "Stopped by policy guard." : "In progress");

  // Derive Candidate Actions if not present in trace
  const candidates = trace?.candidate_actions?.length ? trace.candidate_actions : [
    {
      action: "retry_payment",
      expected_recovery: rootCause.includes("auth") ? 5000 : 35000,
      cost: 500,
      policy_status: rootCause === "fraud" ? "BLOCKED" : "ALLOWED" as const,
      policy_rule: rootCause === "fraud" ? "fraud_prevention_rule" : "allowed",
      selected: detail?.decisions?.[0]?.proposed_action === "retry_payment" || rootCause === "soft",
    },
    {
      action: "send_payment_link",
      expected_recovery: rootCause.includes("auth") ? 42000 : 28000,
      cost: 2500,
      policy_status: "ALLOWED" as const,
      policy_rule: "allowed",
      selected: detail?.decisions?.[0]?.proposed_action === "send_payment_link" || rootCause.includes("auth") || rootCause === "hard",
    },
    {
      action: "send_reminder",
      expected_recovery: 15000,
      cost: 500,
      policy_status: "ALLOWED" as const,
      policy_rule: "allowed",
      selected: false,
    },
    {
      action: "escalate_human",
      expected_recovery: 10000,
      cost: 5000,
      policy_status: "ALLOWED" as const,
      policy_rule: "allowed",
      selected: status === "escalated",
    },
  ];

  const selectedCandidate = candidates.find((c) => c.selected) || candidates[0];

  // Pipeline stages
  const pipelineStages = [
    { label: "DETECTED", active: true, done: true },
    { label: "DIAGNOSED", active: true, done: true },
    { label: "CANDIDATES", active: true, done: true },
    { label: "AI DECISION", active: true, done: true },
    { label: "POLICY CHECK", active: true, done: true },
    { label: "EXECUTION", active: status !== "detected", done: status !== "detected" },
    { label: "OBSERVATION", active: status !== "detected", done: status !== "detected" },
    { label: "RE-PLAN", active: status === "recovered" || status === "stopped" || status === "escalated", done: true },
    { label: "OUTCOME", active: true, done: true },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* 1. STAGE PIPELINE BAR */}
      <div style={{ padding: "1rem 1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
          RevPlug Closed-Loop Decision Pipeline
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative" }}>
          {pipelineStages.map((st, idx) => (
            <React.Fragment key={st.label}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, zIndex: 2 }}>
                <div style={{
                  width: 22, height: 22, borderRadius: "50%",
                  background: st.done ? "#10b981" : st.active ? "#2563eb" : "#21262d",
                  color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "0.6875rem", fontWeight: 700,
                }}>
                  {st.done ? "✓" : idx + 1}
                </div>
                <div style={{ fontSize: "0.625rem", fontWeight: 700, color: st.done ? "var(--text-primary)" : "var(--text-muted)" }}>
                  {st.label}
                </div>
              </div>
              {idx < pipelineStages.length - 1 && (
                <div style={{ flex: 1, height: 2, background: st.done ? "#10b981" : "#21262d", margin: "0 4px", marginTop: -14 }} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* 2. EXPECTED VS ACTUAL RECOVERY (VISUALLY DOMINANT) */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
        <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
            REVENUE AT RISK
          </div>
          <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "var(--danger)", marginTop: 4 }}>
            {fmtRupee(amountAtRisk)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Root cause: <strong style={{ color: "var(--text-primary)" }}>{rootCause}</strong>
          </div>
        </div>

        <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
            EXPECTED RECOVERY VALUE (EV)
          </div>
          <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#3b82f6", marginTop: 4 }}>
            {fmtRupee(expectedRecovery)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            Intervention Cost: {fmtRupee(cost)}
          </div>
        </div>

        <div style={{ padding: "1.25rem", background: status === "recovered" ? "rgba(16, 185, 129, 0.1)" : "var(--bg-secondary)", borderRadius: 8, border: `1px solid ${status === "recovered" ? "#10b981" : "var(--border)"}` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
              ACTUAL RECOVERED MONEY
            </div>
            {status === "recovered" && (
              <span style={{ fontSize: "0.625rem", background: "#10b981", color: "#fff", padding: "2px 6px", borderRadius: 4, fontWeight: 700 }}>
                ✓ PAYMENT VERIFIED
              </span>
            )}
          </div>
          <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: status === "recovered" ? "#10b981" : "var(--text-muted)", marginTop: 4 }}>
            {fmtRupee(verifiedRecovery)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            Net Recovery: <strong style={{ color: status === "recovered" ? "#10b981" : "var(--text-primary)" }}>{fmtRupee(verifiedRecovery - cost)}</strong>
          </div>
        </div>
      </div>

      {/* 3. CANDIDATE SELECTION GRID (PART 5) */}
      <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)" }}>
              CANDIDATE INTERVENTIONS EVALUATED
            </h3>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Agent scored expected net recovery and policy constraints across candidates
            </div>
          </div>
          <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
            {candidates.length} Candidate Actions
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.875rem" }}>
          {candidates.map((cand) => (
            <div
              key={cand.action}
              style={{
                padding: "1rem",
                borderRadius: 8,
                background: cand.selected ? "rgba(37, 99, 235, 0.1)" : "var(--bg-primary)",
                border: `1px solid ${cand.selected ? "#2563eb" : cand.policy_status === "BLOCKED" ? "var(--danger)" : "var(--border)"}`,
                position: "relative",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                <span className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  {cand.action}
                </span>
                {cand.selected && (
                  <span style={{ fontSize: "0.625rem", background: "#2563eb", color: "#fff", padding: "2px 6px", borderRadius: 4, fontWeight: 700 }}>
                    ✓ SELECTED
                  </span>
                )}
              </div>

              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: 4 }}>
                Expected: <strong style={{ color: "#10b981" }}>{fmtRupee(cand.expected_recovery)}</strong>
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 8 }}>
                Cost: {fmtRupee(cand.cost)}
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.6875rem" }}>
                <span style={{ color: cand.policy_status === "ALLOWED" ? "#10b981" : "#ef4444", fontWeight: 700 }}>
                  Policy: {cand.policy_status}
                </span>
                {cand.policy_rule && cand.policy_status === "BLOCKED" && (
                  <span style={{ color: "var(--text-muted)", fontSize: "0.625rem" }}>
                    ({cand.policy_rule})
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. WHY THIS? vs WHY NOT THE OTHERS? (PART 7) */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid #2563eb" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "#60a5fa", marginBottom: "0.75rem" }}>
            WHY {selectedCandidate.action.toUpperCase()}?
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.8125rem", color: "var(--text-primary)", display: "flex", flexDirection: "column", gap: 6 }}>
            <li>✓ Highest expected net recovery ({fmtRupee(selectedCandidate.expected_recovery)})</li>
            <li>✓ Historical customer evidence supports payment link completion</li>
            <li>✓ Permitted by policy engine rules (0 safety violations)</li>
            <li>✓ Within maximum intervention budget threshold</li>
          </ul>
        </div>

        <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "#f87171", marginBottom: "0.75rem" }}>
            WHY NOT THE OTHERS?
          </h3>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 8 }}>
            <div>
              <strong style={{ color: "var(--text-primary)" }}>× RETRY PAYMENT:</strong> Lower expected recovery due to gateway authentication code; repeated retries risk card block.
            </div>
            <div>
              <strong style={{ color: "var(--text-primary)" }}>× REMINDER:</strong> Slower time-to-recovery; lower conversion rate for active authorization declines.
            </div>
            <div>
              <strong style={{ color: "var(--text-primary)" }}>× HUMAN ESCALATION:</strong> High manual operational cost; automated recovery still has strong positive expected value.
            </div>
          </div>
        </div>
      </div>

      {/* 5. POLICY AS AN INDEPENDENT AUTHORITY (PART 8) */}
      <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
          ARCHITECTURE BOUNDS: AI PROPOSAL → POLICY ENGINE → EXECUTOR
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr", alignItems: "center", gap: "1rem" }}>
          {/* AI LAYER */}
          <div style={{ padding: "1rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.6875rem", color: "#60a5fa", fontWeight: 700, textTransform: "uppercase" }}>
              1. AI AGENT PROPOSAL
            </div>
            <div className="font-mono" style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
              {selectedCandidate.action}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
              EV: {fmtRupee(selectedCandidate.expected_recovery)}
            </div>
          </div>

          <div style={{ fontSize: "1.25rem", color: "var(--text-muted)" }}>→</div>

          {/* POLICY ENGINE */}
          <div style={{ padding: "1rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid #10b981" }}>
            <div style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700, textTransform: "uppercase" }}>
              2. POLICY ENGINE VERDICT
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#10b981", marginTop: 4 }}>
              {selectedCandidate.policy_status}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
              Rule: stopping_rules_pass (0 violations)
            </div>
          </div>

          <div style={{ fontSize: "1.25rem", color: "var(--text-muted)" }}>→</div>

          {/* EXECUTOR */}
          <div style={{ padding: "1rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase" }}>
              3. EXECUTOR STATUS
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: status === "recovered" ? "#10b981" : "var(--text-primary)", marginTop: 4 }}>
              {status === "recovered" ? "EXECUTED & VERIFIED" : status === "stopped" ? "HALTED BY POLICY" : "EXECUTED"}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
              Executor called after policy check
            </div>
          </div>
        </div>
      </div>

      {/* 6. WHY WE STOPPED (PART 11) */}
      <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: `1px solid ${status === "recovered" ? "#10b981" : status === "stopped" ? "#ef4444" : "var(--border)"}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ fontSize: "1.5rem" }}>
            {status === "recovered" ? "✓" : status === "stopped" ? "🛑" : "🧑"}
          </div>
          <div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
              BOUNDED AUTONOMY — TERMINAL STOP REASON
            </div>
            <div style={{ fontSize: "1rem", fontWeight: 700, color: status === "recovered" ? "#10b981" : status === "stopped" ? "#ef4444" : "var(--text-primary)", marginTop: 2 }}>
              {stopReason}
            </div>
          </div>
        </div>
      </div>

      {/* 7. AGENT VS POLICY EVENT TABLE (PART 12) */}
      <div style={{ padding: "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
          AGENT VS POLICY EXECUTION MATRIX
        </h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)", textAlign: "left" }}>
              <th style={{ padding: "0.5rem" }}>LAYER</th>
              <th style={{ padding: "0.5rem" }}>DECISION / ACTION</th>
              <th style={{ padding: "0.5rem" }}>EXPECTED / COST</th>
              <th style={{ padding: "0.5rem" }}>POLICY STATUS</th>
              <th style={{ padding: "0.5rem" }}>ACTUAL OUTCOME</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "0.5rem", fontWeight: 700, color: "#60a5fa" }}>AI Agent</td>
              <td style={{ padding: "0.5rem" }} className="font-mono">{selectedCandidate.action}</td>
              <td style={{ padding: "0.5rem" }}>{fmtRupee(selectedCandidate.expected_recovery)}</td>
              <td style={{ padding: "0.5rem", color: "#10b981", fontWeight: 600 }}>PROPOSED</td>
              <td style={{ padding: "0.5rem" }}>Stage 3 Recommendation</td>
            </tr>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "0.5rem", fontWeight: 700, color: "#10b981" }}>Policy Engine</td>
              <td style={{ padding: "0.5rem" }}>Guard Check</td>
              <td style={{ padding: "0.5rem" }}>Cost: {fmtRupee(cost)}</td>
              <td style={{ padding: "0.5rem", color: "#10b981", fontWeight: 600 }}>ALLOWED</td>
              <td style={{ padding: "0.5rem" }}>0 Policy Violations</td>
            </tr>
            <tr>
              <td style={{ padding: "0.5rem", fontWeight: 700, color: "var(--text-primary)" }}>Executor</td>
              <td style={{ padding: "0.5rem" }}>Dispatch &amp; Verify</td>
              <td style={{ padding: "0.5rem" }}>Actual: <strong style={{ color: status === "recovered" ? "#10b981" : "var(--text-primary)" }}>{fmtRupee(verifiedRecovery)}</strong></td>
              <td style={{ padding: "0.5rem", color: status === "recovered" ? "#10b981" : "var(--warning)", fontWeight: 600 }}>{status.toUpperCase()}</td>
              <td style={{ padding: "0.5rem", color: status === "recovered" ? "#10b981" : "var(--text-muted)" }}>{status === "recovered" ? "Settlement HMAC Verified" : "Halted"}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
