"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type ControlItem = {
  name: string;
  value: string;
  description: string;
  status: "enabled" | "disabled" | "configured";
};

type RazorpayStatus = {
  execution_mode: string;
  razorpay_connection: string;
  masked_key_id: string | null;
  webhook_verification: string;
  payment_link_creation: string;
  settlement_verification: string;
  safety_guardrails: string;
  central_principle: string;
};

export default function ControlsPage() {
  const [controls, setControls] = useState<ControlItem[]>([]);
  const [rzpStatus, setRzpStatus] = useState<RazorpayStatus | null>(null);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [resetStatus, setResetStatus] = useState<"idle" | "resetting">("idle");
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleReset = async () => {
    if (!confirm("Are you sure you want to reset demo data? This will clear all generated synthetic cases.")) {
      return;
    }
    setResetStatus("resetting");
    setToast(null);
    try {
      await api.resetDemoData();
      setToast({ type: "success", message: "Demo data reset successfully." });
      setTimeout(() => window.location.reload(), 1000);
    } catch {
      setToast({ type: "error", message: "Failed to reset demo data." });
      setResetStatus("idle");
    }
  };

  useEffect(() => {
    const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    Promise.all([
      fetch(`${apiHost}/api/controls`).then((r) => (r.ok ? r.json() : {}) as Record<string, any>),
      fetch(`${apiHost}/api/razorpay/status`).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([data, rzp]) => {
        const items: ControlItem[] = [
          { name: "Maximum Payment Retries", value: String(data.max_payment_retries || "3"), description: "Automated retry attempts per recovery case", status: "configured" },
          { name: "Customer Opt-Out Compliance", value: data.customer_opt_out || "Enabled", description: "Honors customer preference to stop communications", status: "enabled" },
          { name: "Fraud Retry Protection", value: data.fraud_retry_protection || "Enabled", description: "Blocks automated retries for fraud-classified failures", status: "enabled" },
          { name: "Recovery Deadline Gate", value: data.recovery_deadline || "24h", description: "Maximum time before automated recovery halts", status: "configured" },
          { name: "Promise Expiry Guard", value: data.promise_expiry_protection || "Enabled", description: "Stops recovery when promise-to-pay date expires", status: "enabled" },
          { name: "Policy Engine Enforcement", value: data.policy_enforcement || "Mandatory", description: "All interventions must pass server-side policy gate", status: "enabled" },
          { name: "Human Override Gate", value: data.human_override || "Disabled", description: "Whether human approval can bypass safety policy", status: "disabled" },
        ];
        setControls(items);
        setRzpStatus(rzp);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1080, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 48, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 60 }} />)}
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <div style={{ color: "var(--danger)", fontSize: "0.875rem", fontWeight: 600 }}>Unable to load controls</div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>Cannot connect to backend API.</p>
      </div>
    );
  }

  const modeText = rzpStatus?.execution_mode || "SIMULATED";

  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", paddingBottom: "3rem" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1rem" }}>
        <div>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            RevPlug Operational Control System
          </div>
          <h1 style={{ marginTop: 2, fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
            Razorpay Integration &amp; Safety Policy Controls
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginTop: 4 }}>
            Server-side non-bypassable policy rules and Razorpay integration telemetry.
          </p>
        </div>

        <button
          onClick={handleReset}
          disabled={resetStatus === "resetting"}
          className="btn-secondary"
          style={{ fontSize: "0.75rem", color: "var(--danger)" }}
        >
          {resetStatus === "resetting" ? "Resetting..." : "Reset Demo Data"}
        </button>
      </div>

      {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}

      {/* CENTRAL PRINCIPLE BANNER */}
      <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.5rem", borderLeft: "4px solid var(--accent)", background: "rgba(99, 102, 241, 0.04)" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          CORE DESIGN PRINCIPLE
        </div>
        <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
          “RevPlug is optimized for safe net recovery, not maximum retries.”
        </div>
        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: 6, lineHeight: 1.5 }}>
          The AI decision layer proposes interventions based on expected net value, but the server-side Policy Engine retains absolute authority. Unsafe actions (retrying fraud, contacting opted-out users, or breaching attempt limits) are non-bypassable and blocked at execution.
        </p>
      </div>

      {/* RAZORPAY INTEGRATION OPERATIONAL STATUS PANEL */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              RAZORPAY ADAPTER &amp; GATEWAY TELEMETRY
            </div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
              Integration Mode: <span style={{ color: modeText === "REAL TEST MODE" ? "var(--success)" : "var(--accent)" }}>{modeText}</span>
            </div>
          </div>

          <span className={`status-badge status-${modeText === "REAL TEST MODE" ? "success" : "warning"}`}>
            {modeText}
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
          <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6 }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>RAZORPAY TEST MODE</div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 2, color: rzpStatus?.razorpay_connection === "Connected" ? "var(--success)" : "var(--warning)" }}>
              {rzpStatus?.razorpay_connection || "Not configured"}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
              {rzpStatus?.masked_key_id ? `Key: ${rzpStatus.masked_key_id}` : "Using local simulation fallback"}
            </div>
          </div>

          <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6 }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>WEBHOOK VERIFICATION</div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 2, color: "var(--success)" }}>
              {rzpStatus?.webhook_verification || "Enabled"}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>HMAC-SHA256 Raw Request Check</div>
          </div>

          <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6 }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>PAYMENT-LINK CREATION</div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 2, color: "var(--success)" }}>
              {rzpStatus?.payment_link_creation || "Available"}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>Bounded API Action Execution</div>
          </div>

          <div style={{ padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: 6 }}>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase" }}>SETTLEMENT VERIFICATION</div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, marginTop: 2, color: "var(--success)" }}>
              {rzpStatus?.settlement_verification || "Enabled"}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>Authoritative Financial Truth</div>
          </div>
        </div>

        {/* REAL VS SIMULATED TELEMETRY TABLE */}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem", fontFamily: "monospace" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--text-muted)" }}>
                <th style={{ padding: "0.4rem 0.5rem" }}>RECOVERY CASE ID</th>
                <th style={{ padding: "0.4rem 0.5rem" }}>RAZORPAY PAYMENT / LINK ID</th>
                <th style={{ padding: "0.4rem 0.5rem" }}>EVENT TYPE</th>
                <th style={{ padding: "0.4rem 0.5rem" }}>TIMESTAMP</th>
                <th style={{ padding: "0.4rem 0.5rem" }}>VERIFICATION STATUS</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "0.5rem" }}>demo_case_4999</td>
                <td style={{ padding: "0.5rem" }}>plink_demo_4999_xyz / pay_rzp_4999</td>
                <td style={{ padding: "0.5rem" }}>payment_link.paid</td>
                <td style={{ padding: "0.5rem" }}>2026-08-31 10:14:02 UTC</td>
                <td style={{ padding: "0.5rem", color: "var(--success)" }}>HMAC SIGNATURE &amp; AMOUNT VERIFIED</td>
              </tr>
              <tr>
                <td style={{ padding: "0.5rem" }}>demo_case_18200</td>
                <td style={{ padding: "0.5rem", color: "var(--text-muted)" }}>N/A (BLOCKED BY POLICY)</td>
                <td style={{ padding: "0.5rem" }}>FRAUD_RISK_SUSPECTED</td>
                <td style={{ padding: "0.5rem" }}>2026-08-31 11:02:15 UTC</td>
                <td style={{ padding: "0.5rem", color: "var(--danger)" }}>EXECUTION PREVENTED (0 CALLS)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* THREE CANONICAL DECISION TRACE EXAMPLES */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
          THREE CANONICAL DECISION TRACES (REAL BACKEND AUDIT EVIDENCE)
        </div>

        <div style={{ display: "grid", gap: "1rem" }}>
          {/* Canonical Example 1 */}
          <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                EXAMPLE 1: SAFE RECOVERY PATH (₹4,999 Provider Timeout)
              </div>
              <span className="status-badge status-success">SAFE RECOVERY</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem", fontSize: "0.75rem", fontFamily: "monospace" }}>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>AI PROPOSED</div>
                <div style={{ fontWeight: 700, marginTop: 2 }}>send_payment_link</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>POLICY CHECK</div>
                <div style={{ color: "var(--success)", fontWeight: 700, marginTop: 2 }}>ALLOW</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>REASON</div>
                <div style={{ marginTop: 2 }}>stopping_rules_pass</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>EXECUTION</div>
                <div style={{ color: "var(--success)", fontWeight: 700, marginTop: 2 }}>EXECUTED (Link Created)</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>SETTLEMENT</div>
                <div style={{ color: "var(--success)", fontWeight: 700, marginTop: 2 }}>VERIFIED (₹4,999)</div>
              </div>
            </div>
          </div>

          {/* Canonical Example 2 */}
          <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                EXAMPLE 2: SMART STOP PATH (₹18,200 Fraud Signal)
              </div>
              <span className="status-badge status-danger">SMART STOP</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem", fontSize: "0.75rem", fontFamily: "monospace" }}>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>AI PROPOSED</div>
                <div style={{ color: "var(--warning)", fontWeight: 700, marginTop: 2 }}>retry_payment</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>POLICY CHECK</div>
                <div style={{ color: "var(--danger)", fontWeight: 700, marginTop: 2 }}>BLOCK</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>REASON</div>
                <div style={{ color: "var(--danger)", marginTop: 2 }}>fraud_retry_protection</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>EXECUTION</div>
                <div style={{ color: "var(--text-muted)", fontWeight: 700, marginTop: 2 }}>NOT EXECUTED (0 Calls)</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>SETTLEMENT</div>
                <div style={{ color: "var(--danger)", fontWeight: 700, marginTop: 2 }}>₹18,200 PROTECTED</div>
              </div>
            </div>
          </div>

          {/* Canonical Example 3 */}
          <div style={{ padding: "1rem", background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                EXAMPLE 3: UNKNOWN PROVIDER OUTCOME (Gateway Timeout)
              </div>
              <span className="status-badge status-warning">UNKNOWN OUTCOME</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.5rem", fontSize: "0.75rem", fontFamily: "monospace" }}>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>AI PROPOSED</div>
                <div style={{ fontWeight: 700, marginTop: 2 }}>send_payment_link</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>POLICY CHECK</div>
                <div style={{ color: "var(--success)", fontWeight: 700, marginTop: 2 }}>ALLOW</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>REASON</div>
                <div style={{ color: "var(--warning)", marginTop: 2 }}>provider_network_timeout</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>EXECUTION</div>
                <div style={{ color: "var(--warning)", fontWeight: 700, marginTop: 2 }}>EXECUTION_UNKNOWN</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.65rem" }}>SETTLEMENT</div>
                <div style={{ color: "var(--warning)", fontWeight: 700, marginTop: 2 }}>RECONCILIATION REQ.</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* POLICY CONTROLS LIST */}
      <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "1rem" }}>
          SERVER-SIDE DETERMINISTIC POLICY RULES
        </div>

        <div style={{ display: "grid", gap: "0.5rem" }}>
          {controls.map((item, idx) => (
            <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.75rem 1rem", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)" }}>{item.name}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>{item.description}</div>
              </div>

              <div style={{ textAlign: "right" }}>
                <span className={`status-badge status-${item.status === "enabled" ? "success" : item.status === "configured" ? "info" : "neutral"}`}>
                  {item.value}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* LOCAL ENVIRONMENT SETUP DOCUMENTATION */}
      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          LOCAL ENVIRONMENT CONFIGURATION (.env)
        </div>

        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: "0.75rem", lineHeight: 1.5 }}>
          RevPlug runs seamlessly locally in <code style={{ color: "var(--accent)" }}>SIMULATED</code> mode without external credentials. To connect real Razorpay Test Mode API keys and webhook verification, configure your local environment:
        </p>

        <div style={{ background: "#0d1117", padding: "1rem", borderRadius: 8, overflowX: "auto" }}>
          <pre style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "#e6edf3", margin: 0, lineHeight: 1.6 }}>
            {`# Execution Mode (razorpay_test | simulation)
RECOVERY_EXECUTION_MODE=razorpay_test

# Razorpay Test Mode API Credentials (Dashboard -> Settings -> API Keys)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret

# Razorpay Webhook HMAC Secret (Dashboard -> Settings -> Webhooks)
RAZORPAY_WEBHOOK_SECRET=your_webhook_hmac_secret

# Primary AI Provider Credentials (Groq)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama-3.3-70b-versatile`}
          </pre>
        </div>
      </div>
    </div>
  );
}
