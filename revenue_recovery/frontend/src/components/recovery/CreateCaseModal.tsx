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
      setErrorMsg("Please enter a valid amount at risk.");
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
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: 620,
          maxHeight: "90vh",
          overflowY: "auto",
          padding: "1.75rem",
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              REVENUE RISK EVENT INGESTION
            </div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
              Create Recovery Case
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: "transparent", border: "none", color: "var(--text-muted)", fontSize: "1.25rem", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>

        {errorMsg && (
          <div style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", padding: "0.75rem", borderRadius: 6, marginBottom: "1rem", fontSize: "0.8125rem" }}>
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          {/* EVENT TYPE SELECTOR */}
          <div style={{ gridColumn: "span 2" }}>
            <label style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", display: "block", marginBottom: 4 }}>
              Revenue Surface / Risk Event Type *
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              style={{
                width: "100%",
                padding: "0.6rem 0.75rem",
                borderRadius: 6,
                background: "var(--bg-primary)",
                border: "1px solid var(--accent)",
                color: "var(--text-primary)",
                fontSize: "0.875rem",
                fontWeight: 600,
              }}
            >
              <option value="payment_failed">💳 Payment Failed (Gateway / Issuer Decline)</option>
              <option value="checkout_abandonment">🛒 Checkout Abandoned (Cart Drop-off)</option>
              <option value="subscription_payment_failed">🔄 Subscription Renewal Failed (SaaS Renewal)</option>
              <option value="mandate_failed">🏦 Mandate Failed (UPI AutoPay / eNACH)</option>
              <option value="invoice_overdue">📄 Invoice Overdue (B2B Receivables)</option>
            </select>
          </div>

          {/* COMMON CUSTOMER FIELDS */}
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              Customer / Business ID
            </label>
            <input
              type="text"
              placeholder="cust_acme_101"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
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
              style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
            />
          </div>

          {/* AMOUNT AT RISK */}
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
              style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem", fontFamily: "monospace" }}
            />
          </div>

          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              Currency
            </label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
            </select>
          </div>

          {/* CONDITIONAL SURFACE FIELDS */}
          {eventType === "payment_failed" && (
            <>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Failure Reason / Cause
                </label>
                <select
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
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
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                >
                  <option value="upi">UPI AutoPay / Link</option>
                  <option value="card">Credit / Debit Card</option>
                  <option value="netbanking">Netbanking / eNACH</option>
                </select>
              </div>
            </>
          )}

          {eventType === "checkout_abandonment" && (
            <>
              <div style={{ gridColumn: "span 2" }}>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Abandonment Context / Stage
                </label>
                <input
                  type="text"
                  placeholder="Cart timeout at payment step"
                  value={abandonmentContext}
                  onChange={(e) => setAbandonmentContext(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                />
              </div>
            </>
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
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Renewal Failure Cause
                </label>
                <select
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
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
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Mandate Failure Cause
                </label>
                <select
                  value={failureReason}
                  onChange={(e) => setFailureReason(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
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
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
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
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
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
              style={{ width: "100%", padding: "0.5rem", borderRadius: 6, background: "var(--bg-primary)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "0.8125rem" }}
            />
          </div>

          {/* SAFETY GOVERNANCE CHECKBOXES */}
          <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "0.75rem", background: "var(--bg-primary)", padding: "0.75rem", borderRadius: 6, border: "1px solid var(--border)", marginTop: 4 }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "var(--text-secondary)", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={consentOptOut}
                onChange={(e) => setConsentOptOut(e.target.checked)}
              />
              Customer Opted Out of Reminders (Consent Shield)
            </label>
            {consentOptOut && (
              <div style={{ fontSize: "0.6875rem", color: "#3b82f6", background: "rgba(59, 130, 246, 0.1)", padding: "4px 8px", borderRadius: 4 }}>
                Customer communication actions will be blocked. Non-contact financial actions may still be evaluated according to policy.
              </div>
            )}

            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#ef4444", cursor: "pointer", fontWeight: 600 }}>
              <input
                type="checkbox"
                checked={fraudRisk}
                onChange={(e) => setFraudRisk(e.target.checked)}
              />
              Flag Fraud Signal (Safety Block)
            </label>
            {fraudRisk && (
              <div style={{ fontSize: "0.6875rem", color: "#ef4444", background: "rgba(239, 68, 68, 0.1)", padding: "4px 8px", borderRadius: 4 }}>
                Automated financial recovery will be blocked and routed to review.
              </div>
            )}
          </div>

          <div style={{ gridColumn: "span 2", display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: "0.5rem 1rem", borderRadius: 6, background: "transparent", border: "1px solid var(--border)", color: "var(--text-secondary)", fontSize: "0.8125rem", cursor: "pointer" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{ padding: "0.5rem 1.25rem", borderRadius: 6, background: "#10b981", border: "none", color: "#fff", fontWeight: 700, fontSize: "0.8125rem", cursor: "pointer" }}
            >
              {loading ? "Ingesting Event..." : "Ingest Event & Create Case"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
