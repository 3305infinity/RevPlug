"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CaseDetail, CaseTrace } from "@/lib/api";
import DecisionTraceView from "@/components/recovery/DecisionTraceView";
import DecisionCardCenterpiece from "@/components/recovery/DecisionCardCenterpiece";
import TrustPanel from "@/components/recovery/TrustPanel";

const fmt = (n: number) =>
  "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

interface CandidateEval {
  action: string;
  recovery_probability: number;
  intervention_cost: number;
  gross_expected_recovery: number;
  net_expected_recovery: number;
  policy_status: "ALLOWED" | "BLOCKED";
  policy_rule?: string;
}

interface ReplayStep {
  step: number;
  title: string;
  badge: string;
  badgeType: "neutral" | "info" | "success" | "warning" | "danger";
  summary: string;
  details: Record<string, any>;
}

// ---------------------------------------------------------------------------
// Preset Showcase Demo Cases
// ---------------------------------------------------------------------------
const SHOWCASE_CASE_1_STEPS: ReplayStep[] = [
  {
    step: 1,
    title: "1. REVENUE AT RISK",
    badge: "₹4,999.00",
    badgeType: "info",
    summary: "Payment failure detected on customer account cust_razor_101",
    details: {
      item_id: "demo_case_4999",
      amount_at_risk: "₹4,999.00",
      currency: "INR",
      customer_id: "cust_razor_101",
      source: "payment_failure",
      created_at: "2026-08-31 10:14:02 UTC",
    },
  },
  {
    step: 2,
    title: "2. SIGNAL",
    badge: "BAD_REQUEST_ERROR",
    badgeType: "warning",
    summary: "Gateway returned temporary authorization timeout code during card charge attempt",
    details: {
      gateway_error_code: "BAD_REQUEST_ERROR",
      error_source: "gateway",
      error_step: "payment_authorization",
      gateway_message: "Payment failed due to temporary provider authorization timeout",
      attempt_count: 1,
    },
  },
  {
    step: 3,
    title: "3. AI DIAGNOSIS",
    badge: "network_timeout (91%)",
    badgeType: "info",
    summary: "Groq LLM diagnosed temporary gateway degradation on healthy customer history",
    details: {
      root_cause: "network_timeout",
      confidence: "91%",
      ai_provider: "groq",
      ai_model: "llama-3.3-70b-versatile",
      diagnosis_rationale: "Transient gateway failure. Customer account exhibits normal payment history.",
    },
  },
  {
    step: 4,
    title: "4. AI PROPOSAL",
    badge: "send_payment_link",
    badgeType: "info",
    summary: "AI Agent recommended generating a direct Razorpay payment link",
    details: {
      proposed_action: "send_payment_link",
      confidence: 0.91,
      model_name: "groq-llama-3.3-70b",
      rationale: "Issue a direct payment link to allow customer to complete payment without token retry fees.",
    },
  },
  {
    step: 5,
    title: "5. POLICY CHECK",
    badge: "ALLOWED",
    badgeType: "success",
    summary: "Deterministic policy engine validated proposal against all hard constraints",
    details: {
      verdict: "ALLOWED",
      rule_evaluated: "stopping_rules_pass",
      opt_out_check: "PASS (Opted Out = False)",
      fraud_check: "PASS (Fraud Flag = False)",
      retry_budget: "PASS (Attempt 1 / 3)",
    },
  },
  {
    step: 6,
    title: "6. EV / DECISION",
    badge: "EV ₹4,449.00",
    badgeType: "success",
    summary: "Optimizer ranked 5 candidates; selected send_payment_link for highest net EV",
    details: {
      selected_action: "send_payment_link",
      why: "Highest net expected recovery (₹4,449.00) among policy-permitted actions",
      net_expected_value: "₹4,449.00",
      gross_expected_recovery: "₹4,499.00",
      intervention_cost: "₹50.00",
      recovery_probability: "90.0%",
    },
  },
  {
    step: 7,
    title: "7. RAZORPAY ACTION",
    badge: "LINK CREATED",
    badgeType: "info",
    summary: "Razorpay Test Mode Payment Link generated with embedded reference notes",
    details: {
      action_type: "send_payment_link",
      payment_link_id: "plink_demo_4999_xyz",
      short_url: "https://rzp.io/i/rec_demo_4999",
      reference_id: "demo_case_4999",
      status: "issued",
    },
  },
  {
    step: 8,
    title: "8. PAYMENT EVENT",
    badge: "payment_link.paid",
    badgeType: "info",
    summary: "Razorpay webhook received notifying successful customer payment",
    details: {
      event_type: "payment_link.paid",
      event_id: "evt_pay_link_paid_4999",
      razorpay_payment_id: "pay_rzp_captured_4999",
      amount_received: "₹4,999.00",
    },
  },
  {
    step: 9,
    title: "9. SETTLEMENT VERIFICATION",
    badge: "VERIFIED",
    badgeType: "success",
    summary: "Authoritative SettlementVerifier validated HMAC signature and correlated payment",
    details: {
      signature_check: "HMAC-SHA256 MATCHED",
      amount_check: "₹4,999.00 EXACT MATCH",
      currency_check: "INR MATCHED",
      idempotency_check: "EVENT UNIQUE (FIRST TIME)",
      correlation_id: "demo_case_4999",
    },
  },
  {
    step: 10,
    title: "10. VERIFIED RECOVERY",
    badge: "₹4,999 VERIFIED RECOVERED",
    badgeType: "success",
    summary: "Item transitioned to RECOVERED with immutable audit log proof",
    details: {
      final_status: "RECOVERED",
      verified_recovered_amount: "₹4,999.00",
      net_financial_gain: "₹4,949.00",
      audit_events_recorded: 9,
    },
  },
];

