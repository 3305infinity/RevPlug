"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface StrategySegment {
  segment_key: string;
  failure_category: string;
  payment_method: string;
  attempts: number;
  successful_verifications: number;
  verified_recovered_minor: number;
  recovery_rate_pct: number;
}

interface StrategyRow {
  action: string;
  label: string;
  evidence_level: string;
  attempts_count: number;
  eligible_opportunities: number;
  attempted_opportunities: number;
  successful_verifications: number;
  verified_recovered_minor: number;
  revenue_at_risk_minor: number;
  recovery_rate_pct: number;
  verified_recovery_rate_pct: number;
  success_rate_pct: number;
  average_verified_recovery_minor: number;
  average_time_to_recovery_hours: number | null;
  avg_attempts_per_recovery: number | null;
  policy_blocks: number;
  stop_outcomes: number;
  escalate_outcomes: number;
  wait_outcomes: number;
  intervention_cost_minor: number;
  average_cost_minor: number;
  attribution: Record<string, number>;
  segments: StrategySegment[];
  last_observed_at: string | null;
  explanation: string;
}

interface FinancialKPIs {
  total_revenue_at_risk_minor?: number;
  revenue_recovered_minor?: number;
  net_revenue_recovered_minor?: number;
  recovery_rate_pct?: number;
  average_recovery_per_case_minor?: number;
  intervention_cost_minor?: number;
  cost_per_recovered_rupee?: number;
  verified_cases?: number;
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

interface PolicyPerformanceRow {
  action: string;
  label: string;
  attempted_opportunities: number;
  policy_blocks: number;
  stop_outcomes: number;
  escalate_outcomes: number;
  wait_outcomes: number;
  successful_verifications: number;
  note: string;
}

interface WhatWorksItem {
  action: string;
  label: string;
  evidence_level: string;
  successful_verifications: number;
  verified_recovered_minor: number;
  verified_recovery_rate_pct: number;
  explanation: string;
}

interface WhatDoesntWorkItem {
  action: string;
  label: string;
  evidence_level: string;
  attempts_count: number;
  successful_verifications: number;
  verified_recovery_rate_pct: number;
  stop_outcomes: number;
  policy_blocks: number;
  explanation: string;
}

interface AnalyticsReport {
  total_historical_cases: number;
  strategies: StrategyRow[];
  what_works: WhatWorksItem[];
  what_doesnt_work: WhatDoesntWorkItem[];
  opportunity_signals: string[];
  financial_kpis?: FinancialKPIs;
  calibration_metrics?: CalibrationMetrics;
  revenue_lost_reasons?: RevenueLostReason[];
  policy_performance?: PolicyPerformanceRow[];
  generated_at: string;
}

const EVIDENCE_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  insufficient: {
    label: "Insufficient Evidence",
    color: "var(--text-muted)",
    bg: "rgba(107,114,128,0.08)",
    border: "rgba(107,114,128,0.2)",
  },
  emerging: {
    label: "Emerging Evidence",
    color: "#d97706",
    bg: "rgba(217,119,6,0.08)",
    border: "rgba(217,119,6,0.2)",
  },
  established: {
    label: "Established Evidence",
    color: "#10b981",
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.2)",
  },
};

