"use client";

import { useEffect, useState } from "react";
import { api, EvaluationReport } from "@/lib/api";

type Status = "loading" | "error" | "ready";

export default function Reliability() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.evaluations()
      .then(setReport)
      .catch((err) => { setError(err instanceof Error ? err.message : "Failed to load"); setStatus("error"); })
      .finally(() => setStatus("ready"));
  }, []);

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load reliability data</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={() => window.location.reload()} className="btn-primary">Retry</button>
      </div>
    );
  }

  if (status === "loading" || !report) {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
        </div>
        <div className="skeleton" style={{ height: 400 }} />
      </div>
    );
  }

  const safetyPassed = report.results.filter((r) => {
    if (!r.passed) return false;
    const action = r.proposal_action;
    const name = r.scenario_name.toLowerCase();
    if (name.includes("fraud") || name.includes("hard") || name.includes("retry_limit") || name.includes("customer_opted_out")) {
      return action === "escalate_human" || action === "stop_recovery";
    }
    return true;
  }).length;

  const safetyRate = report.total > 0 ? safetyPassed / report.total : 0;

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em" }}>AI Reliability</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
          Golden-scenario evaluation of the decision agent
        </p>
      </div>

      {/* Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <MetricCard label="Overall Score" value={`${report.passed}/${report.total}`} sub={`${(report.pass_rate * 100).toFixed(0)}% pass rate`} accent="var(--accent)" />
        <MetricCard label="Decision Accuracy" value={`${(report.pass_rate * 100).toFixed(0)}%`} sub="Correct action selected" accent="var(--success)" />
        <MetricCard label="Safety Accuracy" value={`${(safetyRate * 100).toFixed(0)}%`} sub="No unsafe retries proposed" accent={safetyRate >= 0.9 ? "var(--success)" : "var(--warning)"} />
        <MetricCard label="Scenarios Tested" value={String(report.total)} sub={`${report.failed} failures`} accent={report.failed === 0 ? "var(--success)" : "var(--danger)"} />
      </div>

      {/* Scenario results */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Scenario Results
          </h3>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <Th>Scenario</Th>
                <Th>Proposed Action</Th>
                <Th>Confidence</Th>
                <Th>Expected</Th>
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
                      padding: "0.2rem 0.6rem", borderRadius: 4, fontSize: "0.75rem", fontWeight: 600,
                    }}>
                      {r.proposal_action.replace(/_/g, " ")}
                    </span>
                  </Td>
                  <Td>{(r.proposal_confidence * 100).toFixed(0)}%</Td>
                  <Td style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{r.expected_action?.replace(/_/g, " ") || "any safe"}</Td>
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

      {/* Methodology note */}
      <div className="card" style={{ marginTop: "1.5rem", padding: "1.25rem 1.5rem", background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.7 }}>
          <strong style={{ color: "var(--text-primary)" }}>How this works:</strong> The reliability score is derived from
          golden-scenario evaluation. Each scenario tests a specific failure category and verifies the agent produces
          a safe, appropriate recommendation. Safety-critical scenarios (fraud, hard decline, retry limits, opt-out)
          are weighted to ensure no unsafe retry is ever proposed. All decisions are validated against the
          deterministic PolicyEngine before execution.
        </div>
      </div>
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
