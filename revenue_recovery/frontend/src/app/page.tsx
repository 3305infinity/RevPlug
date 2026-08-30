"use client";

import LandingHeader from "@/components/landing/LandingHeader";
import Hero from "@/components/landing/Hero";
import MoneyStorySequence from "@/components/landing/MoneyStorySequence";
import AuthoritySplit from "@/components/landing/AuthoritySplit";
import ControlPlaneSurfaces from "@/components/landing/ControlPlaneSurfaces";
import SystemWorkflowTimeline from "@/components/landing/SystemWorkflowTimeline";
import DeterministicFormula from "@/components/landing/DeterministicFormula";
import SafetyControlMatrix from "@/components/landing/SafetyControlMatrix";
import AuditLogStream from "@/components/landing/AuditLogStream";
import PositioningStatement from "@/components/landing/PositioningStatement";
import FinalCTA from "@/components/landing/FinalCTA";
import LandingFooter from "@/components/landing/LandingFooter";

export default function ProductHomePage() {
  return (
    <div style={{ minHeight: "100vh", background: "#04060a", color: "var(--text-primary)" }}>
      <LandingHeader />
      <Hero />
      <MoneyStorySequence />
      <AuthoritySplit />
      <ControlPlaneSurfaces />
      <SystemWorkflowTimeline />
      <DeterministicFormula />
      <SafetyControlMatrix />
      <AuditLogStream />
      <PositioningStatement />
      <FinalCTA />
      <LandingFooter />
    </div>
  );
}
