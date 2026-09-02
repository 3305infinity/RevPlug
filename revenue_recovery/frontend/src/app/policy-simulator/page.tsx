"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, PolicySimulatorPreviewResponse } from "@/lib/api";

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
  preview_summary?: Record<string, any>;
}

type PolicyField = keyof Pick<PolicyConfigData,
  "max_retries" | "max_contacts_per_24h" | "min_expected_net_ev_minor" |
  "max_intervention_cost_minor" | "cooldown_retry_minutes" | "escalation_thresholds_minor" |
  "systemic_suppression_threshold_pct">;

const POLICY_FIELDS: { key: PolicyField; label: string; description: string; min?: number; max?: number; step?: number }[] = [
  { key: "max_retries", label: "Maximum Retry Attempts", description: "Max retry attempts per opportunity", min: 0, max: 10, step: 1 },
  { key: "max_contacts_per_24h", label: "Max Customer Contacts / 24h", description: "Outbound contact limit within 24 hours", min: 0, max: 10, step: 1 },
  { key: "min_expected_net_ev_minor", label: "Minimum Expected Net EV (Paise)", description: "Minimum expected net economic value to proceed", min: 0, max: 10000000, step: 100 },
  { key: "max_intervention_cost_minor", label: "Max Intervention Cost (Paise)", description: "Maximum cost per intervention", min: 0, max: 10000000, step: 100 },
  { key: "cooldown_retry_minutes", label: "Cooldown Retry (Minutes)", description: "Wait time between retry attempts", min: 0, max: 10080, step: 15 },
  { key: "escalation_thresholds_minor", label: "Escalation Threshold (Paise)", description: "Amount above which human review is required", min: 0, max: 50000000, step: 100 },
  { key: "systemic_suppression_threshold_pct", label: "Systemic Suppression Threshold (%)", description: "Suppression trigger for incident response", min: 0, max: 100, step: 1 },
];

