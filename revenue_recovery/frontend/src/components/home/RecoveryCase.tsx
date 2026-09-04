"use client";

import { useState } from "react";
import Link from "next/link";

export default function RecoveryCase() {
  const [activeTab, setActiveTab] = useState<"case1" | "case2">("case1");

  return (
    <section style={{ padding: "4rem 0" }}>
      {/* SECTION HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem" }}>
        <div>
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: "0.35rem",
            }}
          >
            PRODUCT PROOF
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            One recovery decision, end to end.
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: 4 }}>
            See how diagnosis, policy control, action execution, and settlement verification unite into one recovery record.
          </p>
        </div>

        <div className="hidden-mobile">
          <span
            style={{
              fontSize: "0.6875rem",
              fontFamily: "monospace",
              color: "var(--text-muted)",
              background: "var(--bg-secondary)",
              padding: "0.25rem 0.6rem",
              borderRadius: 4,
              border: "1px solid var(--border)",
            }}
          >
            Illustrative workspace · Razorpay Test Mode
          </span>
        </div>
      </div>

      {/* UNIFIED PRODUCT WORKSPACE CONTAINER */}
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 8,
          background: "var(--bg-primary)",
          overflow: "hidden",
        }}
      >
        {/* WORKSPACE HEADER BAR */}
        <div
          style={{
            padding: "0.75rem 1.25rem",
            background: "var(--bg-secondary)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#ef4444" }} />
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#f59e0b" }} />
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#10b981" }} />
            <span style={{ marginLeft: "0.5rem", fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              app.revplug.io/recovery/cases
            </span>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setActiveTab("case1")}
              style={{
                fontSize: "0.75rem",
                padding: "0.25rem 0.6rem",
                borderRadius: 4,
                border: "1px solid var(--border)",
                background: activeTab === "case1" ? "var(--bg-tertiary)" : "transparent",
                color: activeTab === "case1" ? "var(--text-primary)" : "var(--text-secondary)",
                cursor: "pointer",
                fontWeight: activeTab === "case1" ? 600 : 400,
              }}
            >
              Case #RR-1042 (₹4,999)
            </button>
            <button
              onClick={() => setActiveTab("case2")}
              style={{
                fontSize: "0.75rem",
                padding: "0.25rem 0.6rem",
                borderRadius: 4,
                border: "1px solid var(--border)",
                background: activeTab === "case2" ? "var(--bg-tertiary)" : "transparent",
                color: activeTab === "case2" ? "var(--text-primary)" : "var(--text-secondary)",
                cursor: "pointer",
                fontWeight: activeTab === "case2" ? 600 : 400,
              }}
            >
              Case #RR-9081 (₹18,200)
            </button>
          </div>
        </div>

        {/* WORKSPACE BODY */}
        <div style={{ padding: "1.5rem" }}>
          {activeTab === "case1" ? (
            <div>
              {/* CASE TOP BAR */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: "1.5rem",
                  borderBottom: "1px solid var(--border)",
                  paddingBottom: "1rem",
                }}
              >
                <div>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      CASE-RR-1042
                    </span>
                    <span
                      style={{
                        padding: "0.15rem 0.4rem",
                        borderRadius: 4,
                        background: "rgba(16, 185, 129, 0.12)",
                        color: "var(--success)",
                        fontSize: "0.6875rem",
                        fontWeight: 700,
                      }}
                    >
                      VERIFIED RECOVERED
                    </span>
                  </div>
                  <h3 className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", margin: "4px 0 0 0" }}>
                    ₹4,999.00
                  </h3>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Customer: cust_razor_101 · Telemetry: BAD_REQUEST_ERROR (Gateway Timeout)
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    VERIFIED SETTLEMENT
                  </div>
                  <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--success)", marginTop: 2 }}>
                    ₹4,999.00
                  </div>
                </div>
              </div>

              {/* UNIFIED DECISION PIPELINE FLOW */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: "1rem",
                }}
                className="grid-responsive-4"
              >
                <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    1. PROPOSAL
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                    send_payment_link
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Expected Net EV: +₹4,250
                  </div>
                </div>

                <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    2. POLICY GATE
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--success)", marginTop: 4 }}>
                    ALLOWED
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Stopping rules: ALL PASS
                  </div>
                </div>

                <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    3. EXECUTION
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--accent)", marginTop: 4 }}>
                    Link Created
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: 4, fontFamily: "monospace" }}>
                    pay_link_1042
                  </div>
                </div>

                <div style={{ padding: "1rem", background: "rgba(16, 185, 129, 0.05)", borderRadius: 6, border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--success)", textTransform: "uppercase", fontWeight: 700 }}>
                    4. SETTLEMENT
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--success)", marginTop: 4 }}>
                    HMAC VERIFIED
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Signed webhook verified
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div>
              {/* CASE 2: FRAUD STOP */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: "1.5rem",
                  borderBottom: "1px solid var(--border)",
                  paddingBottom: "1rem",
                }}
              >
                <div>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      CASE-RR-9081
                    </span>
                    <span
                      style={{
                        padding: "0.15rem 0.4rem",
                        borderRadius: 4,
                        background: "rgba(239, 68, 68, 0.12)",
                        color: "var(--danger)",
                        fontSize: "0.6875rem",
                        fontWeight: 700,
                      }}
                    >
                      POLICY STOPPED
                    </span>
                  </div>
                  <h3 className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", margin: "4px 0 0 0" }}>
                    ₹18,200.00
                  </h3>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Customer: cust_risk_909 · Telemetry: FRAUD_RISK_SUSPECTED
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    CAPITAL PROTECTED
                  </div>
                  <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--danger)", marginTop: 2 }}>
                    ₹18,200.00
                  </div>
                </div>
              </div>

              {/* UNIFIED DECISION PIPELINE FLOW */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: "1rem",
                }}
                className="grid-responsive-4"
              >
                <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    1. PROPOSAL
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--warning)", marginTop: 4 }}>
                    retry_payment
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Evaluated by engine
                  </div>
                </div>

                <div style={{ padding: "1rem", background: "rgba(239, 68, 68, 0.05)", borderRadius: 6, border: "1px solid rgba(239, 68, 68, 0.2)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--danger)", textTransform: "uppercase", fontWeight: 700 }}>
                    2. POLICY GATE
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--danger)", marginTop: 4 }}>
                    BLOCKED (STOP)
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--danger)", marginTop: 4 }}>
                    Rule: fraud_retry_protection
                  </div>
                </div>

                <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    3. EXECUTION
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-muted)", marginTop: 4 }}>
                    SUPPRESSED
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    0 API calls dispatched
                  </div>
                </div>

                <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    4. OUTCOME
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--danger)", marginTop: 4 }}>
                    PROTECTED
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    ₹18,200 chargeback risk prevented
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* WORKSPACE FOOTER LINK */}
        <div
          style={{
            padding: "0.75rem 1.5rem",
            background: "var(--bg-secondary)",
            borderTop: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            RevPlug policy engine enforces non-bypassable constraints on all interventions.
          </span>
          <Link
            href="/recovery"
            style={{ fontSize: "0.75rem", color: "var(--accent)", textDecoration: "none", fontWeight: 600 }}
          >
            Open Recovery Workspace in App →
          </Link>
        </div>
      </div>
    </section>
  );
}
