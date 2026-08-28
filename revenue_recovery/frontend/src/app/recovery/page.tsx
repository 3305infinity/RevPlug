"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function RecoveryQueue() {
  const [status, setStatus] = useState<Status>("loading");
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const data = await api.items();
      setItems(data);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((i) => i.status === filter);
  }, [items, filter]);

  const statuses = useMemo(() => {
    const s = new Set(items.map((i) => i.status));
    return Array.from(s).sort();
  }, [items]);

  const fmt = (n: number) =>
    `₹${(n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load recovery queue</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={load} className="btn-primary">Retry</button>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>Recovery Queue</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
            {items.length} case{items.length !== 1 ? "s" : ""} · {fmt(items.reduce((a, i) => a + i.amount_minor, 0))} at risk
          </p>
        </div>
        <Link href="/run-recovery" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
          New Recovery
        </Link>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <FilterButton active={filter === "all"} onClick={() => setFilter("all")}>All</FilterButton>
        {statuses.map((s) => (
          <FilterButton key={s} active={filter === s} onClick={() => setFilter(s)}>
            {s.replace(/_/g, " ")}
          </FilterButton>
        ))}
      </div>

      {status === "loading" ? (
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: "1rem", opacity: 0.6 }}>📭</div>
          <p style={{ fontSize: "0.9375rem", marginBottom: "0.5rem" }}>No cases match this filter</p>
          <Link href="/run-recovery" style={{ fontSize: "0.8125rem" }}>Run a recovery →</Link>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {filtered.map((item) => (
            <Link key={item.id} href={`/recovery/${item.id}`} style={{ textDecoration: "none", display: "block" }}>
              <div className="card" style={{
                padding: "1.25rem 1.5rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                transition: "border-color 0.15s, transform 0.1s",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", flex: 1, minWidth: 0 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem" }}>
                      <span style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "monospace" }}>
                        {item.id}
                      </span>
                      <StatusBadge status={item.status} />
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                      <span>{item.root_cause || "unknown"}</span>
                      <span>·</span>
                      <span>{fmt(item.amount_minor)}</span>
                      <span>·</span>
                      <span>{item.currency}</span>
                      <span>·</span>
                      <span>{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
                  {item.expected_recovery_value != null && (
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>EV</div>
                      <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--accent)" }}>{fmt(item.expected_recovery_value)}</div>
                    </div>
                  )}
                  {item.recovery_probability != null && (
                    <div style={{ textAlign: "right", minWidth: 60 }}>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>P</div>
                      <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{(item.recovery_probability * 100).toFixed(0)}%</div>
                    </div>
                  )}
                  <svg width="16" height="16" fill="none" stroke="var(--text-muted)" strokeWidth="2" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function FilterButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "0.4rem 0.85rem",
        borderRadius: 6,
        fontSize: "0.75rem",
        fontWeight: 500,
        cursor: "pointer",
        border: "1px solid",
        borderColor: active ? "var(--accent)" : "var(--border)",
        background: active ? "var(--accent-subtle)" : "var(--bg-card)",
        color: active ? "var(--accent)" : "var(--text-secondary)",
        transition: "all 0.15s",
      }}
    >
      {children}
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls = `status-badge status-${status}`;
  return <span className={cls}>{status.replace(/_/g, " ")}</span>;
}
