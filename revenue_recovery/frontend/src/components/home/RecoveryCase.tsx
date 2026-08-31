"use client";

import { useState, useEffect, useCallback } from "react";
import { CountUpNumber } from "./motion";

export default function RecoveryCase() {
  const [mode, setMode] = useState<"recover" | "stop">("recover");
  const [step, setStep] = useState(0);
  const [isWatching, setIsWatching] = useState(false);

  const resetWatch = useCallback(() => {
    setStep(0);
    setIsWatching(false);
  }, []);

  useEffect(() => {
    resetWatch();
  }, [mode, resetWatch]);

  const handleWatch = () => {
    if (isWatching) return;

    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setStep(3);
      return;
    }

    setIsWatching(true);
    setStep(0);

    let current = 0;
    const interval = setInterval(() => {
      current++;
      setStep(current);
      if (current >= 3) {
        clearInterval(interval);
        setIsWatching(false);
      }
    }, 350);
  };

  return (
    <section id="central-case" style={{ padding: "3.5rem 0 2.5rem" }}>
      {/* SECTION BREADCRUMB & RECOVER / STOP TOGGLE */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace" }}>
          <span>RevPlug</span>
          <span>/</span>
          <span style={{ color: "#f0f6fc", fontWeight: 600 }}>Case RR-1042</span>
          <span>/</span>
          <span style={{ color: "#8b949e" }}>Live Trace</span>
        </div>

        {/* RECOVER / STOP SEGMENTED TEXT CONTROL */}
        <div style={{ display: "flex", gap: "0.25rem", background: "rgba(22, 27, 34, 0.7)", backdropFilter: "blur(4px)", padding: "0.2rem", borderRadius: 6, border: "1px solid #21262d" }}>
          <button
            onClick={() => setMode("recover")}
            style={{
              padding: "0.35rem 0.85rem",
              fontSize: "0.75rem",
              fontWeight: mode === "recover" ? 700 : 500,
              fontFamily: "monospace",
              background: mode === "recover" ? "rgba(33, 38, 45, 0.9)" : "transparent",
              color: mode === "recover" ? "#10b981" : "#8b949e",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            ● RECOVER CASE
          </button>
          <button
            onClick={() => setMode("stop")}
            style={{
              padding: "0.35rem 0.85rem",
              fontSize: "0.75rem",
              fontWeight: mode === "stop" ? 700 : 500,
              fontFamily: "monospace",
              background: mode === "stop" ? "rgba(33, 38, 45, 0.9)" : "transparent",
              color: mode === "stop" ? "#ef4444" : "#8b949e",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            ● SMART STOP CASE
          </button>
        </div>
      </div>

      {/* CENTRAL OPERATIONAL CASE VISUAL */}
      {mode === "recover" ? (
        <div>
          {/* MASSIVE DISPLAY NUMERAL BREAKOUT ANCHOR WITH COUNT-UP & SOFT GLOW */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2.5rem" }}>
            <div>
              <div style={{ fontSize: "0.75rem", color: "#6e7681", textTransform: "uppercase", fontFamily: "monospace" }}>
                CASE AMOUNT AT PLAY
              </div>
              <div
                className="font-mono glow-white"
                style={{
                  fontSize: "clamp(4.5rem, 9vw, 6.5rem)",
                  fontWeight: 800,
                  color: "#f0f6fc",
                  letterSpacing: "-0.05em",
                  lineHeight: 0.95,
                  marginTop: "0.35rem",
                }}
              >
                ₹<CountUpNumber value={4999} duration={800} />
              </div>
            </div>

            {/* WATCH RECOVERY BUTTON */}
            <button
              onClick={handleWatch}
              disabled={isWatching}
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "0.875rem",
                fontWeight: 600,
                background: isWatching ? "#21262d" : "#2563eb",
                color: "#ffffff",
                border: "none",
                borderRadius: 6,
                cursor: isWatching ? "default" : "pointer",
                fontFamily: "monospace",
                boxShadow: isWatching ? "none" : "0 4px 14px rgba(37, 99, 235, 0.35)",
              }}
            >
              {isWatching ? "WATCHING RECOVERY..." : "WATCH RECOVERY →"}
            </button>
          </div>

          {/* AUDIT / LEDGER RECORD TABLE ROW — SINGLE BORDER, RIGHT-ALIGNED NUMERICS */}
          <div style={{ borderTop: "1px solid #21262d", borderBottom: "1px solid #21262d", padding: "1.5rem 0" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr 1fr", gap: "0" }}>
              {/* Col 1: SIGNAL */}
              <div style={{ paddingRight: "2rem", opacity: step >= 0 ? 1 : 0.4, transition: "opacity 0.25s ease" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#f59e0b" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f0f6fc", fontFamily: "monospace" }}>01 SIGNAL</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace" }}>
                  <span>Event</span>
                  <span style={{ color: "#f59e0b", fontWeight: 600 }}>payment.failed</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Failure Cause</span>
                  <span style={{ color: "#f0f6fc" }}>provider_timeout</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Amount</span>
                  <span style={{ color: "#f0f6fc" }} className="font-mono">₹4,999.00</span>
                </div>
              </div>

              {/* Col 2: RESPONSE */}
              <div style={{ paddingLeft: "2rem", paddingRight: "2rem", borderLeft: "1px solid #21262d", opacity: step >= 1 ? 1 : 0.3, transition: "opacity 0.25s ease" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: step >= 2 ? "#10b981" : "#2563eb" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f0f6fc", fontFamily: "monospace" }}>02 DECISION & POLICY</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace" }}>
                  <span>Groq AI Diagnosis</span>
                  <span style={{ color: "#f0f6fc" }}>Temporary degradation</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Policy Gate</span>
                  <span style={{ color: "#10b981", fontWeight: 700 }}>ALLOW (Budget 1/3)</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Action Selected</span>
                  <span style={{ color: "#f0f6fc" }}>send_payment_link</span>
                </div>
              </div>

              {/* Col 3: OUTCOME */}
              <div style={{ paddingLeft: "2rem", borderLeft: "1px solid #21262d", opacity: step >= 3 ? 1 : 0.3, transition: "opacity 0.25s ease" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: step >= 3 ? "#10b981" : "#6e7681" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f0f6fc", fontFamily: "monospace" }}>03 OUTCOME</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace" }}>
                  <span>Settlement Evidence</span>
                  <span style={{ color: "#10b981", fontWeight: 700 }}>VERIFIED</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Webhook ID</span>
                  <span style={{ color: "#f0f6fc" }}>rzp_pay_9021482</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Ledger Credit</span>
                  <span style={{ color: "#10b981", fontWeight: 700 }} className="font-mono">+₹4,999.00</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* STOP MODE CONTAINER (FRAUD RISK AMOUNT = RED WITH RED GLOW) */
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2.5rem" }}>
            <div>
              <div style={{ fontSize: "0.75rem", color: "#6e7681", textTransform: "uppercase", fontFamily: "monospace" }}>
                FRAUD RISK AMOUNT AT PLAY
              </div>
              <div
                className="font-mono glow-red"
                style={{
                  fontSize: "clamp(4.5rem, 9vw, 6.5rem)",
                  fontWeight: 800,
                  color: "#ef4444",
                  letterSpacing: "-0.05em",
                  lineHeight: 0.95,
                  marginTop: "0.35rem",
                }}
              >
                ₹<CountUpNumber value={18200} duration={800} />
              </div>
            </div>

            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#ef4444", fontFamily: "monospace", padding: "0.4rem 0.85rem", borderRadius: 4, background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.3)", backdropFilter: "blur(4px)" }}>
              ● HARD SAFETY BLOCK ENGAGED
            </div>
          </div>

          <div style={{ borderTop: "1px solid #21262d", borderBottom: "1px solid #21262d", padding: "1.5rem 0" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr 1fr", gap: "0" }}>
              <div style={{ paddingRight: "2rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f0f6fc", fontFamily: "monospace" }}>01 RISK SIGNAL</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace" }}>
                  <span>Event</span>
                  <span style={{ color: "#ef4444", fontWeight: 700 }}>payment_risk_failed</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Amount</span>
                  <span style={{ color: "#ef4444" }} className="font-mono">₹18,200.00</span>
                </div>
              </div>

              <div style={{ paddingLeft: "2rem", paddingRight: "2rem", borderLeft: "1px solid #21262d" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f0f6fc", fontFamily: "monospace" }}>02 POLICY OVERRIDE</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace" }}>
                  <span>AI Proposal</span>
                  <span style={{ color: "#8b949e" }}>Retry payment</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Policy Gate</span>
                  <span style={{ color: "#ef4444", fontWeight: 700 }}>BLOCK (Fraud signal)</span>
                </div>
              </div>

              <div style={{ paddingLeft: "2rem", borderLeft: "1px solid #21262d" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f0f6fc", fontFamily: "monospace" }}>03 OUTCOME</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace" }}>
                  <span>Dispatched Actions</span>
                  <span style={{ color: "#f0f6fc" }}>0 (Halted)</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#8b949e", fontFamily: "monospace", marginTop: 4 }}>
                  <span>Ledger Impact</span>
                  <span style={{ color: "#ef4444", fontWeight: 700 }} className="font-mono">₹0.00</span>
                </div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: "1.5rem", fontSize: "0.8125rem", color: "#f0f6fc", fontFamily: "monospace" }}>
            The correct recovery action was no action. RevPlug is rewarded for safe recovery, not maximum retries.
          </div>
        </div>
      )}
    </section>
  );
}
