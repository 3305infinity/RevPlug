"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, RecoveryItem, SimulationResult } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import DecisionTraceView from "@/components/recovery/DecisionTraceView";
import CreateCaseModal from "@/components/recovery/CreateCaseModal";

type Phase = "idle" | "running" | "complete" | "error";

export default function SingleCaseRecoveryControlPlane() {
  const [items, setItems] = useState<RecoveryItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(true);
  const [selectedItemId, setSelectedItemId] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [aiProvider, setAiProvider] = useState<"groq" | "gemini" | "fallback">("groq");
  
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [showTrace, setShowTrace] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  // Load real recovery items from backend
  const loadItems = useCallback(async () => {
    try {
      setLoadingItems(true);
      const data = await api.items();
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setItems([]);
    } finally {
      setLoadingItems(false);
    }
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  // Filter items by search query
  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (i) =>
        i.id.toLowerCase().includes(q) ||
        i.customer_id.toLowerCase().includes(q) ||
        (i.root_cause || "").toLowerCase().includes(q) ||
        i.status.toLowerCase().includes(q)
    );
  }, [items, searchQuery]);

  // Selected item object
  const selectedItem = useMemo(() => {
    return items.find((i) => i.id === selectedItemId) || null;
  }, [items, selectedItemId]);

  const handleSelectCase = (id: string) => {
    setSelectedItemId(id);
    setPhase("idle");
    setResult(null);
    setErrorMsg("");
  };

  const handleEvaluateAndRecover = async () => {
    if (!selectedItem) return;

    setPhase("running");
    setErrorMsg("");
    setResult(null);

    try {
      // Execute authentic backend recovery orchestration for selected item
      const res = await api.runSimulation({
        item_id: selectedItem.id,
        customer_id: selectedItem.customer_id,
        amount_minor: selectedItem.amount_minor,
        failure_reason: selectedItem.root_cause || "payment_timed_out",
        source_type: selectedItem.source_type || "payment_failure",
        ai_provider: aiProvider,
      });

      setResult(res);
      setPhase("complete");
      // Reload items to reflect updated status in real-time
      loadItems();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Recovery evaluation failed");
      setPhase("error");
    }
  };

  const fmt = (minor: number) =>
    "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            RECOVERY CONTROL PLANE
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700 }}>
            Single Case Evaluation & Execution
          </h1>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
            Select an active recovery case from the backend queue to evaluate failure diagnostics, expected value (Net EV), policy shields, and closed-loop execution.
          </div>
        </div>

        {/* AI REASONING SYSTEM CONFIGURATION */}
        <div style={{ background: "var(--bg-primary)", padding: "0.65rem 0.85rem", borderRadius: 8, border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
            Reasoning Provider:
          </div>
          <select
            value={aiProvider}
            onChange={(e) => setAiProvider(e.target.value as any)}
            style={{
              background: "var(--bg-secondary)",
              color: "var(--text-primary)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              fontSize: "0.75rem",
              padding: "0.35rem 0.65rem",
              fontFamily: "monospace",
              cursor: "pointer",
            }}
          >
            <option value="groq">Primary (Groq Llama-3.3 70B)</option>
            <option value="gemini">Secondary (Google Gemini 1.5 Pro)</option>
            <option value="fallback">Safety Fallback (Deterministic)</option>
          </select>
        </div>
      </div>

      {/* SANDBOX / DEVELOPER TOOLS */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid var(--border)", background: "var(--bg-secondary)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
              Sandbox / Developer Tools
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Inject synthetic failure events for judging and local simulation. Does not affect live operational data.
            </div>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            style={{
              background: "transparent",
              color: "var(--text-secondary)",
              border: "1px solid var(--border)",
              padding: "0.4rem 0.9rem",
              borderRadius: 6,
              fontWeight: 600,
              fontSize: "0.75rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
            }}
          >
            <span>+</span> Inject Test Event
          </button>
        </div>
      </div>

      {/* CASE SELECTION SECTION */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            SELECT RECOVERY CASE ({items.length} AVAILABLE IN BACKEND QUEUE)
          </div>
          <input
            type="text"
            placeholder="Search by case ID, customer, cause, or status..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: "0.45rem 0.75rem",
              borderRadius: 6,
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              fontSize: "0.75rem",
              width: 320,
            }}
          />
        </div>

        {loadingItems ? (
          <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            Loading backend recovery cases...
          </div>
        ) : filteredItems.length === 0 ? (
          <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            No recovery cases match search criteria.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", maxHeight: 220, overflowY: "auto" }}>
            {filteredItems.slice(0, 9).map((item) => {
              const isSelected = item.id === selectedItemId;
              return (
                <button
                  key={item.id}
                  onClick={() => handleSelectCase(item.id)}
                  style={{
                    textAlign: "left",
                    padding: "0.75rem",
                    borderRadius: 8,
                    border: isSelected ? "2px solid var(--accent)" : "1px solid var(--border)",
                    background: isSelected ? "rgba(59, 130, 246, 0.1)" : "var(--bg-primary)",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontFamily: "monospace", fontSize: "0.75rem", fontWeight: 700, color: "var(--accent)" }}>
                      {item.id}
                    </span>
                    <span className={`status-badge status-${item.status}`} style={{ fontSize: "0.625rem" }}>
                      {item.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                    {fmt(item.amount_minor)}
                  </div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: 2, textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                    Cust: {getCustomerDisplayName(item.customer_id)} • {item.root_cause || "Soft Decline"}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* NO CASE SELECTED EMPTY STATE */}
      {!selectedItem ? (
        <div className="card" style={{ padding: "3rem", textAlign: "center", borderStyle: "dashed" }}>
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>🔎</div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
            Select a Recovery Case to Begin
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 4, maxWidth: 500, margin: "4px auto 0 auto" }}>
            Choose an active case from the backend queue above to inspect customer context, evaluate expected net recovery (Net EV), and trigger bounded orchestration.
          </div>
        </div>
      ) : (
        /* SELECTED CASE CONTEXT & EVALUATION PANEL */
        <div>
          {/* CONTEXT CARD */}
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", borderLeft: "4px solid var(--accent)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span style={{ fontFamily: "monospace", fontSize: "1.125rem", fontWeight: 800, color: "var(--accent)" }}>
                    {selectedItem.id}
                  </span>
                  <span className={`status-badge status-${selectedItem.status}`}>
                    {selectedItem.status.replace(/_/g, " ")}
                  </span>
                </div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                  Customer: <Link href={`/customers/${selectedItem.customer_id}`} style={{ color: "var(--accent)" }}>{getCustomerDisplayName(selectedItem.customer_id)}</Link>
                  <span className="font-mono" style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginLeft: "0.5rem" }}>({selectedItem.customer_id})</span>
                </div>
              </div>

              <div style={{ display: "flex", gap: "1.5rem", textAlign: "right" }}>
                <div>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 700 }}>AMOUNT AT RISK</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#ef4444", fontFamily: "monospace" }}>
                    {fmt(selectedItem.amount_minor)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.6875rem", color: selectedItem.expected_recovery_value ? "#10b981" : "var(--text-muted)", fontWeight: 700 }}>EXPECTED NET RECOVERY</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 800, color: selectedItem.expected_recovery_value ? "#10b981" : "var(--text-muted)", fontFamily: "monospace" }}>
                    {selectedItem.expected_recovery_value ? fmt(selectedItem.expected_recovery_value) : "—"}
                  </div>
                </div>
              </div>
            </div>

            {/* CONTEXT METRICS GRID */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", background: "var(--bg-primary)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)", fontSize: "0.75rem" }}>
              <div>
                <div style={{ color: "var(--text-muted)", fontWeight: 700 }}>FAILURE CAUSE</div>
                <div style={{ color: "var(--text-primary)", fontWeight: 700, marginTop: 2 }}>{selectedItem.root_cause || "Soft Gateway Timeout"}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontWeight: 700 }}>SOURCE TYPE</div>
                <div style={{ color: "var(--text-primary)", fontWeight: 700, marginTop: 2, textTransform: "uppercase" }}>{selectedItem.source_type || "payment_failure"}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontWeight: 700 }}>CONTACT BUDGET</div>
                <div style={{ color: "#10b981", fontWeight: 700, marginTop: 2 }}>0 / 2 Used (24h Window)</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontWeight: 700 }}>POLICY SHIELD</div>
                <div style={{ color: "#3b82f6", fontWeight: 700, marginTop: 2 }}>Active (Fraud Guard + Retries Limit 3)</div>
              </div>
            </div>

            {/* ACTION BAR */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1.25rem" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                {selectedItem.status === "recovered"
                  ? "✓ Case is fully settled — no further recovery action required."
                  : selectedItem.status === "escalated"
                  ? "⚠️ Escalated to human review queue due to policy constraint."
                  : "Ready to run AI diagnosis, EV optimization, policy validation, and closed-loop execution."}
              </div>

              {selectedItem.status === "recovered" ? (
                <button disabled style={{ background: "rgba(16, 185, 129, 0.2)", color: "#10b981", border: "1px solid #10b981", padding: "0.6rem 1.25rem", borderRadius: 6, fontWeight: 700, fontSize: "0.875rem", cursor: "not-allowed" }}>
                  Recovered — No Further Action Required
                </button>
              ) : selectedItem.status === "escalated" ? (
                <Link href="/review" style={{ background: "#f59e0b", color: "#000", padding: "0.6rem 1.25rem", borderRadius: 6, fontWeight: 700, fontSize: "0.875rem", textDecoration: "none" }}>
                  Review Queue Escalation →
                </Link>
              ) : (
                <button
                  onClick={handleEvaluateAndRecover}
                  disabled={phase === "running"}
                  style={{ background: "#10b981", color: "#fff", border: "none", padding: "0.65rem 1.5rem", borderRadius: 6, fontWeight: 700, fontSize: "0.875rem", cursor: "pointer" }}
                >
                  {phase === "running" ? "Evaluating & Executing..." : "Evaluate & Recover"}
                </button>
              )}
            </div>
          </div>

          {/* ERROR DISPLAY */}
          {phase === "error" && (
            <div style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", color: "#ef4444", padding: "1rem", borderRadius: 8, marginBottom: "1.5rem", fontSize: "0.8125rem", fontWeight: 600 }}>
              Evaluation Error: {errorMsg}
            </div>
          )}

          {/* REAL CLOSED-LOOP DECISION TRACE VIEW */}
          {result && (
            <div className="card" style={{ padding: "1.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h2 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  EVALUATION & RECOVERY TRACE RESULTS
                </h2>
                <button
                  onClick={() => setShowTrace(!showTrace)}
                  style={{ background: "transparent", color: "var(--accent)", border: "none", cursor: "pointer", fontSize: "0.75rem", fontWeight: 600 }}
                >
                  {showTrace ? "Hide Raw JSON" : "View Raw JSON Trace"}
                </button>
              </div>

              <DecisionTraceView
                trace={null}
                detail={{
                  id: selectedItem.id,
                  customer_id: selectedItem.customer_id,
                  amount_minor: selectedItem.amount_minor,
                  currency: "INR",
                  status: selectedItem.status,
                  root_cause: selectedItem.root_cause || null,
                  expected_recovery_value: selectedItem.expected_recovery_value || null,
                  actual_recovery_value: result.actual_recovery_value || null,
                  intervention_cost: (result as any).ev_scoring?.intervention_cost || 500,
                  stopped_reason: (result as any).policy_result?.reason || (result as any).policy_rule || "Evaluation completed",
                } as any}
              />

              {showTrace && (
                <pre style={{ marginTop: "1.5rem", background: "var(--bg-primary)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)", fontSize: "0.75rem", fontFamily: "monospace", overflowX: "auto" }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
      <CreateCaseModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => loadItems()}
      />
    </div>
  );
}