const SHOWCASE_CASE_1_CANDIDATES: CandidateEval[] = [
  { action: "send_payment_link", recovery_probability: 0.90, intervention_cost: 5000, gross_expected_recovery: 449910, net_expected_recovery: 444910, policy_status: "ALLOWED" },
  { action: "retry_payment", recovery_probability: 0.85, intervention_cost: 50000, gross_expected_recovery: 424915, net_expected_recovery: 374915, policy_status: "ALLOWED" },
  { action: "send_reminder", recovery_probability: 0.50, intervention_cost: 2000, gross_expected_recovery: 249950, net_expected_recovery: 247950, policy_status: "ALLOWED" },
  { action: "escalate_human", recovery_probability: 0.70, intervention_cost: 500000, gross_expected_recovery: 349930, net_expected_recovery: -150070, policy_status: "ALLOWED" },
  { action: "stop_recovery", recovery_probability: 0.00, intervention_cost: 0, gross_expected_recovery: 0, net_expected_recovery: 0, policy_status: "ALLOWED" },
];

const SHOWCASE_CASE_2_STEPS: ReplayStep[] = [
  {
    step: 1,
    title: "1. REVENUE AT RISK",
    badge: "₹18,200.00",
    badgeType: "danger",
    summary: "Payment failure detected on high-risk transaction cust_risk_909",
    details: {
      item_id: "demo_case_18200",
      amount_at_risk: "₹18,200.00",
      currency: "INR",
      customer_id: "cust_risk_909",
      source: "payment_failure",
      created_at: "2026-08-31 11:02:15 UTC",
    },
  },
  {
    step: 2,
    title: "2. SIGNAL",
    badge: "FRAUD_RISK_SUSPECTED",
    badgeType: "danger",
    summary: "Telemetry engine flagged high velocity and synthetic card pattern",
    details: {
      gateway_error_code: "FRAUD_RISK_SUSPECTED",
      fraud_flag: true,
      velocity_alert: "3 attempts in 60s",
      risk_score: "0.94 (CRITICAL)",
    },
  },
  {
    step: 3,
    title: "3. AI DIAGNOSIS",
    badge: "fraud_suspected (95%)",
    badgeType: "danger",
    summary: "Groq LLM identified fraud indicators from velocity metadata",
    details: {
      root_cause: "fraud_suspected",
      confidence: "95%",
      ai_provider: "groq",
      ai_model: "llama-3.3-70b-versatile",
      rationale: "High risk fraud pattern. Card velocity threshold exceeded.",
    },
  },
  {
    step: 4,
    title: "4. AI PROPOSAL",
    badge: "retry_payment",
    badgeType: "warning",
    summary: "Naive AI proposal recommended retrying payment based on soft decline string",
    details: {
      proposed_action: "retry_payment",
      confidence: 0.75,
      model_name: "groq-llama-3.3-70b",
      rationale: "AI suggested retrying token. (UNSAFE PROPOSAL)",
    },
  },
  {
    step: 5,
    title: "5. POLICY CHECK",
    badge: "BLOCKED",
    badgeType: "danger",
    summary: "Deterministic Policy Engine OVERRODE AI proposal due to fraud protection rule",
    details: {
      verdict: "BLOCKED (OVERRIDDEN)",
      rule_evaluated: "fraud_retry_protection",
      reason: "Automated payment retries are strictly prohibited on items with fraud risk flags.",
      policy_override: "TRUE (AI PROPOSAL BLOCKED BY POLICY GATE)",
    },
  },
  {
    step: 6,
    title: "6. EV / DECISION",
    badge: "STOP SELECTED",
    badgeType: "danger",
    summary: "Policy Gate forced STOP action; prevented executing unsafe payment retry",
    details: {
      selected_action: "stop_recovery",
      why: "All intervention actions blocked by fraud safety policy",
      net_expected_value: "₹0.00",
      policy_protection_active: true,
    },
  },
  {
    step: 7,
    title: "7. RAZORPAY ACTION",
    badge: "NOT EXECUTED",
    badgeType: "neutral",
    summary: "Execution boundary blocked gateway calls; 0 API calls made",
    details: {
      gateway_calls_made: 0,
      execution_status: "SKIPPED_BY_SAFETY_GUARD",
      cost_incurred: "₹0.00",
    },
  },
  {
    step: 8,
    title: "8. PAYMENT EVENT",
    badge: "NONE",
    badgeType: "neutral",
    summary: "No payment events generated (stopped safely)",
    details: {
      event_type: "NONE",
      status: "no_event",
    },
  },
  {
    step: 9,
    title: "9. SETTLEMENT VERIFICATION",
    badge: "N/A",
    badgeType: "neutral",
    summary: "Settlement verification skipped because item was safely stopped",
    details: {
      verification_status: "skipped",
      reason: "item_stopped_by_policy",
    },
  },
  {
    step: 10,
    title: "10. VERIFIED RECOVERY",
    badge: "₹18,200 PROTECTED",
    badgeType: "success",
    summary: "Recovered: ₹0 | ₹18,200 Protected from unsafe retries and chargeback fees",
    details: {
      final_status: "STOPPED",
      actual_recovered: "₹0.00",
      protected_capital: "₹18,200.00",
      policy_violations_prevented: 1,
    },
  },
];