function EvidenceBadge({ level }: { level: string }) {
  const meta = EVIDENCE_META[level] || EVIDENCE_META.insufficient;
  return (
    <span
      style={{
        fontSize: "0.5625rem",
        fontWeight: 700,
        color: meta.color,
        background: meta.bg,
        border: `1px solid ${meta.border}`,
        padding: "0.15rem 0.45rem",
        borderRadius: 4,
        textTransform: "uppercase",
        letterSpacing: "0.04em",
        whiteSpace: "nowrap",
      }}
    >
      {meta.label}
    </span>
  );
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

  const fmt = (minor: number) =>
    "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

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
      {/* HEADER */}
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
          <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.5rem" }}>No verified strategy outcomes yet</h2>
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
          {/* 1. OVERALL RECOVERY INTELLIGENCE */}
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

          {/* 2. WHAT WORKS / DOESN'T WORK */}
          {(report.what_works.length > 0 || report.what_doesnt_work.length > 0) && (
            <div style={{ marginBottom: "2rem" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
                Historical Strategy Assessment
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                {report.what_works.length > 0 && (
                  <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #10b981" }}>
                    <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
                      What Works
                    </div>
                    {report.what_works.map((ww) => (
                      <div key={ww.action} style={{ marginBottom: "0.75rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                          <span style={{ fontWeight: 600, fontSize: "0.8125rem" }}>{ww.label}</span>
                          <EvidenceBadge level={ww.evidence_level} />
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                          {ww.successful_verifications} verified recoveries · {fmt(ww.verified_recovered_minor)} · {ww.verified_recovery_rate_pct}% rate
                        </div>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2, lineHeight: 1.4 }}>
                          {ww.explanation}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {report.what_doesnt_work.length > 0 && (
                  <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #ef4444" }}>
                    <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
                      What Doesn&apos;t Work
                    </div>
                    {report.what_doesnt_work.map((wdw) => (
                      <div key={wdw.action} style={{ marginBottom: "0.75rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                          <span style={{ fontWeight: 600, fontSize: "0.8125rem" }}>{wdw.label}</span>
                          <EvidenceBadge level={wdw.evidence_level} />
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                          {wdw.successful_verifications} verified recoveries · {wdw.attempts_count} attempts · {wdw.verified_recovery_rate_pct}% rate
                        </div>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2, lineHeight: 1.4 }}>
                          {wdw.explanation}
                        </div>
                        {wdw.policy_blocks > 0 && (
                          <div style={{ fontSize: "0.6875rem", color: "#d97706", marginTop: 2 }}>
                            {wdw.policy_blocks} policy blocks recorded (policy prevention ≠ strategy failure)
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 3. STRATEGY COMPARISON */}
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
              <div className="card" style={{ overflowX: "auto" }}>
                <table className="ops-table">
                  <thead>
                    <tr>
                      <th>Strategy</th>
                      <th>Evidence</th>
                      <th style={{ textAlign: "right" }}>Attempts</th>
                      <th style={{ textAlign: "right" }}>Verified Recovered</th>
                      <th style={{ textAlign: "right" }}>Verification Rate</th>
                      <th style={{ textAlign: "right" }}>Avg Time to Recovery</th>
                      <th style={{ textAlign: "right" }}>Avg Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.strategies.map((row) => (
                      <tr key={row.action}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{row.label}</div>
                          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                            {row.successful_verifications} verified · {row.policy_blocks} blocked · {row.stop_outcomes} stopped
                          </div>
                        </td>
                        <td><EvidenceBadge level={row.evidence_level} /></td>
                        <td style={{ textAlign: "right", fontFamily: "monospace" }}>{row.attempts_count.toLocaleString()}</td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", fontWeight: 700, color: row.verified_recovered_minor > 0 ? "#10b981" : "var(--text-muted)" }}>
                          {row.verified_recovered_minor > 0 ? fmt(row.verified_recovered_minor) : "—"}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <span style={{
                            fontFamily: "monospace",
                            fontWeight: 700,
                            color: row.verified_recovery_rate_pct >= 50 ? "#10b981" : row.verified_recovery_rate_pct >= 20 ? "#d97706" : "var(--text-muted)",
                          }}>
                            {row.verified_recovery_rate_pct}%
                          </span>
                        </td>
                        <td style={{ textAlign: "right", fontFamily: "monospace", color: "var(--text-muted)" }}>
                          {row.average_time_to_recovery_hours != null ? `${row.average_time_to_recovery_hours}h` : "—"}
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

          {/* 4. STRATEGY SEGMENTS */}
          {report.strategies.some((s) => s.segments.length > 0) && (
            <div style={{ marginBottom: "2rem" }}>
              <button
                onClick={() => setExpandedSection(expandedSection === "segments" ? null : "segments")}
                style={{
                  background: "none", border: "none", padding: 0, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: "0.5rem",
                  fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)",
                  textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem",
                }}
              >
                <span style={{ fontSize: "0.5rem" }}>{expandedSection === "segments" ? "▼" : "▶"}</span>
                Strategy × Failure Category Evidence
                <span style={{ fontSize: "0.625rem", fontWeight: 400, color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                  {report.strategies.reduce((acc, s) => acc + s.segments.length, 0)} segments
                </span>
              </button>

              {expandedSection === "segments" && (
                <div className="card" style={{ overflow: "hidden" }}>
                  <table className="ops-table">
                    <thead>
                      <tr>
                        <th>Strategy</th>
                        <th>Failure Category</th>
                        <th>Payment Method</th>
                        <th style={{ textAlign: "right" }}>Attempts</th>
                        <th style={{ textAlign: "right" }}>Verified</th>
                        <th style={{ textAlign: "right" }}>Recovered</th>
                        <th style={{ textAlign: "right" }}>Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.strategies.flatMap((s) =>
                        s.segments.map((seg) => (
                          <tr key={`${s.action}-${seg.segment_key}`}>
                            <td style={{ fontWeight: 600, fontSize: "0.75rem" }}>{s.label}</td>
                            <td style={{ fontSize: "0.75rem" }}>{seg.failure_category.replace(/_/g, " ")}</td>
                            <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{seg.payment_method}</td>
                            <td style={{ textAlign: "right", fontFamily: "monospace" }}>{seg.attempts}</td>
                            <td style={{ textAlign: "right", fontFamily: "monospace" }}>{seg.successful_verifications}</td>
                            <td style={{ textAlign: "right", fontFamily: "monospace", fontWeight: 700, color: seg.verified_recovered_minor > 0 ? "#10b981" : "var(--text-muted)" }}>
                              {seg.verified_recovered_minor > 0 ? fmt(seg.verified_recovered_minor) : "—"}
                            </td>
                            <td style={{ textAlign: "right", fontFamily: "monospace" }}>
                              <span style={{
                                color: seg.recovery_rate_pct >= 50 ? "#10b981" : seg.recovery_rate_pct >= 20 ? "#d97706" : "var(--text-muted)",
                                fontWeight: 700,
                              }}>
                                {seg.recovery_rate_pct}%
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* 5. POLICY PERFORMANCE */}
          {report.policy_performance && report.policy_performance.length > 0 && (
            <div style={{ marginBottom: "2rem" }}>
              <button
                onClick={() => setExpandedSection(expandedSection === "policy" ? null : "policy")}
                style={{
                  background: "none", border: "none", padding: 0, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: "0.5rem",
                  fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)",
                  textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem",
                }}
              >
                <span style={{ fontSize: "0.5rem" }}>{expandedSection === "policy" ? "▼" : "▶"}</span>
                Policy Performance
                <span style={{ fontSize: "0.625rem", fontWeight: 400, color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                  Bounded autonomy evidence
                </span>
              </button>

              {expandedSection === "policy" && (
                <div className="card" style={{ overflow: "hidden" }}>
                  <table className="ops-table">
                    <thead>
                      <tr>
                        <th>Strategy</th>
                        <th style={{ textAlign: "right" }}>Attempted</th>
                        <th style={{ textAlign: "right" }}>Policy Blocks</th>
                        <th style={{ textAlign: "right" }}>Stopped</th>
                        <th style={{ textAlign: "right" }}>Escalated</th>
                        <th style={{ textAlign: "right" }}>Waited</th>
                        <th style={{ textAlign: "right" }}>Verified</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.policy_performance.map((row) => (
                        <tr key={row.action}>
                          <td style={{ fontWeight: 600 }}>{row.label}</td>
                          <td style={{ textAlign: "right", fontFamily: "monospace" }}>{row.attempted_opportunities}</td>
                          <td style={{ textAlign: "right", fontFamily: "monospace", color: row.policy_blocks > 0 ? "#d97706" : "var(--text-muted)" }}>
                            {row.policy_blocks}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "monospace", color: "var(--text-muted)" }}>{row.stop_outcomes}</td>
                          <td style={{ textAlign: "right", fontFamily: "monospace", color: "var(--text-muted)" }}>{row.escalate_outcomes}</td>
                          <td style={{ textAlign: "right", fontFamily: "monospace", color: "var(--text-muted)" }}>{row.wait_outcomes}</td>
                          <td style={{ textAlign: "right", fontFamily: "monospace", fontWeight: 700, color: "#10b981" }}>
                            {row.successful_verifications}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div style={{ padding: "0.75rem 1rem", fontSize: "0.6875rem", color: "var(--text-muted)", borderTop: "1px solid var(--border)", marginTop: "0.5rem" }}>
                    Policy blocks prevent unsafe execution and do not indicate strategy failure. They are part of bounded autonomy.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 6. PREDICTION VS REALITY */}
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

                  <div style={{ overflowX: "auto" }}>
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
                </div>
              )}
            </div>
          )}

          {/* 7. REVENUE LEAKAGE */}
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

          {/* CONTROLLED EVALUATION LINK */}
          <div className="card" style={{ padding: "1rem 1.25rem", borderLeft: "4px solid #f59e0b", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.25rem" }}>Controlled Performance Evaluation</div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                Compare RevPlug against fixed recovery strategies in a reproducible benchmark environment.
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginTop: "0.25rem" }}>BENCHMARK / SYNTHETIC DATA — separate from live strategy learning above.</span>
              </div>
            </div>
            <Link href="/proof-lab" style={{
              fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b",
              textDecoration: "none", padding: "0.35rem 0.75rem", borderRadius: 4,
              border: "1px solid rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.06)", whiteSpace: "nowrap",
            }}>
              View Proof Lab →
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
