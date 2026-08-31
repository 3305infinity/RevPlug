"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import HomeHero from "@/components/home/HomeHero";
import RecoveryFlow from "@/components/home/RecoveryFlow";
import RecoveryCase from "@/components/home/RecoveryCase";
import ProductExplanation from "@/components/home/ProductExplanation";
import DecisionPipeline from "@/components/home/DecisionPipeline";
import SmartStopSection from "@/components/home/SmartStopSection";
import VerifiedSettlementSection from "@/components/home/VerifiedSettlementSection";
import BenchmarkProof from "@/components/home/BenchmarkProof";
import RazorpayConnectionSection from "@/components/home/RazorpayConnectionSection";
import HomeCTA from "@/components/home/HomeCTA";
import NavbarAuth from "@/components/home/NavbarAuth";

export default function ProductHomePage() {
  const [apiOnline, setApiOnline] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/health`)
      .then((r) => setApiOnline(r.ok))
      .catch(() => setApiOnline(false));
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#0d1117", color: "#f0f6fc", fontFamily: "var(--font-sans, system-ui, sans-serif)" }}>
      {/* 1. MINIMAL PRODUCT HEADER */}
      <header
        style={{
          borderBottom: "1px solid #21262d",
          background: "#0d1117",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "0.75rem 1.5rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "2.5rem" }}>
            <Link href="/" style={{ textDecoration: "none" }}>
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f0f6fc", letterSpacing: "-0.01em" }}>
                RevPlug
              </div>
            </Link>

            <nav style={{ display: "flex", gap: "1.5rem", fontSize: "0.8125rem" }}>
              <a href="#visual-flow" style={{ color: "#8b949e", textDecoration: "none", fontWeight: 500 }}>
                How it works
              </a>
              <Link href="/run-recovery" style={{ color: "#8b949e", textDecoration: "none", fontWeight: 500 }}>
                Recovery
              </Link>
              <Link href="/batch-recovery" style={{ color: "#8b949e", textDecoration: "none", fontWeight: 500 }}>
                Benchmark
              </Link>
            </nav>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace" }}>
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: apiOnline ? "#10b981" : "#ef4444",
                  display: "inline-block",
                }}
              />
              <span style={{ color: apiOnline ? "#10b981" : "#ef4444", fontWeight: 600 }}>
                {apiOnline ? "Razorpay Test Mode" : "Offline"}
              </span>
            </div>

            <NavbarAuth />

            <Link
              href="/run-recovery"
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                padding: "0.4rem 0.85rem",
                borderRadius: 6,
                background: "#2563eb",
                color: "#ffffff",
                textDecoration: "none",
              }}
            >
              Run a recovery
            </Link>
          </div>
        </div>
      </header>

      {/* CONTINUOUS MAIN STORY CONTAINER */}
      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "0 1.5rem" }}>
        {/* 2. HERO */}
        <HomeHero />

        {/* 3 & 4. VISUAL RECOVERY FLOW & INTERACTIVE FLOW */}
        <RecoveryFlow />

        {/* 5. PRODUCT PREVIEW (SHOW THE ACTUAL APP) */}
        <RecoveryCase />

        {/* 6. PRODUCT EXPLANATION (3 COLUMNS) */}
        <ProductExplanation />

        {/* 7. DECISION PIPELINE */}
        <DecisionPipeline />

        {/* 8. SMART STOP SECTION */}
        <SmartStopSection />

        {/* 9. VERIFIED SETTLEMENT SECTION */}
        <VerifiedSettlementSection />

        {/* 10. BENCHMARK PROOF */}
        <BenchmarkProof />

        {/* 11. RAZORPAY CONNECTION */}
        <RazorpayConnectionSection />

        {/* 12. FINAL CTA */}
        <HomeCTA />
      </main>

      {/* FOOTER */}
      <footer style={{ borderTop: "1px solid #21262d", background: "#0d1117", padding: "1.5rem", textAlign: "center", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace" }}>
        RevPlug Product Launch · Bounded Revenue Recovery Engine · Powered by Groq Primary AI &amp; Razorpay Test Mode Integration
      </footer>
    </div>
  );
}