const SHOWCASE_CASE_2_CANDIDATES: CandidateEval[] = [
  { action: "retry_payment", recovery_probability: 0.10, intervention_cost: 50000, gross_expected_recovery: 182000, net_expected_recovery: 132000, policy_status: "BLOCKED", policy_rule: "fraud_retry_protection" },
  { action: "send_payment_link", recovery_probability: 0.05, intervention_cost: 5000, gross_expected_recovery: 91000, net_expected_recovery: 86000, policy_status: "BLOCKED", policy_rule: "fraud_retry_protection" },
  { action: "send_reminder", recovery_probability: 0.00, intervention_cost: 2000, gross_expected_recovery: 0, net_expected_recovery: -2000, policy_status: "BLOCKED", policy_rule: "fraud_retry_protection" },
  { action: "escalate_human", recovery_probability: 0.20, intervention_cost: 500000, gross_expected_recovery: 364000, net_expected_recovery: -136000, policy_status: "BLOCKED", policy_rule: "fraud_retry_protection" },
  { action: "stop_recovery", recovery_probability: 0.00, intervention_cost: 0, gross_expected_recovery: 0, net_expected_recovery: 0, policy_status: "ALLOWED" },
];

export default function CaseWorkspace() {
  const params = useParams();
  const id = params?.id as string;
  const [mode, setMode] = useState<"showcase1" | "showcase2" | "live">("showcase1");
  const [activeStep, setActiveStep] = useState<number>(10);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [techOpen, setTechOpen] = useState<boolean>(false);
  const [liveDetail, setLiveDetail] = useState<CaseDetail | null>(null);
  const [liveTrace, setLiveTrace] = useState<CaseTrace | null>(null);

  useEffect(() => {
    if (id && id !== "demo_case_4999" && id !== "demo_case_18200") {
      setMode("live");
      api.itemDetail(id).then(setLiveDetail).catch(() => {});
      api.caseTrace(id).then(setLiveTrace).catch(() => {});
    }
  }, [id]);

  useEffect(() => {
    let timer: any;
    if (isPlaying) {
      timer = setInterval(() => {
        setActiveStep((prev) => {
          if (prev >= 10) {
            setIsPlaying(false);
            return 10;
          }
          return prev + 1;
        });
      }, 1200);
    }
    return () => clearInterval(timer);
  }, [isPlaying]);

  const currentSteps = mode === "showcase1" ? SHOWCASE_CASE_1_STEPS : mode === "showcase2" ? SHOWCASE_CASE_2_STEPS : SHOWCASE_CASE_1_STEPS;
  const currentCandidates = mode === "showcase1" ? SHOWCASE_CASE_1_CANDIDATES : mode === "showcase2" ? SHOWCASE_CASE_2_CANDIDATES : SHOWCASE_CASE_1_CANDIDATES;
  const activeStepObj = currentSteps.find((s) => s.step === activeStep) || currentSteps[9];

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* NAVIGATION BAR */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none" }}>
          ← Back to Recovery Queue
        </Link>
        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
          RevPlug Case Replay Engine
        </div>
      </div>

      {/* DECISION CARD CENTERPIECE */}
      <DecisionCardCenterpiece trace={liveTrace} detail={liveDetail} />

      {/* TRUST & SAFETY PANEL */}
      <TrustPanel />

      {/* DECISION TRACE CENTERPIECE */}
      <div style={{ marginBottom: "2rem" }}>
        <DecisionTraceView trace={liveTrace} detail={liveDetail} />
      </div>



      {/* CASE HEADER */}
      <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: 4 }}>
              <span className={`status-badge status-${mode === "showcase1" ? "recovered" : "stopped"}`}>
                {mode === "showcase1" ? "RECOVERED" : "STOPPED"}
              </span>
              <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {mode === "showcase1" ? "demo_case_4999" : "demo_case_18200"}
              </span>
            </div>
            <h1 className="font-mono" style={{ fontSize: "1.875rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              {mode === "showcase1" ? "₹4,999.00" : "₹18,200.00"}
            </h1>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>
              Customer: <span className="font-mono">{mode === "showcase1" ? "cust_razor_101" : "cust_risk_909"}</span> · Surface: payment_failure · Currency: INR
            </div>
          </div>

          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {mode === "showcase1" ? "Verified Recovered" : "Capital Protected"}
            </div>
            <div className="font-mono" style={{ fontSize: "1.625rem", fontWeight: 700, color: mode === "showcase1" ? "var(--success)" : "var(--danger)", marginTop: 2 }}>
              {mode === "showcase1" ? "₹4,999.00" : "₹18,200.00"}
            </div>
          </div>
        </div>
      </div>

      {/* 10-STEP TIMELINE PLAYER BAR */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            10-STAGE OPERATIONAL INVESTIGATION TIMELINE
          </div>

          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="btn-primary"
              style={{ fontSize: "0.75rem", padding: "0.3rem 0.75rem", display: "flex", alignItems: "center", gap: "0.35rem" }}
            >
              {isPlaying ? "⏸ Pause Replay" : "▶ Play Case Replay"}
            </button>
            <button
              onClick={() => { setActiveStep(1); setIsPlaying(false); }}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "0.3rem 0.6rem" }}
            >
              ↺ Reset
            </button>
          </div>
        </div>

        {/* STEP BUTTONS GRID */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(10, 1fr)", gap: "0.35rem" }}>
          {currentSteps.map((s) => {
            const isCurrent = s.step === activeStep;
            const isPassed = s.step <= activeStep;

            let bgColor = "var(--bg-secondary)";
            let borderColor = "var(--border)";
            let textColor = "var(--text-muted)";

            if (isPassed) {
              if (s.badgeType === "danger") {
                bgColor = "rgba(239, 68, 68, 0.1)";
                borderColor = "rgba(239, 68, 68, 0.4)";
                textColor = "var(--danger)";
              } else if (s.badgeType === "success") {
                bgColor = "rgba(16, 185, 129, 0.1)";
                borderColor = "rgba(16, 185, 129, 0.4)";
                textColor = "var(--success)";
              } else {
                bgColor = "rgba(99, 102, 241, 0.1)";
                borderColor = "rgba(99, 102, 241, 0.4)";
                textColor = "var(--accent)";
              }
            }

            if (isCurrent) {
              borderColor = "var(--text-primary)";
            }

            return (
              <button
                key={s.step}
                onClick={() => { setActiveStep(s.step); setIsPlaying(false); }}
                style={{
                  padding: "0.5rem 0.25rem",
                  borderRadius: 6,
                  background: bgColor,
                  border: `1px solid ${borderColor}`,
                  cursor: "pointer",
                  textAlign: "center",
                  outline: isCurrent ? "2px solid var(--accent)" : "none",
                  outlineOffset: 1,
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                  STAGE {s.step}
                </div>
                <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: textColor, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.title.replace(/^\d+\.\s*/, "")}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ACTIVE STAGE FOCUS CARD */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.25rem", borderLeft: `4px solid ${activeStepObj.badgeType === "danger" ? "var(--danger)" : activeStepObj.badgeType === "success" ? "var(--success)" : "var(--accent)"}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <div>
            <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              CURRENT FOCUS STAGE ({activeStep} / 10)
            </span>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)", margin: "2px 0 0 0" }}>
              {activeStepObj.title}
            </h2>
          </div>

          <span className={`status-badge status-${activeStepObj.badgeType}`}>
            {activeStepObj.badge}
          </span>
        </div>

        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: "0 0 1rem 0", lineHeight: 1.5 }}>
          {activeStepObj.summary}
        </p>

        {/* Key-Value Details Table */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem", background: "var(--bg-secondary)", padding: "1rem", borderRadius: 8 }}>
          {Object.entries(activeStepObj.details).map(([k, v]) => (
            <div key={k}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "capitalize" }}>
                {k.replace(/_/g, " ")}
              </div>
              <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>
                {String(v)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MULTI-CANDIDATE EV OPTIMIZER COMPARISON TABLE */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              EXPECTED VALUE OPTIMIZER — CANDIDATE EVALUATION MATRIX
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
              EV = (Amount × Probability) − Intervention Cost
            </div>
          </div>

          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
            Authority: AI Proposes → Optimizer Ranks → Policy Decides
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--text-muted)" }}>
                <th style={{ padding: "0.5rem 0.75rem" }}>CANDIDATE ACTION</th>
                <th style={{ padding: "0.5rem 0.75rem" }}>RECOVERY PROB.</th>
                <th style={{ padding: "0.5rem 0.75rem" }}>COST</th>
                <th style={{ padding: "0.5rem 0.75rem" }}>GROSS EV</th>
                <th style={{ padding: "0.5rem 0.75rem" }}>NET EV</th>
                <th style={{ padding: "0.5rem 0.75rem" }}>POLICY STATUS</th>
              </tr>
            </thead>
            <tbody>
              {currentCandidates.map((cand, idx) => {
                const isSelected = mode === "showcase1" ? cand.action === "send_payment_link" : cand.action === "stop_recovery";
                return (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: "1px solid var(--border)",
                      background: isSelected ? "rgba(99, 102, 241, 0.08)" : "transparent",
                      fontWeight: isSelected ? 700 : 400,
                    }}
                  >
                    <td style={{ padding: "0.625rem 0.75rem", fontFamily: "monospace" }}>
                      {cand.action} {isSelected && <span style={{ color: "var(--accent)", fontSize: "0.7rem", marginLeft: 4 }}>★ SELECTED</span>}
                    </td>
                    <td style={{ padding: "0.625rem 0.75rem" }}>{(cand.recovery_probability * 100).toFixed(0)}%</td>
                    <td style={{ padding: "0.625rem 0.75rem" }}>{fmt(cand.intervention_cost)}</td>
                    <td style={{ padding: "0.625rem 0.75rem" }}>{fmt(cand.gross_expected_recovery)}</td>
                    <td style={{ padding: "0.625rem 0.75rem", color: cand.net_expected_recovery > 0 ? "var(--success)" : "var(--text-muted)" }}>
                      {fmt(cand.net_expected_recovery)}
                    </td>
                    <td style={{ padding: "0.625rem 0.75rem" }}>
                      <span className={`status-badge status-${cand.policy_status === "ALLOWED" ? "success" : "danger"}`}>
                        {cand.policy_status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* TECHNICAL AUDIT LOG INSPECTOR */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
            Immutable Technical Audit Log ({currentSteps.length} lifecycle events)
          </div>
          <button onClick={() => setTechOpen(!techOpen)} className="btn-ghost" style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}>
            {techOpen ? "Hide Technical Details ▲" : "Inspect Raw JSON Trail ▼"}
          </button>
        </div>

        {techOpen && (
          <div style={{ marginTop: "1rem", background: "#0d1117", padding: "1rem", borderRadius: 8, overflowX: "auto" }}>
            <pre style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "#e6edf3", margin: 0 }}>
              {JSON.stringify(activeStepObj, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
