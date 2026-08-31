"use client";

import { useState } from "react";

const COMPARISONS = [
  {
    dim: "Diagnosis",
    trad: "Generic retry schedule on any failure code",
    ros: "Contextual failure telemetry diagnosis via Groq LLM",
    detail: "Naive retries ignore failure cause, repeatedly hitting card decline loops. RevPlug classifies root causes before taking action.",
  },
  {
    dim: "Decision",
    trad: "Static cron rules (e.g. retry 3x every 24h)",
    ros: "AI proposal + deterministic policy gate",
    detail: "AI proposes optimal recovery intervention; deterministic server-side policy enforces non-bypassable safety constraints.",
  },
  {
    dim: "Execution",
    trad: "Unbounded automated card retries",
    ros: "Bounded permitted action (e.g. hosted payment link)",
    detail: "Executes bounded actions via Razorpay Test Mode API or simulated provider adapters rather than blind card hammering.",
  },
  {
    dim: "Stopping",
    trad: "Limited (retries until hard limit reached)",
    ros: "Explicit stopping rules (fraud / opt-out)",
    detail: "Immediately halts recovery on fraud signals or customer opt-out to prevent merchant penalties and protect customer trust.",
  },
  {
    dim: "Recovery Metric",
    trad: "Attempted / Dispatched action",
    ros: "Authoritative settlement evidence verified",
    detail: "Money is credited to ledger ONLY after receiving authoritative gateway settlement webhooks (`payment.authorized`).",
  },
  {
    dim: "Auditability",
    trad: "Basic event logs",
    ros: "Immutable end-to-end decision trace",
    detail: "Every case maintains an 8-stage immutable audit log tracking telemetry, AI confidence, policy rules, and settlement.",
  },
];

export default function InteractiveComparison() {
  const [selectedIdx, setSelectedIdx] = useState(0);

  const activeComp = COMPARISONS[selectedIdx];

  return (
    <div style={{ marginBottom: "3rem" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          Architectural Comparison
        </div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
          Traditional Naive Retry vs RevPlug
        </h2>
        <p style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: 2 }}>
          Click any architectural dimension to compare operational behaviors.
        </p>
      </div>

      {/* DIMENSION SELECTOR BUTTONS */}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
        {COMPARISONS.map((comp, idx) => {
          const isSelected = idx === selectedIdx;
          return (
            <button
              key={comp.dim}
              onClick={() => setSelectedIdx(idx)}
              style={{
                padding: "0.4rem 0.85rem",
                fontSize: "0.75rem",
                fontWeight: 600,
                fontFamily: "monospace",
                borderRadius: 4,
                border: isSelected ? "1px solid #3b82f6" : "1px solid #1e293b",
                background: isSelected ? "rgba(59, 130, 246, 0.1)" : "#0d111a",
                color: isSelected ? "#3b82f6" : "#94a3b8",
                cursor: "pointer",
              }}
            >
              {comp.dim}
            </button>
          );
        })}
      </div>

      {/* COMPARISON SPLIT VIEW — NO CARDS */}
      <div style={{ background: "#0d111a", border: "1px solid #1e293b", borderRadius: 6, padding: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", fontFamily: "monospace" }}>
              TRADITIONAL RETRY
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 600, color: "#94a3b8", marginTop: 4 }}>
              {activeComp.trad}
            </div>
          </div>

          <div style={{ borderLeft: "1px solid #1e293b", paddingLeft: "2rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", fontFamily: "monospace" }}>
              RECOVEROS
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f8fafc", marginTop: 4 }}>
              {activeComp.ros}
            </div>
          </div>
        </div>

        <div style={{ marginTop: "1rem", paddingTop: "0.85rem", borderTop: "1px solid #1e293b", fontSize: "0.75rem", color: "#64748b", lineHeight: 1.5 }}>
          {activeComp.detail}
        </div>
      </div>
    </div>
  );
}
