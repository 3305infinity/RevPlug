"use client";

import HomeHeader from "@/components/home/HomeHeader";
import HomeHero from "@/components/home/HomeHero";
import WhyRevenueLeaks from "@/components/home/WhyRevenueLeaks";
import RecoveryCase from "@/components/home/RecoveryCase";
import ControlLoop from "@/components/home/ControlLoop";
import FourDecisionsSection from "@/components/home/FourDecisionsSection";
import HinglishVoiceSection from "@/components/home/HinglishVoiceSection";
import BenchmarkProof from "@/components/home/BenchmarkProof";
import RazorpayIntegration from "@/components/home/RazorpayIntegration";
import HomeCTA from "@/components/home/HomeCTA";
import LandingFooter from "@/components/home/LandingFooter";

export default function ProductHomePage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg-root)",
        color: "var(--text-primary)",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* 1. RESPONSIVE FINTECH HEADER */}
      <HomeHeader />

      {/* 2. MAIN LANDING STORY */}
      <main style={{ maxWidth: 1140, margin: "0 auto", padding: "0 1.5rem" }}>
        {/* HERO */}
        <HomeHero />

        {/* WHY REVENUE LEAKS */}
        <WhyRevenueLeaks />

        {/* ONE RECOVERY DECISION (WORKPLACE ARTIFACT) */}
        <RecoveryCase />

        {/* THE CONTROL LOOP (DETECT / DECIDE / CONTROL / VERIFY) */}
        <ControlLoop />

        {/* THE FOUR OUTCOMES (RECOVER / WAIT / ESCALATE / STOP) */}
        <FourDecisionsSection />

        {/* HINGLISH VOICE-ASSISTED PTP */}
        <HinglishVoiceSection />

        {/* BENCHMARK / SYNTHETIC EVALUATION PROOF */}
        <BenchmarkProof />

        {/* RAZORPAY INTEGRATION & SETTLEMENT TRUST */}
        <RazorpayIntegration />

        {/* FINAL CTA */}
        <HomeCTA />
      </main>

      {/* 3. FOOTER */}
      <LandingFooter />
    </div>
  );
}
