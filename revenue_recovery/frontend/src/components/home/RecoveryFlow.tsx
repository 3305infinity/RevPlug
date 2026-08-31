"use client";

import { useState, useEffect, useCallback } from "react";
import { RecoveryScenario } from "./scenarios";

interface Props {
  scenario: RecoveryScenario;
}

export default function RecoveryFlow({ scenario }: Props) {
  const [selectedStageIndex, setSelectedStageIndex] = useState(0);
  const [animatingStep, setAnimatingStep] = useState<number | null>(null);

  // Auto-play subtle reveal animation once when scenario changes or on load
  const runReplayAnimation = useCallback(() => {
    // Check reduced motion preference
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setAnimatingStep(scenario.stages.length - 1);
      setSelectedStageIndex(0);
      return;
    }

    setAnimatingStep(0);
    setSelectedStageIndex(0);

    let current = 0;
    const interval = setInterval(() => {
      current++;
      if (current < scenario.stages.length) {
        setAnimatingStep(current);
      } else {
        clearInterval(interval);
        setAnimatingStep(null);
      }
    }, 250);

    return () => clearInterval(interval);
  }, [scenario]);

  useEffect(() => {
    setSelectedStageIndex(0);
    setAnimatingStep(null);
  }, [scenario]);

  const activeStage = scenario.stages[selectedStageIndex] || scenario.stages[0];

  return (
    <div style={{ marginBottom: "3rem" }}>
      {/* HEADER & REPLAY CONTROL */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
            Interactive Decision Trace Inspector
          </div>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
            Real-Time Recovery Control Pipeline
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "#94a3b8", marginTop: 2 }}>
            Click any stage to inspect operational telemetry, policy rules, and settlement evidence.
          </p>
        </div>

        <button
          onClick={runReplayAnimation}
          style={{
            padding: "0.45rem 0.85rem",
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            background: "#1e293b",
            color: "#f8fafc",
            border: "1px solid #334155",
            borderRadius: 6,
            cursor: "pointer",
          }}
          aria-label="Replay Recovery Sequence"
        >
          ↻ Replay Recovery Sequence
        </button>
      </div>

      {/* CONTINUOUS PIPELINE DISPLAY */}
      <div
        role="region"
        aria-label="Recovery Pipeline Stages"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "0",
          borderTop: "1px solid #1e293b",
          borderBottom: "1px solid #1e293b",
          background: "#0d111a",
        }}
      >
        {scenario.stages.map((stage, idx) => {
          const isSelected = selectedStageIndex === idx;
          const isRevealed = animatingStep === null || idx <= animatingStep;

          return (
            <button
              key={idx}
              onClick={() => setSelectedStageIndex(idx)}
              aria-selected={isSelected}
              role="tab"
              aria-controls={`stage-panel-${idx}`}
              id={`stage-tab-${idx}`}
              style={{
                padding: "1.25rem 1rem",
                textAlign: "left",
                background: isSelected ? "rgba(37, 99, 235, 0.08)" : "transparent",
                border: "none",
                borderRight: idx < 4 ? "1px solid #1e293b" : "none",
                borderBottom: isSelected ? "2px solid #3b82f6" : "2px solid transparent",
                opacity: isRevealed ? (isSelected ? 1 : 0.75) : 0.3,
                transition: "all 0.15s ease-in-out",
                cursor: "pointer",
                outline: "none",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.6875rem", color: isSelected ? "#3b82f6" : "#64748b", fontFamily: "monospace", fontWeight: 700 }}>
                  {stage.step}
                </span>
                {stage.details.isBlocked && (
                  <span style={{ fontSize: "0.625rem", color: "#ef4444", fontWeight: 700, fontFamily: "monospace" }}>
                    STOPPED
                  </span>
                )}
              </div>

              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: isSelected ? "#f8fafc" : "#cbd5e1", letterSpacing: "0.04em", marginBottom: "0.35rem" }}>
                {stage.label}
              </div>

              <div style={{ fontSize: "0.75rem", color: isSelected ? "#93c5fd" : "#64748b", fontWeight: 500, lineHeight: 1.3 }}>
                {stage.summary}
              </div>
            </button>
          );
        })}
      </div>

      {/* SELECTED STAGE INLINE DETAILS PANEL */}
      <div
        id={`stage-panel-${selectedStageIndex}`}
        role="tabpanel"
        aria-labelledby={`stage-tab-${selectedStageIndex}`}
        style={{
          marginTop: "1rem",
          padding: "1.25rem 1.5rem",
          background: "#090d16",
          border: "1px solid #1e293b",
          borderLeft: activeStage.details.isBlocked ? "3px solid #ef4444" : "3px solid #3b82f6",
          borderRadius: 6,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "monospace" }}>
              Stage {activeStage.step} Details · {activeStage.label}
            </div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "#f8fafc", marginTop: 2 }}>
              {activeStage.details.title}
            </h3>
          </div>
          {activeStage.details.verdict && (
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: 700,
                fontFamily: "monospace",
                color: activeStage.details.verdict === "ALLOW" ? "#10b981" : "#ef4444",
                background: activeStage.details.verdict === "ALLOW" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                padding: "0.2rem 0.6rem",
                borderRadius: 4,
              }}
            >
              VERDICT: {activeStage.details.verdict}
            </span>
          )}
        </div>

        <p style={{ fontSize: "0.8125rem", color: "#94a3b8", marginBottom: "1rem", lineHeight: 1.5 }}>
          {activeStage.details.description}
        </p>

        {activeStage.details.telemetry && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", background: "#0d111a", padding: "0.75rem 1rem", borderRadius: 4, border: "1px solid #1e293b" }}>
            {Object.entries(activeStage.details.telemetry).map(([k, v]) => (
              <div key={k}>
                <div style={{ fontSize: "0.625rem", color: "#64748b", textTransform: "uppercase", fontFamily: "monospace" }}>{k}</div>
                <div style={{ fontSize: "0.75rem", color: "#f8fafc", fontWeight: 600, fontFamily: "monospace", marginTop: 2 }}>{String(v)}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
