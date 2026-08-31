"use client";

import { useState, useEffect, useCallback } from "react";
import { SCENARIOS, RecoveryScenario } from "./scenarios";

export default function RecoverySimulator() {
  const [activeScenario, setActiveScenario] = useState<RecoveryScenario>(SCENARIOS[0]);
  const [animatingStep, setAnimatingStep] = useState<number | null>(null);

  const runReplayAnimation = useCallback(() => {
    // Check reduced motion preference
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setAnimatingStep(activeScenario.stages.length - 1);
      return;
    }

    setAnimatingStep(0);
    let current = 0;
    const interval = setInterval(() => {
      current++;
      if (current < activeScenario.stages.length) {
        setAnimatingStep(current);
      } else {
        clearInterval(interval);
        setAnimatingStep(null);
      }
    }, 250);

    return () => clearInterval(interval);
  }, [activeScenario]);

  useEffect(() => {
    setAnimatingStep(null);
  }, [activeScenario]);

  return (
    <section id="simulator" style={{ padding: "3rem 0", borderTop: "1px solid #1e293b" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem", fontFamily: "monospace" }}>
            Operational Simulator
          </div>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
            SEE RECOVEROS MAKE A DECISION
          </h2>
        </div>

        <button
          onClick={runReplayAnimation}
          style={{
            padding: "0.4rem 0.75rem",
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            background: "transparent",
            color: "#94a3b8",
            border: "1px solid #334155",
            borderRadius: 4,
            cursor: "pointer",
          }}
          aria-label="Replay recovery sequence"
        >
          Replay recovery ↻
        </button>
      </div>

      {/* SEGMENTED TEXT SCENARIO CONTROLS (NOT CARDS) */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid #1e293b", paddingBottom: "0.75rem", marginBottom: "1.75rem" }}>
        {SCENARIOS.map((sc) => {
          const isActive = sc.id === activeScenario.id;
          return (
            <button
              key={sc.id}
              onClick={() => setActiveScenario(sc)}
              style={{
                padding: "0.35rem 0.75rem",
                fontSize: "0.75rem",
                fontWeight: isActive ? 700 : 500,
                fontFamily: "monospace",
                background: isActive ? "#1e293b" : "transparent",
                color: isActive ? "#f8fafc" : "#64748b",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              [ {sc.name} ]
            </button>
          );
        })}
      </div>

      {/* OPERATIONAL LOG TRACE / TIMELINE — NO CARD BACKGROUND */}
      <div
        role="region"
        aria-label="Recovery Operational Trace"
        style={{
          borderLeft: "1px solid #1e293b",
          paddingLeft: "1.5rem",
          marginLeft: "0.5rem",
          display: "flex",
          flexDirection: "column",
          gap: "1.75rem",
        }}
      >
        {activeScenario.stages.map((stage, idx) => {
          const isRevealed = animatingStep === null || idx <= animatingStep;

          return (
            <div
              key={idx}
              style={{
                opacity: isRevealed ? 1 : 0.2,
                transform: isRevealed ? "translateY(0)" : "translateY(4px)",
                transition: "opacity 0.25s ease, transform 0.25s ease",
                position: "relative",
              }}
            >
              {/* Timeline Bullet */}
              <div
                style={{
                  position: "absolute",
                  left: "-1.85rem",
                  top: 4,
                  width: 9,
                  height: 9,
                  borderRadius: "50%",
                  background: stage.details.isBlocked ? "#ef4444" : idx === 4 ? "#10b981" : "#3b82f6",
                  border: "2px solid #080b12",
                }}
              />

              <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "0.35rem" }}>
                <span style={{ fontSize: "0.6875rem", fontFamily: "monospace", color: "#64748b" }}>
                  {stage.step}
                </span>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f8fafc", letterSpacing: "0.05em", fontFamily: "monospace" }}>
                  {stage.label}
                </span>
                {stage.details.verdict && (
                  <span
                    style={{
                      fontSize: "0.6875rem",
                      fontWeight: 700,
                      fontFamily: "monospace",
                      color: stage.details.verdict === "ALLOW" ? "#10b981" : "#ef4444",
                    }}
                  >
                    [{stage.details.verdict}]
                  </span>
                )}
              </div>

              <div style={{ fontSize: "0.875rem", fontWeight: 600, color: stage.details.isBlocked ? "#ef4444" : "#cbd5e1", marginBottom: "0.35rem" }}>
                {stage.details.title}
              </div>

              <div style={{ fontSize: "0.8125rem", color: "#94a3b8", lineHeight: 1.5, maxWidth: 640 }}>
                {stage.details.description}
              </div>

              {stage.details.telemetry && (
                <div style={{ marginTop: "0.5rem", display: "flex", gap: "1.5rem", fontFamily: "monospace", fontSize: "0.75rem" }}>
                  {Object.entries(stage.details.telemetry).map(([k, v]) => (
                    <span key={k} style={{ color: "#64748b" }}>
                      {k}: <strong style={{ color: "#cbd5e1" }}>{String(v)}</strong>
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* SMART STOP EDITORIAL STATEMENT IF BLOCKED */}
      {activeScenario.policyVerdict === "BLOCK" && (
        <div style={{ marginTop: "2rem", paddingTop: "1rem", borderTop: "1px solid #1e293b", fontSize: "0.875rem", fontWeight: 600, color: "#f8fafc", fontFamily: "monospace" }}>
          STOP WAS THE CORRECT ACTION. The system is rewarded for safe recovery, not maximum retries.
        </div>
      )}
    </section>
  );
}
