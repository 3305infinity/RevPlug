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
import StrategyEvidence from "@/components/recovery/StrategyEvidence";
import RecoveryWhy from "@/components/recovery/RecoveryWhy";
import SelectedIntervention from "@/components/recovery/SelectedIntervention";
import AlternativesTable from "@/components/recovery/AlternativesTable";
import PolicyCard from "@/components/recovery/PolicyCard";
import RecoveryEconomics from "@/components/recovery/RecoveryEconomics";
import RecoveryReceipt from "@/components/recovery/RecoveryReceipt";
import CaseTimeline from "@/components/recovery/CaseTimeline";
import CustomerContext from "@/components/recovery/CustomerContext";
import DecisionTraceView from "@/components/recovery/DecisionTraceView";
import TrustPanel from "@/components/recovery/TrustPanel";
import PromiseCommitment from "@/components/recovery/PromiseCommitment";

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
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "3rem 1rem", textAlign: "center", color: "var(--text-muted)" }}>
        <div style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
          Loading recovery decision workspace...
        </div>
        <div style={{ fontSize: "0.8125rem" }}>Fetching decision trace and audit records</div>
      </div>
    );
  }

  if (error || (!liveDetail && !liveTrace)) {
    return (
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "3rem 1rem", textAlign: "center" }}>
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
    <div style={{ maxWidth: 1080, margin: "0 auto", paddingBottom: "3rem" }}>

      {/* ── NAVIGATION BAR & CASE CONTROL ───────────────────────────── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <Link href="/recovery" style={{ fontSize: "0.75rem", color: "var(--text-muted)", textDecoration: "none" }}>
          ← Back to Recovery Queue
        </Link>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            onClick={handleOpenClearModal}
            className="btn-ghost"
            style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem", color: "#ef4444", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: 4 }}
          >
            Clear recovery case
          </button>
        </div>
      </div>

      {/* ── INCIDENT BANNER ── */}
      {incident && (
        <div style={{
          display: "flex", alignItems: "center", gap: "0.875rem", flexWrap: "wrap",
          padding: "0.75rem 1rem", background: "rgba(245,158,11,0.08)",
          border: "1px solid rgba(245,158,11,0.3)", borderRadius: 8, marginBottom: "1rem",
        }}>
          <span style={{
            fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
            background: "rgba(245,158,11,0.15)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.4)",
          }}>
            {incident.severity} INCIDENT
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", flex: 1 }}>
            This opportunity is affected by:{' '}
            <strong style={{ color: "var(--text-primary)" }}>{incident.title}</strong>
            {' '}({incident.payment_method} &middot; {incident.failure_category.replace(/_/g, " ")})
          </span>
          <Link href={`/incidents/${incident.incident_id}`} style={{
            fontSize: "0.6875rem", fontWeight: 700, color: "#f59e0b",
            textDecoration: "none", padding: "0.3rem 0.65rem", borderRadius: 4,
            border: "1px solid rgba(245,158,11,0.4)", background: "rgba(245,158,11,0.08)",
          }}>
            View Incident →
          </Link>
        </div>
      )}

      {/* PAYMENT COMMITMENT */}
      <PromiseCommitment itemId={id} customerId={customerId} />

      <div style={{ marginBottom: "1.5rem" }}>
        <Link
          href={`/recovery/${id}/voice-call`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.8125rem",
            fontWeight: 600,
            color: "var(--accent)",
            textDecoration: "none",
            padding: "0.5rem 0.875rem",
            borderRadius: 6,
            border: "1px solid rgba(99,102,241,0.3)",
            background: "rgba(99,102,241,0.06)",
          }}
        >
          Hinglish Voice-Assisted Promise-to-Pay
        </Link>
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <Link
          href={`/customer-view/${id}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.8125rem",
            fontWeight: 600,
            color: "#10b981",
            textDecoration: "none",
            padding: "0.5rem 0.875rem",
            borderRadius: 6,
            border: "1px solid rgba(16,185,129,0.3)",
            background: "rgba(16,185,129,0.06)",
          }}
        >
          Customer View
        </Link>
      </div>

      {/* MONEY STORY FLOW */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

        {/* 1. DECISION — Centerpiece */}
        <RecoveryDecisionCard
          trace={liveTrace}
          detail={liveDetail}
          itemId={id}
          amountAtRiskMinor={amountAtRiskMinor}
          customerId={customerId}
          customerName={customerName}
        />

        {/* 2. WHY THIS DECISION? */}
        <RecoveryWhy
          trace={liveTrace}
          detail={liveDetail}
          amountAtRiskMinor={amountAtRiskMinor}
        />

        {/* 3. SELECTED INTERVENTION */}
        <SelectedIntervention
          trace={liveTrace}
          detail={liveDetail}
        />

        {/* 4. ALTERNATIVES CONSIDERED */}
        <AlternativesTable
          trace={liveTrace}
        />

        {/* 5. POLICY CHECK */}
        <PolicyCard
          trace={liveTrace}
          detail={liveDetail}
        />

        {/* 6. RECOVERY ECONOMICS */}
        <RecoveryEconomics
          trace={liveTrace}
          detail={liveDetail}
        />

        {/* 7. RECOVERY RECEIPT & SETTLEMENT PROOF */}
        <RecoveryReceipt
          trace={liveTrace}
          detail={liveDetail}
        />

        {/* 8. RECOVERY TIMELINE */}
        <CaseTimeline
          trace={liveTrace}
          detailAuditEvents={liveDetail?.audit_events}
        />

      </div>

      {/* SECONDARY CONTEXT — Collapsible */}
      <div style={{ marginTop: "1.5rem" }}>
        <div className="card" style={{ padding: "1rem 1.25rem", borderLeft: "4px solid #6366f1" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
              Supporting Context
            </div>
            <button onClick={() => setTechOpen(!techOpen)} className="btn-ghost" style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}>
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
