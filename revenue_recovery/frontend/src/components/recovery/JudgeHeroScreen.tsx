"use client";

import React, { useEffect, useState } from "react";

interface Props {
  onStartDemo: () => void;
}

interface EvalSummary {
  actually_recovered?: number;
  revenue_at_risk?: number;
  recovery_rate?: number;
  total_items?: number;
  stopped_cases?: number;
}

export default function JudgeHeroScreen({ onStartDemo }: Props) {
  const [evalData, setEvalData] = useState<EvalSummary | null>(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    fetch(`${apiUrl}/summary`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setEvalData(d))
      .catch(() => {});
  }, []);

  const fmt = (n: number) =>
    "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

  return (
    <div style={{
      padding: "1rem 1.25rem",
      borderRadius: 8,
      background: "var(--bg-secondary)",
      border: "1px solid var(--border)",
      marginBottom: "1.5rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.875rem" }}>
        <div>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>
            Recovery Intelligence
          </div>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
            RevenueRecovery-v1
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
            {evalData?.total_items != null
              ? `${evalData.total_items.toLocaleString()} evaluation opportunities`
              : "Awaiting evaluation data"} · Deterministic benchmark · Evaluation workspace
          </div>
        </div>
        <button
          onClick={onStartDemo}
          style={{
            padding: "0.5rem 1rem",
            borderRadius: 6,
            background: "#2563eb",
            color: "#fff",
            fontSize: "0.8125rem",
            fontWeight: 700,
            border: "none",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          ▶ Start Demo Walkthrough
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
        <div style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 6, padding: "0.75rem" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Revenue at Risk
          </div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, fontFamily: "monospace", color: "#ef4444", marginTop: 4 }}>
            {evalData?.revenue_at_risk != null ? fmt(evalData.revenue_at_risk) : "—"}
          </div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", marginTop: 2, fontWeight: 600, textTransform: "uppercase" }}>
            Evaluation Data
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: 6, padding: "0.75rem" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Verified Recovered
          </div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, fontFamily: "monospace", color: "#10b981", marginTop: 4 }}>
            {evalData?.actually_recovered != null && evalData.actually_recovered > 0
              ? fmt(evalData.actually_recovered)
              : "—"}
          </div>
          <div style={{ fontSize: "0.5625rem", color: "#6ee7b7", marginTop: 2, fontWeight: 600, textTransform: "uppercase" }}>
            Provider Verified
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: 6, padding: "0.75rem" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Recovery Rate
          </div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, fontFamily: "monospace", color: "#6366f1", marginTop: 4 }}>
            {evalData?.recovery_rate != null && evalData.recovery_rate > 0
              ? `${(evalData.recovery_rate * 100).toFixed(1)}%`
              : "—"}
          </div>
          <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", marginTop: 2, fontWeight: 600, textTransform: "uppercase" }}>
            Evaluation Data
          </div>
        </div>

        <div style={{ background: "var(--bg-primary)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: 6, padding: "0.75rem" }}>
          <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Safety Violations
          </div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, fontFamily: "monospace", color: "#10b981", marginTop: 4 }}>
            {evalData && (evalData as any).safety_violations != null
              ? String((evalData as any).safety_violations)
              : "—"}
          </div>
          <div style={{ fontSize: "0.5625rem", color: "#6ee7b7", marginTop: 2, fontWeight: 600, textTransform: "uppercase" }}>
            Evaluation Data
          </div>
        </div>
      </div>
    </div>
  );
}
