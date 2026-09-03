"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CaseDetail } from "@/lib/api";

type ViewState = "idle" | "processing" | "paid" | "failed";

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function getChannel(action: string | undefined): string {
  if (!action) return "notification";
  if (action === "send_payment_link") return "payment_link";
  if (action === "send_reminder") return "reminder";
  if (action === "send_customer_message") return "message";
  if (action === "retry_payment") return "auto_retry";
  if (action === "alternate_channel") return "alternate_channel";
  return "notification";
}

function getMessageText(detail: CaseDetail | null): string {
  if (!detail) return "";
  const decision = detail.decisions?.find((d: any) => d.final_action) || detail.decisions?.[0];
  const attempt = detail.attempts?.[0];

  // Use actual backend-generated data only; do not invent copy.
  const customerMessage = (decision as any)?.customer_message;
  if (customerMessage && typeof customerMessage === "string" && customerMessage.trim()) {
    return customerMessage.trim();
  }

  const decisionReason = decision?.reason;
  if (decisionReason && typeof decisionReason === "string" && decisionReason.trim()) {
    return decisionReason.trim();
  }

  const attemptReason = (attempt as any)?.reason;
  if (attemptReason && typeof attemptReason === "string" && attemptReason.trim()) {
    return attemptReason.trim();
  }

  return `Your payment of ${fmtINR(detail.amount_minor)} is pending.`;
}

