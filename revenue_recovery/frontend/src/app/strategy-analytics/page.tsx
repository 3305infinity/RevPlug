"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface StrategyRow {
  action: string;
  label: string;
  attempts_count: number;
  recovered_amount_minor: number;
  success_rate_pct: number;
  average_cost_minor: number;
}

interface FinancialKPIs {
  total_revenue_at_risk_minor?: number;
  revenue_recovered_minor?: number;
  net_revenue_recovered_minor?: number;
  recovery_rate_pct?: number;
  average_recovery_per_case_minor?: number;
  intervention_cost_minor?: number;
  cost_per_recovered_rupee?: number;
}

interface CalibrationSample {
  case_id: string;
  action: string;
  expected_recovery_minor: number;
  actual_recovery_minor: number;
  prediction_error_pct: number;
  outcome: string;
}

interface CalibrationMetrics {
  mean_absolute_error_pct?: number | null;
  calibration_ratio?: number | null;
  brier_score?: number | null;
  prediction_vs_reality_samples?: CalibrationSample[];
}

interface RevenueLostReason {
  reason_code: string;
  reason_label: string;
  lost_amount_minor: number;
  cases_count: number;
  actionable_recommendation: string;
}

interface AnalyticsReport {
  total_historical_cases: number;
  strategies: StrategyRow[];
  opportunity_signals: string[];
  financial_kpis?: FinancialKPIs;
  calibration_metrics?: CalibrationMetrics;
  revenue_lost_reasons?: RevenueLostReason[];
  generated_at: string;
}

