"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { api, BatchSimulationResult } from "@/lib/api";

type Status = "loading" | "error" | "ready" | "running" | "complete";

const EVENT_TYPES = [
  { value: "payment_timed_out", label: "Gateway Timeout", category: "soft" },
  { value: "gateway_technical_error", label: "Gateway Technical Failure", category: "soft" },
  { value: "card_declined", label: "Hard Card Decline", category: "hard" },
  { value: "payment_risk_check_failed", label: "Fraud Signal", category: "fraud" },
  { value: "authentication_failed", label: "Authentication Required", category: "auth" },
  { value: "unknown_reason", label: "Unknown Failure", category: "unknown" },
];

export default function BatchRecovery() {
  const [status, setStatus] = useState<Status>("loading");
  const [count, setCount] = useState(50);
  const [errorReason, setErrorReason] = useState(EVENT_TYPES[0].value);
  const [baseAmount, setBaseAmount] = useState(50000);
  const [result, setResult] = useState<BatchSimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      setError(null);
      await new Promise((r) => setTimeout(r, 200));
      setStatus("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRun = async () => {
    setStatus("running");
    setError(null);
    setResult(null);
    try {
      const data = await api.batchDemo({
        count,
        error_reason: errorReason,
        amount_minor: baseAmount,
      });
      setResult(data);
      setStatus("complete");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Batch run failed");
      setStatus("error");
    }
  };

  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  const summary = result?.summary;

  if (status === "error" && !result) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to run batch</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={load} className="btn-primary">Retry</button>
      </div>
    );
  }

  const stoppedReasons = useMemo(() => {
    const map = new Map<string, number>();
    result?.results?.forEach((r) => {
      if (r.recovery_status === "stopped" && r.stopped_reason) {
        map.set(r.stopped_reason, (map.get(r.stopped_reason) || 0) + 1);
      }
    });
    return Array.from(map.entries()).map(([reason, count]) => ({ reason, count }));
  }, [result]);

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>Batch Recovery</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Run a recovery program across a portfolio of revenue-risk events.
        </p>
      </div>

      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.25rem", alignItems: "end" }}>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              Number of Cases
            </label>
            <select
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="input"
              style={{ width: "100%" }}
              disabled={status === "running"}
            >
              <option value={10}>10 cases</option>
              <option value={50}>50 cases</option>
              <option value={100}>100 cases</option>
              <option value={500}>500 cases</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              Failure Type
            </label>
            <select
              value={errorReason}
              onChange={(e) => setErrorReason(e.target.value)}
              className="input"
              style={{ width: "100%" }}
              disabled={status === "running"}
            >
              {EVENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "0.5rem" }}>
              Base Amount (₹)
            </label>
            <input
              type="number"
              value={baseAmount / 100}
              onChange={(e) => setBaseAmount(Math.max(100, Number(e.target.value) * 100))}
              className="input"
              style={{ width: "100%" }}
              min={1}
              disabled={status === "running"}
            />
          </div>
        </div>
        <div style={{ marginTop: "1.25rem", display: "flex", alignItems: "center", gap: "1rem" }}>
          <button
            onClick={handleRun}
            disabled={status === "running"}
            className="btn-primary"
            style={{ fontSize: "0.8125rem", padding: "0.75rem 1.5rem" }}
          >
            {status === "running" ? "Processing batch..." : "Run Batch Recovery"}
          </button>
          {status === "running" && (
            <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              Processing {count} cases...
            </span>
          )}
        </div>
      </div>

      {error && status !== "running" && (
        <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.25rem", background: "var(--danger-subtle)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div style={{ color: "var(--danger)", fontSize: "0.8125rem" }}>{error}</div>
        </div>
      )}

      {summary && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
            <Metric label="Revenue at Risk" value={fmt(summary.total_cases * baseAmount)} sub={`${summary.total_cases} cases`} accent="var(--danger)" />
            <Metric label="Actually Recovered" value={fmt(summary.recovered_amount_minor)} sub={`${summary.recovered_count} cases`} accent="var(--success)" />
            <Metric label="Recovery Rate" value={`${(summary.recovery_rate * 100).toFixed(1)}%`} sub="of eligible cases" accent="var(--accent)" />
            <Metric label="Escalated" value={String(summary.escalated_count)} sub="needs human review" accent="var(--warning)" />
            <Metric label="Stopped" value={String(summary.stopped_count)} sub="policy blocked" accent="var(--text-muted)" />
          </div>

          {summary.recovered_amount_minor > 0 && (
            <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", borderLeft: `3px solid var(--success)` }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--success)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
                Total Recovered
              </div>
              <div style={{ fontSize: "2.25rem", fontWeight: 700, color: "var(--success)", fontFamily: "monospace", letterSpacing: "-0.03em", lineHeight: 1.2 }}>
                {fmt(summary.recovered_amount_minor)}
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                {summary.recovered_count} of {summary.total_cases} cases recovered · vs {fmt(summary.total_cases * baseAmount)} at risk
              </div>
            </div>
          )}

          {stoppedReasons.length > 0 && (
            <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "1rem" }}>
                Why Recovery Stopped
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
                {stoppedReasons.map((r) => (
                  <div key={r.reason} style={{ padding: "0.75rem 1rem", background: "var(--bg-tertiary)", borderRadius: 8 }}>
                    <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", textTransform: "capitalize", marginBottom: "0.25rem" }}>
                      {r.reason === "fraud_detected" ? "Fraud (Policy Block)" :
                       r.reason === "retry_limit_exhausted" ? "Retry Limit Exhausted" :
                       r.reason === "deadline_exceeded" ? "Deadline Exceeded" :
                       r.reason === "opt_out" ? "Customer Opt-out" :
                       r.reason === "promise_expired" ? "Promise Expired" :
                       r.reason.replace(/_/g, " ")}
                    </div>
                    <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--danger)", fontFamily: "monospace" }}>{r.count}</div>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>cases stopped</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="card" style={{ overflow: "hidden" }}>
            <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Case Results
              </h3>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <Th>Case ID</Th>
                    <Th>Category</Th>
                    <Th>Amount</Th>
                    <Th>AI Action</Th>
                    <Th>Policy</Th>
                    <Th>Outcome</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r) => (
                    <tr key={r.recovery_item_id || Math.random()} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <Td>
                        {r.recovery_item_id ? (
                          <Link href={`/recovery/${r.recovery_item_id}`} style={{ color: "var(--accent)", textDecoration: "none", fontFamily: "monospace", fontSize: "0.75rem" }}>
                            {r.recovery_item_id}
                          </Link>
                        ) : (
                          <span style={{ color: "var(--text-muted)" }}>—</span>
                        )}
                      </Td>
                      <Td>
                        <span style={{
                          padding: "0.2rem 0.6rem", borderRadius: 4, fontSize: "0.6875rem", fontWeight: 600,
                          background: categoryBg(r.failure_category),
                          color: categoryColor(r.failure_category),
                          textTransform: "capitalize",
                        }}>
                          {r.failure_category?.replace(/_/g, " ") || "—"}
                        </span>
                      </Td>
                      <Td style={{ fontFamily: "monospace", fontSize: "0.8125rem" }}>
                        {r.expected_recovery_value ? fmt(r.expected_recovery_value) : "—"}
                      </Td>
                      <Td>
                        <span style={{
                          background: "var(--purple-subtle)", color: "var(--purple)",
                          padding: "0.2rem 0.6rem", borderRadius: 4, fontSize: "0.6875rem", fontWeight: 600,
                          textTransform: "capitalize",
                        }}>
                          {r.proposed_action?.replace(/_/g, " ") || "—"}
                        </span>
                      </Td>
                      <Td>
                        {r.policy_allowed ? (
                          <span style={{ color: "var(--success)", fontSize: "0.75rem", fontWeight: 600 }}>Allowed</span>
                        ) : (
                          <span style={{ color: "var(--danger)", fontSize: "0.75rem", fontWeight: 600 }}>Blocked</span>
                        )}
                      </Td>
                      <Td>
                        <span className={`status-badge status-${r.recovery_status}`}>
                          {r.recovery_status?.replace(/_/g, " ") || "—"}
                        </span>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {status === "running" && (
        <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
          <div className="skeleton" style={{ height: 48, width: 200, margin: "0 auto 1rem" }} />
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>Processing {count} recovery cases...</p>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, sub, accent }: { label: string; value: string; sub: string; accent: string }) {
  return (
    <div className="metric-card" style={{ borderLeft: `3px solid ${accent}` }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color: accent, marginTop: 4 }}>{value}</div>
      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ padding: "0.875rem 1.25rem", textAlign: "left", fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", background: "var(--bg-secondary)" }}>{children}</th>;
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ padding: "0.875rem 1.25rem", fontSize: "0.8125rem", ...style }}>{children}</td>;
}

function categoryColor(cat: string | null): string {
  const map: Record<string, string> = { soft: "var(--success)", hard: "var(--warning)", fraud: "var(--danger)", auth: "var(--accent)", unknown: "var(--text-muted)" };
  return map[cat || ""] || "var(--text-muted)";
}

function categoryBg(cat: string | null): string {
  const map: Record<string, string> = {
    soft: "var(--success-subtle)",
    hard: "var(--warning-subtle)",
    fraud: "var(--danger-subtle)",
    auth: "var(--accent-subtle)",
    unknown: "rgba(100,116,139,0.12)",
  };
  return map[cat || ""] || "rgba(100,116,139,0.12)";
}
