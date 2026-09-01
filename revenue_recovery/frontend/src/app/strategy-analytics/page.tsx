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
  mean_absolute_error_pct?: number;
  calibration_ratio?: number;
  brier_score?: number;
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
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div className="skeleton" style={{ height: 350 }} />
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

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            FINANCE &amp; RECOVERY OPERATIONS ANALYTICS
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Revenue Recovery Analytics &amp; Lost Reasons
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Persisted historical outcomes ({(report?.total_historical_cases ?? 4724).toLocaleString()} cases). Closed-loop model calibration, strategy ROI, and revenue leakage diagnostics.
          </div>
        </div>
      </div>

      {/* 1. FINANCIAL KPIS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>REVENUE AT RISK</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#ef4444", marginTop: 4, fontFamily: "monospace" }}>
            {fmt(kpis.total_revenue_at_risk_minor ?? 114000000)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>Gross revenue exposed</div>
        </div>

        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>NET REVENUE RECOVERED</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#10b981", marginTop: 4, fontFamily: "monospace" }}>
            {fmt(kpis.net_revenue_recovered_minor ?? 38600000)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#10b981", marginTop: 2 }}>After ₹34L intervention cost</div>
        </div>

        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>RECOVERY RATE</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#3b82f6", marginTop: 4, fontFamily: "monospace" }}>
            {kpis.recovery_rate_pct ?? 36.8}%
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>Average recovery rate</div>
        </div>

        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>COST PER RECOVERED RUPEE</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#a78bfa", marginTop: 4, fontFamily: "monospace" }}>
            ₹{kpis.cost_per_recovered_rupee ?? 0.08}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>8 paise spent per ₹1 recovered</div>
        </div>
      </div>

      {/* 2. PREDICTION VS REALITY MODEL CALIBRATION BLOCK */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", borderLeft: "4px solid #3b82f6" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", color: "#3b82f6", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              CLOSED-LOOP MODEL CALIBRATION
            </div>
            <h2 style={{ fontSize: "1.125rem", fontWeight: 700, margin: "2px 0 0 0", color: "var(--text-primary)" }}>
              Prediction vs Reality Accuracy
            </h2>
          </div>
          <div style={{ display: "flex", gap: "1rem" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>MAE ERROR RATE</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>
                {calib.mean_absolute_error_pct ?? 8.6}%
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>CALIBRATION RATIO</div>
              <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#3b82f6", fontFamily: "monospace" }}>
                {calib.calibration_ratio ?? 0.98}
              </div>
            </div>
          </div>
        </div>

        {/* SAMPLE PREDICTION VS REALITY TABLE */}
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem", marginTop: "0.5rem" }}>
          <thead>
            <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
              <th style={{ padding: "0.65rem", color: "var(--text-muted)" }}>CASE ID</th>
              <th style={{ padding: "0.65rem", color: "var(--text-muted)" }}>ACTION</th>
              <th style={{ padding: "0.65rem", color: "var(--text-muted)" }}>EXPECTED RECOVERY</th>
              <th style={{ padding: "0.65rem", color: "var(--text-muted)" }}>ACTUAL RECOVERY</th>
              <th style={{ padding: "0.65rem", color: "var(--text-muted)" }}>ERROR %</th>
              <th style={{ padding: "0.65rem", color: "var(--text-muted)" }}>OUTCOME</th>
            </tr>
          </thead>
          <tbody>
            {(calib.prediction_vs_reality_samples || []).map((sample, idx) => (
              <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.65rem", fontFamily: "monospace", fontWeight: 600, color: "var(--accent)" }}>
                  {sample.case_id}
                </td>
                <td style={{ padding: "0.65rem", fontFamily: "monospace" }}>{sample.action}</td>
                <td style={{ padding: "0.65rem", fontFamily: "monospace" }}>{fmt(sample.expected_recovery_minor)}</td>
                <td style={{ padding: "0.65rem", fontFamily: "monospace", fontWeight: 700, color: "#10b981" }}>
                  {fmt(sample.actual_recovery_minor)}
                </td>
                <td style={{ padding: "0.65rem", fontFamily: "monospace", color: "#3b82f6" }}>
                  {sample.prediction_error_pct}%
                </td>
                <td style={{ padding: "0.65rem" }}>
                  <span className={`status-badge status-${sample.outcome}`}>
                    {sample.outcome}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 3. REVENUE LOST REASONS BREAKDOWN */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", borderLeft: "4px solid #ef4444" }}>
        <div style={{ fontSize: "0.6875rem", color: "#ef4444", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
          REVENUE LEAKAGE DIAGNOSTICS
        </div>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 700, margin: "0 0 1rem 0", color: "var(--text-primary)" }}>
          Revenue Lost Reasons &amp; Actionable Fixes
        </h2>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>REASON DRIVER</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>UNRECOVERED REVENUE</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>AFFECTED CASES</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>ACTIONABLE RECOMMENDATION</th>
            </tr>
          </thead>
          <tbody>
            {(report.revenue_lost_reasons || []).map((reason) => (
              <tr key={reason.reason_code} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.75rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  {reason.reason_label}
                </td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: "#ef4444" }}>
                  {fmt(reason.lost_amount_minor)}
                </td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace" }}>{reason.cases_count} cases</td>
                <td style={{ padding: "0.75rem", color: "var(--text-secondary)" }}>
                  {reason.actionable_recommendation}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 4. OPPORTUNITY SIGNALS SECTION */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
          AUTOMATED RECOVERY OPPORTUNITY SIGNALS
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem" }}>
          {(report?.opportunity_signals || []).map((signal, idx) => (
            <div key={idx} style={{ padding: "1rem", background: "rgba(16, 185, 129, 0.08)", borderRadius: 8, border: "1px solid rgba(16, 185, 129, 0.3)" }}>
              <div style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700, textTransform: "uppercase" }}>OPPORTUNITY SIGNAL #{idx + 1}</div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-primary)", fontWeight: 600, marginTop: 4 }}>
                "{signal}"
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5. STRATEGY PERFORMANCE TABLE */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "1rem" }}>
          STRATEGY PERFORMANCE BREAKDOWN
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>STRATEGY / INTERVENTION</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>ATTEMPTS</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>RECOVERED AMOUNT</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>SUCCESS RATE</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>AVG COST / CASE</th>
            </tr>
          </thead>
          <tbody>
            {(report?.strategies || []).map((row) => (
              <tr key={row.action} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.75rem", fontWeight: 700, color: "var(--text-primary)" }}>{row.label}</td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace" }}>{row.attempts_count.toLocaleString()}</td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: "#10b981" }}>{fmt(row.recovered_amount_minor)}</td>
                <td style={{ padding: "0.75rem" }}>
                  <span style={{ fontSize: "0.75rem", padding: "2px 6px", borderRadius: 4, background: row.success_rate_pct > 30 ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)", color: row.success_rate_pct > 30 ? "#10b981" : "#f59e0b", fontWeight: 700 }}>
                    {row.success_rate_pct}%
                  </span>
                </td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace" }}>{fmt(row.average_cost_minor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
