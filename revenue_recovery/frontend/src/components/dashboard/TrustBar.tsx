"use client";

import { useEffect, useState } from "react";

export default function TrustBar() {
  const [executionMode, setExecutionMode] = useState<string>("Simulated Execution");
  const [policyVersion, setPolicyVersion] = useState<string>("v1.0");

  useEffect(() => {
    const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    fetch(`${apiHost}/api/razorpay/status`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          if (data.is_live_test_mode) {
            setExecutionMode("Provider Test Mode");
          } else {
            setExecutionMode("Simulated Execution");
          }
        }
      })
      .catch(() => {});

    fetch(`${apiHost}/api/controls`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.policy_version) {
          setPolicyVersion(data.policy_version);
        }
      })
      .catch(() => {});
  }, []);

  const items = [
    { label: "Provider adapter active", status: "active" },
    { label: "Policy engine active", status: "active" },
    { label: "Settlement verification active", status: "active" },
    { label: "Audit logging active", status: "active" },
  ];

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <div
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "0.625rem 1rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", flexWrap: "wrap" }}>
          <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            SYSTEM STATUS
          </span>
          {items.map((item, idx) => (
            <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)" }} />
              {item.label}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem", fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
          <span>Execution: <strong style={{ color: "var(--text-primary)" }}>{executionMode}</strong></span>
          <span>AI Provider: <strong style={{ color: "var(--text-primary)" }}>Groq / Mock Scorer</strong></span>
          <span>Policy: <strong style={{ color: "var(--success)" }}>{policyVersion} Active</strong></span>
        </div>
      </div>
    </div>
  );
}
