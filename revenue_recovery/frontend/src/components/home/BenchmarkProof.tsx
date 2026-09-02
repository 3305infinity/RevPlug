"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const fmt = (n: number) =>
  "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

export default function BenchmarkProof() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/evaluations/canonical`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, []);

  const evalId = data?.canonical_metadata?.evaluation_id || "REC-BENCH-2026-S42-C50";
  const seed = data?.canonical_metadata?.seed || 42;
  const totalAtRisk = data?.revplug?.total_amount_at_risk || 0;
  const revplugRecovered = data?.revplug?.actual_recovered || 0;
  const baselineRecovered = data?.baseline?.actual_recovered || 0;
  const incrementalGain = revplugRecovered - baselineRecovered;
  const revplugActions = data?.revplug?.actions_executed;
  const baselineActions = data?.baseline?.actions_executed;
  const revplugViolations = data?.revplug?.policy_violations_count ?? data?.revplug?.safety_violations;
  const baselineViolations = data?.baseline?.policy_violations_count ?? data?.baseline?.safety_violations;

  const hasData = totalAtRisk > 0 || revplugRecovered > 0;

  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d" }}>
      {/* SECTION HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
            <span style={{ fontSize: "0.625rem", padding: "0.1rem 0.4rem", borderRadius: 4, background: "rgba(99, 102, 241, 0.15)", color: "#6366f1", fontWeight: 700, textTransform: "uppercase" }}>
              CANONICAL BENCHMARK ({evalId})
            </span>
            <span style={{ fontSize: "0.6875rem", color: "#6e7681", fontFamily: "monospace" }}>
              Seed: {seed} · Golden Synthetic Dataset v1
            </span>
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
            Measured across a batch.
          </h2>
          <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
            Same cases. Same starting conditions. Different decision system.
          </p>
        </div>

        <Link href="/batch-recovery" style={{ fontSize: "0.8125rem", color: "#2563eb", textDecoration: "none", fontWeight: 600 }}>
          Inspect batch analytics →
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
                  {baselineActions != null ? baselineActions.toLocaleString() + " actions" : "—"}
                </td>
                <td className="font-mono" style={{ padding: "0.875rem 1.25rem", textAlign: "right", color: "#f0f6fc", fontWeight: 600 }}>
                  {revplugActions != null ? revplugActions.toLocaleString() + " actions" : "—"}
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
    </div>
  );
}
