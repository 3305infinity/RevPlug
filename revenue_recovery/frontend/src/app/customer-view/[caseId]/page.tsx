"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CaseDetail } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";

type ViewState = "idle" | "processing" | "paid" | "failed" | "stopped" | "escalated";

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function getCustomerFacingMessage(detail: CaseDetail): string {
  const primaryDecision = detail.decisions?.find((d: any) => d.final_action) || detail.decisions?.[0];
  const customerMsg = (primaryDecision as any)?.customer_message;
  if (customerMsg && typeof customerMsg === "string" && customerMsg.trim()) {
    return customerMsg.trim();
  }

  const rawAction = primaryDecision?.final_action || primaryDecision?.proposed_action || detail.attempts?.[0]?.action || "";
  const action = String(rawAction).toLowerCase();

  if (action === "send_payment_link" || action === "payment_link") {
    return `Your invoice payment of ${fmtINR(detail.amount_minor)} could not be completed. Complete your payment securely to keep your account active.`;
  }
  if (action === "send_reminder" || action === "send_customer_message") {
    return `This is a reminder regarding your pending payment of ${fmtINR(detail.amount_minor)}. Please complete the payment at your earliest convenience.`;
  }
  if (action === "stop_recovery" || action === "stop") {
    return `This payment recovery notice is no longer active.`;
  }
  if (action === "escalate" || action === "escalate_human") {
    return `Your account requires review by a billing specialist.`;
  }

  return `Payment of ${fmtINR(detail.amount_minor)} is pending. Please complete your transaction below.`;
}