export default function PolicySimulatorPage() {
  const [currentPolicy, setCurrentPolicy] = useState<PolicyConfigData | null>(null);
  const [proposedPolicy, setProposedPolicy] = useState<Record<string, any>>({});
  const [status, setStatus] = useState<"loading" | "ready" | "previewing" | "error">("loading");
  const [result, setResult] = useState<PolicySimulatorPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const loadCurrentPolicy = async () => {
    try {
      const data = await api.policySimulatorCurrent();
      setCurrentPolicy(data);
      setProposedPolicy({
        max_retries: data.max_retries,
        max_contacts_per_24h: data.max_contacts_per_24h,
        min_expected_net_ev_minor: data.min_expected_net_ev_minor,
        max_intervention_cost_minor: data.max_intervention_cost_minor,
        cooldown_retry_minutes: data.cooldown_retry_minutes,
        escalation_thresholds_minor: data.escalation_thresholds_minor,
        systemic_suppression_threshold_pct: data.systemic_suppression_threshold_pct,
      });
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    loadCurrentPolicy();
  }, []);

  const handlePreview = async () => {
    setError(null);
    setResult(null);
    setStatus("previewing");
    try {
      const data = await api.policySimulatorPreview({
        proposed_policy: proposedPolicy,
      });
      setResult(data);
      setStatus("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Policy preview failed");
      setStatus("error");
    }
  };

  const handleReset = () => {
    if (currentPolicy) {
      setProposedPolicy({
        max_retries: currentPolicy.max_retries,
        max_contacts_per_24h: currentPolicy.max_contacts_per_24h,
        min_expected_net_ev_minor: currentPolicy.min_expected_net_ev_minor,
        max_intervention_cost_minor: currentPolicy.max_intervention_cost_minor,
        cooldown_retry_minutes: currentPolicy.cooldown_retry_minutes,
        escalation_thresholds_minor: currentPolicy.escalation_thresholds_minor,
        systemic_suppression_threshold_pct: currentPolicy.systemic_suppression_threshold_pct,
      });
    }
    setResult(null);
    setError(null);
  };

  const fmtMinor = (n: number) => "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  const fmtPct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;

  const distributionChanged = result && (
    JSON.stringify(result.current_distribution) !== JSON.stringify(result.proposed_distribution)
  );

  const hasChanges = result && result.changed_count > 0;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: 4 }}>
          <span style={{
            fontSize: "0.625rem",
            padding: "0.1rem 0.4rem",
            borderRadius: 4,
            fontWeight: 700,
            background: "rgba(59, 130, 246, 0.15)",
            color: "#60a5fa",
            border: "1px solid #3b82f6",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
          }}>POLICY PREVIEW</span>
          {currentPolicy && (
            <span style={{
              fontSize: "0.625rem",
              padding: "0.1rem 0.4rem",
              borderRadius: 4,
              fontWeight: 700,
              background: "var(--bg-secondary)",
              color: "var(--text-muted)",
              border: "1px solid var(--border)",
            }}>CURRENT: {currentPolicy.version}</span>
          )}
        </div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
          Policy Simulator
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4, maxWidth: 700 }}>
          Preview how proposed policy changes would affect recovery decisions. This is a read-only evaluation — no live policy is modified and no actions are executed.
        </p>
      </div>

      {status === "loading" && (
        <div style={{ display: "grid", gap: "1rem" }}>
          <div className="skeleton" style={{ height: 400 }} />
        </div>
      )}

      {status === "error" && !result && (
        <div className="card" style={{ padding: "2.5rem", textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load policy configuration</div>
        </div>
      )}

      {status === "ready" && currentPolicy && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
          {/* CURRENT POLICY */}
          <div className="card" style={{ padding: "1.25rem", borderLeft: "4px solid var(--text-muted)" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
              Current Policy
            </div>
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {POLICY_FIELDS.map((field) => (
                <div key={field.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>{field.label}</div>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>{field.description}</div>
                  </div>
                  <div className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {currentPolicy[field.key]?.toLocaleString?.() ?? currentPolicy[field.key]}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* PROPOSED POLICY */}
          <div className="card" style={{ padding: "1.25rem", borderLeft: "4px solid #f59e0b" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
              Proposed Policy
            </div>
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {POLICY_FIELDS.map((field) => (
                <div key={field.key}>
                  <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}>
                    {field.label}
                  </label>
                  <input
                    type="number"
                    value={proposedPolicy[field.key] ?? currentPolicy[field.key]}
                    onChange={(e) => {
                      const val = field.step && field.step < 1 ? parseFloat(e.target.value) || 0 : parseInt(e.target.value) || 0;
                      setProposedPolicy({ ...proposedPolicy, [field.key]: val });
                    }}
                    min={field.min}
                    max={field.max}
                    step={field.step || 1}
                    style={{
                      width: "100%",
                      padding: "0.5rem",
                      borderRadius: 6,
                      background: "var(--bg-primary)",
                      border: "1px solid var(--border)",
                      color: "var(--text-primary)",
                      fontFamily: "monospace",
                      fontSize: "0.8125rem",
                    }}
                  />
                  <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>{field.description}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ACTION BAR */}
      {currentPolicy && (
        <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            Preview evaluates the proposed policy against the current opportunity set. Nothing is modified.
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button onClick={handleReset} style={{
              padding: "0.5rem 1rem",
              borderRadius: 6,
              border: "1px solid var(--border)",
              background: "var(--bg-primary)",
              color: "var(--text-secondary)",
              fontSize: "0.8125rem",
              fontWeight: 600,
              cursor: "pointer",
            }}>Reset to Current</button>
            <button onClick={handlePreview} disabled={status === "previewing"} style={{
              padding: "0.5rem 1.25rem",
              borderRadius: 6,
              border: "none",
              background: "#f59e0b",
              color: "#fff",
              fontSize: "0.8125rem",
              fontWeight: 700,
              cursor: status === "previewing" ? "not-allowed" : "pointer",
              opacity: status === "previewing" ? 0.7 : 1,
            }}>
              {status === "previewing" ? "Evaluating..." : "Preview Decision Impact"}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="card" style={{ padding: "1rem", marginBottom: "1.25rem", background: "var(--danger-subtle)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.8125rem", fontWeight: 600 }}>{error}</div>
        </div>
      )}

      {/* RESULTS */}
      {result && (
        <div style={{ display: "grid", gap: "1.25rem" }}>
          {/* SUMMARY STRIP */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            <div className="metric-block" style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Opportunities</div>
              <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", marginTop: 4 }}>{result.opportunities_evaluated}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
                {hasChanges ? `${result.changed_count} decisions would change` : "No decisions would change"}
                {result.unevaluable_count > 0 && (
                  <span style={{ color: "var(--warning)", marginLeft: 4 }}>({result.unevaluable_count} unevaluable)</span>
                )}
              </div>
            </div>
            <div className="metric-block" style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Expected Recovery Delta</div>
              <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 800, color: result.expected_recovery_delta_minor >= 0 ? "var(--success)" : "var(--danger)", marginTop: 4 }}>
                {result.expected_recovery_delta_minor >= 0 ? "+" : ""}{fmtMinor(result.expected_recovery_delta_minor)}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>Projected change only</div>
            </div>
            <div className="metric-block" style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Safety Conflicts</div>
              <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 800, color: result.safety_conflicts.length === 0 ? "var(--success)" : "var(--danger)", marginTop: 4 }}>
                {result.safety_conflicts.length}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
                {result.safety_conflicts.length === 0 ? "No safety conflicts" : "Requires review"}
              </div>
            </div>
            <div className="metric-block" style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Scope</div>
              <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", marginTop: 4, textTransform: "capitalize" }}>{result.scope.replace("_", " ")}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>Simulation ID: {result.simulation_id}</div>
            </div>
          </div>

          {/* DECISION DISTRIBUTION */}
          {distributionChanged && (
            <div className="card" style={{ padding: "1.25rem" }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
                Decision Distribution
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
                <div>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.5rem", textTransform: "uppercase" }}>Current Policy</div>
                  <div style={{ display: "grid", gap: "0.5rem" }}>
                    {Object.entries(result.current_distribution).map(([decision, count]) => (
                      <div key={decision} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                        <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>{decision}</span>
                        <span className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.5rem", textTransform: "uppercase" }}>Proposed Policy</div>
                  <div style={{ display: "grid", gap: "0.5rem" }}>
                    {Object.entries(result.proposed_distribution).map(([decision, count]) => (
                      <div key={decision} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                        <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>{decision}</span>
                        <span className="font-mono" style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* FINANCIAL IMPACT */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
              Financial Impact
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
              <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: "0.25rem" }}>Expected Recovery</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>Current</div>
                <div className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>{fmtMinor(result.current_expected_recovery_minor)}</div>
              </div>
              <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: "0.25rem" }}>Expected Recovery</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>Proposed</div>
                <div className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>{fmtMinor(result.proposed_expected_recovery_minor)}</div>
              </div>
              <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginBottom: "0.25rem" }}>Delta</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>Proposed - Current</div>
                <div className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 800, color: result.expected_recovery_delta_minor >= 0 ? "var(--success)" : "var(--danger)" }}>
                  {result.expected_recovery_delta_minor >= 0 ? "+" : ""}{fmtMinor(result.expected_recovery_delta_minor)}
                </div>
              </div>
            </div>
            <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Expected recovery reflects AI-predicted recovery value under each policy. This is not verified recovered money.
            </div>
          </div>

          {/* SAFETY IMPACT */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
              Safety Impact
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem" }}>
              <div>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.5rem", textTransform: "uppercase" }}>Current Policy</div>
                <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
                  <div className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>{result.current_policy_violations}</div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Policy violations</div>
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.5rem", textTransform: "uppercase" }}>Proposed Policy</div>
                <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
                  <div className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 800, color: result.proposed_policy_violations > 0 ? "var(--danger)" : "var(--success)" }}>{result.proposed_policy_violations}</div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Policy violations</div>
                </div>
              </div>
            </div>
            {result.safety_conflicts.length > 0 && (
              <div style={{ marginTop: "1rem", padding: "0.75rem", background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 6 }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--danger)", marginBottom: "0.5rem" }}>Safety Conflicts</div>
                {result.safety_conflicts.map((conflict, i) => (
                  <div key={i} style={{ fontSize: "0.75rem", color: "var(--text-secondary)", padding: "0.25rem 0", borderBottom: i < result.safety_conflicts.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <strong>{conflict.opportunity_id}</strong>: {conflict.type.replace(/_/g, " ")} — {conflict.reason}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* CHANGED DECISIONS TABLE */}
          {hasChanges && (
            <div className="card" style={{ padding: "1.25rem" }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
                Changed Decisions ({result.changed_count})
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)", textAlign: "left" }}>
                      <th style={{ padding: "0.5rem" }}>OPPORTUNITY</th>
                      <th style={{ padding: "0.5rem" }}>CHANGE</th>
                      <th style={{ padding: "0.5rem" }}>POLICY RULE</th>
                      <th style={{ padding: "0.5rem" }}>CURRENT REASON</th>
                      <th style={{ padding: "0.5rem" }}>PROPOSED REASON</th>
                      <th style={{ padding: "0.5rem", textAlign: "right" }}>AMOUNT AT RISK</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.decision_diffs.slice(0, 50).map((diff) => (
                      <tr key={diff.opportunity_id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "0.625rem 0.5rem", fontFamily: "monospace", fontWeight: 600 }}>{diff.opportunity_id}</td>
                        <td style={{ padding: "0.625rem 0.5rem" }}>
                          <span style={{
                            fontSize: "0.75rem",
                            fontWeight: 700,
                            padding: "0.15rem 0.5rem",
                            borderRadius: 4,
                            background: "rgba(245, 158, 11, 0.1)",
                            color: "#f59e0b",
                            border: "1px solid rgba(245, 158, 11, 0.2)",
                          }}>{diff.change_type}</span>
                        </td>
                        <td style={{ padding: "0.625rem 0.5rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>{diff.policy_rule_responsible.replace(/_/g, " ")}</td>
                        <td style={{ padding: "0.625rem 0.5rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>{diff.current.reason}</td>
                        <td style={{ padding: "0.625rem 0.5rem", fontSize: "0.75rem", color: "var(--text-primary)" }}>{diff.proposed.reason}</td>
                        <td style={{ padding: "0.625rem 0.5rem", textAlign: "right", fontFamily: "monospace" }}>{fmtMinor(diff.financial_context.amount_at_risk_minor)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {result.decision_diffs.length > 50 && (
                  <div style={{ padding: "0.75rem", fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center", marginTop: "0.5rem" }}>
                    Showing first 50 of {result.decision_diffs.length} changed decisions
                  </div>
                )}
              </div>
            </div>
          )}

          {/* NO CHANGES */}
          {!hasChanges && result && (
            <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
              <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>No Recovery Decisions Would Change</div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Under the proposed policy, all recovery decisions would remain the same. Consider adjusting policy parameters to see impact.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
