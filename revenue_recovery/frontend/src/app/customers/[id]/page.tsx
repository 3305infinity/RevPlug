"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, Customer360Profile } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import DecisionBadge from "@/components/shared/DecisionBadge";

type Status = "loading" | "error" | "ready";

const fmt = (n: number | null | undefined) =>
  "₹" + ((n || 0) / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

export default function CustomerDetail() {
  const params = useParams();
  const customerId = params?.id as string;
  const [status, setStatus] = useState<Status>("loading");
  const [profile, setProfile] = useState<Customer360Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [promises, setPromises] = useState<Array<Record<string, any>>>([]);

  useEffect(() => {
    if (!customerId) return;
    api.customerRecoveryProfile(customerId)
      .then(setProfile)
      .catch(() => setError("Customer profile not found"))
      .finally(() => setStatus("ready"));
    api.promises().then((allPromises) => {
      setPromises(allPromises.filter((p: any) => p.customer_id === customerId));
    }).catch(() => {});
  }, [customerId]);

  if (status === "error" || error) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Customer profile not found</h2>
        <Link href="/customers" className="btn-primary">Back to Customers</Link>
      </div>
    );
  }

  if (status === "loading" || !profile) {
    return (
      <div style={{ maxWidth: 1080, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
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
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0 }}>
              {getCustomerDisplayName(p.customer_id)}
            </h1>
            <span style={{
              fontSize: "0.625rem", padding: "2px 7px", borderRadius: 4, fontWeight: 700,
              background: p.customer_value_tier === "HIGH" ? "rgba(16,185,129,0.15)" : "rgba(59,130,246,0.15)",
              color: p.customer_value_tier === "HIGH" ? "#10b981" : "#3b82f6",
              border: "1px solid currentColor",
            }}>
              {p.customer_value_tier}
            </span>
            {p.customer_decision && (
              <DecisionBadge decision={p.customer_decision as any} compact />
            )}
          </div>
        </div>
      </div>

      {/* 1. FINANCIAL SUMMARY */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #ef4444" }}>
          <div className="metric-label">Revenue at Risk</div>
          <div className="metric-value" style={{ color: "#ef4444", fontSize: "1.5rem" }}>{fmt(p.current_amount_at_risk_minor)}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>open exposure</div>
        </div>
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #f59e0b" }}>
          <div className="metric-label">Expected Recovery</div>
          <div className="metric-value" style={{ color: "#f59e0b", fontSize: "1.5rem" }}>{fmt(p.current_expected_recovery_minor)}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>projected</div>
        </div>
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #10b981" }}>
          <div className="metric-label">Verified Recovered</div>
          <div className="metric-value" style={{ color: "#10b981", fontSize: "1.5rem" }}>{fmt(p.actually_recovered_lifetime_minor)}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>settlement confirmed</div>
        </div>
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #6366f1" }}>
          <div className="metric-label">Open Opportunities</div>
          <div className="metric-value" style={{ fontSize: "1.5rem" }}>{p.active_opportunities.length}</div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>active cases</div>
        </div>
        <div className="card" style={{ padding: "1.125rem", borderLeft: "3px solid #64748b" }}>
          <div className="metric-label">Recovery Status</div>
          <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
            {p.current_subscription_state}
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
            {(p.historical_recovery_rate * 100).toFixed(0)}% historical rate
          </div>
        </div>
      </div>

      {/* 2. WHY THIS MATTERS NOW */}
      {p.why_this_matters && (
        <div style={{
          padding: "1rem 1.25rem", background: "rgba(99,102,241,0.06)", borderRadius: 8,
          border: "1px solid rgba(99,102,241,0.2)", marginBottom: "1.5rem",
        }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.35rem" }}>
            Why This Matters Now
          </div>
          <div style={{ fontSize: "0.875rem", color: "var(--text-primary)", fontWeight: 500 }}>
            {p.why_this_matters}
          </div>
        </div>
      )}

      {/* 3. CUSTOMER-LEVEL POSTURE + ACTIVE OPPORTUNITIES */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "1rem", marginBottom: "1.5rem" }}>
        {/* Posture */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Customer Posture
          </div>
          {p.customer_decision ? (
            <>
              <DecisionBadge decision={p.customer_decision as any} />
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                {p.customer_decision_reason}
              </div>
            </>
          ) : (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>No active posture</div>
          )}
          <div style={{ marginTop: "1rem", fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
            <div>Total cases: {p.total_cases_count}</div>
            <div>Recovered: {p.successful_recovery_count}</div>
            <div>Active: {p.active_cases_count}</div>
          </div>
        </div>

        {/* Active Opportunities */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Current Recovery Opportunities ({p.active_opportunities.length})
          </div>
          {p.active_opportunities.length === 0 ? (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No open opportunities</div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>OPPORTUNITY</th>
                    <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>AT RISK</th>
                    <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>DECISION</th>
                    <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>STATUS</th>
                    <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>TIMING</th>
                    <th style={{ padding: "0.4rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>POLICY</th>
                  </tr>
                </thead>
                <tbody>
                  {p.active_opportunities.map((opp) => (
                    <tr key={opp.item_id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "0.4rem 0.5rem" }}>
                        <Link href={`/recovery/${opp.item_id}`} style={{ color: "var(--accent)", textDecoration: "none", fontFamily: "monospace", fontSize: "0.6875rem" }}>
                          {opp.item_id.slice(0, 14)}
                        </Link>
                      </td>
                      <td style={{ padding: "0.4rem 0.5rem", fontFamily: "monospace", color: "#ef4444" }}>{fmt(opp.amount_minor)}</td>
                      <td style={{ padding: "0.4rem 0.5rem" }}>
                        <DecisionBadge decision={opp.decision as any} compact />
                      </td>
                      <td style={{ padding: "0.4rem 0.5rem" }}>
                        {opp.incident_affected ? (
                          <span style={{ fontSize: "0.625rem", fontWeight: 600, padding: "1px 5px", borderRadius: 3, background: "rgba(245,158,11,0.12)", color: "#f59e0b" }}>
                            SUPPRESSED
                          </span>
                        ) : (
                          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>{opp.execution_status}</span>
                        )}
                      </td>
                      <td style={{ padding: "0.4rem 0.5rem" }}>
                        {opp.decision === "WAIT" ? (
                          <Link href={`/recovery/${opp.item_id}`} style={{ fontSize: "0.5625rem", fontWeight: 600, color: "#64748b", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.25rem", padding: "2px 6px", borderRadius: 3, background: "rgba(100,116,139,0.1)", border: "1px solid rgba(100,116,139,0.2)" }}>
                            ◷ VIEW TIMING
                          </Link>
                        ) : (
                          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "0.4rem 0.5rem" }}>
                        <Link href={`/policy-simulator?opportunity=${opp.item_id}`} style={{ fontSize: "0.5625rem", fontWeight: 600, color: "var(--accent)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.2rem", padding: "2px 6px", borderRadius: 3, background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.15)" }}>
                          PREVIEW
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* RECOVERY STRATEGY HISTORY */}
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Recovery Strategy History
          </div>
          {p.intervention_outcomes.length === 0 ? (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              No intervention history available for this customer.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>INTERVENTION</th>
                    <th style={{ padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>ATTEMPTS</th>
                    <th style={{ padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>SUCCESS RATE</th>
                    <th style={{ padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>EVIDENCE</th>
                  </tr>
                </thead>
                <tbody>
                  {p.intervention_outcomes.filter(i => i.attempts > 0).map((io) => {
                    const evidence = io.attempts >= 10 && io.successful >= 5 ? "established" : io.attempts >= 3 && io.successful >= 1 ? "emerging" : "insufficient";
                    const evidenceColor = evidence === "established" ? "#10b981" : evidence === "emerging" ? "#d97706" : "var(--text-muted)";
                    return (
                      <tr key={io.intervention} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "0.35rem 0.5rem", color: "var(--text-primary)", textTransform: "capitalize" }}>{io.intervention.replace(/_/g, " ")}</td>
                        <td style={{ padding: "0.35rem 0.5rem", fontFamily: "monospace" }}>{io.attempts}</td>
                        <td style={{ padding: "0.35rem 0.5rem", fontFamily: "monospace", color: io.success_rate_pct > 0 ? "#10b981" : "var(--text-muted)" }}>
                          {io.success_rate_pct > 0 ? `${io.success_rate_pct.toFixed(0)}%` : "—"}
                        </td>
                        <td style={{ padding: "0.35rem 0.5rem" }}>
                          <span style={{
                            fontSize: "0.5625rem",
                            fontWeight: 700,
                            color: evidenceColor,
                            background: evidence === "established" ? "rgba(16,185,129,0.08)" : evidence === "emerging" ? "rgba(217,119,6,0.08)" : "rgba(107,114,128,0.08)",
                            padding: "0.15rem 0.45rem",
                            borderRadius: 4,
                            textTransform: "uppercase",
                            letterSpacing: "0.04em",
                          }}>
                            {evidence}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* 4. WHAT HAS WORKED + RECOVERY PRESSURE */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        {/* Intervention Outcomes */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            What Has Worked
          </div>
          {p.intervention_outcomes.length === 0 ? (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No intervention history available</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>INTERVENTION</th>
                  <th style={{ padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>ATTEMPTS</th>
                  <th style={{ padding: "0.35rem 0.5rem", color: "var(--text-muted)", fontSize: "0.625rem", fontWeight: 700 }}>SUCCESS</th>
                </tr>
              </thead>
              <tbody>
                {p.intervention_outcomes.filter(i => i.attempts > 0).map((io) => (
                  <tr key={io.intervention} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.35rem 0.5rem", color: "var(--text-primary)" }}>{io.intervention.replace(/_/g, " ")}</td>
                    <td style={{ padding: "0.35rem 0.5rem", fontFamily: "monospace" }}>{io.attempts}</td>
                    <td style={{ padding: "0.35rem 0.5rem", fontFamily: "monospace", color: io.success_rate_pct > 0 ? "#10b981" : "var(--text-muted)" }}>
                      {io.success_rate_pct > 0 ? `${io.success_rate_pct.toFixed(0)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Recovery Pressure */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Recovery Pressure
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "0.75rem" }}>
            {p.recovery_pressure_summary}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Contacts today</span>
              <span style={{ fontFamily: "monospace", fontWeight: 600 }}>{p.contact_fatigue.contacts_today}/{p.contact_fatigue.daily_limit}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Last 7 days</span>
              <span style={{ fontFamily: "monospace", fontWeight: 600 }}>{p.contact_fatigue.contacts_last_7d}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Fatigue risk</span>
              <span style={{
                fontSize: "0.625rem", fontWeight: 700, padding: "1px 6px", borderRadius: 3,
                background: p.contact_fatigue.fatigue_risk === "HIGH" ? "rgba(239,68,68,0.12)" : "rgba(16,185,129,0.1)",
                color: p.contact_fatigue.fatigue_risk === "HIGH" ? "#ef4444" : "#10b981",
              }}>
                {p.contact_fatigue.fatigue_risk}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. POLICY CONSTRAINTS */}
      {p.policy_constraints.length > 0 && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid #f59e0b" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Customer Constraints
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {p.policy_constraints.map((c, idx) => (
              <div key={idx} style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ color: "#f59e0b" }}>■</span> {c}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. INCIDENT CONTEXT */}
      {p.active_incident_count > 0 && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid #ef4444" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Active Revenue Incidents ({p.active_incident_count})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {p.active_incident_ids.map((incId) => (
              <Link key={incId} href={`/incidents/${incId}`} style={{
                display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.625rem 0.875rem",
                background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)",
                textDecoration: "none", color: "var(--text-primary)",
              }}>
                <span style={{ fontSize: "0.625rem", fontWeight: 700, padding: "2px 6px", borderRadius: 3, background: "rgba(239,68,68,0.12)", color: "#ef4444" }}>
                  INCIDENT
                </span>
                <span style={{ fontSize: "0.8125rem", fontFamily: "monospace" }}>{incId}</span>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginLeft: "auto" }}>View →</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* 7. RECOVERY HISTORY */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          Recovery History ({p.recovery_history_timeline.length})
        </div>
        {p.recovery_history_timeline.length === 0 ? (
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No recovery history available</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {p.recovery_history_timeline.slice(0, 15).map((item, idx) => (
              <div key={item.id || idx} style={{
                display: "flex", gap: "0.75rem", alignItems: "center", padding: "0.5rem 0.75rem",
                background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)",
              }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: item.amount_recovered_minor > 0 ? "#10b981" : "#3b82f6", flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>
                      {item.action.replace(/_/g, " ").toUpperCase()}
                    </span>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {new Date(item.timestamp).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                    <Link href={`/recovery/${item.item_id}`} style={{ color: "var(--accent)", fontFamily: "monospace" }}>
                      {item.item_id.slice(0, 14)}
                    </Link>
                    {item.reason && <span> • {item.reason}</span>}
                  </div>
                </div>
                {item.amount_recovered_minor > 0 && (
                  <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#10b981", fontFamily: "monospace" }}>
                    +{fmt(item.amount_recovered_minor)}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* PAYMENT COMMITMENTS */}
      {promises.length > 0 && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid #3b82f6" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            Payment Commitments
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {promises.map((prom) => {
              const statusColors: Record<string, string> = {
                promised: "#3b82f6",
                fulfilled: "#10b981",
                broken: "#ef4444",
                expired: "#ef4444",
                cancelled: "#6b7280",
              };
              const sc = statusColors[prom.status] || "#3b82f6";
              return (
                <Link key={prom.id} href={`/recovery/${prom.recovery_item_id}`} style={{
                  display: "flex", gap: "1rem", alignItems: "center", padding: "0.625rem 0.875rem",
                  background: "var(--bg-primary)", borderRadius: 6, border: "1px solid var(--border)",
                  textDecoration: "none", color: "var(--text-primary)",
                }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: sc, flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontFamily: "monospace", fontSize: "0.8125rem", fontWeight: 600 }}>
                        {fmt(prom.promised_amount_minor)}
                      </span>
                      <span style={{ fontSize: "0.625rem", fontWeight: 700, padding: "2px 6px", borderRadius: 3, background: `${sc}18`, color: sc }}>
                        {prom.status.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: "1rem", marginTop: "0.2rem" }}>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                        Due: {new Date(prom.promised_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                      </span>
                      {prom.verified_recovered_minor > 0 && (
                        <span style={{ fontSize: "0.6875rem", color: "#10b981" }}>
                          Settled: {fmt(prom.verified_recovered_minor)}
                        </span>
                      )}
                    </div>
                  </div>
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", flexShrink: 0 }}>View →</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* 8. PAYMENT BEHAVIOR */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card" style={{ padding: "1.125rem" }}>
          <div className="metric-label">Payment Methods</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.5rem" }}>
            {p.payment_methods_used.map((m) => (
              <span key={m} style={{ fontSize: "0.625rem", padding: "2px 7px", borderRadius: 4, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                {m.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
        <div className="card" style={{ padding: "1.125rem" }}>
          <div className="metric-label">Last Successful</div>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "0.5rem" }}>
            {p.last_successful_payment_at ? new Date(p.last_successful_payment_at).toLocaleDateString("en-IN", { dateStyle: "medium" }) : "—"}
          </div>
        </div>
        <div className="card" style={{ padding: "1.125rem" }}>
          <div className="metric-label">Last Failed</div>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "0.5rem" }}>
            {p.last_failed_payment_at ? new Date(p.last_failed_payment_at).toLocaleDateString("en-IN", { dateStyle: "medium" }) : "—"}
          </div>
          {p.last_failed_reason && (
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>{p.last_failed_reason}</div>
          )}
        </div>
      </div>
    </div>
  );
}
