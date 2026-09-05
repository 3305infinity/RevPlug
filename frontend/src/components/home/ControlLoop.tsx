"use client";

const CONTROL_STAGES = [
  {
    num: "01",
    label: "DETECT",
    title: "Find revenue at risk.",
    desc: "Ingest gateway telemetry, authorization errors, subscription drops, and invoice events to identify slipping revenue in real time.",
  },
  {
    num: "02",
    label: "DECIDE",
    title: "Choose the best eligible action.",
    desc: "Expected-value (EV) ranking evaluates candidate recovery actions, weighing expected gross recovery against intervention cost.",
  },
  {
    num: "03",
    label: "CONTROL",
    title: "Enforce policy bounds.",
    desc: "Server-side policy engine evaluates retry budgets, customer opt-out status, fraud risk signals, and cooldown periods before authorizing dispatch.",
  },
  {
    num: "04",
    label: "VERIFY",
    title: "Verify settlement before ledger credit.",
    desc: "Dispatched interventions are never counted as recovered. Money is counted only post-settlement when signed webhooks match expected currency and amounts.",
  },
];

export default function ControlLoop() {
  return (
    <section id="control-loop" style={{ padding: "4rem 0" }}>
      {/* SECTION HEADER */}
      <div style={{ maxWidth: 640, marginBottom: "3rem" }}>
        <div
          style={{
            fontSize: "0.6875rem",
            fontWeight: 700,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "0.35rem",
          }}
        >
          THE CORE CONTROL LOOP
        </div>
        <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Four steps to verified recovery.
        </h2>
        <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: 4 }}>
          RevPlug replaces unconstrained retries with a deterministic revenue control loop.
        </p>
      </div>

      {/* TYPOGRAPHIC FOUR-COLUMN CONNECTED CONTROL LOOP */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "2rem",
          position: "relative",
        }}
        className="grid-responsive-4"
      >
        {CONTROL_STAGES.map((s, i) => (
          <div key={s.num} style={{ position: "relative" }}>
            {/* STAGE NUMBER & LABEL */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginBottom: "1rem",
              }}
            >
              <span
                className="font-mono"
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  color: "#2563eb",
                  background: "var(--bg-secondary)",
                  padding: "0.15rem 0.45rem",
                  borderRadius: 4,
                  border: "1px solid var(--border)",
                }}
              >
                {s.num}
              </span>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.05em" }}>
                {s.label}
              </span>
            </div>

            {/* TITLE & DESCRIPTION */}
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem", lineHeight: 1.3 }}>
              {s.title}
            </h3>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
              {s.desc}
            </p>
          </div>
        ))}
      </div>

      {/* ONE CONTROL LOOP. MULTIPLE REVENUE SURFACES */}
      <div
        style={{
          marginTop: "3rem",
          padding: "1.75rem 2rem",
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 10,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1.5rem", marginBottom: "1.5rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              UNIFIED ARCHITECTURE
            </div>
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
              One control loop. Multiple revenue surfaces.
            </h3>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: 4, maxWidth: 600 }}>
              RevPlug applies the same deterministic policy, Net EV ranking, and settlement verification engine across all revenue-leakage channels.
            </p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }} className="grid-responsive-4">
          <div style={{ background: "var(--bg-primary)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#ef4444" }}>💳 Payment Failures</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>Gateway timeouts, issuer declines, 3DS authentication drops, and soft decline recovery.</div>
          </div>
          <div style={{ background: "var(--bg-primary)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--accent)" }}>🛒 Checkout Abandonment</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>High-intent cart abandonment, checkout payment drop-offs, and dynamic recovery links.</div>
          </div>
          <div style={{ background: "var(--bg-primary)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#10b981" }}>🔄 Subscriptions &amp; Mandates</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>SaaS subscription renewals, UPI AutoPay, eNACH mandate failures, and bounded retry budgets.</div>
          </div>
          <div style={{ background: "var(--bg-primary)", padding: "1rem", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#06b6d4" }}>📄 Overdue Receivables</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4 }}>B2B overdue invoices, automated outreach, Hinglish promise-to-pay, and commitment tracking.</div>
          </div>
        </div>
      </div>

      {/* CORE PRODUCT STATEMENT */}
      <div
        style={{
          marginTop: "2.5rem",
          paddingTop: "1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
          AI proposes. Policy decides. Settlement proves.
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
          RevPlug never treats an attempted action as recovered money.
        </div>
      </div>
    </section>
  );
}