export default function StrategyAnalyticsPage() {
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    fetch(`${apiHost}/api/strategy-analytics`)
      .then((r) => r.json())
      .then((data) => {
        setReport(data);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  const fmt = (minor: number) => "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 56, marginBottom: "1.5rem" }} />
        <div className="skeleton" style={{ height: 180, marginBottom: "1.5rem" }} />
        <div className="skeleton" style={{ height: 280 }} />
      </div>
    );
  }

  if (status === "error" || !report) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load strategy analytics</div>
      </div>
    );
  }

  const kpis = report.financial_kpis || {};
  const calib = report.calibration_metrics || {};
  const hasData = (report.total_historical_cases ?? 0) > 0;
  const hasVerifiedOutcomes = (kpis.revenue_recovered_minor ?? 0) > 0;

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", paddingBottom: "3rem" }}>

      {/* ── HEADER ── */}
      <div style={{ marginBottom: "2rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
          Intelligence · Strategy Analytics
        </div>
        <h1 style={{ marginTop: 4, fontSize: "1.375rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
          Recovery Strategy Performance
        </h1>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
          {report.total_historical_cases.toLocaleString()} cases · outcomes from verified recovery records
        </div>
      </div>

      {!hasData ? (
        <div className="card" style={{ padding: "3rem 2rem", textAlign: "center" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.5rem" }}>
            No verified strategy outcomes yet
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", maxWidth: 480, margin: "0 auto", lineHeight: 1.6 }}>
            Run recovery cases through the operational pipeline. Strategy performance,
            calibration metrics, and revenue leakage diagnostics will appear here
            as cases reach verified outcomes (recovered, stopped, or escalated).
          </p>
          <div style={{ marginTop: "1.5rem" }}>
            <Link href="/recovery" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
              Go to Recovery Queue
            </Link>
          </div>
        </div>
      ) : (
        <>

        {/* ── 1. OVERALL RECOVERY INTELLIGENCE ── */}
        <div style={{ marginBottom: "2rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Overall Recovery Intelligence
          </div>
          <div className="card" style={{ padding: "1.25rem" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0" }}>
              <div style={{ paddingRight: "1.5rem", borderRight: "1px solid var(--border)" }}>
                <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Revenue at Risk
                </div>
                <div className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: "#ef4444", marginTop: 4 }}>
                  {fmt(kpis.total_revenue_at_risk_minor ?? 0)}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  Across {report.total_historical_cases} cases
                </div>
              </div>
              <div style={{ padding: "0 1.5rem", borderRight: "1px solid var(--border)" }}>
                <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Verified Recovered
                </div>
                <div className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: "#10b981", marginTop: 4 }}>
                  {hasVerifiedOutcomes ? fmt(kpis.revenue_recovered_minor ?? 0) : "—"}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {hasVerifiedOutcomes ? `${kpis.recovery_rate_pct ?? 0}% of at-risk revenue` : "No verified recoveries yet"}
                </div>
              </div>
              <div style={{ paddingLeft: "1.5rem" }}>
                <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Net Recovered
                </div>
                <div className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: hasVerifiedOutcomes ? "#10b981" : "var(--text-muted)", marginTop: 4 }}>
                  {hasVerifiedOutcomes ? fmt(kpis.net_revenue_recovered_minor ?? 0) : "—"}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {hasVerifiedOutcomes
                    ? `After ${fmt(kpis.intervention_cost_minor ?? 0)} intervention cost`
                    : "Awaiting outcomes"}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── 2. STRATEGY COMPARISON ── */}
        <div style={{ marginBottom: "2rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Strategy Comparison
            </div>
            {report.strategies.length > 0 && (
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                {report.strategies.length} strategy{report.strategies.length !== 1 ? "ies" : ""} with verified outcomes
              </div>
            )}
          </div>

          {report.strategies.length === 0 ? (
            <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
              <div style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                No strategy outcomes recorded yet. Strategies will appear here once recovery actions are executed and outcomes verified.
              </div>
            </div>
          ) : (
            <div className="card" style={{ overflow: "hidden" }}>
              <table className="ops-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th style={{ textAlign: "right" }}>Attempts</th>
                    <th style={{ textAlign: "right" }}>Verified Recovered</th>
                    <th style={{ textAlign: "right" }}>Success Rate</th>
                    <th style={{ textAlign: "right" }}>Avg Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {report.strategies.map((row) => (
                    <tr key={row.action}>
                      <td style={{ fontWeight: 600 }}>{row.label}</td>
                      <td style={{ textAlign: "right", fontFamily: "monospace" }}>{row.attempts_count.toLocaleString()}</td>
                      <td style={{ textAlign: "right", fontFamily: "monospace", fontWeight: 700, color: row.recovered_amount_minor > 0 ? "#10b981" : "var(--text-muted)" }}>
                        {row.recovered_amount_minor > 0 ? fmt(row.recovered_amount_minor) : "—"}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <span style={{
                          fontFamily: "monospace",
                          fontWeight: 700,
                          color: row.success_rate_pct >= 50 ? "#10b981" : row.success_rate_pct >= 20 ? "#f59e0b" : "var(--text-muted)",
                        }}>
                          {row.success_rate_pct}%
                        </span>
                      </td>
                      <td style={{ textAlign: "right", fontFamily: "monospace", color: "var(--text-muted)" }}>
                        {fmt(row.average_cost_minor)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── 3. EVIDENCE ── */}
        {(calib.prediction_vs_reality_samples && calib.prediction_vs_reality_samples.length > 0) && (
          <div style={{ marginBottom: "2rem" }}>
            <button
              onClick={() => setExpandedSection(expandedSection === "calibration" ? null : "calibration")}
              style={{
                background: "none", border: "none", padding: 0, cursor: "pointer",
                display: "flex", alignItems: "center", gap: "0.5rem",
                fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)",
                textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem",
              }}
            >
              <span style={{ fontSize: "0.5rem" }}>{expandedSection === "calibration" ? "▼" : "▶"}</span>
              Prediction vs Reality Evidence
              <span style={{ fontSize: "0.625rem", fontWeight: 400, color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                {calib.prediction_vs_reality_samples.length} samples
              </span>
            </button>

            {expandedSection === "calibration" && (
              <div className="card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
                  <div>
                    <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                      Mean Absolute Error
                    </div>
                    <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: 2, color: "var(--text-primary)" }}>
                      {calib.mean_absolute_error_pct != null ? `${calib.mean_absolute_error_pct}%` : "Insufficient evidence"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                      Calibration Ratio
                    </div>
                    <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: 2, color: "var(--text-primary)" }}>
                      {calib.calibration_ratio != null ? calib.calibration_ratio.toFixed(2) : "Insufficient evidence"}
                    </div>
                  </div>
                </div>

                <table className="ops-table">
                  <thead>
                    <tr>
                      <th>Case ID</th>
                      <th>Action</th>
                      <th style={{ textAlign: "right" }}>Expected</th>
                      <th style={{ textAlign: "right" }}>Actual</th>
                      <th style={{ textAlign: "right" }}>Error</th>
                      <th>Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {calib.prediction_vs_reality_samples!.map((sample, idx) => (
                      <tr key={idx}>
                        <td style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{sample.case_id}</td>
                        <td style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{sample.action}</td>
                        <td style={{ textAlign: "right", fontFamily: "monospace" }}>{fmt(sample.expected_recovery_minor)}</td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", fontWeight: 700, color: sample.actual_recovery_minor > 0 ? "#10b981" : "var(--text-muted)" }}>
                          {sample.actual_recovery_minor > 0 ? fmt(sample.actual_recovery_minor) : "—"}
                        </td>
                        <td style={{ textAlign: "right", fontFamily: "monospace" }}>{sample.prediction_error_pct}%</td>
                        <td>
                          <span style={{
                            fontSize: "0.6875rem", fontWeight: 700, padding: "2px 6px", borderRadius: 4,
                            background: sample.outcome === "recovered" ? "rgba(16,185,129,0.12)" : "rgba(107,114,128,0.12)",
                            color: sample.outcome === "recovered" ? "#10b981" : "var(--text-muted)",
                            textTransform: "uppercase", letterSpacing: "0.04em",
                          }}>
                            {sample.outcome}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── 4. REVENUE LEAKAGE ── */}
        {(report.revenue_lost_reasons && report.revenue_lost_reasons.length > 0) && (
          <div style={{ marginBottom: "2rem" }}>
            <button
              onClick={() => setExpandedSection(expandedSection === "leakage" ? null : "leakage")}
              style={{
                background: "none", border: "none", padding: 0, cursor: "pointer",
                display: "flex", alignItems: "center", gap: "0.5rem",
                fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)",
                textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem",
              }}
            >
              <span style={{ fontSize: "0.5rem" }}>{expandedSection === "leakage" ? "▼" : "▶"}</span>
              Revenue Leakage Analysis
              <span style={{ fontSize: "0.625rem", fontWeight: 400, color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                {report.revenue_lost_reasons.length} reason{report.revenue_lost_reasons.length !== 1 ? "s" : ""}
              </span>
            </button>

            {expandedSection === "leakage" && (
              <div className="card" style={{ overflow: "hidden" }}>
                <table className="ops-table">
                  <thead>
                    <tr>
                      <th>Reason</th>
                      <th style={{ textAlign: "right" }}>Unrecovered</th>
                      <th style={{ textAlign: "right" }}>Cases</th>
                      <th>Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.revenue_lost_reasons!.map((reason) => (
                      <tr key={reason.reason_code}>
                        <td style={{ fontWeight: 600 }}>{reason.reason_label}</td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", fontWeight: 700, color: "#ef4444" }}>
                          {fmt(reason.lost_amount_minor)}
                        </td>
                        <td style={{ textAlign: "right", fontFamily: "monospace" }}>{reason.cases_count}</td>
                        <td style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>
                          {reason.actionable_recommendation}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        </>
      )}
    </div>
  );
}
