"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CaseDetail } from "@/lib/api";

type Status = "loading" | "error" | "ready";

interface DecisionRow {
  proposed_action: string;
  confidence: number;
  reason: string;
  model_name: string;
  policy_allowed: boolean;
  policy_rule: string;
  policy_reason: string;
}

const fmt = (n: number) =>
  "Rs" +
  (n / 100).toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });

export default function CaseWorkspace() {
  const params = useParams();
  const id = params?.id as string;
  const [status, setStatus] = useState<Status>("loading");
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [techOpen, setTechOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    setStatus("loading");
    api.itemDetail(id)
      .then(setDetail)
      .catch(() => {
        setError("not-found");
        setDetail(null);
      })
      .finally(() => setStatus("ready"));
  }, [id]);

  if (status === "loading" || !detail) {
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div className="skeleton" style={{ height: 60, marginBottom: "1.5rem" }} />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "1rem",
            marginBottom: "1.5rem",
          }}
        >
          {[...Array(3)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 100 }} />
          ))}
        </div>
        <div className="skeleton" style={{ height: 400 }} />
      </div>
    );
  }

  if (error === "not-found") {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🔍</div>
        <h2
          style={{
            fontSize: "1.25rem",
            fontWeight: 600,
            marginBottom: "0.5rem",
          }}
        >
          Case not found
        </h2>
        <p
          style={{
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
            marginBottom: "1.25rem",
          }}
        >
          The recovery case you&apos;re looking for doesn&apos;t exist or has
          been removed.
        </p>
        <Link href="/recovery" className="btn-primary">
          Back to Queue
        </Link>
      </div>
    );
  }

  const firstDecision: DecisionRow | null = detail.decisions?.[0]
    ? {
        proposed_action: String(
          detail.decisions[0].proposed_action || "—"
        ),
        confidence: typeof detail.decisions[0].confidence === "number"
          ? detail.decisions[0].confidence
          : 0,
        reason: String(detail.decisions[0].reason || ""),
        model_name: String(detail.decisions[0].model_name || ""),
        policy_allowed: Boolean(detail.decisions[0].policy_allowed),
        policy_rule: String(detail.decisions[0].policy_rule || ""),
        policy_reason: String(detail.decisions[0].policy_reason || ""),
      }
    : null;

  const meta = detail.metadata || {};
  const errorMeta: Record<string, unknown> = {};
  if (typeof meta === "object" && meta !== null) {
    Object.entries(meta).forEach(([k, v]) => {
      if (
        k !== "original_payload" &&
        k !== "payload" &&
        k !== "headers" &&
        v !== null &&
        v !== undefined &&
        String(v).trim() !== ""
      ) {
        errorMeta[k] = v;
      }
    });
  }

  const timeDetected = new Date(detail.created_at);

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      {/* Breadcrumb */}
      <div style={{ marginBottom: "1.25rem" }}>
        <Link
          href="/recovery"
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            textDecoration: "none",
          }}
        >
          ← Recovery Queue
        </Link>
      </div>

      {/* Header */}
      <div
        className="card"
        style={{
          padding: "1.75rem",
          marginBottom: "1.5rem",
          background:
            "linear-gradient(135deg, var(--bg-card) 0%, var(--bg-elevated) 100%)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                marginBottom: "0.5rem",
                flexWrap: "wrap",
              }}
            >
              <StatusBadge status={detail.status} />
              <span
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.75rem",
                  fontFamily: "monospace",
                }}
              >
                {detail.id}
              </span>
            </div>
            <div
              style={{
                fontSize: "2.25rem",
                fontWeight: 700,
                fontFamily: "monospace",
                letterSpacing: "-0.03em",
                lineHeight: 1.1,
                color: "var(--text-primary)",
                marginBottom: "0.5rem",
              }}
            >
              {fmt(detail.amount_minor)}
            </div>
            <div
              style={{
                display: "flex",
                gap: "0.75rem",
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <span style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                {detail.customer_id || "Unknown Customer"}
              </span>
              <span style={{ color: "var(--text-muted)" }}>·</span>
              <span style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>
                {detail.source_type}
              </span>
              <span style={{ color: "var(--text-muted)" }}>·</span>
              <span style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                Detected {timeDetected.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <MetricCard
          label="Amount at Risk"
          value={fmt(detail.amount_minor)}
          accent="var(--danger)"
        />
        <MetricCard
          label="Expected Recovery"
          value={
            detail.expected_recovery_value
              ? fmt(detail.expected_recovery_value)
              : "—"
          }
          accent="var(--success)"
        />
        <MetricCard
          label="Recovery Probability"
          value={
            detail.recovery_probability !== null
              ? `${(detail.recovery_probability * 100).toFixed(0)}%`
              : "—"
          }
          accent="var(--purple)"
        />
      </div>

      {/* Why this happened */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h3
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            marginBottom: "1rem",
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          Why this happened
        </h3>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
          }}
        >
          <DetailRow label="Root Cause" value={detail.root_cause || "unknown"} />
          {Object.keys(errorMeta).length > 0 &&
            Object.entries(errorMeta).map(([k, v]) => (
              <DetailRow
                key={k}
                label={k.replace(/_/g, " ")}
                value={String(v)}
              />
            ))}
        </div>
      </div>

      {/* AI Diagnosis */}
      <div
        className="card"
        style={{
          padding: "1.5rem",
          marginBottom: "1.5rem",
          borderLeft: `3px solid var(--purple)`,
        }}
      >
        <h3
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            marginBottom: "1rem",
            color: "var(--purple)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          AI Diagnosis
        </h3>
        {firstDecision ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {firstDecision.reason && (
              <p
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.6,
                }}
              >
                {firstDecision.reason}
              </p>
            )}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "1rem",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                Confidence:{" "}
                <strong style={{ color: "var(--text-primary)" }}>
                  {firstDecision.confidence.toFixed(0)}%
                </strong>
              </span>
              {firstDecision.model_name && (
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                    fontFamily: "monospace",
                  }}
                >
                  {firstDecision.model_name}
                </span>
              )}
            </div>
          </div>
        ) : (
          <p
            style={{
              fontSize: "0.8125rem",
              color: "var(--text-muted)",
            }}
          >
            No AI diagnosis recorded.
          </p>
        )}
      </div>

      {/* AI Recommendation */}
      <div
        className="card"
        style={{
          padding: "1.5rem",
          marginBottom: "1.5rem",
          borderLeft: `3px solid var(--accent)`,
        }}
      >
        <h3
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            marginBottom: "1rem",
            color: "var(--accent)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          AI Recommendation
        </h3>
        {firstDecision ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  background: "var(--accent-subtle)",
                  color: "var(--accent)",
                  padding: "0.25rem 0.75rem",
                  borderRadius: 6,
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  textTransform: "capitalize",
                }}
              >
                {(firstDecision.proposed_action || "—").replace(/_/g, " ")}
              </span>
              {firstDecision.confidence > 0 && (
                <span
                  style={{
                    fontSize: "0.8125rem",
                    color: "var(--text-secondary)",
                  }}
                >
                  {firstDecision.confidence.toFixed(0)}% confidence
                </span>
              )}
            </div>
            {detail.expected_recovery_value && (
              <div
                style={{
                  fontSize: "1.125rem",
                  fontWeight: 600,
                  color: "var(--success)",
                  fontFamily: "monospace",
                }}
              >
                Expected Recovery: {fmt(detail.expected_recovery_value)}
              </div>
            )}
          </div>
        ) : (
          <p
            style={{
              fontSize: "0.8125rem",
              color: "var(--text-muted)",
            }}
          >
            No AI recommendation recorded.
          </p>
        )}
      </div>

      {/* Policy Check */}
      <div
        className="card"
        style={{
          padding: "1.5rem",
          marginBottom: "1.5rem",
          borderLeft: `3px solid ${firstDecision ? (firstDecision.policy_allowed ? "var(--success)" : "var(--danger)") : "var(--border)"}`,
        }}
      >
        <h3
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            marginBottom: "1rem",
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          Policy Check
        </h3>
        {firstDecision ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            {[
              {
                label: "Policy Allowed",
                value: firstDecision.policy_allowed ? "Yes" : "No",
                status: firstDecision.policy_allowed
                  ? "var(--success)"
                  : "var(--danger)",
              },
              { label: "Policy Rule", value: firstDecision.policy_rule || "—" },
              { label: "Reason", value: firstDecision.policy_reason || "—" },
            ].map((row) => (
              <div
                key={row.label}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.75rem",
                  fontSize: "0.8125rem",
                }}
              >
                <span
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: "50%",
                    background:
                      row.status === "var(--success)"
                        ? "var(--success-subtle)"
                        : row.status === "var(--danger)"
                          ? "var(--danger-subtle)"
                          : "var(--bg-tertiary)",
                    color: row.status || "var(--text-muted)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "0.625rem",
                    fontWeight: 700,
                    flexShrink: 0,
                    marginTop: 2,
                  }}
                >
                  {row.status === "var(--success)"
                    ? "✓"
                    : row.status === "var(--danger)"
                      ? "✗"
                      : "-"}
                </span>
                <div style={{ flex: 1 }}>
                  <span
                    style={{ color: "var(--text-muted)", marginRight: "0.5rem" }}
                  >
                    {row.label}
                  </span>
                  <span
                    style={{
                      color:
                        row.status === "var(--success)"
                          ? "var(--success)"
                          : row.status === "var(--danger)"
                            ? "var(--danger)"
                            : "var(--text-primary)",
                      fontWeight: 500,
                    }}
                  >
                    {row.value}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p
            style={{
              fontSize: "0.8125rem",
              color: "var(--text-muted)",
            }}
          >
            No policy check recorded.
          </p>
        )}
      </div>

      {/* Execution */}
      {detail.attempts.length > 0 && (
        <div
          className="card"
          style={{ padding: "1.5rem", marginBottom: "1.5rem" }}
        >
          <h3
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              marginBottom: "1rem",
              color: "var(--text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Execution
          </h3>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            {detail.attempts.map((a) => (
              <div
                key={a.attempt_number}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.75rem 1rem",
                  background: "var(--bg-tertiary)",
                  borderRadius: 8,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    flex: 1,
                    minWidth: 0,
                  }}
                >
                  <span
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      background:
                        a.outcome === "success"
                          ? "var(--success-subtle)"
                          : "var(--danger-subtle)",
                      color:
                        a.outcome === "success"
                          ? "var(--success)"
                          : "var(--danger)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.6875rem",
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    {a.attempt_number}
                  </span>
                  <span
                    style={{
                      fontSize: "0.8125rem",
                      fontWeight: 500,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {a.action}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    flexShrink: 0,
                  }}
                >
                  {a.executed_at && (
                    <span
                      style={{
                        fontSize: "0.6875rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      {new Date(a.executed_at).toLocaleTimeString()}
                    </span>
                  )}
                  <span
                    className={`status-badge ${a.outcome === "success" ? "status-recovered" : "status-failed"}`}
                  >
                    {a.outcome}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recovery Timeline */}
      <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h3
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            marginBottom: "1.5rem",
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          Recovery Timeline
        </h3>
        <Timeline stages={buildTimeline(detail, firstDecision)} />
      </div>

      {/* Technical Details */}
      <div className="card" style={{ marginBottom: "1.5rem", overflow: "hidden" }}>
        <button
          onClick={() => setTechOpen((v) => !v)}
          style={{
            width: "100%",
            background: "none",
            border: "none",
            color: "var(--text-secondary)",
            padding: "1rem 1.5rem",
            fontSize: "0.75rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            transition: "color 0.15s",
          }}
        >
          Technical Details
          <span
            style={{
              transition: "transform 0.2s",
              display: "inline-block",
              transform: techOpen ? "rotate(180deg)" : "rotate(0deg)",
              fontSize: "0.625rem",
            }}
          >
            ▼
          </span>
        </button>
        {techOpen && (
          <div
            style={{
              borderTop: "1px solid var(--border-subtle)",
              padding: "1.25rem 1.5rem",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "1.25rem",
              }}
            >
              <div>
                <h4
                  style={{
                    fontSize: "0.6875rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.75rem",
                  }}
                >
                  Raw Metadata
                </h4>
                <pre
                  style={{
                    background: "var(--bg-root)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 6,
                    padding: "1rem",
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    overflow: "auto",
                    maxHeight: 300,
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(detail.metadata, null, 2)}
                </pre>
              </div>
              <div>
                <h4
                  style={{
                    fontSize: "0.6875rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.75rem",
                  }}
                >
                  Decisions
                </h4>
                <pre
                  style={{
                    background: "var(--bg-root)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 6,
                    padding: "1rem",
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    overflow: "auto",
                    maxHeight: 300,
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(detail.decisions, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: "0.8125rem",
        padding: "0.35rem 0",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <span style={{ color: "var(--text-muted)" }}>{label}</span>
      <span
        style={{
          color: "var(--text-primary)",
          fontWeight: 500,
          textAlign: "right",
          maxWidth: "60%",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div
      className="metric-card"
      style={accent ? { borderLeft: `3px solid ${accent}` } : undefined}
    >
      <div className="metric-label">{label}</div>
      <div
        className="metric-value"
        style={{
          color: accent || "var(--text-primary)",
          marginTop: 4,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls = `status-badge status-${status}`;
  return <span className={cls}>{status.replace(/_/g, " ")}</span>;
}

interface TimelineStage {
  label: string;
  timestamp?: string;
  result?: string;
  color: string;
  active: boolean;
}

function Timeline({ stages }: { stages: TimelineStage[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {stages.map((stage, idx) => (
        <div
          key={idx}
          style={{
            display: "flex",
            gap: "1rem",
            paddingBottom:
              idx < stages.length - 1 ? "1.25rem" : 0,
            position: "relative",
          }}
        >
          {/* Vertical line */}
          {idx < stages.length - 1 && (
            <div
              style={{
                position: "absolute",
                left: 11,
                top: 20,
                bottom: 0,
                width: 2,
                background:
                  stage.active && stages[idx + 1].active
                    ? stage.color
                    : "var(--border)",
              }}
            />
          )}
          {/* Dot */}
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: "50%",
              background: stage.active ? stage.color : "var(--border)",
              boxShadow: stage.active
                ? `0 0 8px ${stage.color}40`
                : "none",
              flexShrink: 0,
              zIndex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {stage.active && (
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--bg-root)",
                }}
              />
            )}
          </div>
          {/* Content */}
          <div style={{ flex: 1, paddingTop: 2 }}>
            <div
              style={{
                fontSize: "0.8125rem",
                fontWeight: stage.active ? 600 : 400,
                color: stage.active
                  ? "var(--text-primary)"
                  : "var(--text-muted)",
                textTransform: "capitalize",
              }}
            >
              {stage.label}
            </div>
            {stage.timestamp && (
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  marginTop: 2,
                  fontFamily: "monospace",
                }}
              >
                {new Date(stage.timestamp).toLocaleString()}
              </div>
            )}
            {stage.result && (
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  marginTop: 2,
                }}
              >
                {stage.result}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function buildTimeline(detail: CaseDetail, firstDecision: DecisionRow | null): TimelineStage[] {
  const events = [...detail.audit_events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const eventMap = new Map<string, typeof events[0]>();
  events.forEach((e) => {
    const action = e.action;
    if (!eventMap.has(action)) {
      eventMap.set(action, e);
    }
  });

  const stages: TimelineStage[] = [];

  const addStage = (
    label: string,
    action: string,
    color: string,
    result?: string
  ) => {
    const ev = eventMap.get(action);
    stages.push({
      label,
      timestamp: ev?.timestamp,
      result: result || (ev ? ev.reason || ev.action : undefined),
      color,
      active: !!ev,
    });
  };

  const hasDecision = !!firstDecision;
  const status = detail.status;
  const isExecuted = ["intervention_executed", "recovered", "failed", "escalated", "stopped"].includes(status);
  const isOutcome = ["recovered", "escalated", "stopped", "failed"].includes(status);

  addStage("Detected", "failure_detected", "var(--danger)");

  if (eventMap.has("failure_classified") || detail.root_cause) {
    addStage(
      "Classified",
      "failure_classified",
      "var(--accent)",
      detail.root_cause || undefined
    );
  } else {
    stages.push({ label: "Classified", color: "var(--border)", active: false });
  }

  if (hasDecision) {
    addStage(
      "Value Scored",
      "value_scored",
      "var(--purple)",
      detail.expected_recovery_value
        ? fmt(detail.expected_recovery_value)
        : undefined
    );
  } else {
    stages.push({ label: "Value Scored", color: "var(--border)", active: false });
  }

  if (hasDecision) {
    addStage(
      "AI Recommendation",
      "ai_recommendation",
      "var(--purple)",
      firstDecision.proposed_action
    );
  } else {
    stages.push({ label: "AI Recommendation", color: "var(--border)", active: false });
  }

  if (hasDecision) {
    addStage(
      "Validated",
      "validated",
      "var(--success)",
      firstDecision.policy_allowed ? "Policy allowed" : "Policy denied"
    );
  } else {
    stages.push({ label: "Validated", color: "var(--border)", active: false });
  }

  if (hasDecision) {
    addStage(
      "Policy Decision",
      "policy_decision",
      firstDecision.policy_allowed ? "var(--success)" : "var(--danger)",
      firstDecision.policy_allowed ? "Allowed" : "Denied"
    );
  } else {
    stages.push({ label: "Policy Decision", color: "var(--border)", active: false });
  }

  if (isExecuted) {
    addStage(
      "Execution",
      "intervention_executed",
      "var(--accent)",
      detail.attempts[0]?.outcome || undefined
    );
  } else {
    stages.push({ label: "Execution", color: "var(--border)", active: false });
  }

  if (isOutcome) {
    const outcomeColor =
      status === "recovered"
        ? "var(--success)"
        : status === "escalated"
          ? "var(--danger)"
          : "var(--text-muted)";
    const outcomeResult =
      status === "recovered"
        ? detail.expected_recovery_value
          ? fmt(detail.expected_recovery_value)
          : "Recovered"
        : status === "escalated"
          ? "Escalated"
          : status === "stopped"
            ? "Stopped"
            : status;
    addStage("Outcome", "outcome", outcomeColor, outcomeResult);
  } else {
    stages.push({ label: "Outcome", color: "var(--border)", active: false });
  }

  return stages;
}
