"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import HomeHero from "@/components/home/HomeHero";
import RecoveryCase from "@/components/home/RecoveryCase";
import WhyNotRetry from "@/components/home/WhyNotRetry";
import BenchmarkProof from "@/components/home/BenchmarkProof";
import HomeCTA from "@/components/home/HomeCTA";
import { AnimatedSection } from "@/components/home/motion";
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
      {/* MINIMAL HEADER */}
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
              <Link href="/dashboard" style={{ color: "#8b949e", textDecoration: "none", fontWeight: 500 }}>
                Overview
              </Link>
              <Link href="/run-recovery" style={{ color: "#8b949e", textDecoration: "none", fontWeight: 500 }}>
                Recovery
              </Link>
              <Link href="/batch-recovery" style={{ color: "#8b949e", textDecoration: "none", fontWeight: 500 }}>
                Benchmarks
              </Link>
              <Link href="/recovery" style={{ color: "#8b949e", textDecoration: "none", fontWeight: 500 }}>
                Audit
              </Link>
            </nav>
          </div>

          {/* SYSTEM HEALTHY LIVE STATUS PULSE DOT & AUTH PROFILE */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace" }}>
            <span>Razorpay Test Mode</span>
            <span style={{ color: "#21262d" }}>|</span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <span
                className="live-pulse"
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: apiOnline ? "#10b981" : "#ef4444",
                  boxShadow: apiOnline ? "0 0 8px rgba(16, 185, 129, 0.6)" : "0 0 8px rgba(239, 68, 68, 0.6)",
                }}
              />
              <span style={{ color: apiOnline ? "#10b981" : "#ef4444", fontWeight: 600 }}>
                {apiOnline ? "System Healthy" : "Offline"}
              </span>
            </div>
            <span style={{ color: "#21262d" }}>|</span>
            <NavbarAuth />
          </div>
        </div>
      </header>

      {/* ZONE 1: HERO INTRO MARKETING ZONE (#0d1117) */}
      <section style={{ background: "#0d1117", borderBottom: "1px solid #21262d" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 1.5rem" }}>
          <AnimatedSection>
            <HomeHero />
          </AnimatedSection>
        </div>
      </section>

      {/* ZONE 2: LIVE PRODUCT DATA ZONE (#10151e — SUBTLE SHIFT IN BACKGROUND SHADE) */}
      <section style={{ background: "#10151e" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 1.5rem" }}>
          {/* CENTRAL RECOVERY CASE & WATCH RECOVERY INTERACTION */}
          <AnimatedSection delayMs={100}>
            <RecoveryCase />
          </AnimatedSection>

          <hr style={{ border: 0, borderTop: "1px solid #21262d", margin: "1rem 0" }} />

          {/* WHY THIS WASN'T A RETRY (TERMINAL LOG VIEWER STREAM) */}
          <AnimatedSection delayMs={100}>
            <WhyNotRetry />
          </AnimatedSection>

          <hr style={{ border: 0, borderTop: "1px solid #21262d", margin: "1rem 0" }} />

          {/* BENCHMARK PROOF STATEMENT & TABLE */}
          <AnimatedSection delayMs={100}>
            <BenchmarkProof />
          </AnimatedSection>

          <hr style={{ border: 0, borderTop: "1px solid #21262d", margin: "1rem 0" }} />

          {/* FINAL CTA */}
          <AnimatedSection delayMs={100}>
            <HomeCTA />
          </AnimatedSection>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ borderTop: "1px solid #21262d", background: "#0d1117", padding: "1.5rem", textAlign: "center", fontSize: "0.75rem", color: "#6e7681", fontFamily: "monospace" }}>
        RevPlug Autonomous Revenue Recovery Infrastructure · Powered by Groq Primary AI &amp; Razorpay Test Mode Integration
      </footer>
    </div>
  );
}
