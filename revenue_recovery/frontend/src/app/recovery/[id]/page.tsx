"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  CaseDetail,
  CaseTrace,
  Customer360Profile,
  Incident,
} from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";

import RecoveryDecisionCard from "@/components/recovery/RecoveryDecisionCard";
import RecoveryWhy from "@/components/recovery/RecoveryWhy";
import SelectedIntervention from "@/components/recovery/SelectedIntervention";
import AlternativesTable from "@/components/recovery/AlternativesTable";
import PolicyCard from "@/components/recovery/PolicyCard";
import RecoveryEconomics from "@/components/recovery/RecoveryEconomics";
import RecoveryReceipt from "@/components/recovery/RecoveryReceipt";
import CaseTimeline from "@/components/recovery/CaseTimeline";
import CustomerContext from "@/components/recovery/CustomerContext";
import TrustPanel from "@/components/recovery/TrustPanel";

export default function CaseWorkspace() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [liveDetail, setLiveDetail] = useState<CaseDetail | null>(null);
  const [liveTrace, setLiveTrace] = useState<CaseTrace | null>(null);
  const [customerProfile, setCustomerProfile] = useState<Customer360Profile | null>(null);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [techOpen, setTechOpen] = useState<boolean>(false);

  // Data clearing state
  const [clearModalOpen, setClearModalOpen] = useState<boolean>(false);
  const [clearPreview, setClearPreview] = useState<any | null>(null);
  const [clearing, setClearing] = useState<boolean>(false);
  const [clearedError, setClearedError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);

    Promise.allSettled([
      api.itemDetail(id),
      api.caseTrace(id),
    ]).then(([detailRes, traceRes]) => {
      let detailObj: CaseDetail | null = null;
      let traceObj: CaseTrace | null = null;

      if (detailRes.status === "fulfilled") {
        detailObj = detailRes.value;
        setLiveDetail(detailObj);
      }
      if (traceRes.status === "fulfilled") {
        traceObj = traceRes.value;
        setLiveTrace(traceObj);
      }

      if (!detailObj && !traceObj) {
        setError("Recovery case not found or failed to load.");
      }

      // Fetch customer profile if customer_id is available
      const custId = detailObj?.customer_id || traceObj?.context_snapshot?.item_id;
      if (custId) {
        api.customerRecoveryProfile(custId)
          .then(setCustomerProfile)
          .catch(() => {});
      }

      // Check if this opportunity is affected by an incident
      api.incidentByOpportunity(id)
        .then(setIncident)
        .catch(() => {});

      setLoading(false);
    });
  }, [id]);

  const handleOpenClearModal = async () => {
    setClearedError(null);
    setClearModalOpen(true);
    try {
      const p = await api.previewClearRecoveryItem(id);
      setClearPreview(p);
    } catch {
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

  if (loading) {
    return (
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "3rem 1rem", textAlign: "center", color: "var(--text-muted)" }}>
        <div style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
          Loading recovery decision workspace...
        </div>
        <div style={{ fontSize: "0.8125rem" }}>Fetching decision trace and audit records</div>
      </div>
    );
  }

  if (error || (!liveDetail && !liveTrace)) {
    return (
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "3rem 1rem", textAlign: "center" }}>
        <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "#ef4444", marginBottom: "0.5rem" }}>
          Case Not Found
        </div>
        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
          {error || `Recovery opportunity "${id}" could not be located.`}
        </p>
        <Link href="/recovery" className="btn-primary" style={{ fontSize: "0.8125rem" }}>
          ← Return to Recovery Queue
        </Link>
      </div>
    );
  }

  const amountAtRiskMinor =
    liveTrace?.amount_at_risk_minor ??
    liveDetail?.amount_minor ??
    0;

  const customerId = liveDetail?.customer_id || "unknown";
  const customerName = getCustomerDisplayName(customerId, (liveDetail as any)?.customer_name);

  return (
    <div style={{ maxWidth: 1180, margin: "0 auto", paddingBottom: "3rem" }}>

      {/* ── NAVIGATION BAR & ACTION TOOLBAR ───────────────────────────── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none", fontWeight: 500, display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
          <span>←</span> Back to Recovery Queue
        </Link>

        <div style={{ display: "flex", gap: "0.625rem", alignItems: "center" }}>
          <Link
            href={`/recovery/${id}/voice-call`}
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "#38bdf8",
              background: "rgba(56, 189, 248, 0.08)",
              border: "1px solid rgba(56, 189, 248, 0.25)",
              padding: "0.3rem 0.75rem",
              borderRadius: 6,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.35rem",
              transition: "all 0.12s ease",
            }}
          >
            <span>🎙️</span> Hinglish Voice Assistant
          </Link>
          <button
            onClick={handleOpenClearModal}
            className="btn-ghost"
            style={{ fontSize: "0.75rem", padding: "0.3rem 0.75rem", color: "#f87171", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: 6 }}
          >
            Clear Case
          </button>
        </div>
      </div>

      {/* ── INCIDENT BANNER ── */}
      {incident && (
        <div style={{
          display: "flex", alignItems: "center", gap: "0.875rem", flexWrap: "wrap",
          padding: "0.75rem 1rem", background: "rgba(245,158,11,0.06)",
          border: "1px solid rgba(245,158,11,0.25)", borderRadius: 8, marginBottom: "1rem",
        }}>
          <span style={{
            fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
            background: "rgba(245,158,11,0.12)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)",
          }}>
            {incident.severity} INCIDENT
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", flex: 1 }}>
            This opportunity is affected by:{' '}
            <strong style={{ color: "var(--text-primary)" }}>{incident.title}</strong>
            {' '}({incident.payment_method} &middot; {incident.failure_category.replace(/_/g, " ")})
          </span>
          <Link href={`/incidents/${incident.incident_id}`} style={{
            fontSize: "0.6875rem", fontWeight: 600, color: "#f59e0b",
            textDecoration: "none", padding: "0.3rem 0.65rem", borderRadius: 4,
            border: "1px solid rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.06)",
          }}>
            View Incident →
          </Link>
        </div>
      )}

      {/* ── UNIFIED EXECUTIVE HEADER & PIPELINE STEPPER ── */}
      {(() => {
        const curStatus = (liveDetail?.status || liveTrace?.status || "queued").toLowerCase();
        const isRecovered = curStatus === "recovered";
        const isPendingVer = curStatus === "pending_verification" || curStatus === "intervention_executed";
        const isStopped = curStatus === "stopped";
        const isEscalated = curStatus === "escalated";

        const currentStep = isRecovered || isPendingVer ? 5 : (curStatus === "intervention_pending" ? 4 : (curStatus === "queued" ? 3 : 2));

        const srcType = liveDetail?.source_type || liveDetail?.metadata?.event_type || "payment_failure";
        const surfaceLabel =
          srcType === "checkout_abandonment" ? "CHECKOUT ABANDONMENT" :
          srcType === "subscription_failure" || srcType === "subscription_payment_failed" ? "SUBSCRIPTION RENEWAL" :
          srcType === "mandate_failure" || srcType === "mandate_failed" ? "MANDATE / AUTOPAY" :
          srcType === "overdue_receivable" || srcType === "invoice_overdue" ? "B2B OVERDUE RECEIVABLE" :
          "PAYMENT FAILURE";

        const surfaceDetail =
          liveDetail?.metadata?.invoice_number || liveDetail?.external_id || liveDetail?.metadata?.subscription_id || null;

        const steps = [
          { num: 1, label: "Detect", desc: "Risk Event" },
          { num: 2, label: "Diagnose", desc: "Root Cause" },
          { num: 3, label: "Decision", desc: "Net EV & Policy" },
          { num: 4, label: "Action", desc: "Bounded Dispatch" },
          { num: 5, label: "Verify", desc: "Settlement Proof" },
        ];

        return (
          <div
            className="card"
            style={{
              padding: "1.25rem 1.5rem",
              marginBottom: "1.25rem",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 10,
            }}
          >
            {/* TOP METADATA & OUTCOME STRIP */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <span
                  style={{
                    fontSize: "0.625rem",
                    fontWeight: 700,
                    letterSpacing: "0.06em",
                    color: "var(--accent)",
                    background: "rgba(56, 189, 248, 0.08)",
                    border: "1px solid rgba(56, 189, 248, 0.2)",
                    padding: "0.2rem 0.55rem",
                    borderRadius: 4,
                    textTransform: "uppercase",
                  }}
                >
                  {surfaceLabel}
                </span>
                {surfaceDetail && (
                  <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-muted)" }}>
                    Ref: <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>{surfaceDetail}</span>
                  </span>
                )}
                <span style={{ color: "var(--border)" }}>·</span>
                <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                  Customer: <strong style={{ color: "var(--text-primary)" }}>{customerName}</strong>
                </span>
              </div>

              {/* OUTCOME STATUS PILL */}
              <div>
                {isRecovered && (
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: "#10b981",
                      background: "rgba(16, 185, 129, 0.08)",
                      border: "1px solid rgba(16, 185, 129, 0.25)",
                      padding: "0.3rem 0.75rem",
                      borderRadius: 6,
                    }}
                  >
                    ✓ SETTLEMENT VERIFIED — ₹{(amountAtRiskMinor / 100).toLocaleString()} RECOVERED
                  </span>
                )}
                {isPendingVer && (
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: "#38bdf8",
                      background: "rgba(56, 189, 248, 0.08)",
                      border: "1px solid rgba(56, 189, 248, 0.25)",
                      padding: "0.3rem 0.75rem",
                      borderRadius: 6,
                    }}
                  >
                    ⏳ PENDING SETTLEMENT VERIFICATION
                  </span>
                )}
                {isEscalated && (
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: "#f59e0b",
                      background: "rgba(245, 158, 11, 0.08)",
                      border: "1px solid rgba(245, 158, 11, 0.25)",
                      padding: "0.3rem 0.75rem",
                      borderRadius: 6,
                    }}
                  >
                    ⚑ HUMAN REVIEW REQUIRED
                  </span>
                )}
                {isStopped && (
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: "#f87171",
                      background: "rgba(239, 68, 68, 0.08)",
                      border: "1px solid rgba(239, 68, 68, 0.25)",
                      padding: "0.3rem 0.75rem",
                      borderRadius: 6,
                    }}
                  >
                    🛑 POLICY STOPPED — CAPITAL PROTECTED
                  </span>
                )}
              </div>
            </div>

            {/* STEPPER TRACK PIPELINE */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.625rem" }}>
              {steps.map((st) => {
                const isActive = st.num === currentStep;
                const isPassed = st.num < currentStep || isRecovered;
                return (
                  <div
                    key={st.num}
                    style={{
                      padding: "0.625rem 0.75rem",
                      borderRadius: 6,
                      background: isActive
                        ? "rgba(56, 189, 248, 0.06)"
                        : isPassed
                        ? "rgba(16, 185, 129, 0.04)"
                        : "var(--bg-primary)",
                      border: isActive
                        ? "1px solid rgba(56, 189, 248, 0.3)"
                        : isPassed
                        ? "1px solid rgba(16, 185, 129, 0.18)"
                        : "1px solid var(--border)",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: "0.5625rem", fontWeight: 700, color: isActive ? "var(--accent)" : isPassed ? "#10b981" : "var(--text-muted)", letterSpacing: "0.05em" }}>
                        0{st.num}
                      </span>
                      {isPassed && <span style={{ fontSize: "0.6875rem", color: "#10b981", fontWeight: 800 }}>✓</span>}
                    </div>
                    <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: isActive ? "var(--text-primary)" : isPassed ? "#10b981" : "var(--text-secondary)" }}>
                      {st.label}
                    </div>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 1 }}>
                      {st.desc}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* ── TWO-COLUMN DASHBOARD GRID ───────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1.25rem" }} className="grid-responsive-2-col">
        <style jsx>{`
          @media (min-width: 992px) {
            .grid-responsive-2-col {
              grid-template-columns: 1.7fr 1fr !important;
            }
          }
        `}</style>

        {/* ── MAIN / LEFT COLUMN (63% width) ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

          {/* 1. DECISION CENTERPIECE */}
          <RecoveryDecisionCard
            trace={liveTrace}
            detail={liveDetail}
            itemId={id}
            amountAtRiskMinor={amountAtRiskMinor}
            customerId={customerId}
            customerName={customerName}
          />

          {/* 2. SELECTED INTERVENTION */}
          <SelectedIntervention
            trace={liveTrace}
            detail={liveDetail}
          />

          {/* 3. SETTLEMENT RECEIPT (If verified) */}
          <RecoveryReceipt
            trace={liveTrace}
            detail={liveDetail}
          />

          {/* 4. ALTERNATIVES CONSIDERED TABLE */}
          <AlternativesTable
            trace={liveTrace}
          />

          {/* 5. CASE TIMELINE & AUDIT LOG */}
          <CaseTimeline
            trace={liveTrace}
            detailAuditEvents={liveDetail?.audit_events}
          />
        </div>

        {/* ── SIDEBAR / RIGHT COLUMN (37% width) ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

          {/* 1. DECISION INTELLIGENCE ("WHY THIS DECISION?") */}
          <RecoveryWhy
            trace={liveTrace}
            detail={liveDetail}
            amountAtRiskMinor={amountAtRiskMinor}
          />

          {/* 2. POLICY GATE & GUARDRAILS */}
          <PolicyCard
            trace={liveTrace}
            detail={liveDetail}
          />

          {/* 3. RECOVERY ECONOMICS */}
          <RecoveryEconomics
            trace={liveTrace}
            detail={liveDetail}
          />

          {/* 4. SUPPORTING CUSTOMER CONTEXT (COLLAPSIBLE) */}
          <div className="card" style={{ padding: "1rem 1.25rem", borderLeft: "3px solid #6366f1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                Customer 360 & System Trust
              </div>
              <button onClick={() => setTechOpen(!techOpen)} className="btn-ghost" style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem" }}>
                {techOpen ? "Hide ▲" : "Show ▼"}
              </button>
            </div>

            {techOpen && (
              <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
                <CustomerContext
                  profile={customerProfile}
                  customerId={customerId}
                  customerName={customerName}
                />
                <TrustPanel />
              </div>
            )}
          </div>

        </div>
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
