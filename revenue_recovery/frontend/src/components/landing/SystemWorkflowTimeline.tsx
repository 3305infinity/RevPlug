"use client";

export default function SystemWorkflowTimeline() {
  const steps = [
    { num: "01", title: "DETECT", desc: "Revenue-risk event enters RecoverOS via webhook or API ingestion." },
    { num: "02", title: "DIAGNOSE", desc: "Known failures are classified deterministically. Ambiguous cases can use AI decision agents." },
    { num: "03", title: "SCORE", desc: "Expected Recovery Value (EV) is calculated deterministically prior to action." },
    { num: "04", title: "GUARD", desc: "Policy and stopping rules constrain the recommendation before authorization." },
    { num: "05", title: "EXECUTE", desc: "Only an allowed bounded intervention runs (smart retry, hosted payment link)." },
    { num: "06", title: "VERIFY", desc: "Recovery is counted only after confirmatory payment settlement." },
    { num: "07", title: "AUDIT", desc: "The complete decision trail, event log, and state transitions are immutably recorded." },
  ];

  return (
    <section id="how-it-works" style={{ padding: "4.5rem 0", borderBottom: "1px solid var(--border)", background: "#04060a" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 2rem" }}>
        <div style={{ maxWidth: 720, marginBottom: "3.5rem" }}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            color: "var(--orange)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.75rem",
          }}>
            Lifecycle Workflow
          </div>
          <h2 style={{
            fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
            fontWeight: 800,
            letterSpacing: "-0.035em",
            color: "#f8fafc",
            lineHeight: 1.15,
            margin: 0,
          }}>
            From failure to verified recovery.
          </h2>
        </div>

        {/* Vertical Timeline with Thin Connector Line */}
        <div style={{ position: "relative", paddingLeft: "2.5rem" }}>
          {/* Connector Line */}
          <div style={{
            position: "absolute",
            top: 12,
            bottom: 12,
            left: 11,
            width: 2,
            background: "var(--border)",
          }} />

          <div style={{ display: "grid", gap: "1.25rem" }}>
            {steps.map((step) => (
              <div key={step.num} style={{ position: "relative" }}>
                {/* Timeline Dot */}
                <div style={{
                  position: "absolute",
                  left: "-2.5rem",
                  top: 6,
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: step.num === "06" ? "var(--success)" : step.num === "04" ? "var(--warning)" : "var(--orange)",
                  border: "2px solid #04060a",
                }} />

                <div style={{
                  background: "#0b0f17",
                  border: "1px solid var(--border)",
                  borderRadius: 4,
                  padding: "1.25rem 1.5rem",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: 4 }}>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 700, fontFamily: "monospace", color: "var(--orange)" }}>
                      {step.num}
                    </span>
                    <span style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                      {step.title}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.84375rem", color: "var(--text-secondary)", lineHeight: 1.5, marginLeft: "1.75rem" }}>
                    {step.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
