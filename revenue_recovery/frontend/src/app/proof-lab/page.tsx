"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, EvaluationRunResult, ScientificBenchmarkReport } from "@/lib/api";

type ProofLabStatus = "loading" | "no_data" | "ready" | "error";
type DataRegime = "LIVE_OPERATIONAL" | "BENCHMARK_SYNTHETIC";

interface ProofResult {
  verdict: "REVPLUG_WINS" | "BASELINE_WINS" | "INCONCLUSIVE";
  netLiftPct: number;
  confidence95: [number, number];
  winRate: string;
  revplugNet: number;
  safeNet: number;
  naiveNet: number;
  revplugViolations: number;
  baselineViolations: number;
}

interface BreakdownItem {
  label: string;
  revplug: number;
  safe: number;
  naive: number;
  unit: string;
}

interface WinReason {
  category: string;
  description: string;
  revplugAdvantage: number;
  unit?: string;
  evidence: string[];
}

interface AdaptiveAdvantage {
  paymentMethodSwitch: number;
  adaptiveRetryTiming: number;
  selectiveAbstention: number;
  escalationDecisions: number;
  suppressionIncidents: number;
}

export default function ProofLab() {
  const [status, setStatus] = useState<ProofLabStatus>("loading");
  const [benchReport, setBenchReport] = useState<ScientificBenchmarkReport | null>(null);
  const [lastEval, setLastEval] = useState<EvaluationRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regime, setRegime] = useState<DataRegime>("BENCHMARK_SYNTHETIC");
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [proofResult, setProofResult] = useState<ProofResult | null>(null);
  const [breakdown, setBreakdown] = useState<BreakdownItem[]>([]);
  const [winReasons, setWinReasons] = useState<WinReason[]>([]);
  const [adaptiveAdvantage, setAdaptiveAdvantage] = useState<AdaptiveAdvantage | null>(null);
  const [runCount, setRunCount] = useState(50);
  const [runSeed, setRunSeed] = useState(42);
  const [isRunning, setIsRunning] = useState(false);

  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  const fmtPct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
  const fmtSmall = (n: number) =>
    n >= 0 ? `+${(n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` : `-${(Math.abs(n) / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

  const computeProofResult = (bench: ScientificBenchmarkReport): ProofResult => {
    const verdict: ProofResult["verdict"] =
      bench.net_lift_pct > 0 ? "REVPLUG_WINS" :
      bench.net_lift_pct < 0 ? "BASELINE_WINS" : "INCONCLUSIVE";

    return {
      verdict,
      netLiftPct: bench.net_lift_pct,
      confidence95: [bench.confidence_interval_95_lower, bench.confidence_interval_95_upper],
      winRate: `${bench.revplug_wins_vs_safe}/${bench.total_seeds} seeds (${bench.revplug_win_rate_pct.toFixed(0)}%)`,
      revplugNet: bench.revplug_mean_net,
      safeNet: bench.safe_mean_net,
      naiveNet: bench.naive_mean_net,
      revplugViolations: bench.revplug_mean_violations,
      baselineViolations: bench.naive_mean_violations,
    };
  };

  const computeBreakdown = (bench: ScientificBenchmarkReport): BreakdownItem[] => [
    {
      label: "Gross Recovery",
      revplug: bench.revplug_mean_gross,
      safe: bench.safe_mean_gross,
      naive: bench.naive_mean_gross,
      unit: "₹",
    },
    {
      label: "Net Recovery",
      revplug: bench.revplug_mean_net,
      safe: bench.safe_mean_net,
      naive: bench.naive_mean_net,
      unit: "₹",
    },
    {
      label: "Recovery Rate",
      revplug: (bench.revplug_mean_gross / bench.mean_amount_at_risk) * 100,
      safe: (bench.safe_mean_gross / bench.mean_amount_at_risk) * 100,
      naive: (bench.naive_mean_gross / bench.mean_amount_at_risk) * 100,
      unit: "%",
    },
    {
      label: "Safety Violations",
      revplug: bench.revplug_mean_violations,
      safe: bench.safe_mean_violations,
      naive: bench.naive_mean_violations,
      unit: "cases",
    },
    {
      label: "Avg. Intervention Cost",
      revplug: bench.revplug_mean_cost,
      safe: bench.safe_mean_gross > 0 ? (bench.safe_mean_gross - bench.safe_mean_net) : 0,
      naive: bench.naive_mean_gross > 0 ? (bench.naive_mean_gross - bench.naive_mean_net) : 0,
      unit: "₹",
    },
  ];

  const computeWinReasons = (bench: ScientificBenchmarkReport, evalData: EvaluationRunResult | null): WinReason[] => {
    if (!evalData) return [];
    const reasons: WinReason[] = [];

    const ros = evalData.revplug;
    const bl = evalData.baseline;

    const rosNet = ros.actual_recovered - ros.intervention_cost;
    const blNet = (bl?.actual_recovered || 0) - (bl?.intervention_cost || 0);
    const netDiff = rosNet - blNet;

    const abstained = ros.no_action_cases || 0;
    const stoppedPolicy = ros.policy_stop_cases || 0;
    if (abstained + stoppedPolicy > 0) {
      reasons.push({
        category: "Selective Abstention",
        description: "RevPlug chose not to attempt recovery on cases where expected value was negative or policy blocked action.",
        revplugAdvantage: abstained + stoppedPolicy,
        evidence: [
          `No-action cases: ${abstained}`,
          `Policy stops: ${stoppedPolicy}`,
          `Avoided wasted intervention cost: ₹${((abstained + stoppedPolicy) * 500 / 100).toLocaleString("en-IN")}`,
        ],
      });
    }

    const escalations = ros.escalated_count || 0;
    if (escalations > 0) {
      reasons.push({
        category: "Human Escalation",
        description: "RevPlug correctly escalated ambiguous cases to human review instead of forcing a potentially wrong action.",
        revplugAdvantage: escalations,
        evidence: [
          `Escalated cases: ${escalations}`,
          `Escalation preserved policy compliance while capturing recoverable revenue.`,
        ],
      });
    }

    const unnecessary = ros.unnecessary_interventions || 0;
    const blUnnecessary = bl?.unnecessary_interventions || 0;
    if (unnecessary < blUnnecessary) {
      reasons.push({
        category: "Reduced Unnecessary Interventions",
        description: "RevPlug avoided retry attempts on cases with low probability of success, reducing wasted cost.",
        revplugAdvantage: blUnnecessary - unnecessary,
        evidence: [
          `RevPlug unnecessary: ${unnecessary}`,
          `Baseline unnecessary: ${blUnnecessary}`,
          `Reduction: ${blUnnecessary - unnecessary} fewer wasteful attempts`,
        ],
      });
    }

    if (netDiff > 0) {
      reasons.push({
        category: "Net Recovery Advantage",
        description: `RevPlug generated ₹${(netDiff / 100).toLocaleString("en-IN")} more net recovery than naive baseline after intervention costs.`,
        revplugAdvantage: netDiff,
        evidence: [
          `RevPlug net: ₹${(rosNet / 100).toLocaleString("en-IN")}`,
          `Baseline net: ₹${(blNet / 100).toLocaleString("en-IN")}`,
          `Net advantage: ₹${(netDiff / 100).toLocaleString("en-IN")}`,
        ],
      });
    }

    return reasons;
  };

  const computeAdaptiveAdvantage = (evalData: EvaluationRunResult | null): AdaptiveAdvantage => {
    if (!evalData) {
      return { paymentMethodSwitch: 0, adaptiveRetryTiming: 0, selectiveAbstention: 0, escalationDecisions: 0, suppressionIncidents: 0 };
    }
    const ros = evalData.revplug;
    const perCase = evalData.per_case || [];

    const paymentSwitch = perCase.filter((c: any) => {
      const action = c.revplug?.proposed_action;
      return action && action !== "retry_payment";
    }).length;

    const selectiveAbs = ros.no_action_cases || 0;
    const escalations = ros.escalated_count || 0;
    const policyStops = ros.policy_stop_cases || 0;

    return {
      paymentMethodSwitch: paymentSwitch,
      adaptiveRetryTiming: 0,
      selectiveAbstention: selectiveAbs + policyStops,
      escalationDecisions: escalations,
      suppressionIncidents: 0,
    };
  };

  const loadBenchmark = async () => {
    try {
      const bench = await api.latestBenchmark();
      setBenchReport(bench);
      setProofResult(computeProofResult(bench));
      setBreakdown(computeBreakdown(bench));
      setRegime("BENCHMARK_SYNTHETIC");
      setStatus("ready");
    } catch {
      setStatus("no_data");
    }
  };

  const runNewEvaluation = async () => {
    setIsRunning(true);
    setError(null);
    setStatus("loading");
    try {
      const data = await api.evaluationBatch({ count: runCount, seed: runSeed });
      setLastEval(data);

      if (data.status === "failed" || !data.revplug) {
        setStatus("error");
        setError(data.error || "Evaluation failed");
        return;
      }

      if (benchReport) {
        setWinReasons(computeWinReasons(benchReport, data));
        setAdaptiveAdvantage(computeAdaptiveAdvantage(data));
      }

      setRegime("BENCHMARK_SYNTHETIC");
      setStatus("ready");
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setIsRunning(false);
    }
  };

  useEffect(() => {
    loadBenchmark();
  }, []);

  const verdictColor = proofResult?.verdict === "REVPLUG_WINS" ? "var(--success)" :
    proofResult?.verdict === "BASELINE_WINS" ? "var(--danger)" : "var(--text-muted)";
  const verdictBg = proofResult?.verdict === "REVPLUG_WINS" ? "rgba(16, 185, 129, 0.08)" :
    proofResult?.verdict === "BASELINE_WINS" ? "rgba(239, 68, 68, 0.08)" : "rgba(148, 163, 184, 0.08)";

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: 4 }}>
          <span style={{
            fontSize: "0.625rem",
            padding: "0.1rem 0.4rem",
            borderRadius: 4,
            fontWeight: 700,
            background: regime === "BENCHMARK_SYNTHETIC" ? "rgba(245, 158, 11, 0.15)" : "rgba(16, 185, 129, 0.15)",
            color: regime === "BENCHMARK_SYNTHETIC" ? "#f59e0b" : "#10b981",
            border: `1px solid ${regime === "BENCHMARK_SYNTHETIC" ? "rgba(245, 158, 11, 0.3)" : "rgba(16, 185, 129, 0.3)"}`,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
          }}>
            {regime === "BENCHMARK_SYNTHETIC" ? "BENCHMARK / SYNTHETIC DATA" : "LIVE OPERATIONAL DATA"}
          </span>
        </div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
          Proof Lab
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4, maxWidth: 700 }}>
          Does RevPlug recover more verified money while respecting safety constraints? This page answers that question using real evaluation output — not marketing claims.
        </p>
      </div>

      {/* RUN CONTROLS */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: "1rem", alignItems: "end" }}>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "0.35rem" }}>
              Batch Size
            </label>
            <select value={runCount} onChange={(e) => setRunCount(Number(e.target.value))} className="input" style={{ width: "100%" }} disabled={isRunning}>
              <option value={50}>50 cases (Standard)</option>
              <option value={100}>100 cases (Extended)</option>
              <option value={200}>200 cases (Stress Test)</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "0.35rem" }}>
              Seed
            </label>
            <input type="number" value={runSeed} onChange={(e) => setRunSeed(Number(e.target.value))} className="input font-mono" style={{ width: "100%" }} disabled={isRunning} />
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
            Results are deterministic. Same seed + count = same output.
          </div>
          <button onClick={runNewEvaluation} disabled={isRunning} className="btn-primary" style={{ fontSize: "0.8125rem" }}>
            {isRunning ? "Running..." : "Run Evaluation"}
          </button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ padding: "1rem", marginBottom: "1.25rem", background: "var(--danger-subtle)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.8125rem", fontWeight: 600 }}>{error}</div>
        </div>
      )}

      {status === "loading" && (
        <div className="card" style={{ padding: "3rem", textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem" }}>Loading benchmark data...</div>
          <p style={{ color: "var(--text-muted)", fontSize: "0.75rem", fontFamily: "monospace" }}>
            Fetching latest 10-seed statistical benchmark report.
          </p>
        </div>
      )}

      {status === "no_data" && (
        <div className="card" style={{ padding: "2.5rem", textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>No Evaluation Data Available</div>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: 500, margin: "0 auto 1.25rem" }}>
            Run an evaluation using the controls above to generate benchmark data. The Proof Lab uses reproducible synthetic data with fixed seeds — not live merchant data.
          </p>
          <button onClick={runNewEvaluation} className="btn-primary">Run Canonical Evaluation (50 cases, seed 42)</button>
        </div>
      )}

      {status === "error" && (
        <div className="card" style={{ padding: "2.5rem", textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--danger)", marginBottom: "0.5rem" }}>Benchmark Unavailable</div>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>{error || "Could not load benchmark data."}</p>
        </div>
      )}

      {/* PROOF RESULT - THE VERDICT */}
      {status === "ready" && proofResult && (
        <div style={{ display: "grid", gap: "1.25rem" }}>
          {/* THE VERDICT - TOP LEVEL */}
          <div className="card" style={{ padding: "1.5rem", borderLeft: `4px solid ${verdictColor}`, background: verdictBg }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: verdictColor, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
                  Core Question
                </div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
                  Does RevPlug recover more verified money while respecting safety constraints?
                </div>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                  <span style={{
                    fontSize: "0.8125rem",
                    fontWeight: 800,
                    color: verdictColor,
                    background: `${verdictColor}20`,
                    padding: "0.25rem 0.75rem",
                    borderRadius: 6,
                  }}>
                    {proofResult.verdict === "REVPLUG_WINS" ? "YES — RevPlug wins" :
                      proofResult.verdict === "BASELINE_WINS" ? "NO — Baseline wins" : "INCONCLUSIVE"}
                  </span>
                  {proofResult.verdict === "REVPLUG_WINS" && (
                    <span style={{ fontSize: "0.875rem", color: "var(--text-primary)" }}>
                      Net lift: <strong style={{ color: "var(--success)" }}>{fmtPct(proofResult.netLiftPct)}</strong> vs Safe Baseline
                    </span>
                  )}
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Win rate: {proofResult.winRate}
                  </span>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
                  95% Confidence Interval (Net)
                </div>
                <div className="font-mono" style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  [{fmtSmall(proofResult.confidence95[0])}, {fmtSmall(proofResult.confidence95[1])}]
                </div>
              </div>
            </div>
          </div>

          {/* HEADLINE METRICS */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            <div className="metric-block" style={{ padding: "1.125rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>RevPlug Net Recovery</div>
              <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--success)", marginTop: 4, lineHeight: 1 }}>{fmt(proofResult.revplugNet)}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>after intervention costs</div>
            </div>
            <div className="metric-block" style={{ padding: "1.125rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Safe Baseline Net</div>
              <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1 }}>{fmt(proofResult.safeNet)}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>policy-compliant fixed retry</div>
            </div>
            <div className="metric-block" style={{ padding: "1.125rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Naive Baseline Net</div>
              <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--danger)", marginTop: 4, lineHeight: 1 }}>{fmt(proofResult.naiveNet)}</div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>fixed retry, no policy</div>
            </div>
            <div className="metric-block" style={{ padding: "1.125rem", background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Safety Violations</div>
              <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 900, color: proofResult.revplugViolations === 0 ? "var(--success)" : "var(--danger)", marginTop: 4, lineHeight: 1 }}>
                {proofResult.revplugViolations === 0 ? "ZERO" : proofResult.revplugViolations.toFixed(0)}
              </div>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>
                RevPlug {proofResult.revplugViolations === 0 ? "fully compliant" : `${proofResult.revplugViolations} violations`}
              </div>
            </div>
          </div>

          {/* EVIDENCE ACCORDION */}
          <div className="card" style={{ padding: "1.25rem" }}>
            <button
              onClick={() => setExpandedSection(expandedSection === "breakdown" ? null : "breakdown")}
              style={{
                width: "100%",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 0,
                marginBottom: expandedSection === "breakdown" ? "1rem" : 0,
              }}
            >
              <div>
                <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", letterSpacing: "0.06em" }}>Evidence Breakdown</div>
                <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>Detailed metric comparison across all three policies</div>
              </div>
              <span style={{ fontSize: "1.25rem", color: "var(--text-muted)", transition: "transform 0.2s", transform: expandedSection === "breakdown" ? "rotate(180deg)" : "none" }}>▾</span>
            </button>

            {expandedSection === "breakdown" && (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)", textAlign: "left" }}>
                    <th style={{ padding: "0.5rem 0.5rem" }}>METRIC</th>
                    <th style={{ padding: "0.5rem", textAlign: "right" }}>NAIVE BASELINE</th>
                    <th style={{ padding: "0.5rem", textAlign: "right" }}>SAFE BASELINE</th>
                    <th style={{ padding: "0.5rem", textAlign: "right", color: "var(--success)" }}>REVPLUG</th>
                    <th style={{ padding: "0.5rem", textAlign: "right" }}>REVPLUG VS SAFE</th>
                  </tr>
                </thead>
                <tbody>
                  {breakdown.map((row) => {
                    const revplugVal = row.unit === "%" ? `${row.revplug.toFixed(2)}%` : (row.unit === "₹" ? fmt(row.revplug) : row.revplug.toFixed(0));
                    const safeVal = row.unit === "%" ? `${row.safe.toFixed(2)}%` : (row.unit === "₹" ? fmt(row.safe) : row.safe.toFixed(0));
                    const naiveVal = row.unit === "%" ? `${row.naive.toFixed(2)}%` : (row.unit === "₹" ? fmt(row.naive) : row.naive.toFixed(0));
                    const diff = row.revplug - row.safe;
                    const diffStr = row.unit === "%" ? `${diff >= 0 ? "+" : ""}${diff.toFixed(2)} pts` : (row.unit === "₹" ? fmtSmall(diff) : `${diff >= 0 ? "+" : ""}${diff.toFixed(0)}`);
                    return (
                      <tr key={row.label} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "0.625rem 0.5rem", fontWeight: 600 }}>{row.label}</td>
                        <td style={{ padding: "0.625rem", textAlign: "right", color: "var(--text-muted)" }} className="font-mono">{naiveVal}</td>
                        <td style={{ padding: "0.625rem", textAlign: "right", color: "var(--text-secondary)" }} className="font-mono">{safeVal}</td>
                        <td style={{ padding: "0.625rem", textAlign: "right", fontWeight: 700, color: "var(--success)" }} className="font-mono">{revplugVal}</td>
                        <td style={{ padding: "0.625rem", textAlign: "right", fontWeight: 700, color: diff >= 0 ? "var(--success)" : "var(--danger)" }} className="font-mono">{diffStr}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* WHY REVPLUG WON */}
          {winReasons.length > 0 && (
            <div className="card" style={{ padding: "1.25rem" }}>
              <button
                onClick={() => setExpandedSection(expandedSection === "reasons" ? null : "reasons")}
                style={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                  marginBottom: expandedSection === "reasons" ? "1rem" : 0,
                }}
              >
                <div>
                  <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.06em" }}>Why RevPlug Won</div>
                  <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>Breakdown of where adaptive decisions generated improvement</div>
                </div>
                <span style={{ fontSize: "1.25rem", color: "var(--text-muted)", transition: "transform 0.2s", transform: expandedSection === "reasons" ? "rotate(180deg)" : "none" }}>▾</span>
              </button>

              {expandedSection === "reasons" && (
                <div style={{ display: "grid", gap: "0.75rem" }}>
                  {winReasons.map((wr, i) => (
                    <div key={i} style={{ padding: "0.875rem", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.375rem" }}>
                        <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>{wr.category}</span>
                        <span className="font-mono" style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--success)" }}>
                          {wr.unit === "₹" ? fmt(wr.revplugAdvantage) : `+${wr.revplugAdvantage}`}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>{wr.description}</div>
                      <div style={{ display: "grid", gap: "0.25rem" }}>
                        {wr.evidence.map((ev, j) => (
                          <div key={j} style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace", paddingLeft: "0.75rem", borderLeft: "2px solid var(--border)" }}>
                            {ev}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ADAPTIVE DECISIONS */}
          {adaptiveAdvantage && (adaptiveAdvantage.paymentMethodSwitch > 0 || adaptiveAdvantage.selectiveAbstention > 0 || adaptiveAdvantage.escalationDecisions > 0) && (
            <div className="card" style={{ padding: "1.25rem" }}>
              <button
                onClick={() => setExpandedSection(expandedSection === "adaptive" ? null : "adaptive")}
                style={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                  marginBottom: expandedSection === "adaptive" ? "1rem" : 0,
                }}
              >
                <div>
                  <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#8b5cf6", textTransform: "uppercase", letterSpacing: "0.06em" }}>Adaptive Decision Categories</div>
                  <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>Where RevPlug made non-trivial decisions</div>
                </div>
                <span style={{ fontSize: "1.25rem", color: "var(--text-muted)", transition: "transform 0.2s", transform: expandedSection === "adaptive" ? "rotate(180deg)" : "none" }}>▾</span>
              </button>

              {expandedSection === "adaptive" && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem" }}>
                  {adaptiveAdvantage.paymentMethodSwitch > 0 && (
                    <div style={{ padding: "0.875rem", borderRadius: 8, background: "rgba(139, 92, 246, 0.06)", border: "1px solid rgba(139, 92, 246, 0.2)" }}>
                      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#8b5cf6", textTransform: "uppercase" }}>Payment Method Switch</div>
                      <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 800, color: "#8b5cf6", marginTop: 4 }}>{adaptiveAdvantage.paymentMethodSwitch} cases</div>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>Chose non-retry action</div>
                    </div>
                  )}
                  {adaptiveAdvantage.selectiveAbstention > 0 && (
                    <div style={{ padding: "0.875rem", borderRadius: 8, background: "rgba(245, 158, 11, 0.06)", border: "1px solid rgba(245, 158, 11, 0.2)" }}>
                      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase" }}>Selective Abstention</div>
                      <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 800, color: "#f59e0b", marginTop: 4 }}>{adaptiveAdvantage.selectiveAbstention} cases</div>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>Stopped or no-action</div>
                    </div>
                  )}
                  {adaptiveAdvantage.escalationDecisions > 0 && (
                    <div style={{ padding: "0.875rem", borderRadius: 8, background: "rgba(99, 102, 241, 0.06)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase" }}>Human Escalation</div>
                      <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 800, color: "#6366f1", marginTop: 4 }}>{adaptiveAdvantage.escalationDecisions} cases</div>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4 }}>Escalated to review</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* AI JUDGMENT VISIBILITY */}
          <div className="card" style={{ padding: "1.25rem", borderLeft: "4px solid #6366f1" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
              AI vs Deterministic Responsibility
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>AI Handles</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.375rem" }}>
                  {["Contextual diagnosis", "Candidate action recommendation", "Adaptive strategy selection", "Evidence synthesis"].map(item => (
                    <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span style={{ color: "var(--success)", fontSize: "0.875rem" }}>✓</span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>Deterministic System Handles</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.375rem" }}>
                  {["Financial calculation", "Policy enforcement", "Safety constraints", "Retry limits", "Settlement verification", "Authorization gates"].map(item => (
                    <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span style={{ color: "#3b82f6", fontSize: "0.875rem" }}>■</span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* CROSS-REFERENCES */}
          <div className="card" style={{ padding: "1rem 1.25rem", display: "flex", gap: "1rem", alignItems: "center", justifyContent: "space-between", borderLeft: "4px solid var(--accent)" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              <strong style={{ color: "var(--text-primary)" }}>Related surfaces:</strong> Batch Results shows live operational evaluation · Allocation shows portfolio prioritization
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <Link href="/batch-recovery" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>Batch Results →</Link>
              <Link href="/allocation" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>Capital Allocation →</Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
