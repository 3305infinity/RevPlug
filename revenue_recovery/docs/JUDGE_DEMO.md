# RecoverOS Judge Demo Guide & Presentation Script

This guide prepares judges and reviewers to evaluate RecoverOS in 30 seconds, 2 minutes, or 5 minutes.

---

## 1. The 30-Second Elevator Pitch

> **RecoverOS is an AI-powered revenue recovery control plane that diagnoses slipping revenue, ranks interventions using context reasoning, and executes bounded recovery actions—without ever letting AI bypass safety rules or declare unverified revenue.**

---

## 2. Key Visual Differentiators

```text
AI PROPOSED (Context Diagnosis & Ranking)
       ↓
POLICY DECIDED (Retry Limits, Opt-Outs, Fraud Flags, EV Scoring)
       ↓
BOUNDED ACTION (Idempotent Execution)
       ↓
VERIFIED SETTLEMENT (Authoritative Provider Evidence)
       ↓
₹ MONEY RECOVERED (Measured Net Recovery)
```

---

## 3. The 2-Minute Demo Flow

1. **Step 1: Open Hero Command Center (`http://localhost:3000/dashboard`)**
   - Point out **VERIFIED RECOVERED REVENUE** (Green Accent, ₹13.7L).
   - Point out the **Trust Bar** (`✓ Verified Settlement`, `✓ Policy Constrained`, `✓ Idempotent Execution`, `✓ Fully Auditable`).
   - Show the **Proof of Recovery Funnel** tracking revenue events to verified recoveries.

2. **Step 2: Run Live Scenario (`http://localhost:3000/run-recovery`)**
   - Click **`Preset 1: Successful Recovery`** (Gateway Timeout $\to$ Payment Link $\to$ Verified Recovery).
   - Click **`Preset 2: Smart Stop`** (Fraud Signal $\to$ Safety Policy BLOCKS execution $\to$ STOPPED with ₹0 cost spent).

3. **Step 3: Inspect Benchmark Proof (`http://localhost:3000/batch-recovery`)**
   - Show the reproducible **Counterfactual Benchmark** (`count=50`, `seed=42`).
   - Highlight **+₹2.8L Incremental Revenue Gain (+25.7% Uplift)** over standard fixed retry baseline with **0 safety violations**.

---

## 4. Top 8 Judge Questions & Answers

| Question | Short Answer |
| :--- | :--- |
| **1. Why use AI here?** | AI diagnoses ambiguous failure causes (bank timeouts vs customer issues) and ranks recovery actions by probability. |
| **2. Why not let AI handle everything?** | Financial ledgers, retry limits, consent opt-outs, and fraud blocks remain 100% deterministic and non-bypassable. |
| **3. How do you prove money was recovered?** | Recovery status is updated ONLY when authoritative provider settlement evidence (`actual_recovery_minor`) is received. |
| **4. What happens when AI fails or times out?** | The system triggers `DeterministicFallbackAgent`, logging a `FALLBACK_USED` event while safety controls remain active. |
| **5. What prevents duplicate retries?** | Action execution uses unique idempotency keys (`item_id:action:attempt_number`) and reconciles `UNKNOWN` provider states. |
| **6. Is this real money?** | Payment events in simulation mode are clearly tagged with `● SIMULATION MODE ACTIVE` for complete transparency. |
| **7. How did you measure improvement?** | We ran a seeded counterfactual benchmark (`count=50`, `seed=42`) comparing RecoverOS directly against a fixed retry baseline. |
| **8. What is the financial ROI?** | RecoverOS delivered +25.7% incremental recovery uplift and reduced unnecessary intervention costs by 20%. |
