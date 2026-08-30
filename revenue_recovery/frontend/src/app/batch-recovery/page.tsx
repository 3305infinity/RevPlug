"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, EvaluationRunResult } from "@/lib/api";

type Status = "loading" | "error" | "ready" | "running" | "complete";

export default function BatchEvaluation() {
  const [status, setStatus] = useState<Status>("loading");
  const [count, setCount] = useState(50);
  const [seed, setSeed] = useState(42);
  const [result, setResult] = useState<EvaluationRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      setError(null);
      await new Promise((r) => setTimeout(r, 200));
      setStatus("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

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

  if (status === "error" && !result) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to run evaluation</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={load} className="btn-primary">Retry</button>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>RecoverOS vs Baseline Benchmark</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Run a deterministic batch evaluation comparing RecoverOS intelligent decisions against a fixed retry-strategy baseline.
        </p>
      </div>

      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", alignItems: "end" }}>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              Number of Cases
            </label>
            <select
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="input"
              style={{ width: "100%" }}
              disabled={status === "running"}
            >
              <option value={10}>10 cases (Quick)</option>
              <option value={50}>50 cases (Standard)</option>
              <option value={100}>100 cases</option>
              <option value={500}>500 cases (Stress Test)</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              Random Seed (Determinism)
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
        </div>
        <div style={{ marginTop: "1.25rem", display: "flex", alignItems: "center", gap: "1rem" }}>
          <button
            onClick={handleRun}
            disabled={status === "running"}
            className="btn-primary"
            style={{ fontSize: "0.8125rem", padding: "0.75rem 1.5rem", background: "var(--accent)" }}
          >
            {status === "running" ? "Running Benchmark..." : "Run Benchmark Evaluation"}
          </button>
        </div>
      </div>

      {error && status !== "running" && (
        <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem", background: "var(--danger-subtle)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.8125rem" }}>{error}</div>
        </div>
      )}

      {result && (
        <>
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", background: "var(--bg-tertiary)" }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 700, marginBottom: "0.5rem", color: "var(--text-primary)" }}>
              Head-to-Head Result
            </h3>
            <div style={{ fontSize: "1.25rem", fontWeight: 600, color: result.comparison.recoveros_beat_baseline ? "var(--success)" : "var(--warning)", lineHeight: 1.4 }}>
              {result.comparison.honest_summary}
            </div>
            {!result.comparison.recoveros_beat_baseline && (
              <p style={{ marginTop: "0.5rem", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                <em>Note: The baseline retries everything (including fraud and opted-out customers), which yields occasional accidental recoveries but accumulates massive unnecessary intervention costs and ignores compliance risk. RecoverOS prioritizes safety and cost-efficiency.</em>
              </p>
            )}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
            {/* RecoverOS Column */}
            <div className="card" style={{ overflow: "hidden", borderTop: "4px solid var(--accent)" }}>
              <div style={{ padding: "1.25rem 1.5rem", background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>RecoverOS</h3>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Intelligent Contextual Recovery</div>
              </div>
              <div style={{ padding: "1.5rem" }}>
                <Metric label="Actually Recovered" value={fmt(result.recoveros.actual_recovered)} sub={`${result.recoveros.recovered_count} cases`} accent="var(--success)" />
                <div style={{ height: "1rem" }} />
                <Metric label="Recovery Rate" value={`${(result.recoveros.recovery_rate * 100).toFixed(1)}%`} sub={`of ${fmt(result.recoveros.total_amount_at_risk)} at risk`} accent="var(--accent)" />
                <div style={{ height: "1rem" }} />
                <Metric label="Unnecessary Interventions" value={String(result.recoveros.unnecessary_interventions)} sub={`Total interventions: ${result.recoveros.total_interventions}`} accent="var(--warning)" />
                <div style={{ height: "1rem" }} />
                <Metric label="Intervention Cost" value={fmt(result.recoveros.intervention_cost)} sub={`₹${result.recoveros.cost_per_recovery.toFixed(2)} per recovery`} accent="var(--danger)" />
              </div>
            </div>

            {/* Baseline Column */}
            <div className="card" style={{ overflow: "hidden", borderTop: "4px solid var(--text-muted)" }}>
              <div style={{ padding: "1.25rem 1.5rem", background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Fixed Baseline</h3>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Dumb Retry-Payment Strategy</div>
              </div>
              <div style={{ padding: "1.5rem" }}>
                <Metric label="Actually Recovered" value={fmt(result.baseline.actual_recovered)} sub={`${result.baseline.recovered_count} cases`} accent="var(--success)" />
                <div style={{ height: "1rem" }} />
                <Metric label="Recovery Rate" value={`${(result.baseline.recovery_rate * 100).toFixed(1)}%`} sub={`of ${fmt(result.baseline.total_amount_at_risk)} at risk`} accent="var(--accent)" />
                <div style={{ height: "1rem" }} />
                <Metric label="Unnecessary Interventions" value={String(result.baseline.unnecessary_interventions)} sub={`Total interventions: ${result.baseline.total_interventions}`} accent="var(--danger)" />
                <div style={{ height: "1rem" }} />
                <Metric label="Intervention Cost" value={fmt(result.baseline.intervention_cost)} sub={`₹${result.baseline.cost_per_recovery.toFixed(2)} per recovery`} accent="var(--danger)" />
              </div>
            </div>
          </div>

          <div className="card" style={{ overflow: "hidden" }}>
            <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Case Results (Head-to-Head)
              </h3>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <Th>Case ID</Th>
                    <Th>Category</Th>
                    <Th>Amount</Th>
                    <Th>RecoverOS Action</Th>
                    <Th>RecoverOS Outcome</Th>
                    <Th>Baseline Action</Th>
                    <Th>Baseline Outcome</Th>
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
                      <Td style={{ fontFamily: "monospace", fontSize: "0.8125rem" }}>
                        {fmt(c.amount_at_risk)}
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
                        <span style={{
                          background: c.baseline?.proposed_action ? "var(--purple-subtle)" : "var(--bg-tertiary)", 
                          color: c.baseline?.proposed_action ? "var(--purple)" : "var(--text-muted)",
                          padding: "0.2rem 0.6rem", borderRadius: 4, fontSize: "0.6875rem", fontWeight: 600,
                          textTransform: "capitalize",
                        }}>
                          {c.baseline?.proposed_action?.replace(/_/g, " ") || "No Action"}
                        </span>
                      </Td>
                      <Td>
                        <span className={`status-badge status-${c.baseline?.outcome || 'unknown'}`}>
                          {c.baseline?.outcome.replace(/_/g, " ") || "unknown"}
                        </span>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {status === "running" && (
        <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
          <div className="skeleton" style={{ height: 48, width: 200, margin: "0 auto 1rem" }} />
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>Evaluating {count} cases head-to-head...</p>
        </div>
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
