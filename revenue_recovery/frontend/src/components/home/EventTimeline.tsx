"use client";

import { RecoveryScenario } from "./scenarios";

interface Props {
  events: RecoveryScenario["events"];
}

export default function EventTimeline({ events }: Props) {
  return (
    <div style={{ marginBottom: "3rem" }}>
      <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.75rem" }}>
        Infrastructure Event Stream
      </div>

      <div
        style={{
          background: "#0d111a",
          border: "1px solid #1e293b",
          borderRadius: 6,
          padding: "1rem 1.25rem",
          fontFamily: "monospace",
          fontSize: "0.75rem",
        }}
      >
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {events.map((ev, idx) => (
            <div
              key={idx}
              style={{
                display: "grid",
                gridTemplateColumns: "80px 220px 1fr",
                gap: "1rem",
                padding: "0.25rem 0",
                borderBottom: idx < events.length - 1 ? "1px solid #1e293b" : "none",
                alignItems: "center",
              }}
            >
              <span style={{ color: "#64748b" }}>{ev.time}</span>
              <span style={{ fontWeight: 600, color: "#3b82f6" }}>{ev.event}</span>
              <span style={{ color: "#94a3b8" }}>{ev.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
