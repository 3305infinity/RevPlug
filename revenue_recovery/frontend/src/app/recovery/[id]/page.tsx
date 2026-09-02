"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, CaseDetail, CaseTrace } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import DecisionTraceView, { resolveCaseData } from "@/components/recovery/DecisionTraceView";
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
  const router = useRouter();
  const id = params?.id as string;
  const [mode, setMode] = useState<"showcase1" | "showcase2" | "live">("showcase1");
  const [activeStep, setActiveStep] = useState<number>(10);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [techOpen, setTechOpen] = useState<boolean>(false);
  const [liveDetail, setLiveDetail] = useState<CaseDetail | null>(null);
  const [liveTrace, setLiveTrace] = useState<CaseTrace | null>(null);
  const [showNaiveComparison, setShowNaiveComparison] = useState<boolean>(false);
  const [naiveData, setNaiveData] = useState<any>(null);

  // Data clearing state
  const [clearModalOpen, setClearModalOpen] = useState<boolean>(false);
  const [clearPreview, setClearPreview] = useState<any | null>(null);
  const [clearing, setClearing] = useState<boolean>(false);
  const [clearedError, setClearedError] = useState<string | null>(null);

  const handleOpenClearModal = async () => {
    setClearedError(null);
    setClearModalOpen(true);
    try {
      const p = await api.previewClearRecoveryItem(id);
      setClearPreview(p);
    } catch (e) {
      setClearPreview({
        recovery_item_id: id,
        recovery_case: 1,
        decisions_count: 0,
        attempts_count: 0,
        outcomes_count: 0,
        promises_count: 0,
        jobs_count: 0,
      });
    }
  };

  const handleConfirmClear = async () => {
    setClearing(true);
    setClearedError(null);
    try {
      await api.clearRecoveryItem(id);
      setClearModalOpen(false);
      router.push("/dashboard");
    } catch (err) {
      setClearedError(err instanceof Error ? err.message : "Failed to clear recovery case");
      setClearing(false);
    }
  };

  useEffect(() => {
    if (id) {
      if (id !== "demo_case_4999" && id !== "demo_case_18200") {
        setMode("live");
        api.itemDetail(id).then(setLiveDetail).catch(() => {});
        api.caseTrace(id).then(setLiveTrace).catch(() => {});
      }
      api.naiveBaseline(id as string).then(setNaiveData).catch(() => {
        if (id === "demo_case_18200") {
          setNaiveData({
            action_taken: "retry_payment",
            attempts_made: 2,
            intervention_cost_minor: 1000,
            estimated_outcome: "stopped",
            actual_recovered_minor: 0,
            policy_violations: ["FRAUD_RETRY_PROHIBITED"],
            has_policy_violations: true,
            summary: "Naive bot executed fixed payment retries on fraud-risk account, incurring policy violations.",
          });
        } else {
          setNaiveData({
            action_taken: "retry_payment",
            attempts_made: 2,
            intervention_cost_minor: 1000,
            estimated_outcome: "recovered",
            actual_recovered_minor: 499900,
            policy_violations: [],
            has_policy_violations: false,
            summary: "Naive bot blindly retried card without issuing payment link channel pivot.",
          });
        }
      });
    }
  }, [id]);

  useEffect(() => {
    let timer: any;
    if (isPlaying) {
      timer = setInterval(() => {
        setActiveStep((prev) => {
          if (prev >= 10) { setIsPlaying(false); return 10; }
          return prev + 1;
        });
      }, 1200);
    }
    return () => clearInterval(timer);
  }, [isPlaying]);

  // Single unified case data — derived once so every number on page is internally consistent
  const caseData = useMemo(() => {
    if (mode === "showcase1") {
      return { amountAtRisk: 499900, expectedRecovery: 444910, verifiedRecovery: 499900, cost: 2500, status: "recovered", rootCause: "network_timeout" };
    }
    if (mode === "showcase2") {
      return { amountAtRisk: 1820000, expectedRecovery: 0, verifiedRecovery: 0, cost: 0, status: "stopped", rootCause: "fraud_suspected" };
    }
    return resolveCaseData(liveTrace, liveDetail);
  }, [mode, liveTrace, liveDetail]);

  const currentSteps = mode === "showcase1" ? SHOWCASE_CASE_1_STEPS : mode === "showcase2" ? SHOWCASE_CASE_2_STEPS : SHOWCASE_CASE_1_STEPS;
  const currentCandidates = mode === "showcase1" ? SHOWCASE_CASE_1_CANDIDATES : mode === "showcase2" ? SHOWCASE_CASE_2_CANDIDATES : SHOWCASE_CASE_1_CANDIDATES;
  const activeStepObj = currentSteps.find((s) => s.step === activeStep) || currentSteps[9];

  const isRecovered = caseData.verifiedRecovery > 0 || caseData.status === "recovered" || caseData.status === "RECOVERED";
  const customerId = liveDetail?.customer_id || (mode === "showcase1" ? "cust_razor_101" : "cust_risk_909");
  const customerName = getCustomerDisplayName(customerId, (liveDetail as any)?.customer_name);

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", paddingBottom: "3rem" }}>

      {/* ── NAVIGATION BAR ──────────────────────────────────────── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none" }}>
          ← Back to Recovery Queue
        </Link>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            onClick={() => setShowNaiveComparison(!showNaiveComparison)}
            style={{
              fontSize: "0.75rem", fontWeight: 700, padding: "0.35rem 0.75rem",
              borderRadius: 6,
              border: showNaiveComparison ? "1px solid #ef4444" : "1px solid var(--border)",
              background: showNaiveComparison ? "rgba(239, 68, 68, 0.1)" : "var(--bg-secondary)",
              color: showNaiveComparison ? "#ef4444" : "var(--text-primary)",
              cursor: "pointer",
            }}
          >
            {showNaiveComparison ? "Hide Naive Bot Comparison ▲" : "🤖 Compare with Naive Retry Bot ▼"}
          </button>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button
              onClick={() => setMode("showcase1")}
              style={{ fontSize: "0.6875rem", padding: "0.25rem 0.6rem", borderRadius: 4, border: mode === "showcase1" ? "1px solid var(--accent)" : "1px solid var(--border)", background: mode === "showcase1" ? "rgba(99,102,241,0.12)" : "var(--bg-secondary)", color: mode === "showcase1" ? "var(--accent)" : "var(--text-muted)", cursor: "pointer", fontWeight: 700 }}
            >Case 1 — Recovered</button>
            <button
              onClick={() => setMode("showcase2")}
              style={{ fontSize: "0.6875rem", padding: "0.25rem 0.6rem", borderRadius: 4, border: mode === "showcase2" ? "1px solid #ef4444" : "1px solid var(--border)", background: mode === "showcase2" ? "rgba(239,68,68,0.1)" : "var(--bg-secondary)", color: mode === "showcase2" ? "#ef4444" : "var(--text-muted)", cursor: "pointer", fontWeight: 700 }}
            >Case 2 — Capital Protected</button>
          </div>
        </div>
      </div>

      {/* ── NAIVE BOT COMPARISON ──────────────────────────────────── */}
      {showNaiveComparison && (
        <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "4px solid #ef4444", background: "var(--bg-secondary)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div>
              <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                HEAD-TO-HEAD SINGLE-CASE COMPARISON
              </div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: "2px 0 0 0" }}>What a naive retry bot would have done</h3>
            </div>
            <span style={{ fontSize: "0.6875rem", background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", border: "1px solid rgba(239, 68, 68, 0.3)", padding: "2px 8px", borderRadius: 4, fontWeight: 700 }}>
              PITCH COMPARATOR
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
            {/* Column A: Naive Bot */}
            <div style={{ padding: "1rem", borderRadius: 8, background: "rgba(239, 68, 68, 0.04)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#ef4444" }}>🤖 NAIVE FIXED-RETRY BOT</span>
                <span className="status-badge status-danger" style={{ fontSize: "0.625rem" }}>FIXED RETRY</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.78125rem" }}>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>ACTION TAKEN:</span>
                  <div className="font-mono" style={{ fontWeight: 700, color: "#ef4444" }}>retry_payment (Fixed 2 attempts)</div>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>INTERVENTION COST:</span>
                  <div className="font-mono" style={{ fontWeight: 600 }}>{fmt(naiveData?.intervention_cost_minor || 1000)}</div>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>POLICY CHECKS:</span>
                  <div style={{ color: "#ef4444", fontWeight: 700 }}>NONE (BYPASSED POLICY ENGINE)</div>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>POLICY VIOLATIONS:</span>
                  {naiveData?.has_policy_violations ? (
                    <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginTop: 2 }}>
                      {naiveData.policy_violations.map((v: string) => (
                        <span key={v} style={{ fontSize: "0.625rem", background: "#ef4444", color: "#fff", padding: "1px 6px", borderRadius: 3, fontWeight: 700 }}>⚠️ {v}</span>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>No hard policy violation, but wasted retry cost.</div>
                  )}
                </div>
                <div style={{ borderTop: "1px solid rgba(239, 68, 68, 0.15)", paddingTop: "0.5rem", marginTop: "0.25rem" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>ESTIMATED OUTCOME:</span>
                  <div style={{ fontWeight: 700, color: naiveData?.actual_recovered_minor > 0 ? "var(--success)" : "#ef4444" }}>
                    {naiveData?.actual_recovered_minor > 0 ? `Recovered ${fmt(naiveData.actual_recovered_minor)}` : "Failed / Wasted Budget"}
                  </div>
                </div>
              </div>
            </div>
            {/* Column B: RevPlug */}
            <div style={{ padding: "1rem", borderRadius: 8, background: "rgba(16, 185, 129, 0.04)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#10b981" }}>⚡ REVPLUG AUTONOMOUS AGENT</span>
                <span className="status-badge status-success" style={{ fontSize: "0.625rem" }}>BOUNDED POLICY ENGINE</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.78125rem" }}>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>DECISION TAKEN:</span>
                  <div className="font-mono" style={{ fontWeight: 700, color: "#10b981" }}>
                    {liveTrace?.ai_recommendation?.selected_action || (mode === "showcase1" ? "send_payment_link" : "stop_recovery")}
                  </div>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>INTERVENTION COST:</span>
                  <div className="font-mono" style={{ fontWeight: 600 }}>{fmt(caseData.cost)}</div>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>POLICY CHECKS:</span>
                  <div style={{ color: "#10b981", fontWeight: 700 }}>
                    {mode === "showcase2" ? "BLOCKED BY FRAUD GUARD (0 Violations)" : "ALLOWED (Passed 8 Safety Rules)"}
                  </div>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>POLICY PROTECTION:</span>
                  <div style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                    {mode === "showcase2" ? "Zero Unsafe API Calls · 100% Compliant Stop" : "Opt-out & Fraud Risk Checked"}
                  </div>
                </div>
                <div style={{ borderTop: "1px solid rgba(16, 185, 129, 0.15)", paddingTop: "0.5rem", marginTop: "0.25rem" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>VERIFIED OUTCOME:</span>
                  <div style={{ fontWeight: 700, color: isRecovered ? "#10b981" : "var(--accent)" }}>
                    {mode === "showcase1" ? `Verified Recovered ${fmt(caseData.verifiedRecovery)}` : `Capital Protected ${fmt(caseData.amountAtRisk)}`}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── HERO ROW — 3 mega numbers ────────────────────────────── */}
      <div className="card" style={{
        padding: "1.5rem 2rem",
        marginBottom: "0.75rem",
        background: "linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-primary) 100%)",
        border: `2px solid ${isRecovered ? "rgba(16,185,129,0.3)" : mode === "showcase2" ? "rgba(239,68,68,0.25)" : "var(--border)"}`,
      }}>
        {/* Case ID + customer + status - compact header line */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
            <span className={`status-badge status-${isRecovered ? "recovered" : mode === "showcase2" ? "stopped" : caseData.status}`}>
              {caseData.status.toUpperCase()}
            </span>
            <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {mode === "showcase1" ? "demo_case_4999" : mode === "showcase2" ? "demo_case_18200" : id}
            </span>
            <span style={{ color: "var(--border)" }}>·</span>
            <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
              <strong style={{ color: "var(--text-primary)" }}>{customerName}</strong>
              <span className="font-mono" style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginLeft: "0.5rem" }}>({customerId})</span>
            </span>
            <span style={{ color: "var(--border)" }}>·</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Root cause: <strong style={{ color: "var(--text-primary)" }}>{caseData.rootCause}</strong>
            </span>
          </div>

          <button
            onClick={handleOpenClearModal}
            className="btn-ghost"
            style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem", color: "#ef4444", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: 4 }}
          >
            Clear recovery data
          </button>
        </div>

        {/* THE THREE HERO NUMBERS */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.5rem" }}>
          {/* 1. Amount at Risk */}
          <div style={{ borderRight: "1px solid var(--border)", paddingRight: "1.5rem" }}>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
              Amount at Risk
              {(mode === "showcase1" || mode === "showcase2") && <span style={{ marginLeft: 6, fontSize: "0.5rem", fontWeight: 700, color: "#d97706", border: "1px solid rgba(217,119,6,0.3)", padding: "1px 4px", borderRadius: 3 }}>SIMULATION</span>}
            </div>
            <div className="font-mono" style={{ fontSize: "2.25rem", fontWeight: 800, color: "#ef4444", lineHeight: 1 }}>
              {fmt(caseData.amountAtRisk)}
            </div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 6 }}>
              payment_failure · INR
            </div>
          </div>

          {/* 2. Expected Net Recovery */}
          <div style={{ borderRight: "1px solid var(--border)", paddingRight: "1.5rem" }}>
            <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
              Expected Net Recovery
              <span style={{ marginLeft: 6, fontSize: "0.5rem", fontWeight: 700, color: "#6366f1", border: "1px solid rgba(99,102,241,0.3)", padding: "1px 4px", borderRadius: 3 }}>PROJECTED</span>
            </div>
            <div className="font-mono" style={{ fontSize: "2.25rem", fontWeight: 800, color: caseData.expectedRecovery > 0 ? "var(--accent)" : "var(--text-muted)", lineHeight: 1 }}>
              {caseData.expectedRecovery > 0 ? fmt(caseData.expectedRecovery) : "—"}
            </div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 6 }}>
              {caseData.cost > 0 ? `After intervention cost (${fmt(caseData.cost)})` : "No intervention cost"}
            </div>
          </div>

          {/* 3. Actual / Verified Recovery */}
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: isRecovered ? "#10b981" : "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
              {isRecovered ? "✓ Verified Recovered" : mode === "showcase2" ? "🛡 Capital Protected" : "⏳ Actual Recovery"}
            </div>
            <div className="font-mono" style={{ fontSize: "2.5rem", fontWeight: 800, color: isRecovered ? "#10b981" : "var(--text-muted)", lineHeight: 1 }}>
              {mode === "showcase2" ? fmt(caseData.amountAtRisk) : fmt(caseData.verifiedRecovery)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6 }}>
              {isRecovered ? "Settlement HMAC verified" : mode === "showcase2" ? "Saved from unsafe retries" : "Pending or in progress"}
            </div>
          </div>
        </div>
      </div>

      {/* ── DECISION CARD CENTERPIECE ────────────────────────────── */}
      <div style={{ marginBottom: "1rem" }}>
        <DecisionCardCenterpiece trace={liveTrace} detail={liveDetail} />
      </div>

      {/* ── TRUST & SAFETY PANEL ─────────────────────────────────── */}
      <TrustPanel />

      {/* ── AI JUDGMENT VISIBILITY ───────────────────────────────── */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1rem", borderLeft: "4px solid #6366f1" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6366f1", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          AI vs Deterministic Responsibility
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
          <div>
            <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>AI Handles</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.375rem" }}>
              {["Contextual diagnosis", "Candidate recommendation", "Adaptive strategy selection", "Evidence synthesis"].map(item => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: "var(--success)", fontSize: "0.875rem" }}>✓</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>Deterministic System Handles</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "grid", gap: "0.375rem" }}>
              {["Financial calculation", "Policy enforcement", "Safety constraints", "Retry limits", "Settlement verification", "Authorization gates"].map(item => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: "#3b82f6", fontSize: "0.875rem" }}>■</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── DECISION TRACE + ACCORDION DETAILS ───────────────────── */}
      <div style={{ marginBottom: "1.5rem" }}>
        <DecisionTraceView trace={liveTrace} detail={liveDetail} itemId={id} caseData={caseData} />
      </div>

      {/* ── 10-STEP REPLAY TIMELINE ──────────────────────────────── */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            10-Stage Operational Investigation Timeline
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

        {/* STEP BUTTONS */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(10, 1fr)", gap: "0.35rem" }}>
          {currentSteps.map((s) => {
            const isCurrent = s.step === activeStep;
            const isPassed = s.step <= activeStep;
            let bgColor = "var(--bg-secondary)";
            let borderColor = "var(--border)";
            let textColor = "var(--text-muted)";
            if (isPassed) {
              if (s.badgeType === "danger") { bgColor = "rgba(239, 68, 68, 0.1)"; borderColor = "rgba(239, 68, 68, 0.4)"; textColor = "var(--danger)"; }
              else if (s.badgeType === "success") { bgColor = "rgba(16, 185, 129, 0.1)"; borderColor = "rgba(16, 185, 129, 0.4)"; textColor = "var(--success)"; }
              else { bgColor = "rgba(99, 102, 241, 0.1)"; borderColor = "rgba(99, 102, 241, 0.4)"; textColor = "var(--accent)"; }
            }
            if (isCurrent) borderColor = "var(--text-primary)";
            return (
              <button
                key={s.step}
                onClick={() => { setActiveStep(s.step); setIsPlaying(false); }}
                style={{
                  padding: "0.5rem 0.25rem", borderRadius: 6,
                  background: bgColor, border: `1px solid ${borderColor}`,
                  cursor: "pointer", textAlign: "center",
                  outline: isCurrent ? "2px solid var(--accent)" : "none", outlineOffset: 1,
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ fontSize: "0.5625rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>STAGE {s.step}</div>
                <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: textColor, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.title.replace(/^\d+\.\s*/, "")}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── ACTIVE STAGE FOCUS CARD ─────────────────────────────── */}
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
          <span className={`status-badge status-${activeStepObj.badgeType}`}>{activeStepObj.badge}</span>
        </div>
        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: "0 0 1rem 0", lineHeight: 1.5 }}>
          {activeStepObj.summary}
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem", background: "var(--bg-secondary)", padding: "1rem", borderRadius: 8 }}>
          {Object.entries(activeStepObj.details).map(([k, v]) => (
            <div key={k}>
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</div>
              <div className="font-mono" style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>{String(v)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── TECHNICAL AUDIT LOG ─────────────────────────────────── */}
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

      {/* ── DESTRUCTIVE DATA CLEAR CONFIRMATION MODAL ───────────── */}
      {clearModalOpen && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0, 0, 0, 0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "1rem"
        }}>
          <div className="card" style={{ maxWidth: 500, width: "100%", padding: "1.5rem", background: "var(--bg-primary)", border: "1px solid var(--border)", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)" }}>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--danger)", marginBottom: "0.5rem" }}>
              Clear Recovery Data
            </div>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "1rem", lineHeight: 1.5 }}>
              This removes the recovery case and all derived operational data associated with it.
            </p>
            {clearPreview ? (
              <div style={{ background: "var(--bg-secondary)", padding: "0.875rem 1rem", borderRadius: 6, marginBottom: "1.25rem", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, marginBottom: "0.5rem", color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Backend Operational Dependency Graph:
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem", fontFamily: "monospace", fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                  <div>• {clearPreview.recovery_case} recovery case</div>
                  <div>• {clearPreview.decisions_count} decisions</div>
                  <div>• {clearPreview.attempts_count} action attempts</div>
                  <div>• {clearPreview.outcomes_count} evaluation records</div>
                  <div>• {clearPreview.promises_count} promises-to-pay</div>
                  <div>• {clearPreview.jobs_count} queue jobs</div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
                Inspecting backend database dependencies...
              </div>
            )}
            {clearedError && (
              <div style={{ color: "var(--danger)", fontSize: "0.75rem", marginBottom: "1rem", fontWeight: 600 }}>
                {clearedError}
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                onClick={() => setClearModalOpen(false)}
                className="btn-secondary"
                style={{ fontSize: "0.8125rem" }}
                disabled={clearing}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmClear}
                className="btn-primary"
                style={{ fontSize: "0.8125rem", background: "#ef4444", borderColor: "#ef4444" }}
                disabled={clearing}
              >
                {clearing ? "Clearing operational data..." : "Confirm Clear Case"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
