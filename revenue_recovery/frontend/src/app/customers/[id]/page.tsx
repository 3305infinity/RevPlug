"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, RecoveryItem } from "@/lib/api";

type Status = "loading" | "error" | "ready";

interface CustomerData {
  customer_id: string;
  total_cases: number;
  revenue_at_risk: number;
  recovered: number;
  cases: RecoveryItem[];
}

export default function CustomerDetail() {
  const params = useParams();
  const customerId = params?.id as string;
  const [status, setStatus] = useState<Status>("loading");
  const [data, setData] = useState<CustomerData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!customerId) return;
    api.customerDetail(customerId)
      .then(setData)
      .catch(() => setError("Customer not found"))
      .finally(() => setStatus("ready"));
  }, [customerId]);

  const fmt = (n: number) => "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  if (status === "error" || error) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🔍</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Customer not found</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <Link href="/customers" className="btn-primary">Back to Customers</Link>
      </div>
    );
  }

  if (status === "loading" || !data) {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
        </div>
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  const recoveredCases = data.cases.filter((c) => c.status === "recovered");
  const activeCases = data.cases.filter((c) => !["recovered", "stopped"].includes(c.status));
  const failedCases = data.cases.filter((c) => ["escalated", "failed"].includes(c.status));

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link href="/customers" style={{ fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none" }}>
          ← Customers
        </Link>
      </div>

      <div className="card" style={{ padding: "2rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
              Customer Account
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, fontFamily: "monospace", marginBottom: "0.25rem" }}>
              {data.customer_id}
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              {data.total_cases} total case{data.total_cases !== 1 ? "s" : ""}
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1.5rem" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.25rem" }}>Revenue at Risk</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--danger)", fontFamily: "monospace" }}>{fmt(data.revenue_at_risk)}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.25rem" }}>Recovered</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--success)", fontFamily: "monospace" }}>{fmt(data.recovered)}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.25rem" }}>Active Cases</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)", fontFamily: "monospace" }}>{activeCases.length}</div>
            </div>
          </div>
        </div>
      </div>

      {failedCases.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--danger)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Needs Attention ({failedCases.length})
          </h3>
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {failedCases.map((item) => (
              <div key={item.id} className="card" style={{ padding: "1.25rem", borderLeft: "3px solid var(--danger)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.25rem" }}>
                      <Link href={`/recovery/${item.id}`} style={{ fontWeight: 600, fontSize: "0.875rem", fontFamily: "monospace", color: "var(--accent)", textDecoration: "none" }}>
                        {item.id}
                      </Link>
                      <span className={`status-badge status-${item.status}`}>{item.status.replace(/_/g, " ")}</span>
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {item.root_cause || "unknown"} · {fmt(item.amount_minor)}
                    </div>
                  </div>
                  <Link href={`/recovery/${item.id}`} className="btn-secondary" style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem" }}>
                    Review
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeCases.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Active Cases ({activeCases.length})
          </h3>
          <div className="card" style={{ overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <Th>Case ID</Th>
                  <Th>Failure</Th>
                  <Th>Amount</Th>
                  <Th>Status</Th>
                  <Th>Expected</Th>
                </tr>
              </thead>
              <tbody>
                {activeCases.map((item) => (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <Td>
                      <Link href={`/recovery/${item.id}`} style={{ color: "var(--accent)", textDecoration: "none", fontFamily: "monospace", fontSize: "0.75rem" }}>
                        {item.id}
                      </Link>
                    </Td>
                    <Td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>{item.root_cause || "—"}</Td>
                    <Td style={{ fontFamily: "monospace", fontSize: "0.8125rem" }}>{fmt(item.amount_minor)}</Td>
                    <Td><span className={`status-badge status-${item.status}`}>{item.status.replace(/_/g, " ")}</span></Td>
                    <Td style={{ fontFamily: "monospace", fontSize: "0.8125rem" }}>{item.expected_recovery_value ? fmt(item.expected_recovery_value) : "—"}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {recoveredCases.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
            Recovered Cases ({recoveredCases.length})
          </h3>
          <div className="card" style={{ overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <Th>Case ID</Th>
                  <Th>Failure</Th>
                  <Th>Amount</Th>
                  <Th>Recovered</Th>
                </tr>
              </thead>
              <tbody>
                {recoveredCases.map((item) => (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <Td>
                      <Link href={`/recovery/${item.id}`} style={{ color: "var(--accent)", textDecoration: "none", fontFamily: "monospace", fontSize: "0.75rem" }}>
                        {item.id}
                      </Link>
                    </Td>
                    <Td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>{item.root_cause || "—"}</Td>
                    <Td style={{ fontFamily: "monospace", fontSize: "0.8125rem" }}>{fmt(item.amount_minor)}</Td>
                    <Td style={{ color: "var(--success)", fontWeight: 600, fontSize: "0.875rem" }}>
                      {fmt(item.expected_recovery_value || item.amount_minor)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data.cases.length === 0 && (
        <div className="card" style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ fontSize: "0.875rem" }}>No recovery cases for this customer.</p>
        </div>
      )}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ padding: "0.875rem 1.25rem", textAlign: "left", fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", background: "var(--bg-secondary)" }}>{children}</th>;
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ padding: "0.875rem 1.25rem", fontSize: "0.8125rem", ...style }}>{children}</td>;
}
