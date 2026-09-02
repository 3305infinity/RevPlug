"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import Link from "next/link";
import { api, DecisionStreamEvent, DecisionStreamSummary } from "@/lib/api";
import { getCustomerDisplayName } from "@/lib/customerDisplay";
import DecisionBadge from "@/components/shared/DecisionBadge";

type Status = "loading" | "error" | "ready";
type DecisionFilter = "all" | "RECOVER" | "WAIT" | "ESCALATE" | "STOP";
type EventFilter = "all" | "decisions" | "interventions" | "outcomes" | "settlement";

const DECISION_FILTERS: { key: DecisionFilter; label: string }[] = [
  { key: "all", label: "All Decisions" },
  { key: "RECOVER", label: "Recover" },
  { key: "WAIT", label: "Wait" },
  { key: "ESCALATE", label: "Escalate" },
  { key: "STOP", label: "Stop" },
];

const EVENT_FILTERS: { key: EventFilter; label: string }[] = [
  { key: "all", label: "All Events" },
  { key: "decisions", label: "Decisions" },
  { key: "interventions", label: "Interventions" },
  { key: "outcomes", label: "Outcomes" },
  { key: "settlement", label: "Settlement" },
];

function fmt(n: number) {
  return "₹" + (n / 100).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
  } catch {
    return iso;
  }
}

function fmtDate(iso: string) {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

const EVENT_TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  detection: { color: "#3b82f6", label: "Detection" },
  decision: { color: "#6366f1", label: "Decision" },
  policy: { color: "#f59e0b", label: "Policy" },
  intervention: { color: "#10b981", label: "Intervention" },
  outcome: { color: "#10b981", label: "Outcome" },
  incident: { color: "#f59e0b", label: "Incident" },
  promise: { color: "#3b82f6", label: "Promise" },
};