export default function CustomerViewPage() {
  const params = useParams();
  const caseId = params?.caseId as string;

  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewState, setViewState] = useState<ViewState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    setLoading(true);
    setViewState("idle");
    setErrorMessage(null);

    api
      .itemDetail(caseId)
      .then((d) => {
        const cDetail = d as CaseDetail;
        setDetail(cDetail);

        if (cDetail.status === "recovered" || (cDetail.actual_recovery_value && cDetail.actual_recovery_value > 0) || cDetail.outcome?.outcome_type === "recovered") {
          setViewState("paid");
        } else if (cDetail.status === "stopped") {
          setViewState("stopped");
        } else if (cDetail.status === "escalated") {
          setViewState("escalated");
        } else {
          setViewState("idle");
        }
      })
      .catch(() => {
        setDetail(null);
        setErrorMessage("Payment link expired or invalid case identifier.");
      })
      .finally(() => setLoading(false));
  }, [caseId]);

  const handlePaymentSubmit = async () => {
    if (!caseId || !detail) return;
    setViewState("processing");
    setErrorMessage(null);

    try {
      // 1. Trigger action execution path if needed
      await api.runSimulation({ item_id: caseId }).catch(() => {});

      // 2. Trigger real backend settlement verification path
      const settlementRes = await api.simulateSettlement(caseId);

      // 3. Re-fetch financial truth state from backend
      const freshDetail = (await api.itemDetail(caseId)) as CaseDetail;
      setDetail(freshDetail);

      const isVerifiedRecovered =
        settlementRes.verification_result === "verified" ||
        settlementRes.final_status === "recovered" ||
        freshDetail.status === "recovered" ||
        (freshDetail.actual_recovery_value != null && freshDetail.actual_recovery_value > 0) ||
        freshDetail.outcome?.outcome_type === "recovered";

      if (isVerifiedRecovered) {
        setViewState("paid");
      } else {
        setViewState("failed");
        setErrorMessage("Settlement verification failed. Payment was not confirmed.");
      }
    } catch (err: any) {
      setViewState("failed");
      setErrorMessage(err.message || "Payment processing failed. Please try again.");
    }
  };

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-primary, #090d16)", color: "#94a3b8" }}>
        <div style={{ fontSize: "0.875rem" }}>Loading secure payment portal...</div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-primary, #090d16)", padding: "1rem" }}>
        <div style={{ maxWidth: 440, width: "100%", background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, padding: "2rem", textAlign: "center" }}>
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "#ef4444", marginBottom: "0.5rem" }}>
            Invalid or Expired Payment Link
          </div>
          <p style={{ fontSize: "0.8125rem", color: "#94a3b8", marginBottom: "1.5rem" }}>
            {errorMessage || `Recovery link for case "${caseId}" is invalid.`}
          </p>
          <Link href="/recovery" style={{ fontSize: "0.8125rem", color: "#6366f1", textDecoration: "none", fontWeight: 600 }}>
            ← Return to Recovery Queue
          </Link>
        </div>
      </div>
    );
  }

  const primaryDecision = detail.decisions?.find((d: any) => d.final_action) || detail.decisions?.[0];
  const rawAction = String(primaryDecision?.final_action || primaryDecision?.proposed_action || detail.attempts?.[0]?.action || "").toLowerCase();

  const isStopped = detail.status === "stopped" || rawAction === "stop_recovery" || rawAction === "stop";
  const isEscalated = detail.status === "escalated" || rawAction === "escalate_human" || rawAction === "escalate";
  const isPaid = viewState === "paid" || detail.status === "recovered" || (detail.actual_recovery_value && detail.actual_recovery_value > 0);

  const isActionable = !isPaid && !isStopped && !isEscalated && viewState !== "processing";

  const customerName = getCustomerDisplayName(detail.customer_id, (detail as any).customer_name);
  const messageBody = getCustomerFacingMessage(detail);

  return (
    <div style={{ minHeight: "100vh", background: "#090d16", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "1.5rem 1rem", fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" }}>
      
      {/* CASE NAVIGATION LINK BACK TO INTERNAL CASE WORKSPACE */}
      <div style={{ width: "100%", maxWidth: 480, marginBottom: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Link href={`/recovery/${caseId}`} style={{ fontSize: "0.75rem", color: "#64748b", textDecoration: "none" }}>
          ← Back to Internal Case Workspace
        </Link>
        <span style={{ fontSize: "0.6875rem", padding: "2px 8px", borderRadius: 4, background: "rgba(99,102,241,0.12)", color: "#818cf8", border: "1px solid rgba(99,102,241,0.25)" }}>
          Customer Recovery Portal
        </span>
      </div>

      {/* MAIN CUSTOMER RECOVERY CARD */}
      <div style={{ width: "100%", maxWidth: 480, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, boxShadow: "0 20px 25px -5px rgba(0,0,0,0.5)", overflow: "hidden" }}>
        
        {/* HEADER BRANDING */}
        <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid #1e293b", background: "#1e293b", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#94a3b8" }}>
              Secure Payment Gateway
            </div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f8fafc", marginTop: "0.15rem" }}>
              Payment Recovery
            </div>
          </div>
          <div style={{ textAlign: "right", fontSize: "0.75rem", color: "#64748b" }}>
            Ref: <span style={{ fontFamily: "monospace", color: "#cbd5e1" }}>{detail.id}</span>
          </div>
        </div>

        {/* AMOUNT AT RISK BANNER */}
        <div style={{ padding: "1.5rem", background: "rgba(15,23,42,0.6)", borderBottom: "1px solid #1e293b", textAlign: "center" }}>
          <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "#94a3b8", fontWeight: 600 }}>
            Outstanding Amount Due
          </div>
          <div style={{ fontSize: "2.25rem", fontWeight: 800, color: "#f8fafc", fontFamily: "monospace", marginTop: "0.25rem", letterSpacing: "-0.03em" }}>
            {fmtINR(detail.amount_minor)}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.25rem" }}>
            Account Holder: <strong style={{ color: "#e2e8f0" }}>{customerName}</strong>
          </div>
        </div>

        {/* CONTENT AREA */}
        <div style={{ padding: "1.5rem" }}>
          
          {/* CUSTOMER MESSAGE */}
          <div style={{ background: "#1e293b", borderRadius: 8, padding: "1rem 1.25rem", border: "1px solid #334155", marginBottom: "1.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "#818cf8", marginBottom: "0.35rem" }}>
              Notice Details
            </div>
            <div style={{ fontSize: "0.875rem", color: "#e2e8f0", lineHeight: 1.5 }}>
              {messageBody}
            </div>
          </div>

          {/* STATUS DISPLAY AND CTAS */}
          {isPaid ? (
            <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.3)", borderRadius: 8, padding: "1.25rem", textAlign: "center" }}>
              <div style={{ fontSize: "1rem", fontWeight: 700, color: "#10b981", marginBottom: "0.25rem" }}>
                ✓ Payment Verified & Settled
              </div>
              <div style={{ fontSize: "0.875rem", color: "#cbd5e1", marginTop: "0.5rem" }}>
                Amount Settled: <strong style={{ fontFamily: "monospace", color: "#10b981" }}>{fmtINR(detail.actual_recovery_value || detail.amount_minor)}</strong>
              </div>
              <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.5rem" }}>
                Settlement reference verified by financial ledger. No further action is required.
              </div>
            </div>
          ) : isStopped ? (
            <div style={{ background: "rgba(100,116,139,0.08)", border: "1px solid rgba(100,116,139,0.3)", borderRadius: 8, padding: "1rem 1.25rem", color: "#94a3b8", fontSize: "0.8125rem", textAlign: "center" }}>
              <strong>Notice Inactive:</strong> This payment recovery notice is closed and no longer accepting payments.
            </div>
          ) : isEscalated ? (
            <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: 8, padding: "1rem 1.25rem", color: "#f59e0b", fontSize: "0.8125rem", textAlign: "center" }}>
              <strong>Account Under Review:</strong> Your account has been routed to a specialist. Please contact support.
            </div>
          ) : (
            <div>
              {errorMessage && (
                <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 6, padding: "0.75rem 1rem", marginBottom: "1rem", color: "#ef4444", fontSize: "0.8125rem" }}>
                  {errorMessage}
                </div>
              )}

              <button
                onClick={handlePaymentSubmit}
                disabled={!isActionable || viewState === "processing"}
                style={{
                  width: "100%",
                  padding: "0.875rem",
                  borderRadius: 8,
                  border: "none",
                  background: viewState === "processing" ? "#334155" : "#3b82f6",
                  color: "#ffffff",
                  fontSize: "0.9375rem",
                  fontWeight: 700,
                  cursor: isActionable && viewState !== "processing" ? "pointer" : "not-allowed",
                  boxShadow: isActionable ? "0 4px 12px rgba(59,130,246,0.3)" : "none",
                  transition: "all 0.15s ease",
                }}
              >
                {viewState === "processing" ? "Processing & Verifying Settlement..." : `Pay ${fmtINR(detail.amount_minor)} Securely`}
              </button>

              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "0.5rem", marginTop: "1rem", fontSize: "0.75rem", color: "#64748b" }}>
                <span>🔒 256-bit SSL Encrypted</span>
                <span>&middot;</span>
                <span>Verifiable Ledger Settlement</span>
              </div>
            </div>
          )}

        </div>

        {/* FOOTER SUPPORT INFO */}
        <div style={{ padding: "0.875rem 1.5rem", borderTop: "1px solid #1e293b", background: "#090d16", fontSize: "0.75rem", color: "#64748b", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>RevPlug Recovery Infrastructure</span>
          <Link href={`/recovery/${caseId}`} style={{ color: "#818cf8", textDecoration: "none" }}>
            Internal Case Workspace →
          </Link>
        </div>
      </div>
    </div>
  );
}
