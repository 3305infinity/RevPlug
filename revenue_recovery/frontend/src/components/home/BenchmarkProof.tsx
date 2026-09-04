"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api";

const fmt = (n: number) =>
  "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

interface BenchmarkSummary {
  source: string;
  evaluation_id: string;
  seed: number;
  count: number;
  status: string;
  dataset_version: string;
  evaluation_mode: string;
  single_seed_label: string;
  multi_seed_label: string;
  single_seed: Record<string, unknown>;
  multi_seed: Record<string, unknown>;
}

export default function BenchmarkProof() {
  const [data, setData] = useState<BenchmarkSummary | null>(null);

  useEffect(() => {
    api.benchmarkSummary()
      .then(setData)
      .catch(() => {});
  }, []);

  const ss = data?.single_seed || {};
  const ms = data?.multi_seed || {};

  const evalId = data?.evaluation_id || "REC-CANONICAL-2026-S42-C50";
  const seed = data?.seed ?? 42;
  const singleLabel = data?.single_seed_label || `Seed 42 (50 cases)`;
  const multiLabel = data?.multi_seed_label || "10 seeds (100 cases/seed, 1000 total)";
  const totalAtRisk = (ss.total_amount_at_risk as number) || 0;
  const revplugRecovered = (ss.actual_recovered as number) || 0;
  const baselineRecovered = (ss.baseline_actual_recovered as number) || 0;
  const incrementalGain = (ss.absolute_recovery_difference as number) || 0;
  const revplugActions = ss.total_interventions as number | undefined;
  const baselineActions = ss.total_interventions as number | undefined;
  const revplugViolations = (ss.safety_violations as number) ?? 0;
  const baselineViolations = (ss.baseline_policy_violations as number) ?? 0;

  const hasData = totalAtRisk > 0 || revplugRecovered > 0;

  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d" }}>
      {/* SECTION HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
            <span style={{ fontSize: "0.625rem", padding: "0.1rem 0.4rem", borderRadius: 4, background: "rgba(99, 102, 241, 0.15)", color: "#6366f1", fontWeight: 700, textTransform: "uppercase" }}>
              SEEDED COUNTERFACTUAL EVALUATION ({evalId})
            </span>
            <span style={{ fontSize: "0.6875rem", color: "#6e7681", fontFamily: "monospace" }}>
              {singleLabel} · {data?.dataset_version || "v2-counterfactual"}
            </span>
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
            Measured across a batch.
          </h2>
          <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
            Same seeded cases. Same starting conditions. Different decision system.
          </p>
        </div>

        <Link href="/proof-lab" style={{ fontSize: "0.8125rem", color: "#2563eb", textDecoration: "none", fontWeight: 600 }}>
          Open Proof Lab →
        </Link>
      </div>

      {/* BENCHMARK COMPARISON TABLE */}
      <div
        style={{
          border: "1px solid #21262d",
          borderRadius: 8,
          background: "#0d1117",
          overflow: "hidden",
        }}
      >
        {!hasData ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#8b949e", fontSize: "0.875rem" }}>
            No benchmark evaluation has been executed yet. Run an evaluation to see comparative results here.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #21262d", background: "#161b22", color: "#6e7681", fontSize: "0.75rem" }}>
                <th style={{ padding: "0.875rem 1.25rem", textAlign: "left" }}>METRIC</th>
                <th style={{ padding: "0.875rem 1.25rem", textAlign: "right" }}>FIXED RETRY BASELINE</th>
                <th style={{ padding: "0.875rem 1.25rem", textAlign: "right" }}>REVPLUG ENGINE</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid #21262d" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "#f0f6fc", fontWeight: 600 }}>Amount at risk</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#8b949e" }}>{fmt(totalAtRisk)}</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#f0f6fc", fontWeight: 700 }}>{fmt(totalAtRisk)}</td>
              </tr>

              <tr style={{ borderBottom: "1px solid #21262d" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "#f0f6fc", fontWeight: 600 }}>Verified recovery</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#8b949e" }}>{fmt(baselineRecovered)}</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#10b981", fontWeight: 700 }}>{fmt(revplugRecovered)}</td>
              </tr>

              <tr style={{ borderBottom: "1px solid #21262d" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "#f0f6fc", fontWeight: 600 }}>Recovery rate</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#8b949e" }}>
                  {totalAtRisk > 0 ? ((baselineRecovered / totalAtRisk) * 100).toFixed(1) + "%" : "—"}
                </td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#10b981", fontWeight: 700 }}>
                  {totalAtRisk > 0 ? ((revplugRecovered / totalAtRisk) * 100).toFixed(1) + "%" : "—"}
                </td>
              </tr>

              <tr style={{ borderBottom: "1px solid #21262d" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "#f0f6fc", fontWeight: 600 }}>Incremental recovery</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#6e7681" }}>—</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#10b981", fontWeight: 700 }}>
                  {incrementalGain > 0 ? "+" + fmt(incrementalGain) : "—"}
                </td>
              </tr>

              <tr style={{ borderBottom: "1px solid #21262d" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "#f0f6fc", fontWeight: 600 }}>Interventions executed</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#8b949e" }}>
                  {baselineActions != null ? (baselineActions as number).toLocaleString() + " actions" : "—"}
                </td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#f0f6fc", fontWeight: 600 }}>
                  {revplugActions != null ? (revplugActions as number).toLocaleString() + " actions" : "—"}
                </td>
              </tr>

              <tr>
                <td style={{ padding: "0.875rem 1.25rem", color: "#f0f6fc", fontWeight: 600 }}>Unsafe actions executed</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#ef4444", fontWeight: 700 }}>
                  {baselineViolations != null ? baselineViolations.toLocaleString() + " violations" : "—"}
                </td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#10b981", fontWeight: 700 }}>
                  {revplugViolations != null ? revplugViolations.toLocaleString() + " violations" : "—"}
                </td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* DATA PROVENANCE NOTE */}
      {hasData && (
        <div style={{ marginTop: "0.75rem", fontSize: "0.6875rem", color: "#6e7681", fontFamily: "monospace" }}>
          Source: <span style={{ color: "#8b949e" }}>{data?.source || "evaluation_report.json"}</span>
          {" · "}
          Evaluation mode: <span style={{ color: "#8b949e" }}>{data?.evaluation_mode || "AI_ASSISTED"}</span>
          {" · "}
          Dataset: <span style={{ color: "#8b949e" }}>{data?.dataset_version || "v2-counterfactual"}</span>
        </div>
      )}
    </div>
  );
}
