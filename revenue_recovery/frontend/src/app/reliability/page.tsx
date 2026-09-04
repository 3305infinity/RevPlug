"use client";

import { useEffect, useState, useMemo } from "react";
import { api, EvaluationReport } from "@/lib/api";
import CreateCaseModal from "@/components/recovery/CreateCaseModal";

type Status = "loading" | "error" | "ready";

interface FailureInjectionResponse {
  status: string;
  failure_type: string;
  system_reaction: string;
  [key: string]: any;
}

export default function ReliabilityFailureLab() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);

  // Interactive failure injection lab state
  const [selectedFailure, setSelectedFailure] = useState<string | null>(null);
  const [injectionLoading, setInjectionLoading] = useState(false);
  const [injectionResult, setInjectionResult] = useState<FailureInjectionResponse | null>(null);
  const [injectionError, setInjectionError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    api.evaluations()
      .then(setReport)
      .catch((err) => { setError(err instanceof Error ? err.message : "Failed to load"); setStatus("error"); })
      .finally(() => setStatus("ready"));
  }, []);

  const handleInjectFailure = async (failureType: string) => {
    if (failureType === "synthetic_event") {
      setIsModalOpen(true);
      return;
    }

    setSelectedFailure(failureType);
    setInjectionLoading(true);
    setInjectionResult(null);
    setInjectionError(null);

    try {
      const res = await fetch(`${apiHost}/api/demo/inject-failure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ failure_type: failureType }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}: Failed to execute failure scenario`);
      }

      const data = await res.json();
      setInjectionResult(data);
    } catch (err) {
      setInjectionError(err instanceof Error ? err.message : "Failure injection error");
    } finally {
      setInjectionLoading(false);
    }
  };

  const safetyPassed = useMemo(() => {
    if (!report) return 0;
    return report.results.filter((r) => {
      if (!r.passed) return false;
      const action = r.proposal_action;
      const name = r.scenario_name.toLowerCase();
      if (name.includes("fraud") || name.includes("hard") || name.includes("retry_limit") || name.includes("customer_opted_out")) {
        return action === "escalate_human" || action === "stop_recovery";
      }
      return true;
    }).length;
  }, [report]);

  const safetyRate = report && report.total > 0 ? safetyPassed / report.total : 0;

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load reliability lab data</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={() => window.location.reload()} className="btn-primary">Retry</button>
      </div>
    );
  }

  if (status === "loading" || !report) {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
        </div>
        <div className="skeleton" style={{ height: 400 }} />
      </div>
    );
  }

  const failureScenarios = [
    {
      id: "synthetic_event",
      label: "Synthetic Failure Injection",
      desc: "Simulate incoming payment failure webhook with custom customer, amount, & risk flags.",
      badge: "Ingestion Lab",
      color: "var(--accent)",
    },
    {
      id: "llm_timeout",
      label: "LLM Timeout (504)",
      desc: "Simulate LLM gateway timeout during diagnosis. Proves deterministic policy fallback.",
      badge: "AI Resilience",
      color: "#f59e0b",
    },
    {
      id: "executor_failure",
      label: "Gateway 502 Bad Gateway",
      desc: "Simulate Razorpay 502 API failure during dispatch. Verifies observation & dynamic re-planning.",
      badge: "Gateway Resilience",
      color: "#ef4444",
    },
    {
      id: "duplicate_webhook",
      label: "Duplicate Webhook Event",
      desc: "Simulate duplicate payment failure webhook payload. Verifies idempotency store deduplication.",
      badge: "Idempotency",
      color: "#10b981",
    },
    {
      id: "payment_success_race",
      label: "Payment Success Race",
      desc: "Simulate customer manual payment arriving during recovery worker attempt.",
      badge: "Concurrency Guard",
      color: "#8b5cf6",
    },
    {
      id: "policy_violation",
      label: "Policy Override Attempt",
      desc: "Simulate model proposing unsafe retry on hard failure. Verifies PolicyEngine enforcement.",
      badge: "Deterministic Shield",
      color: "#ec4899",
    },
    {
      id: "unknown_action",
      label: "Hallucinated Action / Registry",
      desc: "Simulate LLM proposing hallucinated action. Verifies ActionRegistry allowlist rejection.",
      badge: "Safety Allowlist",
      color: "#06b6d4",
    },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            DEVELOPER &amp; JUDGING SANDBOX
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>
            Reliability / Failure Lab
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
            Controlled sandbox environment for failure scenario testing, LLM fallback validation, idempotency guards, and golden scenario evaluations.
          </p>
        </div>

        <button
          onClick={async () => {
            if (confirm("Reset operational state? All stale test cases and settlement records will be permanently purged.")) {
              try {
                const res = await fetch(`${apiHost}/api/demo/reset`, { method: "POST" });
                if (res.ok) {
                  alert("Operational state clean. Zero stale items in recovery queue.");
                  window.location.reload();
                }
              } catch (e) {
                alert("Failed to reset operational state.");
              }
            }
          }}
          style={{
            background: "transparent",
            color: "#ef4444",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            padding: "0.45rem 0.85rem",
            borderRadius: 6,
            fontSize: "0.75rem",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Reset Operational State
        </button>
      </div>

      {/* ── SECTION 1: INTERACTIVE FAILURE INJECTION LAB ── */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              FAILURE INJECTION &amp; RESILIENCY TEST SUITE
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: 2 }}>
              Trigger synthetic infrastructure failures, model hallucinations, and race conditions to verify system boundary safety.
            </div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.875rem", marginBottom: "1.5rem" }}>
          {failureScenarios.map((scen) => (
            <button
              key={scen.id}
              onClick={() => handleInjectFailure(scen.id)}
              disabled={injectionLoading && selectedFailure === scen.id}
              style={{
                textAlign: "left",
                padding: "1rem",
                borderRadius: 8,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                cursor: "pointer",
                transition: "border-color 0.15s, background 0.15s",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  {scen.label}
                </span>
                <span style={{ fontSize: "0.625rem", fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "var(--bg-secondary)", color: scen.color, border: "1px solid var(--border)" }}>
                  {scen.badge}
                </span>
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                {scen.desc}
              </div>
              <div style={{ marginTop: 10, fontSize: "0.6875rem", fontWeight: 700, color: scen.color }}>
                {injectionLoading && selectedFailure === scen.id ? "Injecting & Testing..." : "Run Failure Test →"}
              </div>
            </button>
          ))}
        </div>

        {/* INJECTION RESULT EVIDENCE DISPLAY */}
        {injectionError && (
          <div style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", color: "#ef4444", padding: "1rem", borderRadius: 8, fontSize: "0.8125rem", fontWeight: 600 }}>
            Injection Failure: {injectionError}
          </div>
        )}

        {injectionResult && (
          <div style={{ background: "var(--bg-secondary)", padding: "1.25rem", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="status-badge status-recovered" style={{ fontSize: "0.6875rem" }}>
                  {injectionResult.status.toUpperCase()}
                </span>
                <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>
                  {injectionResult.failure_type}
                </span>
              </div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>LIVE BACKEND REACTION EVIDENCE</span>
            </div>

            <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#10b981", marginBottom: "0.75rem" }}>
              ✓ {injectionResult.system_reaction}
            </div>

            <pre style={{ background: "var(--bg-primary)", padding: "0.875rem", borderRadius: 6, border: "1px solid var(--border)", fontSize: "0.75rem", fontFamily: "monospace", overflowX: "auto", margin: 0 }}>
              {JSON.stringify(injectionResult, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* ── SECTION 2: AI SAFETY & GOLDEN SCENARIOS ── */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          GOLDEN SCENARIO EVALUATION SUITE
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <MetricCard label="Decision Accuracy" value={`${(report.pass_rate * 100).toFixed(0)}%`} sub="Pass rate" accent="var(--accent)" />
        <MetricCard label="Safety Accuracy" value={`${(safetyRate * 100).toFixed(0)}%`} sub="No unsafe retries proposed" accent={safetyRate >= 0.9 ? "var(--success)" : "var(--warning)"} />
        <MetricCard label="Scenarios Tested" value={String(report.total)} sub="Golden scenarios" accent="var(--purple)" />
        <MetricCard label="Failures" value={String(report.failed)} sub={report.failed === 0 ? "Perfect score" : "Scenarios failed"} accent={report.failed === 0 ? "var(--success)" : "var(--danger)"} />
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Golden Scenario Results
          </h3>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <Th>Scenario</Th>
                <Th>Proposed Action</Th>
                <Th>Confidence</Th>
                <Th>Expected Outcome</Th>
                <Th>Result</Th>
                <Th>Issues</Th>
              </tr>
            </thead>
            <tbody>
              {report.results.map((r) => (
                <tr key={r.scenario_name} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <Td style={{ fontWeight: 500, textTransform: "capitalize" }}>{r.scenario_name.replace(/_/g, " ")}</Td>
                  <Td>
                    <span style={{
                      background: "var(--purple-subtle)", color: "var(--purple)",
                      padding: "0.2rem 0.6rem", borderRadius: 4, fontSize: "0.75rem", fontWeight: 600, textTransform: "capitalize",
                    }}>
                      {r.proposal_action.replace(/_/g, " ")}
                    </span>
                  </Td>
                  <Td>{(r.proposal_confidence * 100).toFixed(0)}%</Td>
                  <Td style={{ color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "capitalize" }}>{r.expected_action?.replace(/_/g, " ") || "Any safe action"}</Td>
                  <Td>
                    {r.passed ? (
                      <span className="status-badge status-recovered">PASS</span>
                    ) : (
                      <span className="status-badge status-escalated">FAIL</span>
                    )}
                  </Td>
                  <Td>
                    {r.issues.length > 0 ? (
                      <span style={{ color: "var(--danger)", fontSize: "0.75rem" }}>{r.issues[0]}</span>
                    ) : (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>—</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <CreateCaseModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          setInjectionResult({
            status: "handled_safely",
            failure_type: "synthetic_event",
            system_reaction: "Synthetic failure event successfully ingested into operational recovery queue.",
          });
        }}
      />
    </div>
  );
}

function MetricCard({ label, value, sub, accent }: { label: string; value: string; sub: string; accent: string }) {
  return (
    <div className="metric-card" style={{ borderLeft: `3px solid ${accent}` }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color: accent, marginTop: 4 }}>{value}</div>
      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ padding: "0.75rem 1rem", textAlign: "left", fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{children}</th>;
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ padding: "0.75rem 1rem", fontSize: "0.8125rem", ...style }}>{children}</td>;
}
