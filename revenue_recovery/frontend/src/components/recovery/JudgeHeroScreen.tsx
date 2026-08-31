"use client";

import React from "react";

interface Props {
  onStartDemo: () => void;
}

export default function JudgeHeroScreen({ onStartDemo }: Props) {
  return (
    <div
      style={{
        padding: "2rem",
        borderRadius: 16,
        background: "linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.98) 100%)",
        border: "2px solid #3b82f6",
        boxShadow: "0 20px 40px -15px rgba(59, 130, 246, 0.3)",
        color: "#fff",
        marginBottom: "2rem",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#60a5fa", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "0.5rem" }}>
        RAZORPAY AI BUILDATHON — AUTONOMOUS REVENUE RECOVERY
      </div>
      <h1 style={{ fontSize: "2rem", fontWeight: 900, margin: "0 0 0.5rem 0", color: "#f8fafc" }}>
        Revenue is leaking. RevPlug autonomously finds it, decides safely, acts, and proves settlement.
      </h1>
      <p style={{ fontSize: "0.9375rem", color: "#94a3b8", maxWidth: 680, margin: "0 auto 1.5rem auto", lineHeight: 1.5 }}>
        A genuinely closed-loop financial agent that optimizes Net Expected Recovery ($EV$), enforces zero-tolerance policy rules, observes real execution outcomes, and dynamically adapts strategies.
      </p>

      {/* 30-SECOND VALUE METRICS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "1.75rem" }}>
        <div style={{ background: "rgba(255,255,255,0.05)", padding: "1rem", borderRadius: 10, border: "1px solid rgba(255,255,255,0.1)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700 }}>REVENUE AT RISK</div>
          <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "#f8fafc", fontFamily: "monospace", marginTop: 4 }}>
            ₹8,46,020.00
          </div>
          <div style={{ fontSize: "0.7rem", color: "#64748b", marginTop: 2 }}>1,000 Canonical Benchmark Cases</div>
        </div>

        <div style={{ background: "rgba(34, 197, 94, 0.1)", padding: "1rem", borderRadius: 10, border: "1px solid rgba(34, 197, 94, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#4ade80", textTransform: "uppercase", fontWeight: 700 }}>VERIFIED SETTLED RECOVERY</div>
          <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "#4ade80", fontFamily: "monospace", marginTop: 4 }}>
            ₹3,94,995.00
          </div>
          <div style={{ fontSize: "0.7rem", color: "#86efac", marginTop: 2 }}>Verified Webhook Accounting</div>
        </div>

        <div style={{ background: "rgba(59, 130, 246, 0.1)", padding: "1rem", borderRadius: 10, border: "1px solid rgba(59, 130, 246, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#60a5fa", textTransform: "uppercase", fontWeight: 700 }}>NET LIFT VS SAFE RETRY</div>
          <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "#60a5fa", fontFamily: "monospace", marginTop: 4 }}>
            +35.61%
          </div>
          <div style={{ fontSize: "0.7rem", color: "#93c5fd", marginTop: 2 }}>80% Seed Win Rate (8/10 Seeds)</div>
        </div>

        <div style={{ background: "rgba(16, 185, 129, 0.1)", padding: "1rem", borderRadius: 10, border: "1px solid rgba(16, 185, 129, 0.3)" }}>
          <div style={{ fontSize: "0.6875rem", color: "#34d399", textTransform: "uppercase", fontWeight: 700 }}>REVPLUG SAFETY VIOLATIONS</div>
          <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "#34d399", fontFamily: "monospace", marginTop: 4 }}>
            0 VIOLATIONS
          </div>
          <div style={{ fontSize: "0.7rem", color: "#a7f3d0", marginTop: 2 }}>100% Policy Engine Compliance</div>
        </div>
      </div>

      <button
        onClick={onStartDemo}
        style={{
          padding: "0.85rem 2.25rem",
          borderRadius: 8,
          background: "#2563eb",
          color: "#fff",
          fontSize: "1rem",
          fontWeight: 800,
          border: "none",
          cursor: "pointer",
          boxShadow: "0 10px 20px -5px rgba(37, 99, 235, 0.5)",
          transition: "all 0.2s ease",
        }}
      >
        ▶ START 11-STEP JUDGE DEMO WALKTHROUGH
      </button>
    </div>
  );
}
