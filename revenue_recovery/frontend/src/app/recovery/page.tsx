"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function RecoveryQueue() {
  const [status, setStatus] = useState<Status>("loading");
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sourceFilter, setSourceFilter] = useState<string>("all");

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
    return items.filter((i) => {
      const matchStatus = statusFilter === "all" || i.status === statusFilter;
      const src = String(i.source_type || i.metadata?.source_type || "payment_failure");
      const matchSource = sourceFilter === "all" || src.includes(sourceFilter);
      return matchStatus && matchSource;
    });
  }, [items, statusFilter, sourceFilter]);

  const statuses = useMemo(() => {
    const s = new Set(items.map((i) => i.status));
    return Array.from(s).sort();
  }, [items]);

  const fmt = (n: number) =>
    `₹${(n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

  if (status === "error") {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load recovery queue</div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>{error}</p>
        <button onClick={load} className="btn-primary" style={{ marginTop: "1rem" }}>Retry</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1150, margin: "0 auto" }}>
      {/* Page Header */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            RevPlug Case Operations
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>Recovery Cases</h1>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            {items.length} total cases · <span className="font-mono">{fmt(items.reduce((a, i) => a + i.amount_minor, 0))}</span> gross risk at play
          </div>
        </div>
        <Link href="/run-recovery" className="btn-primary">
          Run Recovery
        </Link>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ padding: "0.75rem 1rem", marginBottom: "1.25rem", display: "flex", gap: "1.5rem", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginRight: 4 }}>Source:</span>
          {["all", "payment_failure", "checkout", "subscription", "receivable"].map((src) => (
            <button
              key={src}
              onClick={() => setSourceFilter(src)}
              style={{
                padding: "0.25rem 0.5rem",
                borderRadius: 4,
                fontSize: "0.75rem",
                fontWeight: sourceFilter === src ? 600 : 400,
                background: sourceFilter === src ? "var(--bg-tertiary)" : "transparent",
                color: sourceFilter === src ? "var(--text-primary)" : "var(--text-secondary)",
                border: sourceFilter === src ? "1px solid var(--border-focus)" : "1px solid transparent",
                cursor: "pointer",
              }}
            >
              {src === "all" ? "All" : src.replace(/_/g, " ").toUpperCase()}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, marginRight: 4 }}>Status:</span>
          <button
            onClick={() => setStatusFilter("all")}
            style={{
              padding: "0.25rem 0.5rem",
              borderRadius: 4,
              fontSize: "0.75rem",
              fontWeight: statusFilter === "all" ? 600 : 400,
              background: statusFilter === "all" ? "var(--bg-tertiary)" : "transparent",
              color: statusFilter === "all" ? "var(--text-primary)" : "var(--text-secondary)",
              border: statusFilter === "all" ? "1px solid var(--border-focus)" : "1px solid transparent",
              cursor: "pointer",
            }}
          >
            All
          </button>
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              style={{
                padding: "0.25rem 0.5rem",
                borderRadius: 4,
                fontSize: "0.75rem",
                fontWeight: statusFilter === s ? 600 : 400,
                background: statusFilter === s ? "var(--bg-tertiary)" : "transparent",
                color: statusFilter === s ? "var(--text-primary)" : "var(--text-secondary)",
                border: statusFilter === s ? "1px solid var(--border-focus)" : "1px solid transparent",
                cursor: "pointer",
              }}
            >
              {s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {/* OPERATIONS TABLE */}
      {status === "loading" ? (
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 48 }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
          No recovery cases match this filter.
        </div>
      ) : (
        <div className="card">
          <table className="ops-table">
            <thead>
              <tr>
                <th>CASE ID</th>
                <th>CUSTOMER</th>
                <th>ISSUE / ROOT CAUSE</th>
                <th style={{ textAlign: "right" }}>RISK (INR)</th>
                <th>RECOMMENDED ACTION</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td className="font-mono" style={{ fontWeight: 600 }}>
                    <Link href={`/recovery/${item.id}`} style={{ color: "var(--text-primary)" }}>
                      {item.external_id || item.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>{item.customer_id}</td>
                  <td style={{ textTransform: "capitalize" }}>
                    {item.root_cause ? item.root_cause.replace(/_/g, " ") : "Telemetry Failure"}
                  </td>
                  <td className="font-mono" style={{ textAlign: "right", fontWeight: 600 }}>
                    {fmt(item.amount_minor)}
                  </td>
                  <td>
                    <span className="badge-neutral" style={{ padding: "0.15rem 0.4rem", borderRadius: 4, fontSize: "0.6875rem" }}>
                      {String(item.metadata?.proposed_action || item.metadata?.action || "payment_link").replace(/_/g, " ")}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge status-${item.status}`}>
                      {item.status.replace(/_/g, " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
