"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, DashboardSummary, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function RevenueRecovery() {
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

  const needsAttention = useMemo(
    () => items.filter((i) => ["escalated", "failed", "intervention_pending", "stopped"].includes(i.status)),
    [items]
  );
  const activeRecoveries = useMemo(
    () => items.filter((i) => ["queued", "intervention_executed", "diagnosed", "intervention_pending"].includes(i.status)),
    [items]
  );
  const recentRecoveries = useMemo(
    () => items.filter((i) => i.status === "recovered").sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 5),
    [items]
  );

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem", opacity: 0.9 }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to connect to RecoverOS</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>
          {error || "Start the Recovery Engine API on port 8000 and try again."}
        </p>
        <button onClick={load} className="btn-primary">Retry Connection</button>
      </div>
    );
  }

  if (status === "loading" || !summary) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "0.35rem" }}>
          Revenue Recovery
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: 600, lineHeight: 1.6 }}>
          Find revenue at risk. Recover it safely. Prove what happened.
        </p>
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
          <Link href="/run-recovery" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
            Run Recovery
          </Link>
          <Link href="/batch-recovery" className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
            Batch Recovery
          </Link>
        </div>
      </div>

      {/* Financial Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <div className="metric-card" style={{ borderLeft: `3px solid var(--danger)` }}>
          <div className="metric-label">Revenue at Risk</div>
          <div className="metric-value" style={{ color: "var(--danger)", marginTop: 4 }}>{fmt(summary.revenue_at_risk)}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{summary.active_recoveries} cases</div>
        </div>
        <div className="metric-card" style={{ borderLeft: `3px solid var(--success)` }}>
          <div className="metric-label">Actually Recovered</div>
          <div className="metric-value" style={{ color: "var(--success)", marginTop: 4 }}>{fmt(summary.actually_recovered)}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{summary.recovered_cases} cases resolved</div>
        </div>
        <div className="metric-card" style={{ borderLeft: `3px solid var(--accent)` }}>
          <div className="metric-label">Recovery Rate</div>
          <div className="metric-value" style={{ color: "var(--accent)", marginTop: 4 }}>{(summary.recovery_rate * 100).toFixed(1)}%</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>of revenue at risk</div>
        </div>
        <div className="metric-card" style={{ borderLeft: `3px solid var(--purple)` }}>
          <div className="metric-label">Expected Recovery</div>
          <div className="metric-value" style={{ color: "var(--purple)", marginTop: 4 }}>{fmt(summary.expected_recovery)}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>projected deterministically</div>
        </div>
      </div>

      {/* Needs Attention */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ marginBottom: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Needs Attention</h2>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
              Stopped, escalated, and failed cases requiring operator action
            </p>
          </div>
          {needsAttention.length > 0 && (
            <span style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              padding: "0.25rem 0.625rem",
              borderRadius: 4,
              background: "var(--danger-subtle)",
              color: "var(--danger)",
            }}>
              {needsAttention.length} case{needsAttention.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        {needsAttention.length === 0 ? (
          <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ fontSize: "0.8125rem" }}>All clear — no cases require human action.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {needsAttention.slice(0, 8).map((item) => (
              <CaseRow key={item.id} item={item} fmt={fmt} />
            ))}
          </div>
        )}
      </div>

      {/* Active Recoveries */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Active Recoveries</h2>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
            Cases currently moving through the recovery workflow
          </p>
        </div>
        {activeRecoveries.length === 0 ? (
          <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ fontSize: "0.8125rem" }}>No active recoveries in progress.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {activeRecoveries.slice(0, 8).map((item) => (
              <CaseRow key={item.id} item={item} fmt={fmt} />
            ))}
          </div>
        )}
      </div>

      {/* Recently Recovered */}
      <div>
        <div style={{ marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Recently Recovered</h2>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
            Successfully resolved cases with measured financial outcomes
          </p>
        </div>
        {recentRecoveries.length === 0 ? (
          <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ fontSize: "0.8125rem" }}>No recoveries yet. Run a recovery to see the engine in action.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {recentRecoveries.map((item) => (
              <Link key={item.id} href={`/recovery/${item.id}`} style={{ textDecoration: "none", display: "block" }}>
                <div className="card" style={{
                  padding: "1rem 1.25rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  transition: "border-color 0.15s",
                }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.25rem" }}>
                      <span style={{ fontWeight: 600, fontSize: "0.8125rem", fontFamily: "monospace", color: "var(--accent)" }}>
                        {item.id}
                      </span>
                      <span className="status-badge status-recovered">Recovered</span>
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {item.root_cause || "unknown"} · {new Date(item.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>
                      Recovered
                    </div>
                    <div style={{ fontSize: "1.0625rem", fontWeight: 700, color: "var(--success)", fontFamily: "monospace" }}>
                      {fmt(item.expected_recovery_value || item.actual_recovery_value || item.amount_minor)}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function CaseRow({ item, fmt }: { item: RecoveryItem; fmt: (n: number) => string }) {
  const isBlocked = item.status === "stopped";
  const isEscalated = item.status === "escalated";
  const isFailed = item.status === "failed";
  const isPending = item.status === "intervention_pending";

  let statusLabel = item.status.replace(/_/g, " ");
  let statusColor: string;
  let actionLabel: string | null = null;
  let policyLabel: string | null = null;
  let policyColor: string | null = null;

  if (isBlocked) {
    statusColor = "var(--text-muted)";
    actionLabel = (item.metadata?.proposed_action as string | undefined)?.replace(/_/g, " ") || null;
    policyLabel = (item.stopped_reason || "Stopped").replace(/_/g, " ");
    policyColor = "var(--danger)";
  } else if (isEscalated) {
    statusColor = "var(--danger)";
    actionLabel = (item.metadata?.proposed_action as string | undefined)?.replace(/_/g, " ") || null;
    policyLabel = "Requires human review";
    policyColor = "var(--warning)";
  } else if (isFailed) {
    statusColor = "var(--danger)";
    actionLabel = (item.metadata?.proposed_action as string | undefined)?.replace(/_/g, " ") || null;
    policyLabel = item.stopped_reason ? item.stopped_reason.replace(/_/g, " ") : "Failed";
    policyColor = "var(--danger)";
  } else if (isPending) {
    statusColor = "var(--warning)";
    actionLabel = (item.metadata?.proposed_action as string | undefined)?.replace(/_/g, " ") || null;
    policyLabel = "Awaiting approval";
    policyColor = "var(--warning)";
  } else {
    statusColor = "var(--accent)";
    actionLabel = (item.metadata?.proposed_action as string | undefined)?.replace(/_/g, " ") || null;
    policyLabel = item.stopped_reason ? item.stopped_reason.replace(/_/g, " ") : "Policy allows execution";
    policyColor = "var(--accent)";
  }

  const nextAction = isBlocked ? "None (Blocked)" : isEscalated ? "Human Review Required" : isFailed ? "None (Failed)" : isPending ? "Awaiting Human" : actionLabel ? `Executing: ${actionLabel}` : "Processing";

  return (
    <Link href={`/recovery/${item.id}`} style={{ textDecoration: "none", display: "block" }}>
      <div className="card" style={{
        padding: "1rem 1.25rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        transition: "border-color 0.15s",
      }}>
        <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: "1.25rem" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.25rem", flexWrap: "wrap" }}>
              <span style={{ fontWeight: 600, fontSize: "0.8125rem", fontFamily: "monospace", color: "var(--accent)" }}>
                {item.id}
              </span>
              <span className={`status-badge status-${item.status}`} style={{ background: isBlocked ? "rgba(100,116,139,0.12)" : undefined, color: statusColor }}>
                {statusLabel}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap", fontSize: "0.75rem", color: "var(--text-muted)" }}>
              <span>{item.customer_id || "Unknown"}</span>
              <span style={{ opacity: 0.4 }}>|</span>
              <span>{item.root_cause || "unknown"}</span>
              <span style={{ opacity: 0.4 }}>|</span>
              <span style={{ fontFamily: "monospace" }}>{fmt(item.amount_minor)}</span>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1.5rem", flexShrink: 0 }}>
            {item.expected_recovery_value != null && (
              <div style={{ textAlign: "right", minWidth: 80 }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Expected</div>
                <div style={{ fontWeight: 600, fontSize: "0.8125rem", color: "var(--purple)" }}>{fmt(item.expected_recovery_value)}</div>
              </div>
            )}
            {actionLabel && (
              <div style={{ textAlign: "right", minWidth: 100 }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>AI Recommendation</div>
                <div style={{ fontWeight: 500, fontSize: "0.75rem", color: "var(--text-secondary)", textTransform: "capitalize" }}>{actionLabel}</div>
              </div>
            )}
            {policyLabel && (
              <div style={{ textAlign: "right", minWidth: 100 }}>
                <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Policy State</div>
                <div style={{ fontWeight: 500, fontSize: "0.75rem", color: policyColor || "var(--text-secondary)", textTransform: "capitalize" }}>{policyLabel}</div>
              </div>
            )}
            <div style={{ textAlign: "right", minWidth: 120 }}>
              <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Next Action</div>
              <div style={{ fontWeight: 500, fontSize: "0.75rem", color: "var(--text-secondary)" }}>{nextAction}</div>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
