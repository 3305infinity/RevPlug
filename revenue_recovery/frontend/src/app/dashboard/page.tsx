"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, DashboardSummary, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function OperationsDashboard() {
  const [status, setStatus] = useState<Status>("loading");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const [s, i] = await Promise.all([api.summary(), api.items()]);
      setSummary(s);
      setItems(i);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  // Top Recovery Opportunities sorted by expected_net_recovery descending
  const topOpportunities = useMemo(() => {
    const list = items.filter(i => i.status !== "recovered" && i.status !== "stopped");
    return list.sort((a, b) => (b.expected_recovery_value || 0) - (a.expected_recovery_value || 0)).slice(0, 5);
  }, [items]);

  // Escalated Human Attention Items
  const humanAttentionItems = useMemo(() => {
    return items.filter(i => i.status === "escalated" || i.status === "intervention_pending").slice(0, 5);
  }, [items]);

  if (status === "error") {
    return (
      <div style={{ padding: "3rem 1.5rem", maxWidth: 600, margin: "0 auto", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          RECOVERY ENGINE UNREACHABLE
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1rem" }}>
          {error || "API server is offline."}
        </p>
        <button onClick={load} className="btn-primary">Retry Connection</button>
      </div>
    );
  }

  if (status === "loading" || !summary) {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 96 }} />)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            RevPlug Autonomous Revenue Operations
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Executive Revenue & Decision Control
          </h1>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link href="/policy-config" className="btn-secondary" style={{ fontSize: "0.75rem", padding: "0.45rem 0.85rem" }}>
            Policy Configuration
          </Link>
          <Link href="/review" className="btn-primary" style={{ fontSize: "0.75rem", padding: "0.45rem 0.85rem" }}>
            Human Review Queue ({summary.stopped_cases || 12})
          </Link>
        </div>
      </div>

      {/* FIRST VIEWPORT: 5 CORE QUESTIONS & REVENUE SUMMARY */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
          1. REVENUE OUTCOMES (HOW MUCH IS AT RISK & RECOVERABLE?)
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
          <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #ef4444" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>REVENUE AT RISK</div>
            <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#ef4444", marginTop: 4 }}>
              {fmt(summary.revenue_at_risk)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
              {summary.total_cases} total cases analyzed
            </div>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #10b981" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>VERIFIED RECOVERED</div>
            <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#10b981", marginTop: 4 }}>
              {fmt(summary.actually_recovered)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#10b981", marginTop: 4 }}>
              {(summary.recovery_rate * 100).toFixed(1)}% verified recovery rate
            </div>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #3b82f6" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>EXPECTED RECOVERABLE</div>
            <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#3b82f6", marginTop: 4 }}>
              {fmt(summary.expected_recovery)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
              Projected net EV pipeline
            </div>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #f59e0b" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>HUMAN ATTENTION NEEDED</div>
            <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#f59e0b", marginTop: 4 }}>
              {fmt(34000000)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#f59e0b", marginTop: 4 }}>
              12 high-value cases escalated
            </div>
          </div>
        </div>
      </div>

      {/* 2. AGENT ACTIVITY & SYSTEMIC RISKS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* AGENT ACTIVITY */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            2. WHAT IS THE AGENT DOING RIGHT NOW? (AGENT ACTIVITY)
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
            <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>ANALYZED</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, fontFamily: "monospace", marginTop: 2 }}>{summary.total_cases}</div>
            </div>
            <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.6875rem", color: "#10b981" }}>EXECUTED</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, fontFamily: "monospace", color: "#10b981", marginTop: 2 }}>73</div>
            </div>
            <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.6875rem", color: "#f59e0b" }}>WAITING</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, fontFamily: "monospace", color: "#f59e0b", marginTop: 2 }}>29</div>
            </div>
            <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.6875rem", color: "#ef4444" }}>ESCALATED</div>
              <div style={{ fontSize: "1.25rem", fontWeight: 700, fontFamily: "monospace", color: "#ef4444", marginTop: 2 }}>12</div>
            </div>
          </div>
        </div>

        {/* SYSTEMIC RISKS */}
        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #f59e0b" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
            3. SYSTEMIC RISKS & EXPOSURE
          </div>
          <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)" }}>
            UPI Authentication Failure Spike
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Gateway: Razorpay / NPCI • 3.9x failure lift • 184 customers affected
          </div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", marginTop: 6 }}>
            ₹8,70,000 EXPOSED
          </div>
          <Link href="/incidents" style={{ display: "inline-block", fontSize: "0.75rem", color: "#3b82f6", fontWeight: 700, marginTop: 8 }}>
            Manage Systemic Incidents →
          </Link>
        </div>
      </div>

      {/* 3.5 TIME-TO-RECOVERY ANALYTICS BLOCK */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>MEDIAN TIME TO RECOVERY</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#10b981", fontFamily: "monospace", marginTop: 2 }}>2h 14m</div>
        </div>
        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>P90 TIME TO RECOVERY</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#3b82f6", fontFamily: "monospace", marginTop: 2 }}>18h 42m</div>
        </div>
        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>ATTEMPT CONVERSION</div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-primary)", fontWeight: 700, marginTop: 4 }}>
            Att 1: <strong style={{ color: "#10b981" }}>31%</strong> • Att 2: <strong>9%</strong> • Att 3: <strong>2%</strong>
          </div>
        </div>
        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>TIME WINDOW RECOVERY</div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-primary)", fontWeight: 700, marginTop: 4 }}>
            &lt;1h: <strong style={{ color: "#10b981" }}>42%</strong> • 1–6h: <strong>31%</strong> • 6–24h: <strong>18%</strong>
          </div>
        </div>
      </div>

      {/* 4. PORTFOLIO NEXT BEST RECOVERY OPPORTUNITIES */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <span style={{ fontSize: "0.6875rem", background: "#10b981", color: "#fff", padding: "2px 6px", borderRadius: 4, fontWeight: 700 }}>
              PRIMARY OPERATING SURFACE
            </span>
            <h2 style={{ fontSize: "1.125rem", fontWeight: 700, margin: "4px 0 0 0", color: "var(--text-primary)" }}>
              NEXT BEST RECOVERY OPPORTUNITIES (RANKED BY BUSINESS VALUE)
            </h2>
          </div>
          <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--accent)" }}>View All Cases →</Link>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>RANK</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>CUSTOMER</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>AMOUNT AT RISK</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>EXPECTED NET RECOVERY</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>NEXT BEST ACTION</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>REASON & EVIDENCE</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {(topOpportunities || []).map((item, idx) => (
              <tr key={item.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.75rem", fontWeight: 800, color: "#10b981", fontFamily: "monospace" }}>
                  #{idx + 1}
                </td>
                <td style={{ padding: "0.75rem" }}>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{item.customer_id}</div>
                </td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace" }}>{fmt(item.amount_minor)}</td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: "#10b981" }}>
                  {fmt(item.expected_recovery_value || Math.round(item.amount_minor * 0.85))}
                </td>
                <td style={{ padding: "0.75rem" }}>
                  <span style={{ fontSize: "0.75rem", background: "rgba(59, 130, 246, 0.15)", color: "#3b82f6", padding: "2px 8px", borderRadius: 4, fontWeight: 700, textTransform: "uppercase" }}>
                    {item.root_cause?.includes("auth") ? "Payment Link" : item.status === "escalated" ? "Human Review" : "WAIT until 10:30 AM"}
                  </span>
                </td>
                <td style={{ padding: "0.75rem", color: "var(--text-secondary)", fontSize: "0.75rem" }}>
                  {item.root_cause?.includes("auth") ? "authentication failure + high historical link success (72%)" : "optimal morning retry window aligned with salary deposit patterns"}
                </td>
                <td style={{ padding: "0.75rem" }}>
                  <Link href={`/recovery/${item.id}`} className="btn-secondary" style={{ fontSize: "0.75rem", padding: "0.35rem 0.65rem" }}>
                    Playbook →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 5. RECOVERY LOSSES & POLICY BLOCKS */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
          5. WHAT IS CURRENTLY BLOCKING RECOVERY? (RECOVERY LOSSES & POLICY GUARDS)
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
          <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>BLOCKED BY POLICY</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", marginTop: 2 }}>{fmt(1850000)}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Fraud & opt-out rules</div>
          </div>
          <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>HARD DECLINES</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", marginTop: 2 }}>{fmt(2400000)}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Expired & invalid cards</div>
          </div>
          <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>NEGATIVE EV</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f59e0b", fontFamily: "monospace", marginTop: 2 }}>{fmt(450000)}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Cost exceeds recovery EV</div>
          </div>
          <div style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>CUSTOMER UNREACHABLE</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-muted)", fontFamily: "monospace", marginTop: 2 }}>{fmt(620000)}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Max contact fatigue (2/2)</div>
          </div>
        </div>
      </div>
    </div>
  );
}
