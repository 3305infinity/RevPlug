"use client";

import { useEffect, useState } from "react";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import Link from "next/link";

interface CheckoutSummary {
  checkout_revenue_at_risk_minor: number;
  abandoned_checkouts_count: number;
  expected_recoverable_minor: number;
  top_abandonment_reason: string;
  recovery_rate: number;
  intent_breakdown: {
    high_intent: number;
    payment_error: number;
    low_intent: number;
    contact_fatigue: number;
  };
}

interface CheckoutItem {
  checkout_id: string;
  customer_id: string;
  cart_value_minor: number;
  intent_classification: string;
  time_since_abandonment_minutes: number;
  failure_signal: string | null;
  contacts_today: number;
  recommended_action: string;
  expected_recovery_prob: number;
  expected_net_ev_minor: number;
  lifecycle_stage: string;
}

export default function CheckoutRecoveryPage() {
  const [summary, setSummary] = useState<CheckoutSummary | null>(null);
  const [items, setItems] = useState<CheckoutItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    Promise.all([
      fetch(`${apiHost}/api/checkout-recovery/summary`).then((r) => r.json()),
      fetch(`${apiHost}/api/checkout-recovery/items`).then((r) => r.json()),
    ])
      .then(([s, i]) => {
        setSummary(s);
        setItems(Array.isArray(i) ? i : (i?.items || []));
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  const fmt = (minor: number) => "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 96 }} />)}
        </div>
      </div>
    );
  }

  if (status === "error" || !summary) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load checkout recovery metrics</div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            RevPlug Autonomous Checkout Governance
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Checkout Abandonment Recovery
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            First-class revenue-risk workflow: Abandoned → Diagnosed → Intervention → Customer Returned → Payment Verified
          </div>
        </div>
      </div>

      {/* METRICS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="metric-block" style={{ borderLeft: "3px solid #ef4444" }}>
          <div className="metric-label">CHECKOUT REVENUE AT RISK</div>
          <div className="metric-value" style={{ color: "#ef4444" }}>{fmt(summary.checkout_revenue_at_risk_minor)}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            {summary.abandoned_checkouts_count} abandoned sessions
          </div>
        </div>

        <div className="metric-block" style={{ borderLeft: "3px solid #10b981" }}>
          <div className="metric-label">EXPECTED RECOVERABLE</div>
          <div className="metric-value" style={{ color: "#10b981" }}>{fmt(summary.expected_recoverable_minor)}</div>
          <div style={{ fontSize: "0.75rem", color: "#10b981", marginTop: 4 }}>
            High-intent & payment error
          </div>
        </div>

        <div className="metric-block" style={{ borderLeft: "3px solid #3b82f6" }}>
          <div className="metric-label">RECOVERY RATE</div>
          <div className="metric-value">{(summary.recovery_rate * 100).toFixed(1)}%</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            Verified return conversion
          </div>
        </div>

        <div className="metric-block" style={{ borderLeft: "3px solid #f59e0b" }}>
          <div className="metric-label">TOP ABANDONMENT REASON</div>
          <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 6, lineHeight: 1.2 }}>
            {summary.top_abandonment_reason}
          </div>
        </div>
      </div>

      {/* INTENT GOVERNANCE CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ padding: "1rem", background: "rgba(16, 185, 129, 0.1)", borderRadius: 8, border: "1px solid rgba(16, 185, 129, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 700 }}>HIGH INTENT ({summary.intent_breakdown?.high_intent ?? 0})</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>Action: Send Payment Link / Resume</div>
        </div>

        <div style={{ padding: "1rem", background: "rgba(59, 130, 246, 0.1)", borderRadius: 8, border: "1px solid rgba(59, 130, 246, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#3b82f6", fontWeight: 700 }}>PAYMENT ERROR ({summary.intent_breakdown?.payment_error ?? 0})</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>Action: Diagnose & Pivot Method</div>
        </div>

        <div style={{ padding: "1rem", background: "rgba(245, 158, 11, 0.1)", borderRadius: 8, border: "1px solid rgba(245, 158, 11, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#f59e0b", fontWeight: 700 }}>LOW INTENT ({summary.intent_breakdown?.low_intent ?? 0})</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>Action: WAIT (Suppress messaging)</div>
        </div>

        <div style={{ padding: "1rem", background: "rgba(239, 68, 68, 0.1)", borderRadius: 8, border: "1px solid rgba(239, 68, 68, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#ef4444", fontWeight: 700 }}>CONTACT FATIGUE ({summary.intent_breakdown?.contact_fatigue ?? 0})</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>Action: NO_ACTION (Policy Shield)</div>
        </div>
      </div>

      {/* ABANDONED CHECKOUT TABLE */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "1rem" }}>
          ACTIVE CHECKOUT ABANDONMENT QUEUE ({Array.isArray(items) ? items.length : 0})
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>CHECKOUT ID</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>CUSTOMER</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>CART VALUE</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>INTENT CLASS</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>RECOMMENDED ACTION</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>EXPECTED NET EV</th>
              <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>LIFECYCLE STAGE</th>
            </tr>
          </thead>
          <tbody>
            {(Array.isArray(items) ? items : []).map((item) => (
              <tr key={item.checkout_id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 600, color: "var(--accent)" }}>
                  {item.checkout_id}
                </td>
                <td style={{ padding: "0.75rem", color: "var(--text-primary)", fontWeight: 600 }}>{getCustomerDisplayName(item.customer_id)}</td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 600 }}>{fmt(item.cart_value_minor)}</td>
                <td style={{ padding: "0.75rem" }}>
                  <span style={{
                    fontSize: "0.6875rem", padding: "2px 6px", borderRadius: 4, fontWeight: 700,
                    background: item.intent_classification === "HIGH INTENT" ? "rgba(16, 185, 129, 0.15)" : item.intent_classification === "PAYMENT ERROR" ? "rgba(59, 130, 246, 0.15)" : "rgba(245, 158, 11, 0.15)",
                    color: item.intent_classification === "HIGH INTENT" ? "#10b981" : item.intent_classification === "PAYMENT ERROR" ? "#3b82f6" : "#f59e0b"
                  }}>
                    {item.intent_classification}
                  </span>
                </td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace" }}>{item.recommended_action}</td>
                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: "#10b981" }}>{fmt(item.expected_net_ev_minor)}</td>
                <td style={{ padding: "0.75rem" }}>
                  <span style={{ fontSize: "0.6875rem", padding: "2px 6px", borderRadius: 4, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                    {item.lifecycle_stage}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
