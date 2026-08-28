"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { api, RecoveryItem, CaseDetail } from "@/lib/api";

type Status = "loading" | "error" | "ready";

interface CustomerAccount {
  customerId: string;
  name: string;
  totalOutstanding: number;
  revenueAtRisk: number;
  recovered: number;
  openCases: number;
  lastActivity: string;
  cases: RecoveryItem[];
}

export default function Customers() {
  const [status, setStatus] = useState<Status>("loading");
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const data = await api.items();
      setItems(data);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load customers");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const customers = useMemo<CustomerAccount[]>(() => {
    const map = new Map<string, CustomerAccount>();

    items.forEach((item) => {
      const cid = item.customer_id || "unknown";
      if (!map.has(cid)) {
        map.set(cid, {
          customerId: cid,
          name: "Customer " + cid.slice(-4),
          totalOutstanding: 0,
          revenueAtRisk: 0,
          recovered: 0,
          openCases: 0,
          lastActivity: item.created_at,
          cases: [],
        });
      }
      const c = map.get(cid)!;
      c.cases.push(item);
      c.totalOutstanding += item.amount_minor;
      if (item.status !== "recovered" && item.status !== "stopped") {
        c.revenueAtRisk += item.amount_minor;
      }
      if (item.status === "recovered") {
        c.recovered += item.amount_minor;
      }
      if (["queued", "intervention_executed", "diagnosed", "processing", "escalated", "intervention_pending"].includes(item.status)) {
        c.openCases += 1;
      }
      if (new Date(item.created_at) > new Date(c.lastActivity)) {
        c.lastActivity = item.created_at;
      }
    });

    return Array.from(map.values()).sort((a, b) => b.totalOutstanding - a.totalOutstanding);
  }, [items]);

  const selectedCustomer = useMemo(
    () => customers.find((c) => c.customerId === selectedCustomerId) || null,
    [customers, selectedCustomerId]
  );

  const fmt = (n: number) => "Rs" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load customers</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={load} className="btn-primary">Retry</button>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div style={{ display: "grid", gap: "0.75rem" }}>
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 120 }} />)}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>Customers</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
          Accounts with active or past recovery workflows
        </p>
      </div>

      {selectedCustomer && (
        <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem", background: "var(--accent-subtle)", border: "1px solid rgba(99,102,241,0.15)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--accent)", marginBottom: 2 }}>
              Showing cases for {selectedCustomer.name}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              {selectedCustomer.cases.length} case{selectedCustomer.cases.length !== 1 ? "s" : ""} · {fmt(selectedCustomer.totalOutstanding)} total outstanding
            </div>
          </div>
          <button onClick={() => setSelectedCustomerId(null)} className="btn-secondary" style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem" }}>
            Clear filter
          </button>
        </div>
      )}

      <div style={{ display: "grid", gap: "0.75rem" }}>
        {(selectedCustomer ? [selectedCustomer] : customers).map((customer) => (
          <div
            key={customer.customerId}
            className="card"
            style={{
              padding: "1.25rem 1.5rem",
              cursor: "pointer",
              border: selectedCustomerId === customer.customerId ? "1px solid var(--accent)" : undefined,
              transition: "border-color 0.15s",
            }}
            onClick={() => {
              if (selectedCustomerId === customer.customerId) {
                window.location.href = `/customers/${customer.customerId}`;
              } else {
                setSelectedCustomerId(customer.customerId);
              }
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem", gap: "1rem", flexWrap: "wrap" }}>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <div style={{ fontWeight: 600, fontSize: "0.9375rem" }}>{customer.name}</div>
                  <Link href={`/customers/${customer.customerId}`} onClick={(e) => e.stopPropagation()} style={{ fontSize: "0.6875rem", color: "var(--accent)", textDecoration: "none" }}>
                    Open →
                  </Link>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {customer.customerId}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Outstanding</div>
                <div style={{ fontWeight: 700, fontSize: "1.0625rem", color: "var(--danger)" }}>{fmt(customer.totalOutstanding)}</div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", marginBottom: "0.75rem" }}>
              <MetricCell label="Revenue at Risk" value={fmt(customer.revenueAtRisk)} accent="var(--warning)" />
              <MetricCell label="Recovered" value={fmt(customer.recovered)} accent="var(--success)" />
              <MetricCell label="Open Cases" value={String(customer.openCases)} accent="var(--accent)" />
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "var(--text-secondary)", flexWrap: "wrap", gap: "0.5rem" }}>
              <span>
                {customer.cases.length} case{customer.cases.length !== 1 ? "s" : ""}
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                Last activity: {new Date(customer.lastActivity).toLocaleString()}
              </span>
            </div>
          </div>
        ))}
      </div>

      {selectedCustomer && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
            Cases for {selectedCustomer.name}
          </h3>
          <div style={{ display: "grid", gap: "0.5rem" }}>
            {selectedCustomer.cases.map((item) => (
              <Link
                key={item.id}
                href={`/recovery/${item.id}`}
                style={{ textDecoration: "none", display: "block" }}
              >
                <div className="card" style={{ padding: "0.75rem 1rem", display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid var(--border-subtle)" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.8125rem", fontFamily: "monospace", color: "var(--accent)" }}>
                      {item.id}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
                      {item.root_cause || "unknown"} · {new Date(item.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Amount</div>
                      <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{fmt(item.amount_minor)}</div>
                    </div>
                    <span className={`status-badge status-${item.status}`}>{item.status.replace(/_/g, " ")}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCell({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{ padding: "0.625rem 0.75rem", background: "var(--bg-tertiary)", borderRadius: 8 }}>
      <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: 600, fontSize: "0.875rem", color: accent }}>{value}</div>
    </div>
  );
}
