"use client";

import { useState } from "react";

interface CreateCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newItem: any) => void;
}

export default function CreateCaseModal({ isOpen, onClose, onSuccess }: CreateCaseModalProps) {
  const [customerId, setCustomerId] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [amountRupees, setAmountRupees] = useState("4999");
  const [currency, setCurrency] = useState("INR");
  const [eventType, setEventType] = useState("payment_failed");
  const [failureReason, setFailureReason] = useState("payment_timed_out");
  const [paymentMethod, setPaymentMethod] = useState("upi");
  const [referenceId, setReferenceId] = useState("");
  const [consentOptOut, setConsentOptOut] = useState(false);
  const [fraudRisk, setFraudRisk] = useState(false);

  // Surface-specific conditional inputs
  const [subscriptionId, setSubscriptionId] = useState("");
  const [abandonmentContext, setAbandonmentContext] = useState("Payment step timeout at checkout");
  const [mandateRef, setMandateRef] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [daysOverdue, setDaysOverdue] = useState("15");

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amountRupees || isNaN(Number(amountRupees))) {
      setErrorMsg("Please enter a valid numerical amount at risk.");
      return;
    }

    setLoading(true);
    setErrorMsg("");

    const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    const amountMinor = Math.round(Number(amountRupees) * 100);

    const ref = referenceId.trim() ||
      (eventType === "invoice_overdue" ? invoiceNumber || `INV-${Date.now().toString().slice(-6)}` :
       eventType === "subscription_payment_failed" ? subscriptionId || `SUB-${Date.now().toString().slice(-6)}` :
       eventType === "mandate_failed" ? mandateRef || `MAN-${Date.now().toString().slice(-6)}` :
       `REF-${Date.now().toString().slice(-6)}`);

    try {
      const res = await fetch(`${apiHost}/api/recovery-items/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_id: customerId.trim() || `cust_corp_${Date.now().toString().slice(-4)}`,
          customer_name: customerName.trim() || "Enterprise Client",
          amount_minor: amountMinor,
          currency: currency.toUpperCase(),
          event_type: eventType,
          failure_reason: failureReason,
          payment_method: paymentMethod,
          reference_id: ref,
          consent_opt_out: consentOptOut,
          fraud_risk: fraudRisk,
          subscription_id: subscriptionId.trim(),
          abandonment_context: abandonmentContext.trim(),
          mandate_ref: mandateRef.trim(),
          invoice_number: invoiceNumber.trim(),
          days_overdue: daysOverdue ? Number(daysOverdue) : 15,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || errData.error || errData.message || `HTTP ${res.status}: Unable to create recovery case`);
      }

      const newItem = await res.json();
      onSuccess(newItem);
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error creating case");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        backdropFilter: "blur(6px)",
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: 640,
          maxHeight: "88vh",
          overflowY: "auto",
          padding: "1.75rem 2rem",
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          boxShadow: "0 24px 48px -12px rgba(0, 0, 0, 0.6)",
        }}
      >
        {/* MODAL HEADER */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            paddingBottom: "1rem",
            borderBottom: "1px solid var(--border)",
            marginBottom: "1.25rem",
          }}
        >
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              INDEPENDENT RECOVERY ENGINE
            </div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "2px 0 0 0", color: "var(--text-primary)" }}>
              Create Recovery Case
            </h2>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", margin: "4px 0 0 0" }}>
              Ingest a high-intent revenue risk event for evaluation and automated recovery.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            style={{
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              color: "var(--text-muted)",
              borderRadius: 6,
              width: 32,
              height: 32,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "var(--text-primary)";
              e.currentTarget.style.borderColor = "var(--text-muted)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--text-muted)";
              e.currentTarget.style.borderColor = "var(--border)";
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {errorMsg && (
          <div style={{ background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#ef4444", padding: "0.75rem 1rem", borderRadius: 8, marginBottom: "1.25rem", fontSize: "0.8125rem", fontWeight: 500 }}>
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.125rem" }}>
          {/* REVENUE SURFACE / RISK EVENT SELECTOR */}
          <div style={{ gridColumn: "span 2" }}>
            <label style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>
              Revenue Surface / Risk Event Type *
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              style={{
                width: "100%",
                padding: "0.65rem 0.85rem",
                borderRadius: 8,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
                fontSize: "0.875rem",
                fontWeight: 600,
                cursor: "pointer",
                outline: "none",
              }}
            >
              <option value="payment_failed">Payment Failed (Gateway / Issuer Decline)</option>
              <option value="checkout_abandonment">Checkout Abandoned (Cart Drop-off)</option>
              <option value="subscription_payment_failed">Subscription Renewal Failed (SaaS Renewal)</option>
              <option value="mandate_failed">Mandate Failed (UPI AutoPay / eNACH)</option>
              <option value="invoice_overdue">Invoice Overdue (B2B Receivables)</option>
            </select>
          </div>

          {/* CUSTOMER INFORMATION */}
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              Customer / Business ID
            </label>
            <input
              type="text"
              placeholder="cust_acme_101"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              style={{
                width: "100%",
                padding: "0.55rem 0.75rem",
                borderRadius: 6,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
                fontSize: "0.8125rem",
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              Customer / Account Name
            </label>
            <input
              type="text"
              placeholder="Enterprise Client"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              style={{
                width: "100%",
                padding: "0.55rem 0.75rem",
                borderRadius: 6,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
                fontSize: "0.8125rem",
              }}
            />
          </div>

          {/* AMOUNT AT RISK & CURRENCY */}
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              {eventType === "checkout_abandonment" ? "Checkout / Cart Value (₹) *" :
               eventType === "subscription_payment_failed" ? "Renewal Amount (₹) *" :
               eventType === "mandate_failed" ? "Mandate Amount (₹) *" :
               eventType === "invoice_overdue" ? "Invoice Amount (₹) *" :
               "Amount at Risk (₹) *"}
            </label>
            <input
              type="number"
              required
              placeholder="4999"
              value={amountRupees}
              onChange={(e) => setAmountRupees(e.target.value)}
              style={{
                width: "100%",
                padding: "0.55rem 0.75rem",
                borderRadius: 6,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
                fontSize: "0.8125rem",
                fontFamily: "monospace",
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              Currency
            </label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              style={{
                width: "100%",
                padding: "0.55rem 0.75rem",
                borderRadius: 6,
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
                fontSize: "0.8125rem",
              }}
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
            </select>
          </div>

          {/* CONDITIONAL SURFACE-SPECIFIC FIELDS */}
          {eventType === "payment_failed" && (
            <>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Failure Reason / Cause
                </label>
                <select
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                >
                  <option value="payment_timed_out">Soft Gateway Timeout</option>
                  <option value="insufficient_funds">Insufficient Funds</option>
                  <option value="expired_card">Expired Card</option>
                  <option value="authentication_failed">Authentication Failed</option>
                  <option value="risk_check_failed">Risk Check Failed</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Payment Method
                </label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                >
                  <option value="upi">UPI AutoPay / Link</option>
                  <option value="card">Credit / Debit Card</option>
                  <option value="netbanking">Netbanking / eNACH</option>
                </select>
              </div>
            </>
          )}

          {eventType === "checkout_abandonment" && (
            <div style={{ gridColumn: "span 2" }}>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Abandonment Context / Stage
              </label>
              <input
                type="text"
                placeholder="Cart timeout at payment step"
                value={abandonmentContext}
                onChange={(e) => setAbandonmentContext(e.target.value)}
                style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
              />
            </div>
          )}

          {eventType === "subscription_payment_failed" && (
            <>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Subscription ID
                </label>
                <input
                  type="text"
                  placeholder="sub_saas_pro_901"
                  value={subscriptionId}
                  onChange={(e) => setSubscriptionId(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Renewal Failure Cause
                </label>
                <select
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                >
                  <option value="expired_card">Expired Card</option>
                  <option value="insufficient_funds">Insufficient Funds</option>
                  <option value="mandate_failed">Mandate Revoked / Invalid</option>
                  <option value="payment_timed_out">Soft Issuer Timeout</option>
                </select>
              </div>
            </>
          )}

          {eventType === "mandate_failed" && (
            <>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Mandate / AutoPay Reference
                </label>
                <input
                  type="text"
                  placeholder="man_upi_autopay_771"
                  value={mandateRef}
                  onChange={(e) => setMandateRef(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Mandate Failure Cause
                </label>
                <select
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                >
                  <option value="mandate_failed">Bank Technical Execution Error</option>
                  <option value="insufficient_funds">Account Balance Below Threshold</option>
                  <option value="authentication_failed">Mandate Authorization Expired</option>
                </select>
              </div>
            </>
          )}

          {eventType === "invoice_overdue" && (
            <>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Invoice Number
                </label>
                <input
                  type="text"
                  placeholder="INV-2026-8801"
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Days Overdue
                </label>
                <input
                  type="number"
                  placeholder="15"
                  value={daysOverdue}
                  onChange={(e) => setDaysOverdue(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                />
              </div>
            </>
          )}

          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              External Reference ID
            </label>
            <input
              type="text"
              placeholder="tx_882019"
              value={referenceId}
              onChange={(e) => setReferenceId(e.target.value)}
              style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
            />
          </div>

          {/* POLICY & SAFETY GOVERNANCE SHIELDS */}
          <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "0.75rem", background: "var(--bg-primary)", padding: "0.875rem 1rem", borderRadius: 8, border: "1px solid var(--border)", marginTop: "0.25rem" }}>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              POLICY & SAFETY GOVERNANCE SHIELDS
            </div>

            <label style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem", fontSize: "0.78125rem", color: "var(--text-secondary)", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={consentOptOut}
                onChange={(e) => setConsentOptOut(e.target.checked)}
                style={{ marginTop: 2, accentColor: "var(--accent)" }}
              />
              <div>
                <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Customer Opted Out of Reminders</span> (Consent Shield)
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  Communication actions will be blocked by policy. Non-contact financial retries remain evaluable.
                </div>
              </div>
            </label>

            <label style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem", fontSize: "0.78125rem", color: "#ef4444", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={fraudRisk}
                onChange={(e) => setFraudRisk(e.target.checked)}
                style={{ marginTop: 2, accentColor: "#ef4444" }}
              />
              <div>
                <span style={{ fontWeight: 700, color: "#ef4444" }}>Flag Fraud Signal</span> (Deterministic Safety Block)
                <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  Automated financial recovery will be immediately blocked and flagged for human review.
                </div>
              </div>
            </label>
          </div>

          {/* MODAL ACTIONS FOOTER */}
          <div style={{ gridColumn: "span 2", display: "flex", justifyContent: "flex-end", alignItems: "center", gap: "0.75rem", marginTop: "0.75rem" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "0.6rem 1.125rem",
                borderRadius: 6,
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                fontSize: "0.8125rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: "0.6rem 1.35rem",
                borderRadius: 6,
                background: "#2563eb",
                border: "none",
                color: "#ffffff",
                fontWeight: 700,
                fontSize: "0.8125rem",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.7 : 1,
                boxShadow: "0 2px 8px rgba(37, 99, 235, 0.3)",
                transition: "all 0.15s ease",
              }}
            >
              {loading ? "Ingesting Event..." : "Create Recovery Case"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
