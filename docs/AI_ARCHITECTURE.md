# RevPlug — AI Architecture & Closed-Loop Reasoning Specification

## 1. Overview
RevPlug utilizes a **hybrid control plane** combining LLM contextual reasoning with strict, server-side deterministic policy enforcement.

```text
[Telemetry Ingestion] -> [Customer 360 Profile] -> [LLM Reasoning Layer]
                                                            │
                                                            ▼
                                                 [Candidate Proposals]
                                                            │
                                                            ▼
                                                 [EV & Timing Scorer]
                                                            │
                                                            ▼
                                                 [Deterministic Policy Shield]
                                                            │
                                                     (ALLOW / BLOCK)
                                                            │
                                                            ▼
                                                 [Bounded Execution Layer]
                                                            │
                                                            ▼
                                                 [Outcome & Attribution Ledger]
```

---

## 2. LLM Reasoning Layer
- **Primary Model**: Groq `llama-3.3-70b-versatile` (Sub-second latency, structured JSON output).
- **Secondary Fallback**: Google Gemini `gemini-1.5-pro`.
- **System Prompt Integrity**: System prompts treat all external customer names, error descriptions, and notes as `UNTRUSTED DATA` to eliminate prompt-injection vulnerabilities.
- **Action Validation**: Model action outputs are validated against an explicit `ActionRegistry` allowlist before policy checks or execution.

---

## 3. Expected Net Value ($EV_{\text{net}}$) & Timing Scorer
Objective scoring formula:
$$EV_{\text{net}} = \text{Gross Amount} \cdot P_{\text{recovery}}(\text{Action}, \text{History}) - \text{Intervention Cost} - \text{Friction Penalty}$$

Where:
- $P_{\text{recovery}}$ is derived from the **Outcome-Learning Recovery Memory** ($P(\text{Success} \mid \text{Category}, \text{Action})$).
- Friction penalties scale dynamically with customer contact frequency in the trailing 24h window.

---

## 4. Deterministic Policy Shield
The policy shield operates downstream of the AI reasoning layer. AI models cannot bypass policy rules:
1. `RETRY_LIMIT`: Maximum 3 retries per case.
2. `BLOCK_HARD_FAILURE`: Automatic suppression of hard declines (`expired_card`, `invalid_account`).
3. `OPT_OUT_BLOCK`: Complete suppression of customer communications for opted-out users.
4. `CONTACT_FREQUENCY_LIMIT`: Maximum 2 contacts per 24h.
5. `TERMINAL_STATE_BLOCK`: Terminal states (`RECOVERED`, `STOPPED`) cannot be re-opened by execution calls.
6. `INCIDENT_SUPPRESSION`: Active gateway outages suppress retries and hold cases in `WAITING`.

---

## 5. Outcome-Learning Memory & Causal Attribution
- **Outcome Learning**: Persists structured outcome features (`failure_category`, `action`, `channel`, `payment_method`, `retry_number`, `success/failure`) and exposes inspectable frequency signals inside Decision Cards.
- **Strict Attribution**: Evaluates timeline causality for every payment success:
  - `DIRECT_AGENT`: Payment settled via agent payment link.
  - `AGENT_ASSISTED`: Payment settled following agent reminder.
  - `ORGANIC`: Payment settled without active agent action (credited to Organic Recovery, ₹0 Agent Attribution).
