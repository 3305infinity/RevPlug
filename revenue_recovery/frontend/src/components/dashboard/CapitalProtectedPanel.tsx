"use client";

import { useEffect, useState } from "react";

interface BreakdownEntry {
  reason: string;
  label: string;
  count: number;
  amount_minor: number;
}

interface ItemizedCase {
  id: string;
  customer_id: string;
  customer_name: string;
  amount_minor: number;
  status: string;
  block_reason: string;
  block_reason_label: string;
  human_readable_line: string;
}

interface CapitalProtectedData {
  total_capital_protected_minor: number;
  case_count: number;
  breakdown_by_reason: BreakdownEntry[];
  itemized_cases: ItemizedCase[];
}

const fmt = (minor: number) =>
  "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

interface Props {
  apiHost?: string;
  compact?: boolean;
}

export default function CapitalProtectedPanel({ apiHost, compact = false }: Props) {
  const [data, setData] = useState<CapitalProtectedData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  const host = apiHost || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    fetch(`${host}/api/portfolio/capital-protected`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [host]);

  if (loading) {
    return (
      <div style={{ padding: compact ? "0.75rem" : "1.25rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
        <div className="skeleton" style={{ height: 40, borderRadius: 6 }} />
      </div>
    );
  }

  if (!data) return null;

  const total = data.total_capital_protected_minor || 0;
  const count = data.case_count || 0;
  const breakdown = Array.isArray(data.breakdown_by_reason) ? data.breakdown_by_reason : [];
  const itemized = Array.isArray(data.itemized_cases) ? data.itemized_cases : [];

  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: compact ? "0.875rem 1rem" : "1.25rem 1.5rem",
      }}
    >
      {/* HEADER ROW */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--warning)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            CAPITAL PROTECTED
          </div>
          <div className="font-mono" style={{ fontSize: compact ? "1.5rem" : "1.75rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2, lineHeight: 1.2 }}>
            {fmt(total)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
            {count} case{count !== 1 ? "s" : ""} safely declined by policy
          </div>
        </div>

        {!compact && count > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              borderRadius: 6,
              padding: "0.35rem 0.75rem",
              fontSize: "0.75rem",
              fontWeight: 500,
              cursor: "pointer",
              transition: "background 0.15s ease, color 0.15s ease",
            }}
          >
            {expanded ? "Hide ▲" : "Details ▼"}
          </button>
        )}
      </div>

      {/* REASON SUMMARY BREAKDOWN */}
      {!compact && breakdown.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: "1.25rem",
            flexWrap: "wrap",
            marginTop: "0.875rem",
            paddingTop: "0.75rem",
            borderTop: "1px solid var(--border-subtle)",
            fontSize: "0.75rem",
            color: "var(--text-secondary)",
            fontFamily: "monospace",
          }}
        >
          {breakdown.map((b) => {
            const isHard = b.reason === "hard_decline" || b.reason === "fraud";
            const reasonColor = isHard ? "var(--danger)" : "var(--text-secondary)";
            return (
              <span key={b.reason} style={{ color: reasonColor }}>
                {b.label}: {b.count} ({fmt(b.amount_minor)})
              </span>
            );
          })}
        </div>
      )}

      {/* ITEMIZED DECLINE LOG TABLE */}
      {!compact && expanded && itemized.length > 0 && (
        <div style={{ marginTop: "1rem", paddingTop: "0.875rem", borderTop: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
            ITEMIZED DECLINE LOG
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                <th style={{ padding: "0.5rem 0.75rem", width: 120 }}>AMOUNT</th>
                <th style={{ padding: "0.5rem 0.75rem", width: 200 }}>CUSTOMER</th>
                <th style={{ padding: "0.5rem 0.75rem" }}>POLICY DECLINE REASON</th>
              </tr>
            </thead>
            <tbody>
              {itemized.slice(0, 10).map((item) => {
                const isHard = item.block_reason === "hard_decline" || item.block_reason === "fraud";
                const reasonLabel = item.block_reason_label || item.block_reason.replace(/_/g, " ");
                const reasonColor = isHard ? "var(--danger)" : "var(--text-secondary)";

                return (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td className="font-mono" style={{ padding: "0.5rem 0.75rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      {fmt(item.amount_minor)}
                    </td>
                    <td style={{ padding: "0.5rem 0.75rem", color: "var(--text-primary)", fontWeight: 500 }}>
                      {item.customer_name || item.customer_id}
                    </td>
                    <td style={{ padding: "0.5rem 0.75rem", color: reasonColor }}>
                      {reasonLabel}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {itemized.length > 10 && (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center", paddingTop: "0.5rem" }}>
              +{itemized.length - 10} more policy-declined cases
            </div>
          )}
        </div>
      )}
    </div>
  );
}