export default function CustomerViewPage() {
  const params = useParams();
  const caseId = params?.caseId as string;

  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewState, setViewState] = useState<ViewState>("idle");

  useEffect(() => {
    if (!caseId) return;
    setLoading(true);
    setViewState("idle");
    api
      .itemDetail(caseId)
      .then((d) => setDetail(d as CaseDetail))
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [caseId]);

  const primaryDecision = detail?.decisions?.find((d: any) => d.final_action) || detail?.decisions?.[0];
  const primaryAttempt = detail?.attempts?.[0];
  const rawAction = primaryDecision?.final_action || primaryDecision?.proposed_action || primaryAttempt?.action || "";
  const action = String(rawAction || "");
  const channel = getChannel(action);

  const messageText = getMessageText(detail);

  const isPaid =
    detail?.outcome?.outcome_type === "recovered" ||
    (detail?.actual_recovery_value && detail.actual_recovery_value > 0) ||
    primaryAttempt?.outcome === "success";

  const handleCtaClick = async () => {
    setViewState("processing");
    try {
      const result = await api.runSimulation({ item_id: caseId });
      const recovered =
        result.settlement_verified === true ||
        result.recovery_status === "recovered" ||
        (result.actual_recovery_value != null && result.actual_recovery_value > 0);
      setViewState(recovered ? "paid" : "failed");
    } catch {
      setViewState("failed");
    }
  };

  const showCta = channel === "payment_link" && viewState !== "paid" && viewState !== "failed";

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f0f2f5",
        }}
      >
        <div style={{ color: "#666", fontSize: "0.875rem" }}>Loading recovery message...</div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f0f2f5",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "#ef4444", marginBottom: "1rem", fontWeight: 600 }}>Case not found</div>
          <Link href="/recovery" style={{ color: "#2563eb", textDecoration: "none", fontSize: "0.875rem" }}>
            Back to Recovery
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f0f2f5",
        padding: "1rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 360,
          background: "#fff",
          borderRadius: 28,
          boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)",
          overflow: "hidden",
          border: "6px solid #1a1a1a",
        }}
      >
        {/* Status bar */}
        <div
          style={{
            background: "#1a1a1a",
            color: "#fff",
            padding: "0.5rem 1.25rem",
            display: "flex",
            justifyContent: "space-between",
            fontSize: "0.75rem",
            fontWeight: 600,
          }}
        >
          <span>9:41</span>
          <span>📶 🔋</span>
        </div>

        {/* App header */}
        <div
          style={{
            background: "#075e54",
            color: "#fff",
            padding: "0.75rem 1rem",
            fontSize: "0.9375rem",
            fontWeight: 600,
          }}
        >
          {channel === "payment_link" ? "Payment Link" : channel === "reminder" ? "Reminder" : "Recovery"}
        </div>

        {/* Message area */}
        <div
          style={{
            padding: "1rem",
            background: "#e5ddd5",
            minHeight: 280,
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
          }}
        >
          {/* Recovery message bubble */}
          <div
            style={{
              background: "#fff",
              borderRadius: 8,
              padding: "0.75rem 1rem",
              maxWidth: "88%",
              boxShadow: "0 1px 1px rgba(0,0,0,0.1)",
              fontSize: "0.9375rem",
              lineHeight: 1.5,
              color: "#303030",
            }}
          >
            {messageText}
          </div>

          {/* Amount context */}
          <div
            style={{
              background: "#fff",
              borderRadius: 8,
              padding: "0.6rem 1rem",
              maxWidth: "88%",
              boxShadow: "0 1px 1px rgba(0,0,0,0.1)",
              fontSize: "0.8125rem",
              color: "#555",
            }}
          >
            Amount: <strong style={{ color: "#075e54" }}>{fmtINR(detail.amount_minor)}</strong>
            {detail.currency && detail.currency !== "INR" && <span style={{ marginLeft: 4 }}>{detail.currency}</span>}
          </div>

          {/* Payment CTA */}
          {showCta && (
            <div style={{ marginTop: "0.5rem" }}>
              <button
                onClick={handleCtaClick}
                disabled={viewState === "processing"}
                style={{
                  width: "100%",
                  padding: "0.75rem",
                  borderRadius: 8,
                  border: "none",
                  background: viewState === "processing" ? "#ccc" : "#075e54",
                  color: "#fff",
                  fontSize: "0.9375rem",
                  fontWeight: 600,
                  cursor: viewState === "processing" ? "not-allowed" : "pointer",
                }}
              >
                {viewState === "processing" ? "Processing..." : "Pay Now"}
              </button>
            </div>
          )}

          {/* Processing indicator */}
          {viewState === "processing" && (
            <div
              style={{
                background: "#fff",
                borderRadius: 8,
                padding: "0.6rem 1rem",
                maxWidth: "88%",
                boxShadow: "0 1px 1px rgba(0,0,0,0.1)",
                fontSize: "0.8125rem",
                color: "#666",
                textAlign: "center",
              }}
            >
              Processing payment...
            </div>
          )}

          {/* Paid / verified state */}
          {viewState === "paid" && (
            <div
              style={{
                background: "#dcf8c6",
                borderRadius: 8,
                padding: "0.75rem 1rem",
                maxWidth: "88%",
                boxShadow: "0 1px 1px rgba(0,0,0,0.1)",
                fontSize: "0.9375rem",
                color: "#303030",
              }}
            >
              <div style={{ fontWeight: 700, color: "#128c7e", marginBottom: 4 }}>Payment Successful</div>
              <div style={{ fontSize: "0.875rem" }}>
                {detail.actual_recovery_value ? `${fmtINR(detail.actual_recovery_value)} settled` : "Payment verified"}
              </div>
              {(() => {
                const rawRecoveredAt = (detail.outcome as any)?.recovered_at;
                if (!rawRecoveredAt || typeof rawRecoveredAt !== "string") return null;
                return (
                  <div style={{ fontSize: "0.75rem", color: "#666", marginTop: 4 }}>
                    {new Date(rawRecoveredAt).toLocaleString()}
                  </div>
                );
              })()}
            </div>
          )}

          {/* Failed state */}
          {viewState === "failed" && (
            <div
              style={{
                background: "#fff",
                borderRadius: 8,
                padding: "0.75rem 1rem",
                maxWidth: "88%",
                boxShadow: "0 1px 1px rgba(0,0,0,0.1)",
                fontSize: "0.9375rem",
                color: "#303030",
              }}
            >
              <div style={{ fontWeight: 700, color: "#e53e3e", marginBottom: 4 }}>Payment Failed</div>
              <div style={{ fontSize: "0.875rem" }}>
                {primaryAttempt?.failure_reason || "The payment could not be processed. Please try again later."}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "0.75rem 1rem",
            background: "#f0f2f5",
            borderTop: "1px solid #ddd",
            textAlign: "center",
          }}
        >
          <Link
            href={`/recovery/${caseId}`}
            style={{ fontSize: "0.8125rem", color: "#666", textDecoration: "none" }}
          >
            ← Back to case
          </Link>
        </div>
      </div>
    </div>
  );
}
