"use client";

import { RecoveryScenario } from "./scenarios";

interface Props {
  scenarios: RecoveryScenario[];
  activeScenarioId: string;
  onSelectScenario: (scenario: RecoveryScenario) => void;
}

export default function ScenarioSwitcher({ scenarios, activeScenarioId, onSelectScenario }: Props) {
  return (
    <div style={{ marginBottom: "2rem" }}>
      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
        SELECT RECOVERY SCENARIO
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.5rem" }}>
        {scenarios.map((sc) => {
          const isActive = sc.id === activeScenarioId;

          return (
            <button
              key={sc.id}
              onClick={() => onSelectScenario(sc)}
              style={{
                padding: "0.75rem 0.625rem",
                borderRadius: 6,
                background: isActive ? "#1e293b" : "#0d111a",
                border: isActive ? "1px solid #3b82f6" : "1px solid #1e293b",
                textAlign: "left",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: isActive ? "#f8fafc" : "#cbd5e1" }}>
                  {sc.name}
                </span>
                <span
                  style={{
                    fontSize: "0.625rem",
                    fontWeight: 700,
                    fontFamily: "monospace",
                    padding: "0.1rem 0.35rem",
                    borderRadius: 4,
                    color: sc.badgeType === "success" ? "#10b981" : sc.badgeType === "danger" ? "#ef4444" : sc.badgeType === "warning" ? "#f59e0b" : "#60a5fa",
                    background: sc.badgeType === "success" ? "rgba(16, 185, 129, 0.1)" : sc.badgeType === "danger" ? "rgba(239, 68, 68, 0.1)" : sc.badgeType === "warning" ? "rgba(245, 158, 11, 0.1)" : "rgba(59, 130, 246, 0.1)",
                  }}
                >
                  {sc.badge}
                </span>
              </div>
              <div style={{ fontSize: "0.6875rem", color: "#64748b", lineHeight: 1.3 }}>
                {sc.description}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
