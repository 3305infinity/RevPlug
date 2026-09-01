"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface LeakageCategory {
  category_id: string;
  category_label: string;
  amount_at_risk_minor: number;
  recoverable_estimate_minor: number;
  actual_recovered_minor: number;
  unrecovered_minor: number;
  recovery_rate_pct: number;
  recommended_policy_change: string;
}

interface LeakageReport {
  total_revenue_at_risk_minor: number;
  total_unrecovered_minor: number;
  categories: LeakageCategory[];
  generated_at: string;
}

export default function RevenueLeakagePage() {
  const [report, setReport] = useState<LeakageReport | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    fetch(`${apiHost}/api/analytics/revenue-leakage`)
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
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load revenue leakage analytics</div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            REVENUE LEAKAGE DIAGNOSTICS & POLICY FIXES
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Where Is My Revenue Leaking?
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Aggregated leakage analysis pinpointing exact failure categories, unrecovered amounts, and actionable policy changes.
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>TOTAL REVENUE AT RISK</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#ef4444", fontFamily: "monospace" }}>
            {fmt(report.total_revenue_at_risk_minor)}
          </div>
        </div>
      </div>

      {/* LEAKAGE CATEGORY TABLE */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1rem", color: "var(--text-primary)" }}>
          REVENUE LEAKAGE BREAKDOWN BY FAILURE CATEGORY
        </h2>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
              <th style={{ padding: "0.85rem", color: "var(--text-muted)" }}>FAILURE CATEGORY</th>
              <th style={{ padding: "0.85rem", color: "var(--text-muted)" }}>AMOUNT AT RISK</th>
              <th style={{ padding: "0.85rem", color: "var(--text-muted)" }}>RECOVERABLE ESTIMATE</th>
              <th style={{ padding: "0.85rem", color: "var(--text-muted)" }}>ACTUAL RECOVERED</th>
              <th style={{ padding: "0.85rem", color: "var(--text-muted)" }}>UNRECOVERED</th>
              <th style={{ padding: "0.85rem", color: "var(--text-muted)" }}>RECOVERY RATE</th>
              <th style={{ padding: "0.85rem", color: "var(--text-muted)" }}>DRILL DOWN</th>
            </tr>
          </thead>
          <tbody>
          {(report.categories || []).map((cat) => (
            <tr key={cat.category_id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {cat.category_label}
              </td>
              <td style={{ padding: "0.85rem", fontFamily: "monospace", fontWeight: 600 }}>
                {fmt(cat.amount_at_risk_minor)}
              </td>
              <td style={{ padding: "0.85rem", fontFamily: "monospace", color: "#3b82f6" }}>
                {fmt(cat.recoverable_estimate_minor)}
              </td>
              <td style={{ padding: "0.85rem", fontFamily: "monospace", fontWeight: 700, color: "#10b981" }}>
                {fmt(cat.actual_recovered_minor)}
              </td>
              <td style={{ padding: "0.85rem", fontFamily: "monospace", fontWeight: 700, color: "#ef4444" }}>
                {fmt(cat.unrecovered_minor)}
              </td>
              <td style={{ padding: "0.85rem" }}>
                <span style={{ fontSize: "0.875rem", fontWeight: 700, color: cat.recovery_rate_pct > 50 ? "#10b981" : "#ef4444", fontFamily: "monospace" }}>
                  {cat.recovery_rate_pct.toFixed(1)}%
                </span>
              </td>
              <td style={{ padding: "0.85rem" }}>
                <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 700 }}>
                  Drill Cases →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {/* WHAT SHOULD I CHANGE TO STOP THE LEAK? */}
    <div className="card" style={{ padding: "1.5rem", borderLeft: "4px solid #3b82f6" }}>
      <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "1rem" }}>
        WHAT SHOULD I CHANGE TO STOP THE LEAK? (RECOMMENDED POLICY FIXES)
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
        {(report.categories || []).map((cat) => (
          <div key={cat.category_id} style={{ padding: "0.85rem 1rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>{cat.category_label}:</span>
              <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginLeft: 6 }}>{cat.recommended_policy_change}</span>
            </div>
            <Link href="/policy-config" className="btn-secondary" style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem", flexShrink: 0 }}>
              Update Policy
            </Link>
          </div>
        ))}
      </div>
    </div>
    </div>
  );
}
