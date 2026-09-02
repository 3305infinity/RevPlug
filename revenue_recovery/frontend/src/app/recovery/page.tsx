"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, RecoveryItem, DashboardSummary } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import CreateCaseModal from "@/components/recovery/CreateCaseModal";
import CapitalProtectedPanel from "@/components/dashboard/CapitalProtectedPanel";

type StatusFilter = "all" | "at_risk" | "recovering" | "awaiting_customer" | "recovered" | "escalated" | "stopped" | "failed";

export default function RecoveryInboxPage() {
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [itemsData, summaryData] = await Promise.all([
        api.items(),
        api.summary().catch(() => null),
      ]);
      setItems(Array.isArray(itemsData) ? itemsData : []);
      setSummary(summaryData);
      setErrorMsg("");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load recovery inbox");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCaseCreated = (newItem: any) => {
    setItems((prev) => [newItem, ...prev]);
  };

  // Filter & sort primarily by Expected Net Recovery (EV_net) descending
  const filteredAndSortedItems = useMemo(() => {
    let result = [...items];

    // Status filtering
    if (statusFilter !== "all") {
      result = result.filter((i) => {
        if (statusFilter === "at_risk") return i.status === "queued" || i.status === "detected";
        if (statusFilter === "recovering") return i.status === "intervention_pending" || i.status === "intervention_executed";
        if (statusFilter === "awaiting_customer") return i.status === "pending_verification";
        if (statusFilter === "recovered") return i.status === "recovered";
        if (statusFilter === "escalated") return i.status === "escalated";
        if (statusFilter === "stopped") return i.status === "stopped";
        if (statusFilter === "failed") return i.status === "failed";
        return i.status === statusFilter;
      });
    }

    // Search query filtering
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (i) =>
          i.id.toLowerCase().includes(q) ||
          i.customer_id.toLowerCase().includes(q) ||
          String(i.metadata?.customer_name || "").toLowerCase().includes(q) ||
          (i.root_cause || "").toLowerCase().includes(q) ||
          (i.external_id || "").toLowerCase().includes(q)
      );
    }

    // Sort primarily by Expected Net Recovery (EV_net) descending
    return result.sort((a, b) => {
      const evA = a.expected_recovery_value ?? Math.round(a.amount_minor * (a.recovery_probability ?? 0.65));
      const evB = b.expected_recovery_value ?? Math.round(b.amount_minor * (b.recovery_probability ?? 0.65));
      return evB - evA;
    });
  }, [items, statusFilter, searchQuery]);

  const fmt = (minor: number) =>
    "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const totalAtRisk = useMemo(
    () => items.filter((i) => i.status !== "recovered" && i.status !== "stopped").reduce((acc, i) => acc + i.amount_minor, 0),
    [items]
  );

  const totalRecovered = useMemo(
    () => summary?.actually_recovered ?? items.reduce((acc, i) => acc + (i.actual_recovery_value || 0), 0),
    [summary, items]
  );

  const expectedRecoverable = useMemo(
    () =>
      items
        .filter((i) => i.status !== "recovered" && i.status !== "stopped")
        .reduce((acc, i) => acc + (i.expected_recovery_value || 0), 0),
    [items]
  );

  return (
    <div style={{ maxWidth: 1180, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* INBOX HEADER & PRIMARY ACTIONS */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            REVENUE OPERATIONS INBOX
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
            Recovery Case Queue
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Persisted recovery items ranked strictly by Expected Net Recovery (Net EV) and business priority.
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            onClick={() => setIsModalOpen(true)}
            style={{
              background: "#10b981",
              color: "#fff",
              border: "none",
              padding: "0.6rem 1.25rem",
              borderRadius: 6,
              fontWeight: 700,
              fontSize: "0.8125rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span>+</span> Create Recovery Case
          </button>

          <Link
            href="/run-recovery"
            style={{
              background: "var(--bg-secondary)",
              color: "var(--text-primary)",
              border: "1px solid var(--border)",
              padding: "0.6rem 1.15rem",
              borderRadius: 6,
              fontWeight: 600,
              fontSize: "0.8125rem",
              textDecoration: "none",
            }}
          >
            Single Case Control Plane →
          </Link>
        </div>
      </div>

      {/* METRIC OVERVIEW CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>REVENUE AT RISK</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#ef4444", marginTop: 4, fontFamily: "monospace" }}>{fmt(totalAtRisk)}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>{items.filter((i) => i.status !== "recovered" && i.status !== "stopped").length} active cases</div>
        </div>

        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>EXPECTED RECOVERABLE</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#3b82f6", marginTop: 4, fontFamily: "monospace" }}>{fmt(expectedRecoverable)}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>Based on Net EV scoring</div>
        </div>

        <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>VERIFIED RECOVERED</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#10b981", marginTop: 4, fontFamily: "monospace" }}>{fmt(totalRecovered)}</div>
          <div style={{ fontSize: "0.75rem", color: "#10b981", marginTop: 2 }}>HMAC verified settlement</div>
        </div>

        <div style={{ padding: "1rem", background: "linear-gradient(135deg, rgba(251, 191, 36, 0.10) 0%, rgba(245, 158, 11, 0.05) 100%)", borderRadius: 8, border: "1px solid rgba(251, 191, 36, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#f59e0b", textTransform: "uppercase", fontWeight: 700 }}>🛡 CAPITAL PROTECTED</div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#fbbf24", marginTop: 4, fontFamily: "monospace" }}>
            {fmt(items.filter((i) => i.status === "stopped" || i.status === "escalated").reduce((acc, i) => acc + i.amount_minor, 0))}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
            {items.filter((i) => i.status === "stopped" || i.status === "escalated").length} policy-blocked cases
          </div>
        </div>
      </div>

      {/* CAPITAL PROTECTED DETAIL PANEL */}
      <div style={{ marginBottom: "1.5rem" }}>
        <CapitalProtectedPanel />
      </div>

      {/* FILTER TOOLBAR & SEARCH BAR */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          {/* STATUS CHIPS */}
          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
            {[
              { id: "all", label: "All Cases" },
              { id: "at_risk", label: "At Risk" },
              { id: "recovering", label: "Recovering" },
              { id: "awaiting_customer", label: "Awaiting Customer" },
              { id: "recovered", label: "Recovered" },
              { id: "escalated", label: "Human Escalation" },
              { id: "stopped", label: "Policy Blocked" },
            ].map((chip) => {
              const active = statusFilter === chip.id;
              return (
                <button
                  key={chip.id}
                  onClick={() => setStatusFilter(chip.id as StatusFilter)}
                  style={{
                    padding: "0.35rem 0.75rem",
                    borderRadius: 20,
                    fontSize: "0.75rem",
                    fontWeight: active ? 700 : 500,
                    background: active ? "var(--accent)" : "var(--bg-primary)",
                    color: active ? "#fff" : "var(--text-secondary)",
                    border: active ? "1px solid var(--accent)" : "1px solid var(--border)",
                    cursor: "pointer",
                  }}
                >
                  {chip.label}
                </button>
              );
            })}
          </div>

          {/* SEARCH INPUT */}
          <input
            type="text"
            placeholder="Search by customer, invoice, ID, or root cause..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: "0.45rem 0.85rem",
              borderRadius: 6,
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              fontSize: "0.75rem",
              width: 320,
            }}
          />
        </div>
      </div>

      {/* RECOVERY INBOX TABLE */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "1rem" }}>
          ACTIVE RECOVERY QUEUE ({filteredAndSortedItems.length} CASES)
        </div>

        {loading ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>Loading recovery items...</div>
        ) : errorMsg ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>{errorMsg}</div>
        ) : filteredAndSortedItems.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>No recovery cases match criteria.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ background: "var(--bg-primary)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>CASE &amp; CUSTOMER</th>
                <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>AMOUNT AT RISK</th>
                <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>FAILURE / CAUSE</th>
                <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>EXPECTED NET EV</th>
                <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>PRIORITY</th>
                <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>STATUS</th>
                <th style={{ padding: "0.75rem", color: "var(--text-muted)" }}>POLICY &amp; ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedItems.map((item) => {
                const expVal = item.expected_recovery_value ?? null;
                // Build concise evidence tag
                const causeRaw = item.root_cause || "";
                let evidence = "Awaiting diagnosis";
                if (causeRaw.includes("hard") || causeRaw.includes("decline")) evidence = "Hard decline · Stop";
                else if (causeRaw.includes("fraud")) evidence = "Fraud flag · Blocked";
                else if (causeRaw.includes("auth") || causeRaw.includes("transient") || causeRaw.includes("timeout")) evidence = "Transient failure · Retry allowed";
                else if (causeRaw.includes("dispute")) evidence = "Dispute · Policy restricted";
                else if (causeRaw.includes("opt")) evidence = "Opt-out · Blocked";
                else if (causeRaw) evidence = causeRaw.replace(/_/g, " ");
                return (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.75rem" }}>
                      <div style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.875rem" }}>
                        {getCustomerDisplayName(item.customer_id, (item as any).customer_name || item.metadata?.customer_name)}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
                        Ref: <Link href={`/recovery/${item.id}`} style={{ color: "var(--accent)", fontFamily: "monospace" }}>{item.id}</Link>
                      </div>
                    </td>

                    <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: "var(--text-primary)" }}>
                      {fmt(item.amount_minor)}
                    </td>

                    <td style={{ padding: "0.75rem" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.8125rem" }}>{item.root_cause?.replace(/_/g, " ") || "—"}</div>
                      <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: 2 }}>{evidence}</div>
                    </td>

                    <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: expVal ? "#10b981" : "var(--text-muted)" }}>
                      {expVal ? fmt(expVal) : "—"}
                    </td>

                    <td style={{ padding: "0.75rem" }}>
                      <span
                        style={{
                          fontSize: "0.6875rem",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontWeight: 700,
                          background: (item as any).priority === "CRITICAL" ? "rgba(239, 68, 68, 0.15)" : (item as any).priority === "HIGH" ? "rgba(245, 158, 11, 0.15)" : "rgba(59, 130, 246, 0.15)",
                          color: (item as any).priority === "CRITICAL" ? "#ef4444" : (item as any).priority === "HIGH" ? "#f59e0b" : "#3b82f6",
                        }}
                      >
                        {(item as any).priority || "HIGH"}
                      </span>
                    </td>

                    <td style={{ padding: "0.75rem" }}>
                      <span className={`status-badge status-${item.status}`}>
                        {item.status.replace(/_/g, " ")}
                      </span>
                    </td>

                    <td style={{ padding: "0.75rem", fontSize: "0.75rem" }}>
                      <div style={{ color: item.status === "stopped" ? "#ef4444" : "var(--text-primary)", fontWeight: 600 }}>
                        {item.status === "stopped" ? (item.stopped_reason || "Policy Blocked") : "Allowed by Policy"}
                      </div>
                      <Link href={`/recovery/${item.id}`} style={{ color: "var(--accent)", fontSize: "0.7rem", textDecoration: "none", marginTop: 2, display: "inline-block" }}>
                        Inspect Trace →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* CREATE CASE MODAL */}
      <CreateCaseModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleCaseCreated}
      />
    </div>
  );
}
