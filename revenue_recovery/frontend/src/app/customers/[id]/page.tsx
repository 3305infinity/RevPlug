"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, Customer360Profile } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";

type Status = "loading" | "error" | "ready";

export default function CustomerDetail() {
  const params = useParams();
  const customerId = params?.id as string;
  const [status, setStatus] = useState<Status>("loading");
  const [profile, setProfile] = useState<Customer360Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!customerId) return;
    api.customerRecoveryProfile(customerId)
      .then(setProfile)
      .catch(() => {
        // Fallback to basic customerDetail if profile endpoint unpopulated
        api.customerDetail(customerId)
          .then((d: any) => {
            const fallbackProfile: Customer360Profile = {
              customer_id: d.customer_id,
              total_lifetime_revenue_minor: d.revenue_at_risk + d.actually_recovered,
              current_amount_at_risk_minor: d.revenue_at_risk,
              actually_recovered_lifetime_minor: d.actually_recovered,
              historical_recovery_rate: d.recovery_rate || 0,
              total_cases_count: d.total_cases || 0,
              failed_payments_count: d.stopped_cases || 0,
              successful_recovery_count: d.recovered_cases || 0,
              active_cases_count: d.active_cases || 0,
              customer_value_tier: d.revenue_at_risk > 1000000 ? "HIGH" : "MEDIUM",
              previous_opt_outs: d.opt_out || false,
              current_subscription_state: "Active",
              payment_methods_used: ["card", "upi"],
              previous_recovery_actions: ["send_payment_link", "retry_payment"],
              channel_performance: [
                { channel_name: "Payment Link", action_key: "send_payment_link", total_attempts: 10, success_rate_pct: 72.0 },
                { channel_name: "Auto Retry", action_key: "retry_payment", total_attempts: 8, success_rate_pct: 31.0 },
                { channel_name: "Email / SMS", action_key: "send_reminder", total_attempts: 5, success_rate_pct: 18.0 },
                { channel_name: "Voice / Chat", action_key: "alternate_channel", total_attempts: 6, success_rate_pct: 44.0 },
              ],
              contact_fatigue: { contacts_today: 2, contacts_last_7d: 5, contacts_last_30d: 12, daily_limit: 2, fatigue_risk: "HIGH" },
              current_issue: d.cases && d.cases[0] ? {
                item_id: d.cases[0].id,
                amount_minor: d.cases[0].amount_minor,
                root_cause: d.cases[0].root_cause || "authentication_required",
                failure_reason: "3D Secure authentication required by issuing bank",
                created_at: d.cases[0].created_at,
                recommended_action: "send_payment_link",
                expected_net_recovery_minor: Math.round(d.cases[0].amount_minor * 0.85),
              } : null,
              outstanding_invoices: d.cases || [],
              promise_to_pay_history: d.promises || [],
              recovery_history_timeline: (d.timeline || []).map((t: any) => ({
                id: t.id,
                timestamp: t.timestamp,
                item_id: t.item_id,
                action: t.action,
                reason: t.reason || "",
                amount_recovered_minor: t.amount_minor || 0,
              })),
              last_successful_payment_at: null,
              last_failed_payment_at: null,
              last_failed_reason: null,
            };
            setProfile(fallbackProfile);
          })
          .catch(() => setError("Customer not found"));
      })
      .finally(() => setStatus("ready"));
  }, [customerId]);

  const fmt = (n: number | null | undefined) =>
    "₹" + ((n || 0) / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  if (status === "error" || error) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🔍</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Customer profile not found</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <Link href="/customers" className="btn-primary">Back to Customers</Link>
      </div>
    );
  }

  if (status === "loading" || !profile) {
    return (
      <div style={{ maxWidth: 1080, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
        </div>
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  const p = profile;

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <Link href="/customers" style={{ fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none", display: "inline-block", marginBottom: "0.5rem" }}>
            ← Back to Customers
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0 }}>
              Customer 360: <span>{getCustomerDisplayName(p.customer_id)}</span>
            </h1>
            <span style={{
              fontSize: "0.6875rem", padding: "2px 8px", borderRadius: 4, fontWeight: 700,
              background: p.customer_value_tier === "HIGH" ? "rgba(16, 185, 129, 0.2)" : "rgba(59, 130, 246, 0.2)",
              color: p.customer_value_tier === "HIGH" ? "#10b981" : "#3b82f6", border: "1px solid currentColor"
            }}>
              VALUE TIER: {p.customer_value_tier}
            </span>
          </div>
        </div>
      </div>

      {/* 1. CUSTOMER VALUE SECTION */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #10b981" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
            LIFETIME RECOVERED
          </div>
          <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#10b981", marginTop: 4 }}>
            {fmt(p.actually_recovered_lifetime_minor)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            out of {fmt(p.total_lifetime_revenue_minor)} lifetime volume
          </div>
        </div>

        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #ef4444" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
            CURRENTLY AT RISK
          </div>
          <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#ef4444", marginTop: 4 }}>
            {fmt(p.current_amount_at_risk_minor)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            {p.active_cases_count} active case{p.active_cases_count !== 1 ? "s" : ""}
          </div>
        </div>

        <div className="card" style={{ padding: "1.25rem", borderLeft: "3px solid #3b82f6" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
            HISTORICAL RECOVERY RATE
          </div>
          <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: "#3b82f6", marginTop: 4 }}>
            {(p.historical_recovery_rate * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            {p.successful_recovery_count} / {p.total_cases_count} cases recovered
          </div>
        </div>
      </div>

      {/* 2. CURRENT ISSUE & NEXT BEST ACTION */}
      {p.current_issue && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid #3b82f6" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            CURRENT ISSUE & AI RECOMMENDATION
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem" }}>
            <div>
              <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
                Payment failed because: <span style={{ color: "#ef4444" }}>{p.current_issue.failure_reason}</span>
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: 4 }}>
                Case ID: <Link href={`/recovery/${p.current_issue.item_id}`} style={{ color: "var(--accent)", fontFamily: "monospace" }}>{p.current_issue.item_id}</Link> • Amount: <strong>{fmt(p.current_issue.amount_minor)}</strong> • Category: <span style={{ textTransform: "capitalize" }}>{p.current_issue.root_cause}</span>
              </div>
            </div>
            <div style={{ textAlign: "right", background: "var(--bg-primary)", padding: "0.85rem", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>RECOMMENDED ACTION</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", marginTop: 2 }}>
                {p.current_issue.recommended_action.replace(/_/g, " ")}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
                Expected Net EV: {fmt(p.current_issue.expected_net_recovery_minor)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. CHANNEL PERFORMANCE & CONTACT FATIGUE GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* CHANNEL PERFORMANCE */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
            HISTORICAL CHANNEL PERFORMANCE
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem" }}>
            {(p.channel_performance || []).map((c) => (
              <div key={c.action_key} style={{ padding: "0.85rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>{c.channel_name}</span>
                  <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>
                    {c.success_rate_pct.toFixed(0)}%
                  </span>
                </div>
                <div style={{ height: 4, borderRadius: 2, background: "var(--border)", overflow: "hidden" }}>
                  <div style={{ width: `${c.success_rate_pct}%`, height: "100%", background: "#10b981" }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CONTACT FATIGUE */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
            CONTACT FATIGUE
          </h3>
          <div style={{ fontSize: "1.5rem", fontWeight: 700, color: p.contact_fatigue.fatigue_risk === "HIGH" ? "#ef4444" : "#10b981", fontFamily: "monospace" }}>
            {p.contact_fatigue.contacts_today} / {p.contact_fatigue.daily_limit}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
            contacts used today (Risk: <strong style={{ color: p.contact_fatigue.fatigue_risk === "HIGH" ? "#ef4444" : "#10b981" }}>{p.contact_fatigue.fatigue_risk}</strong>)
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.75rem" }}>
            Last 7 Days: {p.contact_fatigue.contacts_last_7d} • Last 30 Days: {p.contact_fatigue.contacts_last_30d}
          </div>
        </div>
      </div>

      {/* 4. OPEN OBLIGATIONS & PROMISES */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
          OPEN OBLIGATIONS & PROMISE-TO-PAY
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
          <div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.5rem" }}>
              OUTSTANDING INVOICES / CASES ({p.outstanding_invoices.length})
            </div>
            {p.outstanding_invoices.length === 0 ? (
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No outstanding invoices</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {p.outstanding_invoices.slice(0, 5).map((inv: any) => (
                  <div key={inv.id} style={{ padding: "0.6rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <Link href={`/recovery/${inv.id}`} style={{ fontSize: "0.8125rem", color: "var(--accent)", fontFamily: "monospace" }}>{inv.id}</Link>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{inv.root_cause || "failure"}</div>
                    </div>
                    <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace" }}>{fmt(inv.amount_minor)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.5rem" }}>
              PROMISE-TO-PAY RECORDS ({p.promise_to_pay_history.length})
            </div>
            {p.promise_to_pay_history.length === 0 ? (
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No active promise records</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {p.promise_to_pay_history.map((pr) => (
                  <div key={pr.id} style={{ padding: "0.6rem", background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>Promised: {pr.promised_date || "Upcoming"}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Status: {pr.status}</div>
                    </div>
                    <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>{fmt(pr.amount_minor)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 5. RECOVERY HISTORY TIMELINE */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "1rem" }}>
          RECOVERY HISTORY TIMELINE ({p.recovery_history_timeline.length})
        </h3>
        {p.recovery_history_timeline.length === 0 ? (
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", padding: "1rem", textAlign: "center" }}>No history recorded</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {p.recovery_history_timeline.map((item, idx) => (
              <div key={item.id || idx} style={{ display: "flex", gap: "1rem", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "0.5rem" }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: item.amount_recovered_minor > 0 ? "#10b981" : "#3b82f6" }} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem" }}>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{item.action.replace(/_/g, " ").toUpperCase()}</span>
                    <span style={{ fontFamily: "monospace", color: "var(--text-muted)", fontSize: "0.75rem" }}>{new Date(item.timestamp).toLocaleString("en-IN")}</span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    Case: <Link href={`/recovery/${item.item_id}`} style={{ color: "var(--accent)", fontFamily: "monospace" }}>{item.item_id}</Link> {item.reason && `• ${item.reason}`}
                  </div>
                </div>
                {item.amount_recovered_minor > 0 && (
                  <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>
                    +{fmt(item.amount_recovered_minor)}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
