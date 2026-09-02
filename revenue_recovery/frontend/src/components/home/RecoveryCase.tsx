"use client";

import { useState } from "react";
import Link from "next/link";

export default function RecoveryCase() {
  const [activeTab, setActiveTab] = useState<"case1" | "case2">("case1");

  return (
    <div style={{ padding: "3rem 0" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          ACTUAL PRODUCT PREVIEW
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
          Built for the moment revenue starts slipping.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
          Live workspace view showing real AI proposal, server-side policy gate, and verified settlement telemetry.
        </p>
      </div>

      {/* PRODUCT PREVIEW CONTAINER (WIDE & CLEAN) */}
      <div
        style={{
          border: "1px solid #21262d",
          borderRadius: 8,
          background: "#0d1117",
          overflow: "hidden",
        }}
      >
        {/* APP HEADER BAR */}
        <div
          style={{
            padding: "0.75rem 1.25rem",
            background: "#161b22",
            borderBottom: "1px solid #21262d",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444", display: "inline-block" }} />
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b", display: "inline-block" }} />
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#10b981", display: "inline-block" }} />
            <span style={{ marginLeft: "0.5rem", fontSize: "0.75rem", color: "#8b949e", fontFamily: "monospace" }}>
              app.revplug.internal/recovery/workspace
            </span>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setActiveTab("case1")}
              style={{
                fontSize: "0.75rem",
                padding: "0.25rem 0.6rem",
                borderRadius: 4,
                border: "1px solid #30363d",
                background: activeTab === "case1" ? "#21262d" : "transparent",
                color: activeTab === "case1" ? "#f0f6fc" : "#8b949e",
                cursor: "pointer",
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
                border: "1px solid #30363d",
                background: activeTab === "case2" ? "#21262d" : "transparent",
                color: activeTab === "case2" ? "#f0f6fc" : "#8b949e",
                cursor: "pointer",
              }}
            >
              Case #RR-9081 (₹18,200)
            </button>
          </div>
        </div>

        {/* WORKSPACE CONTENT */}
        <div style={{ padding: "1.5rem" }}>
          {activeTab === "case1" ? (
            <div>
              {/* CASE TOP INFO */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem", borderBottom: "1px solid #21262d", paddingBottom: "1rem" }}>
                <div>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className="font-mono" style={{ fontSize: "0.75rem", color: "#6e7681" }}>CASE-RR-1042</span>
                    <span style={{ padding: "0.15rem 0.4rem", borderRadius: 4, background: "rgba(16, 185, 129, 0.15)", color: "#10b981", fontSize: "0.6875rem", fontWeight: 700 }}>
                      RECOVERED
                    </span>
                  </div>
                  <h3 className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0 0 0" }}>
                    ₹4,999.00
                  </h3>
                  <div style={{ fontSize: "0.75rem", color: "#8b949e", marginTop: 4 }}>
                    Customer: cust_razor_101 · Telemetry: BAD_REQUEST_ERROR (Gateway Timeout)
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase" }}>VERIFIED SETTLEMENT</div>
                  <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "#10b981", marginTop: 2 }}>
                    ₹4,999.00
                  </div>
                </div>
              </div>

              {/* DECISION TRACE GRID */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>AI PROPOSAL</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#f0f6fc", marginTop: 4 }}>send_payment_link</div>
                  <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: 4 }}>Groq Llama-3.3-70b (91% confidence)</div>
                </div>

                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>POLICY GATE</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981", marginTop: 4 }}>ALLOWED</div>
                  <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: 4 }}>Rule: stopping_rules_pass</div>
                </div>

                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>RAZORPAY ACTION</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#6366f1", marginTop: 4 }}>Link Created</div>
                  <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: 4 }}>https://rzp.io/i/rec_sample_4999</div>
                </div>

                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>SETTLEMENT</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#10b981", marginTop: 4 }}>VERIFIED</div>
                  <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: 4 }}>HMAC-SHA256 &amp; Amount Matched</div>
                </div>
              </div>
            </div>
          ) : (
            <div>
              {/* CASE 2 TOP INFO */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem", borderBottom: "1px solid #21262d", paddingBottom: "1rem" }}>
                <div>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className="font-mono" style={{ fontSize: "0.75rem", color: "#6e7681" }}>CASE-RR-9081</span>
                    <span style={{ padding: "0.15rem 0.4rem", borderRadius: 4, background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", fontSize: "0.6875rem", fontWeight: 700 }}>
                      STOPPED
                    </span>
                  </div>
                  <h3 className="font-mono" style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", margin: "4px 0 0 0" }}>
                    ₹18,200.00
                  </h3>
                  <div style={{ fontSize: "0.75rem", color: "#8b949e", marginTop: 4 }}>
                    Customer: cust_risk_909 · Telemetry: FRAUD_RISK_SUSPECTED
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "0.6875rem", color: "#6e7681", textTransform: "uppercase" }}>CAPITAL PROTECTED</div>
                  <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "#ef4444", marginTop: 2 }}>
                    ₹18,200.00
                  </div>
                </div>
              </div>

              {/* DECISION TRACE GRID */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>AI PROPOSED</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#f59e0b", marginTop: 4 }}>retry_payment</div>
                  <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: 4 }}>Groq Llama-3.3-70b (75% confidence)</div>
                </div>

                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>POLICY GATE</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#ef4444", marginTop: 4 }}>BLOCKED</div>
                  <div style={{ fontSize: "0.7rem", color: "#ef4444", marginTop: 4 }}>Rule: fraud_retry_protection</div>
                </div>

                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>RAZORPAY ACTION</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#8b949e", marginTop: 4 }}>NOT EXECUTED</div>
                  <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: 4 }}>0 API calls made</div>
                </div>

                <div style={{ padding: "1rem", background: "#161b22", borderRadius: 6, border: "1px solid #21262d" }}>
                  <div style={{ fontSize: "0.65rem", color: "#6e7681", textTransform: "uppercase" }}>SETTLEMENT</div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#ef4444", marginTop: 4 }}>₹0 RECOVERED</div>
                  <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: 4 }}>₹18,200 Shielded from unsafe retry</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* WORKSPACE FOOTER LINK */}
        <div style={{ padding: "0.75rem 1.5rem", background: "#161b22", borderTop: "1px solid #21262d", textAlign: "right" }}>
          <Link href="/recovery" style={{ fontSize: "0.75rem", color: "#6366f1", textDecoration: "none", fontWeight: 600 }}>
            Open Recovery Workspace in App →
          </Link>
        </div>
      </div>
    </div>
  );
}
