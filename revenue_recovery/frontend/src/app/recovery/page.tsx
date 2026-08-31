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

  const totalRisk = useMemo(() => items.reduce((a, i) => a + i.amount_minor, 0), [items]);
  const totalRecovered = useMemo(() => items.reduce((a, i) => a + (i.actual_recovery_value || (i.status === "recovered" ? i.amount_minor : 0)), 0), [items]);
  const totalStopped = useMemo(() => items.filter((i) => i.status === "stopped").length, [items]);

  if (status === "error") {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load recovery control room</div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>{error}</p>
        <button onClick={load} className="btn-primary" style={{ marginTop: "1rem" }}>Retry Connection</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1180, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* CONTROL ROOM HEADER */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            RevPlug Real-Time Recovery Control Room
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
            Recovery Queue Operations
          </h1>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: 2 }}>
            {items.length} total recovery cases · <span className="font-mono">{fmt(totalRisk)}</span> gross risk at play
          </div>
        </div>

        <Link href="/run-recovery" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
          Run Recovery Engine →
        </Link>
      </div>

      {/* OPERATIONAL SUMMARY COUNTERS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.25rem" }}>
        <div style={{ padding: "0.875rem 1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>TOTAL PORTFOLIO AT RISK</div>
          <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--danger)", marginTop: 2 }}>{fmt(totalRisk)}</div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>{items.length} telemetry cases</div>
        </div>

        <div style={{ padding: "0.875rem 1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>VERIFIED RECOVERED</div>
          <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--success)", marginTop: 2 }}>{fmt(totalRecovered)}</div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>Settlement HMAC verified</div>
        </div>

        <div style={{ padding: "0.875rem 1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>POLICY SAFETY STOPS</div>
          <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--danger)", marginTop: 2 }}>{totalStopped} Stopped</div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>Fraud &amp; opt-out shielded</div>
        </div>

        <div style={{ padding: "0.875rem 1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>RAZORPAY ADAPTER MODE</div>
          <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--accent)", marginTop: 2 }}>TEST MODE</div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>Webhook verification enabled</div>
        </div>
      </div>

      {/* FILTER TOOLBAR */}
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

      {/* DENSE OPERATIONS TABLE */}
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
                <th>SOURCE / TYPE</th>
                <th>CUSTOMER</th>
                <th>SIGNAL / CAUSE</th>
                <th style={{ textAlign: "right" }}>AT RISK</th>
                <th>AI RECOMMENDATION</th>
                <th>POLICY GATE</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const isBlocked = item.status === "stopped" || item.root_cause === "fraud";
                const srcType = String(item.source_type || item.metadata?.source_type || "payment_failure");
                return (
                  <tr key={item.id} style={{ cursor: "pointer" }}>
                    <td className="font-mono" style={{ fontWeight: 600 }}>
                      <Link href={`/recovery/${item.id}`} style={{ color: "var(--accent)", textDecoration: "none" }}>
                        {item.external_id || item.id.slice(0, 10)} →
                      </Link>
                    </td>
                    <td style={{ textTransform: "uppercase", fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {srcType.replace(/_/g, " ")}
                    </td>
                    <td className="font-mono" style={{ fontSize: "0.75rem" }}>{item.customer_id}</td>
                    <td style={{ textTransform: "capitalize", fontSize: "0.75rem" }}>
                      {item.root_cause ? item.root_cause.replace(/_/g, " ") : "Telemetry Failure"}
                    </td>
                    <td className="font-mono" style={{ textAlign: "right", fontWeight: 600 }}>
                      {fmt(item.amount_minor)}
                    </td>
                    <td>
                      <span className="badge-neutral" style={{ padding: "0.15rem 0.4rem", borderRadius: 4, fontSize: "0.6875rem", fontFamily: "monospace" }}>
                        {String(item.metadata?.proposed_action || item.metadata?.action || "send_payment_link").replace(/_/g, " ")}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge status-${isBlocked ? "danger" : "success"}`}>
                        {isBlocked ? "BLOCKED" : "ALLOWED"}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge status-${item.status}`}>
                        {item.status.replace(/_/g, " ")}
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
  );
}
