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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.benchmarkSummary()
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  const ss = data?.single_seed || {};
  const evalId = data?.evaluation_id || "REC-CANONICAL-2026-S42-C50";
  const singleLabel = data?.single_seed_label || "Seed 42 (50 cases)";
  const totalAtRisk = (ss.total_amount_at_risk as number) || 0;
  const revplugRecovered = (ss.actual_recovered as number) || 0;
  const baselineRecovered = (ss.baseline_actual_recovered as number) || 0;
  const incrementalGain = (ss.absolute_recovery_difference as number) || 0;
  const revplugActions = ss.total_interventions as number | undefined;
  const baselineActions = ss.total_interventions as number | undefined;
  const revplugViolations = (ss.safety_violations as number) ?? 0;
  const baselineViolations = (ss.baseline_policy_violations as number) ?? 0;

  const hasData = !loading && !error && (totalAtRisk > 0 || revplugRecovered > 0);

  return (
    <section style={{ padding: "4rem 0" }}>
      {/* SECTION HEADER WITH CLEAR DATA PROVENANCE BADGE */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem", flexWrap: "wrap" }}>
            <span
              style={{
                fontSize: "0.625rem",
                padding: "0.15rem 0.45rem",
                borderRadius: 4,
                background: "rgba(99, 102, 241, 0.12)",
                color: "#6366f1",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              BENCHMARK / SYNTHETIC
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              Seeded counterfactual evaluation — not live merchant revenue
            </span>
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            Measured across a seeded evaluation batch.
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Identical test cases. Identical starting state. Comparing naive retries against policy-bounded recovery.
          </p>
        </div>

        <Link href="/proof-lab" style={{ fontSize: "0.8125rem", color: "var(--accent)", textDecoration: "none", fontWeight: 600 }} className="hidden-mobile">
          Open Proof Lab →
        </Link>
      </div>

      {/* BENCHMARK COMPARISON TABLE */}
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 8,
          background: "var(--bg-primary)",
          overflow: "hidden",
        }}
      >
        {loading ? (
          <div style={{ padding: "2.5rem 1.5rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div className="skeleton" style={{ height: 24, width: "30%" }} />
            <div className="skeleton" style={{ height: 40, width: "100%" }} />
            <div className="skeleton" style={{ height: 40, width: "100%" }} />
            <div className="skeleton" style={{ height: 40, width: "100%" }} />
          </div>
        ) : error ? (
          <div style={{ padding: "2.5rem 1.5rem", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
            <div style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>Benchmark data unavailable</div>
            <Link href="/proof-lab" style={{ color: "var(--accent)", fontWeight: 600 }}>
              Run batch evaluation in Proof Lab →
            </Link>
          </div>
        ) : !hasData ? (
          <div style={{ padding: "2.5rem 1.5rem", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
            No evaluation report loaded. Visit the Proof Lab to execute seeded benchmarks.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-secondary)", color: "var(--text-muted)", fontSize: "0.75rem" }}>
                <th style={{ padding: "0.875rem 1.25rem", textAlign: "left" }}>METRIC</th>
                <th style={{ padding: "0.875rem 1.25rem", textAlign: "right" }}>FIXED RETRY BASELINE</th>
                <th style={{ padding: "0.875rem 1.25rem", textAlign: "right" }}>REVPLUG ENGINE</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "var(--text-primary)", fontWeight: 600 }}>Amount at risk</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--text-secondary)" }}>{fmt(totalAtRisk)}</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--text-primary)", fontWeight: 700 }}>{fmt(totalAtRisk)}</td>
              </tr>

              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "var(--text-primary)", fontWeight: 600 }}>Evaluated recovery</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--text-secondary)" }}>{fmt(baselineRecovered)}</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--success)", fontWeight: 700 }}>{fmt(revplugRecovered)}</td>
              </tr>

              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "var(--text-primary)", fontWeight: 600 }}>Recovery rate</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--text-secondary)" }}>
                  {totalAtRisk > 0 ? ((baselineRecovered / totalAtRisk) * 100).toFixed(1) + "%" : "—"}
                </td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--success)", fontWeight: 700 }}>
                  {totalAtRisk > 0 ? ((revplugRecovered / totalAtRisk) * 100).toFixed(1) + "%" : "—"}
                </td>
              </tr>

              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "var(--text-primary)", fontWeight: 600 }}>Incremental recovery lift</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--text-muted)" }}>—</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--success)", fontWeight: 700 }}>
                  {incrementalGain > 0 ? "+" + fmt(incrementalGain) : "—"}
                </td>
              </tr>

              <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "0.875rem 1.25rem", color: "var(--text-primary)", fontWeight: 600 }}>Interventions executed</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--text-secondary)" }}>
                  {baselineActions != null ? (baselineActions as number).toLocaleString() + " actions" : "—"}
                </td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--text-primary)", fontWeight: 600 }}>
                  {revplugActions != null ? (revplugActions as number).toLocaleString() + " actions" : "—"}
                </td>
              </tr>

              <tr>
                <td style={{ padding: "0.875rem 1.25rem", color: "var(--text-primary)", fontWeight: 600 }}>Unsafe policy violations</td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--danger)", fontWeight: 700 }}>
                  {baselineViolations != null ? baselineViolations.toLocaleString() + " violations" : "—"}
                </td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "var(--success)", fontWeight: 700 }}>
                  {revplugViolations != null ? revplugViolations.toLocaleString() + " violations" : "—"}
                </td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* FOOTNOTE */}
      {hasData && (
        <div style={{ marginTop: "0.75rem", fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
          Run ID: <span style={{ color: "var(--text-secondary)" }}>{evalId}</span>
          {" · "}
          Dataset: <span style={{ color: "var(--text-secondary)" }}>{singleLabel}</span>
          {" · "}
          Source: <span style={{ color: "var(--text-secondary)" }}>{data?.source || "evaluation_report.json"}</span>
        </div>
      )}
    </section>
  );
}
