"use client";

import { useState } from "react";

export default function TrustBar() {
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);

  const trustItems = [
    {
      id: "settlement",
      icon: "✓",
      label: "Verified Settlement",
      detail: "Revenue is counted ONLY after authoritative provider settlement/conversion evidence is received.",
    },
    {
      id: "policy",
      icon: "🛡️",
      label: "Policy Constrained",
      labelColor: "var(--success)",
      detail: "AI proposals are strictly gated by non-bypassable retry limits, opt-outs, fraud checks, and EV bounds.",
    },
    {
      id: "idempotent",
      icon: "⚡",
      label: "Idempotent Execution",
      detail: "Actions use unique item:action:attempt keys to guarantee zero duplicate customer contacts or retries.",
    },
    {
      id: "audit",
      icon: "📜",
      label: "Fully Auditable",
      detail: "Every context assembly, AI proposal, policy rule, execution, and settlement event is immutably logged.",
    },
  ];

  return (
    <div style={{ marginBottom: "2rem" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "1rem",
          background: "rgba(255, 255, 255, 0.02)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "1rem 1.25rem",
        }}
      >
        {trustItems.map((item) => (
          <div
            key={item.id}
            onMouseEnter={() => setActiveTooltip(item.id)}
            onMouseLeave={() => setActiveTooltip(null)}
            style={{
              position: "relative",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span style={{ fontSize: "1rem" }}>{item.icon}</span>
            <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: item.labelColor || "var(--text-primary)" }}>
              {item.label}
            </span>

            {/* Hover Explainer Tooltip */}
            {activeTooltip === item.id && (
              <div
                style={{
                  position: "absolute",
                  bottom: "125%",
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: 220,
                  background: "#0f172a",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: 6,
                  padding: "0.75rem",
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                  boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
                  zIndex: 50,
                  pointerEvents: "none",
                }}
              >
                <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                  {item.label}
                </div>
                {item.detail}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
