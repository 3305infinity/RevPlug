"use client";

import Link from "next/link";
import { useState, useCallback, useEffect } from "react";

const CAROUSEL_CASES = [
  {
    id: "card-0",
    title: "Checkout Abandoned",
    subtitle: "High intent drop-off",
    amount: "₹7,500",
    iconType: "cart",
    iconBg: "rgba(168, 85, 247, 0.15)",
    iconColor: "#c084fc",
    action: "Send recovery link",
    actionColor: "#60a5fa",
    expected: "Expected recovery: ₹6,980",
    policy: "ALLOWED",
    policyColor: "#10b981",
    policySub: "Cooldown: 0/2 (Pass)",
    badgeType: "pending",
    badgeLabel: "PENDING ACTION",
    badgeBg: "rgba(245, 158, 11, 0.12)",
    badgeColor: "#f59e0b",
    badgeBorder: "rgba(245, 158, 11, 0.3)",
  },
  {
    id: "card-1",
    title: "Payment Failed",
    subtitle: "Gateway Timeout",
    amount: "₹4,999",
    iconType: "card",
    iconBg: "rgba(37, 99, 235, 0.18)",
    iconColor: "#3b82f6",
    action: "Send payment link",
    actionColor: "#60a5fa",
    expected: "Expected recovery: ₹4,799",
    policy: "ALLOWED",
    policyColor: "#10b981",
    policySub: "Retry budget: 1/3 (Pass)",
    badgeType: "verified",
    badgeLabel: "SETTLEMENT VERIFIED",
    badgeAmount: "+₹4,999",
    badgeBg: "rgba(16, 185, 129, 0.15)",
    badgeColor: "#10b981",
    badgeBorder: "rgba(16, 185, 129, 0.35)",
  },
  {
    id: "card-2",
    title: "Invoice Overdue",
    subtitle: "B2B Receivables",
    amount: "₹15,000",
    iconType: "invoice",
    iconBg: "rgba(245, 158, 11, 0.15)",
    iconColor: "#f59e0b",
    action: "Record promise-to-pay",
    actionColor: "#60a5fa",
    expected: "Expected recovery: ₹14,250",
    policy: "WAIT",
    policyColor: "#f59e0b",
    policySub: "Promise date: Tomorrow",
    badgeType: "hold",
    badgeLabel: "PTP HOLD ACTIVE",
    badgeBg: "rgba(245, 158, 11, 0.12)",
    badgeColor: "#f59e0b",
    badgeBorder: "rgba(245, 158, 11, 0.3)",
  },
  {
    id: "card-3",
    title: "Fraud Risk",
    subtitle: "Suspicious activity",
    amount: "₹18,200",
    iconType: "shield",
    iconBg: "rgba(239, 68, 68, 0.15)",
    iconColor: "#ef4444",
    action: "No automated action",
    actionColor: "#9ca3af",
    expected: "Expected recovery: ₹0",
    policy: "STOPPED",
    policyColor: "#ef4444",
    policySub: "Fraud rule triggered",
    badgeType: "blocked",
    badgeLabel: "BLOCKED",
    badgeBg: "rgba(239, 68, 68, 0.12)",
    badgeColor: "#ef4444",
    badgeBorder: "rgba(239, 68, 68, 0.3)",
  },
];

