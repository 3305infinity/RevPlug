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

const REASON_COLORS: Record<string, string> = {
  fraud: "#ef4444",
  opt_out: "#f59e0b",
  hard_decline: "#6366f1",
  promise_active: "#3b82f6",
  negative_ev: "#8b5cf6",
  human_review: "#14b8a6",
};

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
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [host]);

  if (loading) {
    return (
      <div style={{ padding: compact ? "0.75rem" : "1.25rem", background: "rgba(251, 191, 36, 0.05)", borderRadius: 8, border: "1px solid rgba(251, 191, 36, 0.2)" }}>
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
        background: "linear-gradient(135deg, rgba(251, 191, 36, 0.08) 0%, rgba(245, 158, 11, 0.04) 100%)",
        border: "1px solid rgba(251, 191, 36, 0.3)",
        borderRadius: 10,
        padding: compact ? "0.875rem 1rem" : "1.25rem 1.5rem",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ position: "absolute", top: -20, right: -20, width: 100, height: 100, background: "radial-gradient(circle, rgba(251, 191, 36, 0.12) 0%, transparent 70%)", borderRadius: "50%", pointerEvents: "none" }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: compact ? 0 : "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 2 }}>
            🛡 CAPITAL PROTECTED
          </div>
          <div className="font-mono" style={{ fontSize: compact ? "1.5rem" : "2rem", fontWeight: 900, color: "#fbbf24", lineHeight: 1 }}>
            {fmt(total)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 3 }}>
            {count} case{count !== 1 ? "s" : ""} safely declined by policy
          </div>
        </div>

        {!compact && count > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{ background: "transparent", border: "1px solid rgba(251, 191, 36, 0.3)", color: "#f59e0b", borderRadius: 6, padding: "0.3rem 0.65rem", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}
          >
            {expanded ? "Hide ▲" : "Details ▼"}
          </button>
        )}
      </div>

      {!compact && breakdown.length > 0 && (
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.75rem" }}>
          {breakdown.map((b) => (
            <div
              key={b.reason}
              title={`${b.label}: ${fmt(b.amount_minor)} (${b.count} cases)`}
              style={{ display: "flex", alignItems: "center", gap: "0.35rem", background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 20, padding: "0.2rem 0.65rem", fontSize: "0.7rem", fontWeight: 600, color: REASON_COLORS[b.reason] || "var(--text-secondary)" }}
            >
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: REASON_COLORS[b.reason] || "#888", flexShrink: 0 }} />
              {b.label} · {b.count} · {fmt(b.amount_minor)}
            </div>
          ))}
        </div>
      )}

      {!compact && expanded && itemized.length > 0 && (
        <div style={{ marginTop: "1rem", borderTop: "1px solid rgba(251, 191, 36, 0.15)", paddingTop: "0.875rem" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
            ITEMIZED DECLINE LOG
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            {itemized.slice(0, 10).map((item) => (
              <div key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.35rem 0.65rem", background: "var(--bg-secondary)", borderRadius: 6, fontSize: "0.75rem" }}>
                <span style={{ color: "var(--text-secondary)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {item.human_readable_line}
                </span>
                <span style={{ marginLeft: "0.75rem", flexShrink: 0, fontSize: "0.6875rem", fontWeight: 700, color: REASON_COLORS[item.block_reason] || "var(--text-muted)", background: "var(--bg-primary)", border: `1px solid ${REASON_COLORS[item.block_reason] || '#888'}44`, borderRadius: 4, padding: "1px 6px" }}>
                  {item.block_reason.replace(/_/g, " ").toUpperCase()}
                </span>
              </div>
            ))}
            {itemized.length > 10 && (
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center", paddingTop: "0.25rem" }}>
                +{itemized.length - 10} more cases
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
