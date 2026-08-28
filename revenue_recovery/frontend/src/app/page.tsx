"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, DashboardSummary, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function CommandCenter() {
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

  const fmt = (n: number) =>
    `₹${(n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

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
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
        {[...Array(8)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "0.5rem" }}>
          <div>
            <h1 style={{ fontSize: "1.875rem", fontWeight: 700, letterSpacing: "-0.03em" }}>
              Command Center
            </h1>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: "0.25rem" }}>
              Real-time revenue recovery intelligence
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <Link href="/simulator" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" style={{ marginRight: 6 }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              New Simulation
            </Link>
            <button onClick={load} className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Hero metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <MetricCard
          label="Revenue at Risk"
          value={fmt(summary.total_amount_minor)}
          sub={`${summary.total_items} case${summary.total_items !== 1 ? "s" : ""}`}
          accent="var(--danger)"
        />
        <MetricCard
          label="Recovered"
          value={fmt(summary.recovered_amount_minor)}
          sub={`${summary.recovered_count} case${summary.recovered_count !== 1 ? "s" : ""}`}
          accent="var(--success)"
        />
        <MetricCard
          label="Recovery Rate"
          value={`${(summary.recovery_rate * 100).toFixed(1)}%`}
          sub={`${summary.pending_count} pending`}
          accent="var(--accent)"
        />
        <MetricCard
          label="Expected Recovery"
          value={fmt(summary.expected_recovery_value)}
          sub={`${summary.escalated_count} escalated`}
          accent="var(--purple)"
        />
      </div>

      {/* Two column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "2rem" }}>
        {/* Needs Attention */}
        <Section title="Needs Attention" subtitle="Escalated and blocked cases">
          {needsAttention.length === 0 ? (
            <EmptyState message="No cases need attention right now." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {needsAttention.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/recovery/${item.id}`}
                  style={{ textDecoration: "none", display: "block" }}
                >
                  <div className="card" style={{ padding: "1rem 1.25rem", transition: "border-color 0.15s" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.25rem" }}>
                          {item.id.replace(/^pay_/, "")}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {item.root_cause || "unknown"} · {fmt(item.amount_minor)}
                        </div>
                      </div>
                      <StatusBadge status={item.status} />
                    </div>
                    {(item.metadata?.proposed_action as string) && (
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        Proposed: <span style={{ color: "var(--purple)", fontWeight: 500 }}>{(item.metadata.proposed_action as string)}</span>
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Section>

        {/* Recovering Automatically */}
        <Section title="Recovering Automatically" subtitle="Active recovery cases">
          {recovering.length === 0 ? (
            <EmptyState message="No active recoveries in progress." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {recovering.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/recovery/${item.id}`}
                  style={{ textDecoration: "none", display: "block" }}
                >
                  <div className="card" style={{ padding: "1rem 1.25rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: "0.875rem", marginBottom: "0.25rem" }}>
                          {item.id.replace(/^pay_/, "")}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {item.root_cause || "unknown"} · {fmt(item.amount_minor)}
                        </div>
                      </div>
                      <StatusBadge status={item.status} />
                    </div>
                    <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      <span>EV: {item.expected_recovery_value ? fmt(item.expected_recovery_value) : "—"}</span>
                      <span>P: {item.recovery_probability !== null ? `${(item.recovery_probability * 100).toFixed(0)}%` : "—"}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Section>
      </div>

      {/* Recent Recoveries */}
      <Section title="Recent Recoveries" subtitle="Successfully resolved cases">
        {recentRecoveries.length === 0 ? (
          <EmptyState message="No recoveries yet. Run a simulation to see the engine in action." />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
            {recentRecoveries.map((item) => (
              <Link key={item.id} href={`/recovery/${item.id}`} style={{ textDecoration: "none", display: "block" }}>
                <div className="card" style={{ padding: "1.25rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                    <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>
                      {item.id.replace(/^pay_/, "")}
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
                    {new Date(item.created_at).toLocaleString()}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                    <div>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Amount</div>
                      <div style={{ fontWeight: 600, fontSize: "0.9375rem" }}>{fmt(item.amount_minor)}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Recovered</div>
                      <div style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--success)" }}>
                        {item.expected_recovery_value ? fmt(item.expected_recovery_value) : "—"}
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function MetricCard({ label, value, sub, accent }: { label: string; value: string; sub: string; accent: string }) {
  return (
    <div className="metric-card" style={{ borderLeft: `3px solid ${accent}` }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color: accent, marginTop: 4 }}>{value}</div>
      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 600 }}>{title}</h2>
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="card" style={{ padding: "2.5rem", textAlign: "center", color: "var(--text-muted)" }}>
      <p style={{ fontSize: "0.8125rem" }}>{message}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls = `status-badge status-${status}`;
  return <span className={cls}>{status.replace(/_/g, " ")}</span>;
}
