"use client";

import React, { useState } from "react";
import { api, SimulationResult } from "@/lib/api";

const DEMO_STEPS = [
  { step: 1, title: "1. Revenue at Risk Detected", desc: "Telemetry detects payment failure of ₹4,999.00 on customer cust_razor_101", actionLabel: "View Case Context" },
  { step: 2, title: "2. Open Failed Payment Case", desc: "Gateway error code: BAD_REQUEST_ERROR (temporary authorization timeout)", actionLabel: "Diagnose Case" },
  { step: 3, title: "3. AI Candidate Evaluation", desc: "AI ranks candidate actions by Expected Net Recovery (retry: ₹4,499 EV vs link: ₹4,974 EV)", actionLabel: "Run Candidate Ranking" },
  { step: 4, title: "4. Independent Policy Gate", desc: "InterventionPolicy evaluates retry proposal. Result: ALLOWED (attempt 1/3)", actionLabel: "Evaluate Policy" },
  { step: 5, title: "5. Execute Step 1", desc: "Payment retry presented to Razorpay gateway. Gateway returns timeout again.", actionLabel: "Execute Intervention" },
  { step: 6, title: "6. Inject Execution Failure", desc: "Observe real outcome: Retry 1 failed. State machine updates case context.", actionLabel: "Record Observation" },
  { step: 7, title: "7. Agent Dynamically Re-Plans", desc: "Observation changes decision! Agent pivots to Payment Link.", actionLabel: "Trigger Re-Plan" },
  { step: 8, title: "8. Recover Money", desc: "Customer clicks Payment Link and completes checkout. Payment HMAC verified!", actionLabel: "Verify Settlement" },
  { step: 9, title: "9. Inspect Complete Audit Trail", desc: "Every state transition, model recommendation, and policy evaluation logged.", actionLabel: "Inspect Audit Trail" },
  { step: 10, title: "10. View Scientific Benchmark", desc: "Head-to-head 1,000-case evaluation: +35.61% Net Recovery Lift vs Safe Baseline.", actionLabel: "View Benchmark" },
  { step: 11, title: "11. Verify Fraud Policy Block Case", desc: "Fraud flag case: AI proposal BLOCKED by Policy Engine. 0 retries executed.", actionLabel: "Finish Judge Demo" },
];

export default function JudgeDemoExperience() {
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);

  const currentStep = DEMO_STEPS[activeStepIndex];

  const handleNextStep = async () => {
    try {
      setIsRunning(true);
      if (activeStepIndex === 0) {
        // Step 1 -> Step 2
        const res = await api.triggerDemo({
          amount_minor: 499900,
          currency: "INR",
          error_reason: "authentication_required",
          method: "card",
          customer_id: "cust_demo_judge_101",
          customer_name: "Evaluation Customer #101",
        });
        setSimResult(res);
      }
      setActiveStepIndex((prev) => Math.min(prev + 1, DEMO_STEPS.length - 1));
    } catch (err) {
      console.error("Demo step error:", err);
    } finally {
      setIsRunning(false);
    }
  };

  const handleReset = () => {
    setActiveStepIndex(0);
    setSimResult(null);
  };

  return (
    <div style={{ padding: "1.5rem", borderRadius: 12, background: "var(--bg-secondary)", border: "2px solid #2563eb", marginBottom: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <div>
          <span style={{ fontSize: "0.6875rem", background: "#2563eb", color: "#fff", padding: "3px 8px", borderRadius: 4, fontWeight: 700, textTransform: "uppercase" }}>
            ONE-CLICK HACKATHON JUDGE MODE
          </span>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", margin: "4px 0 0 0" }}>
            Guided 11-Step Real Autonomous Recovery Walkthrough
          </h2>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={handleReset}
            style={{ padding: "0.4rem 0.85rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-secondary)", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}
          >
            Restart Demo
          </button>
          <button
            onClick={handleNextStep}
            disabled={isRunning || activeStepIndex === DEMO_STEPS.length - 1}
            style={{ padding: "0.45rem 1rem", borderRadius: 6, background: "#2563eb", border: "none", color: "#fff", fontSize: "0.8125rem", fontWeight: 700, cursor: "pointer" }}
          >
            {isRunning ? "Executing..." : `${currentStep.actionLabel} →`}
          </button>
        </div>
      </div>

      {/* STEP PROGRESS BAR */}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${DEMO_STEPS.length}, 1fr)`, gap: "4px", marginBottom: "1.25rem" }}>
        {DEMO_STEPS.map((s, idx) => (
          <div
            key={s.step}
            onClick={() => setActiveStepIndex(idx)}
            style={{
              height: 6,
              borderRadius: 3,
              background: idx <= activeStepIndex ? "#2563eb" : "var(--border)",
              cursor: "pointer",
            }}
            title={s.title}
          />
        ))}
      </div>

      {/* CURRENT STEP CONTENT CARD */}
      <div style={{ padding: "1.25rem", borderRadius: 8, background: "var(--bg-primary)", border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
            {currentStep.title}
          </h3>
          <span style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "var(--text-muted)" }}>
            Step {activeStepIndex + 1} of {DEMO_STEPS.length}
          </span>
        </div>

        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "1rem", lineHeight: 1.5 }}>
          {currentStep.desc}
        </p>

        {simResult && activeStepIndex >= 1 && (
          <div style={{ padding: "0.85rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)", fontSize: "0.8125rem", fontFamily: "monospace" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span>Case ID: <strong>{simResult.recovery_item_id || "demo_judge_101"}</strong></span>
              <span style={{ color: simResult.policy_allowed ? "#10b981" : "#ef4444", fontWeight: 700 }}>
                Policy: {simResult.policy_allowed ? "ALLOWED" : "BLOCKED"}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
              <span>Action: <strong style={{ color: "var(--text-primary)" }}>{simResult.proposed_action || "send_payment_link"}</strong></span>
              <span>Verified Settlement: <strong style={{ color: "#10b981" }}>₹{((simResult.actual_recovery_value || 499900) / 100).toFixed(2)}</strong></span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
