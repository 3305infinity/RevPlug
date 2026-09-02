"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface StrategyEvidenceProps {
  itemId: string;
  selectedAction: string | null;
}

interface StrategyPerformanceRow {
  action: string;
  label: string;
  evidence_level: string;
  attempts_count: number;
  successful_verifications: number;
  verified_recovered_minor: number;
  verified_recovery_rate_pct: number;
  average_time_to_recovery_hours: number | null;
  avg_attempts_per_recovery: number | null;
  policy_blocks: number;
  stop_outcomes: number;
  explanation: string;
}

export default function StrategyEvidence({ itemId, selectedAction }: StrategyEvidenceProps) {
  const [report, setReport] = useState<{ strategies: StrategyPerformanceRow[] } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedAction || selectedAction === "no_action" || selectedAction === "wait" || selectedAction === "stop_recovery") {
      return;
    }
    setLoading(true);
    api.evaluateTiming(itemId)
      .then(() => {})
      .catch(() => {})
      .finally(() => setLoading(false));

    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/strategy-analytics`)
      .then((r) => r.json())
      .then((data) => setReport(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [itemId, selectedAction]);

  if (!selectedAction || selectedAction === "no_action" || selectedAction === "wait" || selectedAction === "stop_recovery") {
    return null;
  }

  const strategyRow = report?.strategies.find((s) => s.action === selectedAction);

  if (loading) {
    return (
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1rem" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
          Strategy Evidence
        </div>
        <div className="skeleton" style={{ height: 40 }} />
      </div>
    );
  }

  if (!strategyRow) {
    return (
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1rem" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
          Strategy Evidence
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
          No historical strategy advantage established for {selectedAction.replace(/_/g, " ")}.
        </div>
      </div>
    );
  }

  const evidenceColor = strategyRow.evidence_level === "established" ? "#10b981" : strategyRow.evidence_level === "emerging" ? "#d97706" : "var(--text-muted)";

  return (
    <div className="card" style={{ padding: "1.25rem", marginBottom: "1rem", borderLeft: `3px solid ${evidenceColor}` }}>
      <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
        Strategy Evidence — {strategyRow.label}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "0.75rem" }}>
        <div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>Evidence Level</div>
          <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: evidenceColor, marginTop: 2, textTransform: "capitalize" }}>
            {strategyRow.evidence_level}
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>Historical Verifications</div>
          <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, marginTop: 2 }}>
            {strategyRow.successful_verifications} / {strategyRow.attempts_count} attempts
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>Verified Recovery</div>
          <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#10b981", marginTop: 2 }}>
            ₹{(strategyRow.verified_recovered_minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </div>
        </div>
      </div>

      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.5rem" }}>
        {strategyRow.explanation}
      </div>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
        <span>Verification rate: <strong style={{ color: "var(--text-secondary)" }}>{strategyRow.verified_recovery_rate_pct}%</strong></span>
        {strategyRow.average_time_to_recovery_hours != null && (
          <span>Avg time to recovery: <strong style={{ color: "var(--text-secondary)" }}>{strategyRow.average_time_to_recovery_hours}h</strong></span>
        )}
        {strategyRow.avg_attempts_per_recovery != null && (
          <span>Avg attempts per recovery: <strong style={{ color: "var(--text-secondary)" }}>{strategyRow.avg_attempts_per_recovery}</strong></span>
        )}
        {strategyRow.policy_blocks > 0 && (
          <span style={{ color: "#d97706" }}>{strategyRow.policy_blocks} policy blocks</span>
        )}
        {strategyRow.stop_outcomes > 0 && (
          <span>{strategyRow.stop_outcomes} stopped</span>
        )}
      </div>
    </div>
  );
}