export default function HomeHero() {
  const [activeIndex, setActiveIndex] = useState(1);

  const scrollToHowItWorks = (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById("how-it-works");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const handleNext = useCallback(() => {
    setActiveIndex((prev) => (prev + 1) % CAROUSEL_CASES.length);
  }, []);

  const handlePrev = useCallback(() => {
    setActiveIndex((prev) => (prev - 1 + CAROUSEL_CASES.length) % CAROUSEL_CASES.length);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        handlePrev();
      } else if (e.key === "ArrowRight") {
        handleNext();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleNext, handlePrev]);

  return (
    <section style={{ padding: "3.5rem 0 3.5rem" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "0.9fr 1.1fr",
          gap: "2.5rem",
          alignItems: "center",
        }}
        className="grid-responsive-2"
      >
        {/* LEFT: HERO COPY & CTAS */}
        <div>
          {/* HEADLINE */}
          <h1
            style={{
              fontSize: "clamp(2.5rem, 4.5vw, 3.75rem)",
              fontWeight: 700,
              letterSpacing: "-0.035em",
              lineHeight: 1.1,
              marginBottom: "1.25rem",
              color: "var(--text-primary)",
            }}
          >
            Turn failed payments into recovered revenue.
          </h1>

          {/* SUPPORTING COPY */}
          <p
            style={{
              fontSize: "1.0625rem",
              color: "var(--text-secondary)",
              lineHeight: 1.6,
              marginBottom: "2rem",
              maxWidth: 540,
            }}
          >
            RevPlug finds revenue at risk, chooses the next recovery action within policy, and counts the money only after settlement is verified.
          </p>

          {/* CTAS */}
          <div style={{ display: "flex", gap: "0.875rem", alignItems: "center", flexWrap: "wrap" }}>
            <Link
              href="/dashboard"
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "0.875rem",
                fontWeight: 600,
                background: "#2563eb",
                color: "#ffffff",
                borderRadius: 6,
                textDecoration: "none",
                transition: "background 0.15s ease",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              <span>Open Dashboard</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>

            <a
              href="#how-it-works"
              onClick={scrollToHowItWorks}
              style={{
                padding: "0.75rem 1.35rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "var(--text-secondary)",
                textDecoration: "none",
                border: "1px solid var(--border)",
                borderRadius: 6,
                background: "var(--bg-secondary)",
                transition: "border-color 0.15s ease, color 0.15s ease",
              }}
            >
              See how it works ↓
            </a>
          </div>
        </div>

        {/* RIGHT: HORIZONTAL 4-CARD CAROUSEL STACK */}
        <div style={{ position: "relative", width: "100%", overflow: "hidden", padding: "1rem 0" }}>
          {/* PREVIOUS ARROW BUTTON */}
          <button
            onClick={handlePrev}
            aria-label="Previous recovery case"
            style={{
              position: "absolute",
              left: 4,
              top: "50%",
              transform: "translateY(-50%)",
              zIndex: 20,
              width: 34,
              height: 34,
              borderRadius: "50%",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              background: "rgba(15, 23, 42, 0.85)",
              backdropFilter: "blur(6px)",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              fontSize: "1.125rem",
              boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
              transition: "all 0.15s ease",
            }}
          >
            ‹
          </button>

          {/* NEXT ARROW BUTTON */}
          <button
            onClick={handleNext}
            aria-label="Next recovery case"
            style={{
              position: "absolute",
              right: 4,
              top: "50%",
              transform: "translateY(-50%)",
              zIndex: 20,
              width: 34,
              height: 34,
              borderRadius: "50%",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              background: "rgba(15, 23, 42, 0.85)",
              backdropFilter: "blur(6px)",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              fontSize: "1.125rem",
              boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
              transition: "all 0.15s ease",
            }}
          >
            ›
          </button>

          {/* HORIZONTAL CAROUSEL TRACK */}
          <div
            style={{
              display: "flex",
              gap: "0.875rem",
              alignItems: "stretch",
              transition: "transform 300ms cubic-bezier(0.16, 1, 0.3, 1)",
              transform: `translateX(calc(50% - 110px - ${activeIndex * 230}px))`,
              padding: "0.5rem 0",
            }}
          >
            {CAROUSEL_CASES.map((item, idx) => {
              const isActive = idx === activeIndex;

              return (
                <div
                  key={item.id}
                  onClick={() => setActiveIndex(idx)}
                  style={{
                    flex: "0 0 220px",
                    background: isActive ? "rgba(15, 23, 42, 0.95)" : "rgba(15, 23, 42, 0.65)",
                    border: isActive ? "2px solid #2563eb" : "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: 14,
                    padding: "1.125rem 1rem",
                    cursor: "pointer",
                    transition: "all 300ms cubic-bezier(0.16, 1, 0.3, 1)",
                    transform: isActive ? "scale(1.04)" : "scale(0.94)",
                    opacity: isActive ? 1 : 0.6,
                    boxShadow: isActive
                      ? "0 12px 28px rgba(0, 0, 0, 0.5)"
                      : "0 4px 16px rgba(0, 0, 0, 0.4)",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                  }}
                >
                  {/* TOP HEADER: ICON, TITLE, SUBTITLE, AMOUNT */}
                  <div>
                    {/* ICON CONTAINER */}
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 8,
                        background: item.iconBg,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        marginBottom: "0.75rem",
                      }}
                    >
                      {item.iconType === "cart" && (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={item.iconColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="9" cy="21" r="1" /><circle cx="20" cy="21" r="1" />
                          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
                        </svg>
                      )}
                      {item.iconType === "card" && (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={item.iconColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                          <line x1="1" y1="10" x2="23" y2="10" />
                        </svg>
                      )}
                      {item.iconType === "invoice" && (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={item.iconColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                          <line x1="16" y1="13" x2="8" y2="13" />
                          <line x1="16" y1="17" x2="8" y2="17" />
                        </svg>
                      )}
                      {item.iconType === "shield" && (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={item.iconColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                      )}
                    </div>

                    {/* CARD TITLE & SUBTITLE */}
                    <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.2 }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2, marginBottom: "0.875rem" }}>
                      {item.subtitle}
                    </div>

                    {/* AMOUNT AT RISK */}
                    <div className="font-mono" style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", marginBottom: "1rem" }}>
                      {item.amount}
                    </div>

                    {/* RECOMMENDED ACTION */}
                    <div style={{ marginBottom: "0.875rem" }}>
                      <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>
                        RECOMMENDED ACTION
                      </div>
                      <div style={{ fontSize: "0.75rem", fontWeight: 700, color: item.actionColor }}>
                        {item.action}
                      </div>
                      <div style={{ fontSize: "0.625rem", color: item.expected.includes("₹0") ? "var(--text-muted)" : "#10b981", marginTop: 2 }}>
                        {item.expected}
                      </div>
                    </div>

                    {/* POLICY AUTHORITY */}
                    <div style={{ marginBottom: "1rem" }}>
                      <div style={{ fontSize: "0.5625rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>
                        POLICY AUTHORITY
                      </div>
                      <div style={{ fontSize: "0.75rem", fontWeight: 700, color: item.policyColor }}>
                        {item.policy}
                      </div>
                      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 2 }}>
                        {item.policySub}
                      </div>
                    </div>
                  </div>

                  {/* BOTTOM ACTION BADGE / PILL */}
                  <div
                    style={{
                      background: item.badgeBg,
                      border: `1px solid ${item.badgeBorder}`,
                      borderRadius: 8,
                      padding: "0.45rem 0.6rem",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: item.badgeAmount ? "space-between" : "flex-start",
                      gap: "0.4rem",
                      marginTop: "0.5rem",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      {item.badgeType === "verified" && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={item.badgeColor} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                      {(item.badgeType === "pending" || item.badgeType === "hold") && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={item.badgeColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
                        </svg>
                      )}
                      {item.badgeType === "blocked" && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={item.badgeColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" /><line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
                        </svg>
                      )}
                      <span style={{ fontSize: "0.625rem", fontWeight: 700, color: item.badgeColor, letterSpacing: "0.03em" }}>
                        {item.badgeLabel}
                      </span>
                    </div>

                    {item.badgeAmount && (
                      <span className="font-mono" style={{ fontSize: "0.6875rem", fontWeight: 800, color: item.badgeColor }}>
                        {item.badgeAmount}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* BOTTOM PAGINATION DOTS */}
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "0.5rem", marginTop: "1rem" }}>
            {CAROUSEL_CASES.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setActiveIndex(idx)}
                aria-label={`Go to case ${idx + 1}`}
                style={{
                  width: idx === activeIndex ? 10 : 8,
                  height: idx === activeIndex ? 10 : 8,
                  borderRadius: "50%",
                  background: idx === activeIndex ? "#2563eb" : "rgba(255, 255, 255, 0.2)",
                  border: "none",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  boxShadow: "none",
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
