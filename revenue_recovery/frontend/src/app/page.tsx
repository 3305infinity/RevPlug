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
    "Rs" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const needsAttention = useMemo(
    () => items.filter((i) => ["escalated", "failed", "intervention_pending"].includes(i.status)),
    [items]
  );
  const recovering = useMemo(
    () => items.filter((i) => ["queued", "intervention_executed", "diagnosed"].includes(i.status)),
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
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to connect</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>
          {error || "Start the Recovery Engine API on port 8000."}
        </p>
        <button onClick={load} className="btn-primary">Retry Connection</button>
      </div>
    );
  }

  if (status === "loading" || !summary) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
      </div>
    );
  }

  return (
    <div>
      {/* Hero */}
      <div className="card" style={{ padding: "2rem", marginBottom: "1.5rem", background: "linear-gradient(135deg, var(--bg-card), var(--bg-elevated))", borderColor: "var(--border-focus)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
          <div>
            <h1 style={{ fontSize: "2rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>
              Revenue Recovery
            </h1>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", maxWidth: 520 }}>
              Your AI recovery agent is continuously finding and recovering lost revenue.
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <Link href="/run-recovery" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
              New Recovery
            </Link>
            <Link href="/batch-recovery" className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
              Batch Recovery
            </Link>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
          <div className="metric-card" style={{ borderLeft: `3px solid var(--danger)` }}>
            <div className="metric-label">Revenue at Risk</div>
            <div className="metric-value" style={{ color: "var(--danger)", marginTop: 4 }}>{fmt(summary.total_amount_minor)}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{summary.total_items} case{summary.total_items !== 1 ? "s" : ""}</div>
          </div>
          <div className="metric-card" style={{ borderLeft: `3px solid var(--success)` }}>
            <div className="metric-label">Recovered</div>
            <div className="metric-value" style={{ color: "var(--success)", marginTop: 4 }}>{fmt(summary.recovered_amount_minor)}</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{summary.recovered_count} case{summary.recovered_count !== 1 ? "s" : ""}</div>
          </div>
          <div className="metric-card" style={{ borderLeft: `3px solid var(--accent)` }}>
            <div className="metric-label">Recovery Rate</div>
            <div className="metric-value" style={{ color: "var(--accent)", marginTop: 4 }}>{(summary.recovery_rate * 100).toFixed(1)}%</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{summary.pending_count} pending</div>
          </div>
        </div>
      </div>

      {/* Needs your attention */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 600 }}>Needs your attention</h2>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Escalated, failed, and intervention-pending cases</p>
        </div>
        {needsAttention.length === 0 ? (
          <div className="card" style={{ padding: "2.5rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ fontSize: "0.8125rem" }}>All clear — no cases need human action.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
            {needsAttention.slice(0, 5).map((item) => (
              <div key={item.id} className="card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <Link href={`/recovery/${item.id}`} style={{ fontWeight: 600, fontSize: "0.875rem", textDecoration: "none" }}>
                      {item.id.replace(/^pay_/, "")}
                    </Link>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {item.root_cause || "unknown"} · {fmt(item.amount_minor)}
                    </div>
                  </div>
                  <span className={`status-badge status-${item.status}`}>{item.status.replace(/_/g, " ")}</span>
                </div>
                <Link href="/review" className="btn-secondary" style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem", alignSelf: "flex-start" }}>
                  Review case
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recovering automatically */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 600 }}>Recovering automatically</h2>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Queued, diagnosed, and intervention-executed cases</p>
        </div>
        {recovering.length === 0 ? (
          <div className="card" style={{ padding: "2.5rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ fontSize: "0.8125rem" }}>No active recoveries in progress.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
            {recovering.slice(0, 5).map((item) => (
              <div key={item.id} className="card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <Link href={`/recovery/${item.id}`} style={{ fontWeight: 600, fontSize: "0.875rem", textDecoration: "none" }}>
                      {item.id.replace(/^pay_/, "")}
                    </Link>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {item.root_cause || "unknown"} · {fmt(item.amount_minor)}
                    </div>
                  </div>
                  <span className={`status-badge status-${item.status}`}>{item.status.replace(/_/g, " ")}</span>
                </div>
                <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                  <span>EV: {item.expected_recovery_value ? fmt(item.expected_recovery_value) : "—"}</span>
                  <span>P: {item.recovery_probability !== null ? `${(item.recovery_probability * 100).toFixed(0)}%` : "—"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent recoveries */}
      <div>
        <div style={{ marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 600 }}>Recent recoveries</h2>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>Successfully resolved cases</p>
        </div>
        {recentRecoveries.length === 0 ? (
          <div className="card" style={{ padding: "2.5rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ fontSize: "0.8125rem" }}>No recoveries yet. Run a recovery to see the engine in action.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
            {recentRecoveries.map((item) => (
              <div key={item.id} className="card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>
                      {item.id.replace(/^pay_/, "")}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
                      {item.root_cause || "unknown"} · {new Date(item.created_at).toLocaleString()}
                    </div>
                  </div>
                  <span className={`status-badge status-${item.status}`}>{item.status.replace(/_/g, " ")}</span>
                </div>
                <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--success)" }}>
                  {fmt(item.expected_recovery_value || item.amount_minor)} recovered
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
