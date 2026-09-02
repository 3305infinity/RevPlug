"use client";

import { useState } from "react";
import Link from "next/link";

export default function SmartStopSection() {
  const [whyOpen, setWhyOpen] = useState(false);

  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          SMART STOP &amp; TRUST
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
          Sometimes the right recovery action is no action.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
          Blind automated retries on fraud or hard declines destroy brand trust and incur gateway penalty fees.
        </p>
      </div>

      {/* CASE DISPLAY CONTAINER */}
      <div
        style={{
          border: "1px solid #21262d",
          borderRadius: 8,
          background: "#0d1117",
          padding: "1.5rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", borderBottom: "1px solid #21262d", paddingBottom: "1rem" }}>
          <div>
            <span className="font-mono" style={{ fontSize: "0.75rem", color: "#6e7681" }}>CASE-RR-9081</span>
            <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f0f6fc", marginTop: 2 }}>
              ₹18,200.00 at risk
            </div>
          </div>

          <div style={{ textAlign: "right" }}>
            <span style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase" }}>PROTECTED CAPITAL</span>
            <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "#ef4444", marginTop: 2 }}>
              ₹18,200.00
            </div>
          </div>
        </div>

        {/* COMPACT TRACE MOMENT */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "0.75rem", fontSize: "0.75rem", fontFamily: "monospace" }}>
          <div style={{ padding: "0.75rem", background: "#161b22", borderRadius: 6 }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>AI PROPOSED</div>
            <div style={{ color: "#f59e0b", fontWeight: 700, marginTop: 2 }}>retry_payment</div>
          </div>

          <div style={{ padding: "0.75rem", background: "#161b22", borderRadius: 6 }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>POLICY GATE</div>
            <div style={{ color: "#ef4444", fontWeight: 700, marginTop: 2 }}>BLOCK (STOP)</div>
          </div>

          <div style={{ padding: "0.75rem", background: "#161b22", borderRadius: 6 }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>REASON</div>
            <div style={{ color: "#ef4444", marginTop: 2 }}>Fraud signal detected</div>
          </div>

          <div style={{ padding: "0.75rem", background: "#161b22", borderRadius: 6 }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>EXECUTION</div>
            <div style={{ color: "#8b949e", fontWeight: 700, marginTop: 2 }}>NOT EXECUTED</div>
          </div>

          <div style={{ padding: "0.75rem", background: "#161b22", borderRadius: 6 }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>RECOVERED</div>
            <div style={{ color: "#8b949e", fontWeight: 700, marginTop: 2 }}>₹0.00</div>
          </div>

          <div style={{ padding: "0.75rem", background: "#161b22", borderRadius: 6 }}>
            <div style={{ color: "#6e7681", fontSize: "0.65rem" }}>PROTECTED</div>
            <div style={{ color: "#ef4444", fontWeight: 700, marginTop: 2 }}>₹18,200.00</div>
          </div>
        </div>

        {/* INTERACTIVE EXPLANATION TRIGGER */}
        <div style={{ marginTop: "1.25rem", paddingTop: "1rem", borderTop: "1px solid #21262d" }}>
          <button
            onClick={() => setWhyOpen(!whyOpen)}
            style={{
              background: "transparent",
              border: "none",
              color: "#6366f1",
              fontSize: "0.8125rem",
              fontWeight: 600,
              cursor: "pointer",
              padding: 0,
            }}
          >
            {whyOpen ? "Hide explanation ▲" : "Why did RevPlug stop this? ▼"}
          </button>

          {whyOpen && (
            <div style={{ marginTop: "0.75rem", padding: "0.875rem 1rem", background: "#161b22", borderRadius: 6, fontSize: "0.8125rem", color: "#8b949e", lineHeight: 1.5 }}>
              “Fraud signal violated the execution policy. No recovery action was dispatched. By stopping automated retries on fraud risk, RevPlug prevented potential chargebacks, card brand fines, and customer dispute escalation.”
            </div>
          )}
        </div>
      </div>

      {/* PRODUCT LINK STRIP */}
      <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", marginTop: "1.5rem" }}>
        <Link
          href="/customers"
          style={{ fontSize: "0.8125rem", color: "#2563eb", textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.35rem" }}
        >
          Explore customer intelligence →
        </Link>
        <Link
          href="/dashboard"
          style={{ fontSize: "0.8125rem", color: "#8b949e", textDecoration: "none", fontWeight: 500, display: "flex", alignItems: "center", gap: "0.35rem" }}
        >
          Live decision dashboard →
        </Link>
      </div>
    </div>
  );
}
