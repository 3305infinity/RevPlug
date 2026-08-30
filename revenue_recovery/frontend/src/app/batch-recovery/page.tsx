"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, EvaluationRunResult } from "@/lib/api";

type Status = "loading" | "error" | "ready" | "running" | "complete";

export default function BatchEvaluation() {
  const [status, setStatus] = useState<Status>("ready");
  const [count, setCount] = useState(50);
  const [seed, setSeed] = useState(42);
  const [result, setResult] = useState<EvaluationRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  const handleRun = async () => {
    setStatus("running");
    setError(null);
    setResult(null);
    try {
      const data = await api.evaluationBatch({ count, seed });
      setResult(data);
      setStatus("complete");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
      setStatus("error");
    }
  };

  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem", color: "var(--text-primary)" }}>
          RecoverOS Live Evaluation Engine
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: 800 }}>
          Run an automated, deterministic batch evaluation comparing RecoverOS policy-driven intelligence against a fixed retry baseline on the exact same dataset.
        </p>
      </div>

      {/* Control Bar */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", background: "var(--bg-secondary)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.25rem", alignItems: "end" }}>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              Evaluation Batch Size
            </label>
            <select
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="input"
              style={{ width: "100%" }}
              disabled={status === "running"}
            >
              <option value={10}>10 opportunities (Quick)</option>
              <option value={50}>50 opportunities (Standard)</option>
              <option value={100}>100 opportunities (Benchmark)</option>
              <option value={200}>200 opportunities (Stress)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              Random Seed (Seeded Determinism)
            </label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="input"
              style={{ width: "100%" }}
              disabled={status === "running"}
            />
          </div>

          <div>
            <button
              onClick={handleRun}
              disabled={status === "running"}
              className="btn-primary"
              style={{ width: "100%", fontSize: "0.8125rem", padding: "0.75rem 1.5rem", background: "var(--accent)", fontWeight: 600 }}
            >
              {status === "running" ? `Processing ${count} cases...` : "Run Live Evaluation Batch"}
            </button>
          </div>
        </div>
      </div>

      {/* Deterministic EV Callout */}
      <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.5rem", background: "rgba(249, 115, 22, 0.04)", border: "1px solid rgba(249, 115, 22, 0.2)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f97316", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Deterministic Expected Value Scoring
            </div>
            <div style={{ fontSize: "0.875rem", color: "var(--text-primary)", fontWeight: 600, marginTop: "0.25rem" }}>
              Expected Value = Amount × Probability − Intervention Cost
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
              The LLM does NOT control this value. Expected recovery is calculated deterministically from failure category, historical recovery probability, and attempt cost.
            </div>
          </div>
          <div style={{ background: "#09090b", padding: "0.75rem 1rem", borderRadius: 6, border: "1px solid rgba(255,255,255,0.08)", fontFamily: "monospace", fontSize: "0.8125rem", color: "#f8fafc" }}>
            Sample: ₹50,000 × 70% − ₹500 = <span style={{ color: "#34d399", fontWeight: 700 }}>₹34,500</span>
          </div>
        </div>
      </div>

      {error && status !== "running" && (
        <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem", background: "var(--danger-subtle)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.8125rem" }}>{error}</div>
        </div>
      )}

      {/* Progress Loading State */}
      {status === "running" && (
        <div className="card" style={{ padding: "3rem", textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Running Batch Evaluation...</div>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
            Executing {count} seeded revenue opportunities through RecoverOS & Baseline...
          </p>
          <div style={{ width: "100%", maxWidth: 400, margin: "0 auto", height: 6, background: "rgba(255,255,255,0.1)", borderRadius: 3, overflow: "hidden" }}>
            <div style={{ width: "60%", height: "100%", background: "var(--accent)", transition: "width 0.3s" }} />
          </div>
        </div>
      )}

      {/* Results Section */}
      {result && (
        <>
          {/* Honest Summary Banner */}
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", background: "var(--bg-tertiary)" }}>
            <h3 style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem", color: "var(--text-muted)" }}>
              Benchmark Execution Summary
            </h3>
            <div style={{ fontSize: "1.25rem", fontWeight: 600, color: result.comparison.recoveros_beat_baseline ? "var(--success)" : "var(--warning)", lineHeight: 1.4 }}>
              {result.comparison.honest_summary}
            </div>
            {result.comparison.relative_improvement !== null && (
              <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "0.5rem" }}>
                Relative Improvement: <span style={{ fontWeight: 700, color: "var(--success)" }}>+{(result.comparison.relative_improvement * 100).toFixed(1)}%</span> over fixed retry baseline.
              </div>
            )}
          </div>

          {/* Side-by-Side Head to Head Metrics */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
            {/* RecoverOS */}
            <div className="card" style={{ overflow: "hidden", borderTop: "4px solid var(--accent)" }}>
              <div style={{ padding: "1.25rem 1.5rem", background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>RecoverOS</h3>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Policy-Constrained Autonomous Agent</div>
                </div>
                <span style={{ fontSize: "0.6875rem", fontWeight: 700, padding: "0.2rem 0.5rem", borderRadius: 4, background: "var(--accent-subtle)", color: "var(--accent)" }}>
                  INTELLIGENT
                </span>
              </div>
              <div style={{ padding: "1.5rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
                <Metric label="Actually Recovered" value={fmt(result.recoveros.actual_recovered)} sub={`${result.recoveros.recovered_count} cases`} accent="var(--success)" />
                <Metric label="Recovery Rate" value={`${(result.recoveros.recovery_rate * 100).toFixed(1)}%`} sub={`of ${fmt(result.recoveros.total_amount_at_risk)} at risk`} accent="var(--accent)" />
                <Metric label="Unnecessary Interventions" value={String(result.recoveros.unnecessary_interventions)} sub="Retries that failed" accent="var(--warning)" />
                <Metric label="Cost Per Recovery" value={`₹${result.recoveros.cost_per_recovery.toFixed(2)}`} sub={`Total cost: ${fmt(result.recoveros.intervention_cost)}`} accent="#f8fafc" />
              </div>
            </div>

            {/* Fixed Baseline */}
            <div className="card" style={{ overflow: "hidden", borderTop: "4px solid var(--text-muted)" }}>
              <div style={{ padding: "1.25rem 1.5rem", background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>Fixed Baseline</h3>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Fixed Retry-Payment Strategy (retry × 2)</div>
                </div>
                <span style={{ fontSize: "0.6875rem", fontWeight: 700, padding: "0.2rem 0.5rem", borderRadius: 4, background: "rgba(100,116,139,0.12)", color: "var(--text-muted)" }}>
                  UNINTELLIGENT
                </span>
              </div>
              <div style={{ padding: "1.5rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
                <Metric label="Actually Recovered" value={fmt(result.baseline.actual_recovered)} sub={`${result.baseline.recovered_count} cases`} accent="var(--success)" />
                <Metric label="Recovery Rate" value={`${(result.baseline.recovery_rate * 100).toFixed(1)}%`} sub={`of ${fmt(result.baseline.total_amount_at_risk)} at risk`} accent="var(--accent)" />
                <Metric label="Unnecessary Interventions" value={String(result.baseline.unnecessary_interventions)} sub="Retries that failed" accent="var(--danger)" />
                <Metric label="Cost Per Recovery" value={`₹${result.baseline.cost_per_recovery.toFixed(2)}`} sub={`Total cost: ${fmt(result.baseline.intervention_cost)}`} accent="#f8fafc" />
              </div>
            </div>
          </div>

          {/* Rules-First vs LLM Breakdown & Safety Statistics */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
            {/* Rules vs LLM */}
            <div className="card" style={{ padding: "1.25rem 1.5rem" }}>
              <h3 style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem", color: "var(--text-muted)" }}>
                Rules-First vs LLM Classification Pathing
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "0.75rem 1rem", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Deterministic Rules</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#38bdf8", fontFamily: "monospace" }}>{result.recoveros.rules_classified_count || 0}</div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Bypassed LLM</div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "0.75rem 1rem", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>LLM Evaluated</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f59e0b", fontFamily: "monospace" }}>{result.recoveros.llm_classified_count || 0}</div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Ambiguous Intent</div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "0.75rem 1rem", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Fallback Count</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-muted)", fontFamily: "monospace" }}>{result.recoveros.llm_fallback_count || 0}</div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Rule Safetied</div>
                </div>
              </div>
            </div>

            {/* Safety Matrix */}
            <div className="card" style={{ padding: "1.25rem 1.5rem" }}>
              <h3 style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem", color: "var(--text-muted)" }}>
                Safety Control Matrix Decisions
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "0.75rem" }}>
                <div style={{ background: "rgba(52,211,153,0.08)", padding: "0.75rem 0.5rem", borderRadius: 6, textAlign: "center" }}>
                  <div style={{ fontSize: "0.6875rem", color: "#34d399", fontWeight: 700 }}>ALLOWED</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#34d399", fontFamily: "monospace" }}>{result.dataset.safety_statistics?.ALLOWED || 0}</div>
                </div>
                <div style={{ background: "rgba(239,68,68,0.08)", padding: "0.75rem 0.5rem", borderRadius: 6, textAlign: "center" }}>
                  <div style={{ fontSize: "0.6875rem", color: "#fca5a5", fontWeight: 700 }}>BLOCKED</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#fca5a5", fontFamily: "monospace" }}>{result.dataset.safety_statistics?.DENY || 0}</div>
                </div>
                <div style={{ background: "rgba(245,158,11,0.08)", padding: "0.75rem 0.5rem", borderRadius: 6, textAlign: "center" }}>
                  <div style={{ fontSize: "0.6875rem", color: "#fbbf24", fontWeight: 700 }}>STOPPED</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#fbbf24", fontFamily: "monospace" }}>{result.dataset.safety_statistics?.STOPPED || 0}</div>
                </div>
                <div style={{ background: "rgba(168,85,247,0.08)", padding: "0.75rem 0.5rem", borderRadius: 6, textAlign: "center" }}>
                  <div style={{ fontSize: "0.6875rem", color: "#c084fc", fontWeight: 700 }}>ESCALATE</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#c084fc", fontFamily: "monospace" }}>{result.dataset.safety_statistics?.ESCALATE || 0}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Dataset Surface & Scenario Matrix */}
          <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem", color: "var(--text-muted)" }}>
              Revenue Surface & Scenario Coverage
            </h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {Object.entries(result.dataset.surfaces || {}).map(([surf, count]) => (
                <div key={surf} style={{ background: "#121215", border: "1px solid rgba(255,255,255,0.08)", padding: "0.4rem 0.75rem", borderRadius: 4, fontSize: "0.75rem" }}>
                  <span style={{ color: "var(--text-muted)", textTransform: "uppercase", fontSize: "0.6875rem", letterSpacing: "0.05em" }}>{surf.replace(/_/g, " ")}: </span>
                  <span style={{ fontWeight: 700, color: "#f8fafc", fontFamily: "monospace" }}>{count}</span>
                </div>
              ))}
              {Object.entries(result.dataset.categories || {}).map(([cat, count]) => (
                <div key={cat} style={{ background: "rgba(249,115,22,0.05)", border: "1px solid rgba(249,115,22,0.2)", padding: "0.4rem 0.75rem", borderRadius: 4, fontSize: "0.75rem" }}>
                  <span style={{ color: "#f97316", fontSize: "0.6875rem" }}>{cat.replace(/_/g, " ")}: </span>
                  <span style={{ fontWeight: 700, color: "#ffffff", fontFamily: "monospace" }}>{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Per-Case Table */}
          <div className="card" style={{ overflow: "hidden" }}>
            <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Evaluated Case Opportunities ({result.per_case.length})
              </h3>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Click any case to inspect workspace
              </span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <Th>Case ID</Th>
                    <Th>Category</Th>
                    <Th>Amount</Th>
                    <Th>Path</Th>
                    <Th>RecoverOS Action</Th>
                    <Th>RecoverOS Outcome</Th>
                    <Th>Baseline Outcome</Th>
                    <Th>Action</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.per_case.map((c) => (
                    <tr key={c.case_id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <Td>
                        <span style={{ color: "var(--text-muted)", fontFamily: "monospace", fontSize: "0.75rem" }}>
                          {c.case_id}
                        </span>
                      </Td>
                      <Td>
                        <span style={{
                          padding: "0.2rem 0.6rem", borderRadius: 4, fontSize: "0.6875rem", fontWeight: 600,
                          background: categoryBg(c.original_category),
                          color: categoryColor(c.original_category),
                          textTransform: "capitalize",
                        }}>
                          {c.original_category.replace(/_/g, " ")}
                        </span>
                      </Td>
                      <Td style={{ fontFamily: "monospace", fontSize: "0.8125rem", color: "#f8fafc" }}>
                        {fmt(c.amount_at_risk)}
                      </Td>
                      <Td>
                        <span style={{
                          fontSize: "0.6875rem", fontWeight: 600, padding: "0.15rem 0.4rem", borderRadius: 4,
                          background: c.recoveros.diagnosis_path === "rules" ? "rgba(56,189,248,0.12)" : "rgba(245,158,11,0.12)",
                          color: c.recoveros.diagnosis_path === "rules" ? "#38bdf8" : "#f59e0b",
                        }}>
                          {c.recoveros.diagnosis_path.toUpperCase()}
                        </span>
                      </Td>
                      <Td>
                        <span style={{
                          background: c.recoveros.proposed_action ? "var(--purple-subtle)" : "var(--bg-tertiary)",
                          color: c.recoveros.proposed_action ? "var(--purple)" : "var(--text-muted)",
                          padding: "0.2rem 0.6rem", borderRadius: 4, fontSize: "0.6875rem", fontWeight: 600,
                          textTransform: "capitalize",
                        }}>
                          {c.recoveros.proposed_action?.replace(/_/g, " ") || "No Action"}
                        </span>
                      </Td>
                      <Td>
                        <span className={`status-badge status-${c.recoveros.outcome}`}>
                          {c.recoveros.outcome.replace(/_/g, " ")}
                        </span>
                      </Td>
                      <Td>
                        <span className={`status-badge status-${c.baseline?.outcome || "unknown"}`}>
                          {c.baseline?.outcome.replace(/_/g, " ") || "unknown"}
                        </span>
                      </Td>
                      <Td>
                        <Link
                          href={`/recovery/${c.case_id}`}
                          style={{ fontSize: "0.75rem", color: "#f97316", textDecoration: "none", fontWeight: 600 }}
                        >
                          Workspace →
                        </Link>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Metric({ label, value, sub, accent }: { label: string; value: string; sub: string; accent: string }) {
  return (
    <div>
      <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
      <div style={{ fontSize: "1.75rem", fontWeight: 700, color: accent, fontFamily: "monospace", letterSpacing: "-0.03em", lineHeight: 1.2, marginTop: "0.25rem" }}>{value}</div>
      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>{sub}</div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ padding: "0.875rem 1.25rem", textAlign: "left", fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", background: "var(--bg-secondary)" }}>{children}</th>;
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ padding: "0.875rem 1.25rem", fontSize: "0.8125rem", ...style }}>{children}</td>;
}

function categoryColor(cat: string | null): string {
  const map: Record<string, string> = { soft: "var(--success)", hard: "var(--warning)", fraud: "var(--danger)", authentication_required: "var(--accent)", unknown: "var(--text-muted)" };
  return map[cat || ""] || "var(--text-muted)";
}

function categoryBg(cat: string | null): string {
  const map: Record<string, string> = {
    soft: "var(--success-subtle)",
    hard: "var(--warning-subtle)",
    fraud: "var(--danger-subtle)",
    authentication_required: "var(--accent-subtle)",
    unknown: "rgba(100,116,139,0.12)",
  };
  return map[cat || ""] || "rgba(100,116,139,0.12)";
}