export default function Activity() {
  const [status, setStatus] = useState<Status>("loading");
  const [events, setEvents] = useState<DecisionStreamEvent[]>([]);
  const [summary, setSummary] = useState<DecisionStreamSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>("all");
  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [priorityMode, setPriorityMode] = useState<boolean>(true);
  const knownIdsRef = useRef<Set<string>>(new Set());

  const load = useCallback(async () => {
    try {
      const data = await api.decisionStream();
      // Deduplicate by event_id
      const newEvents = data.events.filter((e) => !knownIdsRef.current.has(e.event_id));
      if (newEvents.length > 0) {
        newEvents.forEach((e) => knownIdsRef.current.add(e.event_id));
        setEvents((prev) => [...newEvents, ...prev].sort((a, b) => b.timestamp.localeCompare(a.timestamp)));
      }
      setSummary(data.summary);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load decision stream");
      setStatus("error");
    }
  }, []);

  // Initial load
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Polling for live updates (every 10 seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      load();
    }, 10000);
    return () => clearInterval(interval);
  }, [load]);

  const filtered = useMemo(() => {
    let result = events;

    // Decision filter
    if (decisionFilter !== "all") {
      result = result.filter((e) => e.decision === decisionFilter);
    }

    // Event type filter
    if (eventFilter !== "all") {
      if (eventFilter === "settlement") {
        result = result.filter((e) => e.event_action === "settlement_verified");
      } else if (eventFilter === "decisions") {
        result = result.filter((e) => e.event_type === "decision");
      } else if (eventFilter === "interventions") {
        result = result.filter((e) => e.event_type === "intervention");
      } else if (eventFilter === "outcomes") {
        result = result.filter((e) => e.event_type === "outcome");
      }
    }

    // Priority mode: sort by expected recovery descending
    if (priorityMode) {
      result = [...result].sort((a, b) => b.expected_recovery_minor - a.expected_recovery_minor);
    }

    return result;
  }, [events, decisionFilter, eventFilter, priorityMode]);

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load decision stream</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={load} className="btn-primary">Retry</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      {/* ── HEADER ── */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.25rem" }}>
          Autonomous Recovery Stream
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Portfolio-level decisions · Bounded execution · Verified settlement
        </p>
      </div>

      {/* ── SUMMARY HEADER ── */}
      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
          <SummaryCard label="Opportunities Evaluated" value={summary.total_opportunities.toString()} color="var(--text-primary)" />
          <SummaryCard label="Recovery Decisions" value={summary.total_decisions.toString()} color="#6366f1" />
          <SummaryCard label="Awaiting Action" value={summary.awaiting_action.toString()} color="#f59e0b" />
          <SummaryCard label="Expected Recovery" value={fmt(summary.total_expected_recovery)} color="#10b981" sublabel="Projected" />
        </div>
      )}

      {/* ── FILTERS ── */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
          {DECISION_FILTERS.map((f) => (
            <FilterButton key={f.key} label={f.label} active={decisionFilter === f.key} onClick={() => setDecisionFilter(f.key)} />
          ))}
        </div>
        <div style={{ width: 1, height: 24, background: "var(--border)" }} />
        <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
          {EVENT_FILTERS.map((f) => (
            <FilterButton key={f.key} label={f.label} active={eventFilter === f.key} onClick={() => setEventFilter(f.key)} />
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <button
          onClick={() => setPriorityMode(!priorityMode)}
          style={{
            fontSize: "0.75rem",
            padding: "0.4rem 0.75rem",
            borderRadius: 6,
            border: priorityMode ? "1px solid var(--accent)" : "1px solid var(--border)",
            background: priorityMode ? "rgba(99,102,241,0.1)" : "var(--bg-secondary)",
            color: priorityMode ? "var(--accent)" : "var(--text-secondary)",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          {priorityMode ? "↑ Highest Impact" : "↓ Chronological"}
        </button>
      </div>

      {/* ── EVENTS ── */}
      {status === "loading" && events.length === 0 ? (
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ fontSize: "0.9375rem", fontWeight: 500, marginBottom: "0.25rem" }}>No recovery decisions yet</p>
          <p style={{ fontSize: "0.8125rem" }}>Decisions will appear here as RevPlug evaluates revenue opportunities.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {filtered.map((evt) => (
            <EventCard key={evt.event_id} event={evt} />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, color, sublabel }: { label: string; value: string; color: string; sublabel?: string }) {
  return (
    <div className="card" style={{ padding: "1rem" }}>
      <div style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>
        {label}
      </div>
      <div className="font-mono" style={{ fontSize: "1.25rem", fontWeight: 700, color }}>{value}</div>
      {sublabel && <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginTop: 2 }}>{sublabel}</div>}
    </div>
  );
}

function FilterButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: "0.75rem",
        padding: "0.35rem 0.7rem",
        borderRadius: 6,
        border: active ? "1px solid var(--accent)" : "1px solid var(--border)",
        background: active ? "rgba(99,102,241,0.1)" : "var(--bg-secondary)",
        color: active ? "var(--accent)" : "var(--text-secondary)",
        cursor: "pointer",
        fontWeight: 600,
      }}
    >{label}</button>
  );
}

function EventCard({ event }: { event: DecisionStreamEvent }) {
  const typeConfig = EVENT_TYPE_CONFIG[event.event_type] || EVENT_TYPE_CONFIG.decision;
  const hasOutcome = event.verified_recovered_minor > 0;
  const hasExpected = event.expected_recovery_minor > 0;
  const isIncident = event.event_type === "incident" && !!event.incident_id;
  const cardHref = isIncident ? `/incidents/${event.incident_id}` : `/recovery/${event.opportunity_id}`;

  return (
    <Link href={cardHref} style={{ textDecoration: "none", display: "block" }}>
      <div
        className="card"
        style={{
          padding: "1rem 1.25rem",
          borderLeft: `3px solid ${typeConfig.color}`,
          transition: "border-color 0.15s",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: "0.875rem" }}>
          {/* Timeline dot */}
          <div style={{ flexShrink: 0, paddingTop: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: typeConfig.color }} />
          </div>

          {/* Content */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Top row: time + decision badge */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: 4, flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                {fmtDate(event.timestamp)}
              </span>
              <DecisionBadge decision={event.decision as any} compact />
              {isIncident && (
                <span style={{ fontSize: "0.625rem", fontWeight: 700, color: "#f59e0b", padding: "0.1rem 0.4rem", borderRadius: 4, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.25)" }}>
                  Incident
                </span>
              )}
              {event.requires_human_review && !isIncident && (
                <span style={{ fontSize: "0.625rem", fontWeight: 700, color: "#f59e0b", padding: "0.1rem 0.4rem", borderRadius: 4, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.25)" }}>
                  Review
                </span>
              )}
            </div>

            {/* Event label */}
            <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
              {event.event_label}
            </div>

            {/* Customer + amount (skip for incidents) */}
            {!isIncident && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap", marginBottom: 4 }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                  {getCustomerDisplayName(event.customer_id, event.customer_name)}
                </span>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {event.opportunity_id.slice(0, 12)}
              </span>
              {event.root_cause && (
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                    · {event.root_cause.replace(/_/g, " ")}
                  </span>
                )}
              </div>
            )}

            {/* Money context */}
            <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                At Risk: <span className="font-mono" style={{ fontWeight: 700, color: "#ef4444" }}>{fmt(event.amount_at_risk_minor)}</span>
              </span>
              {hasExpected && event.decision === "RECOVER" && (
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  Expected: <span className="font-mono" style={{ fontWeight: 700, color: "#6366f1" }}>{fmt(event.expected_recovery_minor)}</span>
                </span>
              )}
              {hasOutcome && (
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  Verified: <span className="font-mono" style={{ fontWeight: 700, color: "#10b981" }}>{fmt(event.verified_recovered_minor)}</span>
                </span>
              )}
            </div>

            {/* Decision reason */}
            {event.decision_reason && (
              <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 4, fontStyle: "italic" }}>
                Why: {event.decision_reason}
              </div>
            )}

            {/* Closed loop indicator */}
            {event.terminal && hasOutcome && (
              <div style={{ marginTop: 6, paddingTop: 6, borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.625rem", fontWeight: 700, color: "#10b981" }}>✓ Recovery complete</span>
                <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
                  {fmt(event.amount_at_risk_minor)} at risk → {fmt(event.verified_recovered_minor)} verified
                </span>
              </div>
            )}
          </div>

          {/* Right side: execution status */}
          <div style={{ flexShrink: 0, textAlign: "right" }}>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", marginBottom: 4 }}>
              {fmtTime(event.timestamp)}
            </div>
            <div style={{
              fontSize: "0.5625rem",
              fontWeight: 600,
              textTransform: "uppercase",
              color: event.execution_status === "verified" ? "#10b981" : event.execution_status === "executed" ? "#3b82f6" : "var(--text-muted)",
            }}>
              {event.execution_status}
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
