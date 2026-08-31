"use client";

const SETTLEMENT_STEPS = [
  { step: "01", label: "ACTION DISPATCHED", subtext: "Razorpay payment link created", status: "complete" },
  { step: "02", label: "RAZORPAY EVENT", subtext: "payment_link.paid webhook received", status: "complete" },
  { step: "03", label: "SIGNATURE VERIFIED", subtext: "HMAC-SHA256 header matched", status: "complete" },
  { step: "04", label: "PAYMENT MATCHED", subtext: "Correlated to RecoveryItem #RR-1042", status: "complete" },
  { step: "05", label: "AMOUNT VERIFIED", subtext: "₹4,999 exact currency match", status: "complete" },
  { step: "06", label: "SETTLEMENT VERIFIED", subtext: "Financial ledger updated", status: "complete" },
  { step: "07", label: "₹4,999 RECOVERED", subtext: "Money authoritatively settled", status: "success" },
];

export default function VerifiedSettlementSection() {
  return (
    <div style={{ padding: "4rem 0", borderTop: "1px solid #21262d" }}>
      {/* SECTION HEADER */}
      <div style={{ marginBottom: "2rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#6e7681", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.35rem" }}>
          FINANCIAL TRUTH ARCHITECTURE
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.02em" }}>
          An attempted recovery is not a recovered payment.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "#8b949e", marginTop: 4 }}>
          RevPlug never counts money as recovered merely because an API action was dispatched. Only signed, verified webhooks count.
        </p>
      </div>

      {/* HORIZONTAL TIMELINE */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          borderTop: "1px solid #21262d",
          borderBottom: "1px solid #21262d",
          background: "#0d1117",
        }}
      >
        {SETTLEMENT_STEPS.map((s, idx) => (
          <div key={idx} style={{ padding: "1.25rem 0.75rem", borderRight: idx === SETTLEMENT_STEPS.length - 1 ? "none" : "1px solid #21262d" }}>
            <div className="font-mono" style={{ fontSize: "0.65rem", color: "#6e7681", fontWeight: 700 }}>
              {s.step}
            </div>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: s.status === "success" ? "#10b981" : "#f0f6fc", margin: "4px 0" }}>
              {s.label}
            </div>
            <div style={{ fontSize: "0.6875rem", color: "#8b949e", lineHeight: 1.3 }}>
              {s.subtext}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
