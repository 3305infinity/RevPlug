"use client";

import React, { useEffect, useState } from "react";
import { api, PromiseToPay } from "@/lib/api";
import DecisionBadge from "@/components/shared/DecisionBadge";

interface Props {
  itemId: string;
  customerId?: string;
}

function fmtINR(minor: number) {
  return "₹" + (minor / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatPromiseDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return dateStr;
  }
}

function PromiseStatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string; label: string }> = {
    promised: { bg: "rgba(59,130,246,0.12)", color: "#3b82f6", label: "PENDING" },
    fulfilled: { bg: "rgba(16,185,129,0.12)", color: "#10b981", label: "FULFILLED" },
    broken: { bg: "rgba(239,68,68,0.12)", color: "#ef4444", label: "BROKEN" },
    expired: { bg: "rgba(239,68,68,0.12)", color: "#ef4444", label: "EXPIRED" },
    cancelled: { bg: "rgba(107,114,128,0.12)", color: "#6b7280", label: "CANCELLED" },
  };
  const s = styles[status] || styles.promised;
  return (
    <span style={{ fontSize: "0.625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4, background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
}

export default function PromiseCommitment({ itemId, customerId }: Props) {
  const [promise, setPromise] = useState<PromiseToPay | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!itemId) return;
    api.promiseActive(itemId)
      .then((p) => { setPromise(p as PromiseToPay | null); setError(null); })
      .catch(() => {
        api.promiseByItem(itemId)
          .then((p) => { setPromise(p as PromiseToPay | null); setError(null); })
          .catch(() => { setError("Unable to load promise data"); setPromise(null); })
          .finally(() => setLoading(false));
      })
      .finally(() => setLoading(false));
  }, [itemId]);

  const handleFulfill = async () => {
    if (!promise?.id) return;
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.fulfillPromise(promise.id);
      setPromise(updated as PromiseToPay);
    } catch {
      setActionError("Failed to mark promise as fulfilled");
    } finally {
      setActionLoading(false);
    }
  };

  const handleBreak = async (reason?: string) => {
    if (!promise?.id) return;
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.breakPromise(promise.id, reason || "Payment not received by promised date");
      setPromise(updated as PromiseToPay);
    } catch {
      setActionError("Failed to mark promise as broken");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div className="skeleton" style={{ height: 16, width: "40%" }} />
      </div>
    );
  }

  if (!promise) {
    return null;
  }

  const isPromised = promise.status === "promised";
  const isFulfilled = promise.status === "fulfilled";
  const isBroken = promise.status === "broken";
  const isTerminal = isFulfilled || isBroken || promise.status === "cancelled" || promise.status === "expired";

  return (
    <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem", borderLeft: "3px solid #3b82f6" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ fontSize: "0.625rem", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Payment Commitment
          </div>
          <PromiseStatusBadge status={promise.status} />
        </div>
        {isPromised && (
          <DecisionBadge decision="WAIT" compact />
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
        <div>
          <div className="metric-label">Committed Amount</div>
          <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>
            {fmtINR(promise.promised_amount_minor)}
          </div>
        </div>
        <div>
          <div className="metric-label">Commitment Date</div>
          <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {formatPromiseDate(promise.promised_date)}
          </div>
        </div>
        <div>
          <div className="metric-label">Recorded</div>
          <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            {promise.created_at ? formatPromiseDate(promise.created_at) : "—"}
          </div>
        </div>
      </div>

      {isPromised && promise.verified_recovered_minor === undefined && (
        <div style={{ background: "rgba(59,130,246,0.06)", borderRadius: 6, padding: "0.75rem 1rem", marginBottom: "1rem", border: "1px solid rgba(59,130,246,0.15)" }}>
          <div style={{ fontSize: "0.8125rem", color: "#3b82f6", fontWeight: 600, marginBottom: "0.25rem" }}>
            Active payment commitment
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            Immediate recovery action is paused because a valid payment commitment exists.
            The committed amount will be verified when settlement evidence is received.
          </div>
        </div>
      )}

      {isFulfilled && (
        <div style={{ background: "rgba(16,185,129,0.06)", borderRadius: 6, padding: "0.75rem 1rem", marginBottom: "1rem", border: "1px solid rgba(16,185,129,0.2)" }}>
          <div style={{ fontSize: "0.8125rem", color: "#10b981", fontWeight: 600, marginBottom: "0.25rem" }}>
            Promise fulfilled — settlement verified
          </div>
          {promise.verified_recovered_minor !== undefined && promise.verified_recovered_minor !== null && (
            <div style={{ fontSize: "0.875rem", color: "#10b981", fontFamily: "monospace", fontWeight: 700 }}>
              {fmtINR(promise.verified_recovered_minor)} settled
            </div>
          )}
          {promise.fulfilled_at && (
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
              Settled {formatPromiseDate(promise.fulfilled_at)}
            </div>
          )}
        </div>
      )}

      {isBroken && (
        <div style={{ background: "rgba(239,68,68,0.06)", borderRadius: 6, padding: "0.75rem 1rem", marginBottom: "1rem", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div style={{ fontSize: "0.8125rem", color: "#ef4444", fontWeight: 600, marginBottom: "0.25rem" }}>
            Promise broken
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            {promise.break_reason || "Payment not received by the promised date."}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
            The system will reassess this opportunity through normal recovery decision logic.
          </div>
        </div>
      )}

      {actionError && (
        <div style={{ color: "#ef4444", fontSize: "0.75rem", marginBottom: "0.75rem" }}>{actionError}</div>
      )}

      {isPromised && (
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            onClick={handleFulfill}
            disabled={actionLoading}
            style={{
              fontSize: "0.75rem", padding: "0.4rem 0.875rem", borderRadius: 6,
              border: "1px solid rgba(16,185,129,0.3)", background: "rgba(16,185,129,0.1)",
              color: "#10b981", cursor: actionLoading ? "not-allowed" : "pointer", fontWeight: 600,
            }}
          >
            {actionLoading ? "Processing..." : "Mark Fulfilled (Settlement Received)"}
          </button>
          <button
            onClick={() => handleBreak()}
            disabled={actionLoading}
            style={{
              fontSize: "0.75rem", padding: "0.4rem 0.875rem", borderRadius: 6,
              border: "1px solid rgba(239,68,68,0.3)", background: "rgba(239,68,68,0.06)",
              color: "#ef4444", cursor: actionLoading ? "not-allowed" : "pointer", fontWeight: 600,
            }}
          >
            Mark Broken
          </button>
        </div>
      )}
    </div>
  );
}
