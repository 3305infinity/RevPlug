"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { api, CustomerDetail } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function Customers() {
  const [status, setStatus] = useState<Status>("loading");
  const [customers, setCustomers] = useState<CustomerDetail[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const data = await api.customers();
      setCustomers(data.sort((a, b) => b.revenue_at_risk - a.revenue_at_risk));
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load customers");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const selectedCustomer = useMemo(
    () => customers.find((c) => c.customer_id === selectedCustomerId) || null,
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
              Showing cases for Customer {selectedCustomer.customer_id.slice(-4)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              {selectedCustomer.cases.length} case{selectedCustomer.cases.length !== 1 ? "s" : ""} · {fmt(selectedCustomer.revenue_at_risk)} revenue at risk
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
            key={customer.customer_id}
            className="card"
            style={{
              padding: "1.25rem 1.5rem",
              cursor: "pointer",
              border: selectedCustomerId === customer.customer_id ? "1px solid var(--accent)" : undefined,
              transition: "border-color 0.15s",
            }}
            onClick={() => {
              if (selectedCustomerId === customer.customer_id) {
                window.location.href = `/customers/${customer.customer_id}`;
              } else {
                setSelectedCustomerId(customer.customer_id);
              }
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem", gap: "1rem", flexWrap: "wrap" }}>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <div style={{ fontWeight: 600, fontSize: "0.9375rem" }}>Customer {customer.customer_id.slice(-4)}</div>
                  {customer.opt_out && <span className="status-badge status-stopped">Opted Out</span>}
                  <Link href={`/customers/${customer.customer_id}`} onClick={(e) => e.stopPropagation()} style={{ fontSize: "0.6875rem", color: "var(--accent)", textDecoration: "none" }}>
                    Open →
                  </Link>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {customer.customer_id}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>At Risk</div>
                <div style={{ fontWeight: 700, fontSize: "1.0625rem", color: "var(--danger)" }}>{fmt(customer.revenue_at_risk)}</div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", marginBottom: "0.75rem" }}>
              <MetricCell label="Total Cases" value={String(customer.total_cases)} accent="var(--text-primary)" />
              <MetricCell label="Actually Recovered" value={fmt(customer.actually_recovered)} accent="var(--success)" />
              <MetricCell label="Active Cases" value={String(customer.active_cases)} accent="var(--accent)" />
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "var(--text-secondary)", flexWrap: "wrap", gap: "0.5rem" }}>
              <span>
                {customer.promises && customer.promises.length > 0 ? (
                  <span style={{ color: "var(--warning)" }}>{customer.promises.length} promises</span>
                ) : (
                  `${customer.cases.length} case${customer.cases.length !== 1 ? "s" : ""}`
                )}
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                Last activity: {customer.last_action_at ? new Date(customer.last_action_at).toLocaleString() : "Unknown"}
              </span>
            </div>
          </div>
        ))}
      </div>

      {selectedCustomer && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.75rem" }}>
            Cases for Customer {selectedCustomer.customer_id.slice(-4)}
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
