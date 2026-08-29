"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { api, AuditEvent } from "@/lib/api";

type Status = "loading" | "error" | "ready";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "provider", label: "Provider" },
  { key: "recovery", label: "Recovery" },
  { key: "ai", label: "AI" },
  { key: "policy", label: "Policy" },
  { key: "execution", label: "Execution" },
  { key: "worker", label: "Worker" },
  { key: "human", label: "Human" },
  { key: "outcome", label: "Outcome" },
] as const;

export default function Activity() {
  const [status, setStatus] = useState<Status>("loading");
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const load = useCallback(async () => {
    try {
      setStatus("loading");
      const data = await api.auditEvents();
      setEvents(data);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load activity");
      setStatus("error");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (filter === "all") return events;
    return events.filter((e) => {
      const act = e.action.toLowerCase();
      const actor = e.actor.toLowerCase();
      switch (filter) {
        case "provider": return act.includes("provider") || actor.includes("provider");
        case "recovery": return act.includes("recovery") || actor.includes("recovery");
        case "ai": return actor === "agent" || act.includes("ai_");
        case "policy": return actor === "policy" || act.includes("guard_") || act.includes("policy");
        case "execution": return actor === "execution" || act.includes("execution") || act.includes("intervention_");
        case "worker": return actor === "worker" || act.includes("worker") || act.includes("job_") || act.includes("batch_");
        case "human": return actor === "human" || act.includes("human");
        case "outcome": return act.includes("outcome") || act.includes("recovered") || act.includes("escalated") || act.includes("stopped");
        default: return true;
      }
    });
  }, [events, filter]);

  if (status === "error") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>Unable to load activity log</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>{error}</p>
        <button onClick={load} className="btn-primary">Retry</button>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {[...Array(8)].map((_, i) => <div key={i} className="skeleton" style={{ height: 72 }} />)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: "0.5rem" }}>Activity</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
          Chronological log of every recovery event
        </p>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: "0.4rem 0.85rem",
              borderRadius: 6,
              fontSize: "0.75rem",
              fontWeight: 500,
              cursor: "pointer",
              border: "1px solid",
              borderColor: filter === f.key ? "var(--accent)" : "var(--border)",
              background: filter === f.key ? "var(--accent-subtle)" : "var(--bg-card)",
              color: filter === f.key ? "var(--accent)" : "var(--text-secondary)",
              transition: "all 0.15s",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="card" style={{ padding: "4rem", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ fontSize: "0.9375rem", fontWeight: 500, marginBottom: "0.25rem" }}>No events to display</p>
          <p style={{ fontSize: "0.8125rem" }}>There are no activity events matching this filter.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {filtered.map((event) => {
            const actionLower = event.action.toLowerCase();
            const dotColor = actionColor(actionLower);
            const isBlocked = actionLower.includes("denied") || actionLower.includes("stopped");
            const isSuccess = actionLower.includes("succeeded") || actionLower.includes("recovered");
            return (
              <Link key={event.id} href={`/recovery/${event.recovery_item_id}`} style={{ textDecoration: "none", display: "block" }}>
                <div className="card" style={{
                  padding: "0.875rem 1.25rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  cursor: "pointer",
                  borderLeft: isBlocked ? "3px solid var(--danger)" : isSuccess ? "3px solid var(--success)" : undefined,
                  transition: "border-color 0.15s",
                }}>
                  <div style={{ flexShrink: 0, width: 8, height: 8, borderRadius: "50%", background: dotColor }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: 2, flexWrap: "wrap" }}>
                      <span style={{ fontWeight: 600, fontSize: "0.8125rem" }}>{formatAction(event.action)}</span>
                      {event.reason && (
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>· {event.reason}</span>
                      )}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                      <span style={{ fontFamily: "monospace" }}>{event.recovery_item_id}</span>
                      <span>Actor: <span style={{ color: dotColor, fontWeight: 500 }}>{event.actor}</span></span>
                      <span>{new Date(event.timestamp).toLocaleString()}</span>
                    </div>
                  </div>
                  <span
                    className="status-badge"
                    style={{
                      flexShrink: 0,
                      textTransform: "capitalize",
                      background: actorBadgeBg(event.actor),
                      color: dotColor,
                    }}
                  >
                    {event.actor}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function actionColor(action: string): string {
  if (action.includes("succeeded") || action.includes("approved") || action.includes("recovered")) return "var(--success)";
  if (action.includes("failed") || action.includes("rejected") || action.includes("denied")) return "var(--danger)";
  if (action.includes("escalated") || action.includes("human")) return "var(--warning)";
  if (action.includes("proposal") || action.includes("ai") || action.includes("recommendation")) return "var(--purple)";
  if (action.includes("policy")) return "var(--accent)";
  return "var(--text-muted)";
}

function actorBadgeBg(actor: string): string {
  const lower = actor.toLowerCase();
  if (lower === "system") return "rgba(99,102,241,0.1)";
  if (lower === "agent") return "rgba(168,85,247,0.1)";
  if (lower === "human") return "rgba(245,158,11,0.1)";
  return "var(--bg-tertiary)";
}

function formatAction(action: string): string {
  return action
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
