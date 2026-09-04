const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface DashboardSummary {
  revenue_at_risk: number;
  actually_recovered: number;
  expected_recovery: number;
  recovery_rate: number;
  total_items: number;
  active_recoveries: number;
  recovered_cases: number;
  stopped_cases: number;
  escalated_cases: number;
  priority_distribution: Record<string, number>;
  recovery_by_failure_category: Record<string, { total: number; recovered: number; amount_minor: number }>;
  recovery_by_action: Record<string, number>;
  recovered_value_by_day: Array<{ date: string; amount_minor: number; count: number }>;
  net_recovered?: number;
  total_cases?: number;
  active_cases?: number;
  // Legacy fields
  total_amount_minor?: number;
  recovered_count?: number;
  recovered_amount_minor?: number;
  expected_recovery_value?: number;
  escalated_count?: number;
  pending_count?: number;
  executed_count?: number;
  attempts_total?: number;
  attempts_successful?: number;
  attempts_failed?: number;
  decisions_total?: number;
  policy_allowed?: number;
  policy_denied?: number;
}

export interface PromiseToPay {
  id: string;
  recovery_item_id: string;
  customer_id: string;
  promised_amount_minor: number;
  promised_date: string;
  status: string;
  created_at: string;
  fulfilled_at?: string;
  expired_at?: string;
  verified_recovered_minor?: number | null;
  settled_amount_minor?: number | null;
  break_reason?: string | null;
  source?: string | null;
  channel?: string | null;
  metadata: Record<string, unknown>;
}

export interface ExtractedPromise {
  intent: string;
  amount_minor: number | null;
  promised_date: string | null;
  confidence: number;
  source_text: string;
}

export interface VoicePromiseResponse {
  extracted: ExtractedPromise;
  promise_created: boolean;
  promise: PromiseToPay | null;
  decision?: string | null;
  reason?: string | null;
  follow_up_date?: string | null;
}

export interface PromiseSummary {
  active_count: number;
  committed_amount_minor: number;
  due_soon_count: number;
  fulfilled_count: number;
  fulfilled_amount_minor: number;
  broken_count: number;
}

export interface Batch {
  batch_id: string;
  name: string;
  dataset_label: string;
  is_synthetic: boolean;
  status: string;
  total_items: number;
  total_amount_at_risk: number;
  expected_recovery: number;
  actual_recovered?: number;
  recovery_rate?: number;
  recovered_count?: number;
  stopped_count?: number;
  escalated_count?: number;
  active_count?: number;
  completion_pct?: number;
  created_at: string;
  completed_at?: string;
  metadata: Record<string, unknown>;
  items?: RecoveryItem[];
}

export interface CustomerDetail {
  customer_id: string;
  opt_out: boolean;
  revenue_at_risk: number;
  actually_recovered: number;
  expected_recovery: number;
  recovery_rate: number;
  total_cases: number;
  active_cases: number;
  recovered_cases: number;
  escalated_cases: number;
  stopped_cases: number;
  promises: PromiseToPay[];
  last_action: string | null;
  last_action_at: string | null;
  timeline: AuditEvent[];
  cases: RecoveryItem[];
}

export interface TimeSeriesPoint {
  date: string;
  amount_minor?: number;
  count?: number;
  success?: number;
  failed?: number;
  total?: number;
  reason_code?: string;
}

export interface LifecycleStage {
  stage: string;
  completed: boolean;
  timestamp: string | null;
  events: AuditEvent[];
  data?: Record<string, unknown>;
}

export interface Lifecycle {
  item_id: string;
  item: RecoveryItem;
  stages: LifecycleStage[];
  total_audit_events: number;
}


export interface RecoveryItem {
  id: string;
  source_type: string;
  external_id: string;
  customer_id: string;
  amount_minor: number;
  currency: string;
  created_at: string;
  status: string;
  root_cause: string | null;
  recovery_probability: number | null;
  intervention_cost: number | null;
  expected_recovery_value: number | null;
  actual_recovery_value: number | null;
  stopped_reason: string | null;
  stopped_rule: string | null;
  metadata: Record<string, unknown>;
}

export interface CaseDetail extends RecoveryItem {
  actual_recovery_value: number | null;
  decisions: Array<Record<string, unknown>>;
  attempts: Array<{
    recovery_item_id: string;
    attempt_number: number;
    action: string;
    executed_at: string | null;
    outcome: string;
    failure_reason: string | null;
    metadata: Record<string, unknown>;
  }>;
  audit_events: AuditEvent[];
  outcome: Record<string, unknown> | null;
}

export interface EvaluationResult {
  scenario_name: string;
  passed: boolean;
  proposal_action: string;
  proposal_confidence: number;
  expected_action: string | null;
  issues: string[];
}

export interface EvaluationReport {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  results: EvaluationResult[];
}

export interface SimulationResult {
  status: string;
  recovery_item_id: string | null;
  item_id?: string;
  customer_id?: string;
  amount_minor?: number;
  confidence?: number;
  action_executed?: string;
  attempt_count?: number;
  settlement_verified?: boolean;
  audit_event_count: number;
  failure_category?: string;
  expected_recovery_value?: number;
  proposed_action?: string;
  agent_confidence?: number;
  policy_allowed?: boolean;
  policy_rule?: string;
  execution_status?: string;
  attempt_number?: number;
  retry_scheduled?: boolean;
  escalation_reason?: string;
  recovery_status?: string;
  actual_recovery_value?: number;
  stopped_reason?: string;
  stopped_rule?: string;
}

export async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> || {}),
  };

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("revplug_session_token");
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorMsg = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      if (json && (json.detail || json.message || json.error)) {
        errorMsg = json.detail || json.message || json.error;
      }
    } catch {
      if (res.status === 404) {
        errorMsg = "Requested resource or recovery case could not be found.";
      } else {
        errorMsg = `Server error ${res.status}`;
      }
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export interface AuditEvent {
  id: string;
  recovery_item_id: string;
  actor: string;
  action: string;
  reason: string | null;
  metadata: Record<string, unknown>;
  timestamp: string;
  label?: string;
  item_id?: string;
  amount_minor?: number;
}

export interface BatchSimulationResult {
  results: Array<{
    recovery_item_id: string | null;
    status: string;
    failure_category: string | null;
    expected_recovery_value: number | null;
    recovery_status: string | null;
    proposed_action: string | null;
    agent_confidence: number | null;
    policy_allowed: boolean | null;
    policy_rule: string | null;
    execution_status: string | null;
    stopped_reason?: string | null;
  }>;
  summary: {
    total_cases: number;
    recovered_count: number;
    recovered_amount_minor: number;
    escalated_count: number;
    stopped_count: number;
    recovery_rate: number;
  };
}

export interface EvaluationRunResult {
  evaluation_id: string;
  seed: number;
  count: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  dataset: {
    count: number;
    seed: number;
    categories: Record<string, number>;
    surfaces?: Record<string, number>;
    safety_statistics?: Record<string, number>;
    opted_out_customer_count: number;
    case_ids: string[];
    calibration_buckets?: Record<string, any>;
  };
  revplug: {
    cases_evaluated: number;
    cases_completed: number;
    cases_failed_processing: number;
    total_amount_at_risk: number;
    expected_recovery: number;
    actual_recovered: number;
    recovery_rate: number;
    recovered_count: number;
    stopped_count: number;
    escalated_count: number;
    total_interventions: number;
    intervention_cost: number;
    cost_per_recovery: number;
    unnecessary_interventions: number;
    net_revenue_recovered?: number;
    net_recovered?: number;
    no_action_cases?: number;
    negative_ev_no_action_cases?: number;
    policy_stop_cases?: number;
    rules_classified_count?: number;
    llm_classified_count?: number;
    llm_fallback_count?: number;
    unnecessary_intervention_definition?: string;
  };
  recoveros?: {
    cases_evaluated: number;
    cases_completed: number;
    cases_failed_processing: number;
    total_amount_at_risk: number;
    expected_recovery: number;
    actual_recovered: number;
    recovery_rate: number;
    recovered_count: number;
    stopped_count: number;
    escalated_count: number;
    total_interventions: number;
    intervention_cost: number;
    cost_per_recovery: number;
    unnecessary_interventions: number;
    no_action_cases?: number;
    negative_ev_no_action_cases?: number;
    policy_stop_cases?: number;
  };
  baseline: {
    cases_evaluated: number;
    cases_completed: number;
    cases_failed_processing: number;
    total_amount_at_risk: number;
    actual_recovered: number;
    recovery_rate: number;
    recovered_count: number;
    stopped_count: number;
    total_interventions: number;
    intervention_cost: number;
    cost_per_recovery: number;
    unnecessary_interventions: number;
    raw_retry_attempts: number;
    raw_retries_that_failed: number;
    baseline_policy_violations?: any;
  };
  safe_baseline?: {
    cases_evaluated: number;
    cases_completed: number;
    cases_failed_processing: number;
    total_amount_at_risk: number;
    actual_recovered: number;
    recovery_rate: number;
    recovered_count: number;
    stopped_count: number;
    total_interventions: number;
    intervention_cost: number;
    cost_per_recovery: number;
    unnecessary_interventions: number;
    raw_retry_attempts: number;
    raw_retries_that_failed: number;
    baseline_policy_violations?: any;
  };
  comparison: {
    absolute_recovery_difference: number;
    recovery_rate_difference: number;
    relative_improvement: number | null;
    revplug_beat_baseline: boolean;
    revplug_beat_safe: boolean;
    honest_summary: string;
    safe_baseline_net: number;
    naive_baseline_net: number;
    revplug_net: number;
    safe_lift_pct: number | null;
    naive_lift_pct: number | null;
  };
  per_case: Array<{
    case_id: string;
    case_map_id: string;
    failure_category: string;
    original_category: string;
    amount_at_risk: number;
    customer_id: string;
    revplug: {
      proposed_action: string | null;
      safety_decision: string | null;
      outcome: string;
      actual_recovered: number;
      expected_recovery: number;
      intervention_cost: number;
      unnecessary_intervention: boolean;
      stop_reason: string | null;
      escalation_reason: string | null;
      diagnosis_path: string;
      audit_event_count: number;
      processing_error: string | null;
    };
    baseline: {
      proposed_action: string | null;
      outcome: string;
      actual_recovered: number;
      intervention_cost: number;
      attempts_made: number;
      unnecessary_intervention: boolean;
      stop_reason: string | null;
    } | null;
    safe_baseline?: {
      proposed_action: string | null;
      outcome: string;
      actual_recovered: number;
      intervention_cost: number;
      attempts_made: number;
      unnecessary_intervention: boolean;
      stop_reason: string | null;
      policy_violations?: Record<string, number>;
    } | null;
  }>;
  error: string | null;
}

export interface OpportunityItem {
  rank: number;
  item_id: string;
  customer_id: string;
  customer_name: string;
  amount_at_risk_minor: number;
  expected_net_recovery_minor: number;
  action: string;
  action_label: string;
  reason: string;
  urgency: string;
  decision: "RECOVER" | "WAIT" | "ESCALATE" | "STOP";
  reason_code: string;
}

export interface DashboardActivityEvent {
  id: string;
  timestamp: string;
  recovery_item_id: string;
  customer_id: string;
  amount_minor: number;
  action: string;
  reason: string;
  actor: string;
  item_status: string;
  root_cause: string | null;
}

export interface DecisionDistribution {
  count: number;
  total_at_risk: number;
  total_expected: number;
  top_opportunity: {
    item_id: string;
    customer_id: string;
    amount_minor: number;
    expected_recovery_value: number | null;
    root_cause: string | null;
    reason: string;
  } | null;
}

export interface DecisionStreamEvent {
  event_id: string;
  timestamp: string;
  opportunity_id: string;
  customer_id: string;
  customer_name: string;
  amount_at_risk_minor: number;
  decision: string;
  decision_reason: string;
  reason_code: string;
  selected_action: string | null;
  event_type: string;
  event_action: string;
  event_label: string;
  execution_status: string;
  expected_recovery_minor: number;
  verified_recovered_minor: number;
  policy_status: string;
  requires_human_review: boolean;
  terminal: boolean;
  root_cause: string;
  actor: string;
  incident_id?: string;
}

export interface DecisionStreamSummary {
  total_opportunities: number;
  total_decisions: number;
  awaiting_action: number;
  total_expected_recovery: number;
}

export interface DecisionStreamResponse {
  events: DecisionStreamEvent[];
  summary: DecisionStreamSummary;
}

// Revenue Incidents
export interface IncidentSummary {
  active_incidents_count: number;
  total_revenue_at_risk_minor: number;
  revenue_protected_by_waiting_minor: number;
  total_affected_customers: number;
  suppressed_actions_count: number;
  resumed_cases_count: number;
}

export interface Incident {
  incident_id: string;
  gateway: string;
  payment_method: string;
  issuer_bank: string;
  failure_category: string;
  title: string;
  failure_rate_pct: number;
  baseline_failure_rate_pct: number;
  lift_vs_baseline: number;
  amount_at_risk_minor: number;
  affected_customers_count: number;
  estimated_recoverable_minor: number;
  revenue_protected_by_waiting_minor: number;
  status: string;
  recommendation: string;
  reason: string;
  affected_opportunity_ids: string[];
  detected_at: string;
  severity: string;
  decision: string;
  decision_reason: string;
  resolution_condition: string;
  resolved_at?: string;
  created_at: string;
}

export interface IncidentDetail extends Incident {
  systemic_incident_meta?: Record<string, unknown>;
}

export interface IncidentOpportunity {
  opportunity_id: string;
  customer_id: string;
  customer_name: string;
  amount_at_risk_minor: number;
  root_cause: string;
  current_status: string;
  policy_state: string;
  recommended_action: string;
  verified_recovery_minor: number;
  incident_relationship: string;
}

export interface IncidentTimelineEvent {
  timestamp: string;
  event: string;
  action: string;
  recovery_item_id: string;
  actor: string;
  reason: string;
}

export interface PortfolioSummary {
  total_revenue_at_risk_minor: number;
  actually_recovered: number;
  expected_recovery: number;
  recovery_rate: number;
  total_items: number;
  active_recoveries: number;
  recovered_cases: number;
  stopped_cases: number;
  escalated_cases: number;
}

export interface CapitalProtected {
  total_capital_protected_minor: number;
  case_count: number;
  breakdown_by_reason: Record<string, number>;
  itemized_cases: Array<{
    item_id: string;
    customer_id: string;
    amount_minor: number;
    reason: string;
    status: string;
  }>;
}

export const api = {
  evaluationBatch: (data: { count: number; seed: number }) =>
    fetchAPI<EvaluationRunResult>("/api/evaluations/batch", { method: "POST", body: JSON.stringify(data) }),
  health: () => fetchAPI<{ status: string }>("/health"),
  summary: () => fetchAPI<DashboardSummary>("/api/dashboard/summary"),
  items: () => fetchAPI<RecoveryItem[]>("/api/recovery-items"),
  itemDetail: (id: string) => fetchAPI<CaseDetail>(`/api/recovery-items/${id}`),
  evaluations: () => fetchAPI<EvaluationReport>("/api/evaluations"),
  pendingReviews: () => fetchAPI<RecoveryItem[]>("/api/reviews/pending"),
  auditEvents: () => fetchAPI<AuditEvent[]>("/api/audit-events"),
  customerDetail: (id: string) => fetchAPI<CustomerDetail>(`/api/customers/${id}`),
  customers: () => fetchAPI<CustomerDetail[]>("/api/customers"),
  customerRecoveryProfile: (id: string) => fetchAPI<Customer360Profile>(`/api/customers/${id}/recovery-profile`),
  
  // Promises
  promises: () => fetchAPI<PromiseToPay[]>("/api/promises"),
  promiseByItem: (itemId: string) => fetchAPI<PromiseToPay | null>(`/api/promises/by-item/${itemId}`),
  promiseActive: (itemId: string) => fetchAPI<PromiseToPay | null>(`/api/promises/by-item/${itemId}?active=true`),
  createPromise: (data: { item_id: string; customer_id: string; promised_amount_minor: number; promised_date: string }) =>
    fetchAPI<PromiseToPay>("/api/promises", { method: "POST", body: JSON.stringify(data) }),
  fulfillPromise: (id: string) => fetchAPI<PromiseToPay>(`/api/promises/${id}/fulfill`, { method: "POST" }),
  breakPromise: (id: string, reason?: string) => fetchAPI<PromiseToPay>(`/api/promises/${id}/break`, {
    method: "POST", body: JSON.stringify({ reason })
  }),
  promiseSummary: () => fetchAPI<PromiseSummary>("/api/dashboard/promise-summary"),
  voicePromise: (itemId: string, transcript: string, referenceDate?: string) =>
    fetchAPI<VoicePromiseResponse>(`/api/recovery-items/${itemId}/voice-promise`, {
      method: "POST",
      body: JSON.stringify({ transcript, reference_date: referenceDate }),
    }),
  simulateSettlement: (itemId: string) =>
    fetchAPI<{ status: string; recovery_item_id: string; verification_result: string; actual_recovery_minor: number; final_status: string }>(
      `/api/recovery-items/${itemId}/simulate-settlement`,
      { method: "POST" }
    ),
  tsRisk: () => fetchAPI<TimeSeriesPoint[]>("/api/time-series/revenue-at-risk-by-day"),
  tsAttempts: () => fetchAPI<TimeSeriesPoint[]>("/api/time-series/attempts-by-day"),
  tsStopped: () => fetchAPI<TimeSeriesPoint[]>("/api/time-series/stopped-by-reason"),
  
  // Decision Trace & Scientific Benchmark
  caseTrace: (id: string) => fetchAPI<CaseTrace>(`/api/recovery-items/${id}/trace`),
  naiveBaseline: (id: string) => fetchAPI<NaiveBaselineResult>(`/api/recovery-items/${id}/naive-baseline`),
  batchSummary: (id: string) => fetchAPI<any>(`/api/batches/${id}/summary`),
  latestBenchmark: () => fetchAPI<ScientificBenchmarkReport>("/api/benchmark/latest"),
  benchmarkSummary: () => fetchAPI<{
    source: string;
    evaluation_id: string;
    seed: number;
    count: number;
    status: string;
    dataset_version: string;
    evaluation_mode: string;
    single_seed_label: string;
    multi_seed_label: string;
    single_seed: Record<string, any>;
    multi_seed: Record<string, any>;
  }>("/api/benchmark-summary"),
  portfolioNextBestActions: () => fetchAPI<OpportunityItem[]>("/api/portfolio/next-best-actions"),
  capitalProtected: () => fetchAPI<CapitalProtected>("/api/portfolio/capital-protected"),
  dashboardActivity: () => fetchAPI<DashboardActivityEvent[]>("/api/dashboard/activity"),
  dashboardDecisions: () => fetchAPI<Record<string, DecisionDistribution>>("/api/dashboard/decisions"),
  decisionStream: () => fetchAPI<DecisionStreamResponse>("/api/decisions/stream"),

  // Revenue Incidents
  incidents: () => fetchAPI<IncidentSummary>("/api/incidents/summary"),
  incidentActive: () => fetchAPI<Incident[]>("/api/incidents/active"),
  incidentDetail: (id: string) => fetchAPI<IncidentDetail>(`/api/incidents/${id}`),
  incidentOpportunities: (id: string) => fetchAPI<IncidentOpportunity[]>(`/api/incidents/${id}/opportunities`),
  incidentTimeline: (id: string) => fetchAPI<IncidentTimelineEvent[]>(`/api/incidents/${id}/timeline`),
  resolveIncident: (id: string) => fetchAPI<{ status: string; incident_id: string }>(`/api/incidents/${id}/resolve`, { method: "POST" }),
  incidentByOpportunity: (itemId: string) => fetchAPI<Incident | null>(`/api/incidents/by-opportunity/${itemId}`),

  // Lifecycle & Audit
  lifecycle: (id: string) => fetchAPI<Lifecycle>(`/api/recovery-items/${id}/lifecycle`),
  auditTrail: (id: string) => fetchAPI<{ item_id: string; total_events: number; timeline: AuditEvent[] }>(`/api/recovery-items/${id}/audit-trail`),

  triggerDemo: (data: Record<string, unknown>) =>
    fetchAPI<SimulationResult>("/api/demo/payment-failure", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  runSimulation: (data: Record<string, unknown>) => {
    const itemId = data.item_id || data.id;
    const url = itemId ? `/api/recovery-items/${itemId}/recover` : "/api/run-simulation";
    return fetchAPI<SimulationResult>(url, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  injectFailure: (data: { failure_type: string; item_id?: string }) =>
    fetchAPI<any>("/api/demo/inject-failure", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  batchDemo: (data: Record<string, unknown>) =>
    fetchAPI<BatchSimulationResult>("/api/demo/batch-payment-failures", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getProgramsConfig: () => fetchAPI<Record<string, Record<string, unknown>>>("/api/programs/config"),
  updateProgramsConfig: (updates: Record<string, Record<string, unknown>>) =>
    fetchAPI<{ status: string; config: Record<string, Record<string, unknown>> }>("/api/programs/config", {
      method: "PUT",
      body: JSON.stringify(updates),
    }),
  approve: (id: string, action: string) =>
    fetchAPI<{ status: string; message: string }>(`/api/recovery-items/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  reject: (id: string) =>
    fetchAPI<{ status: string; message: string }>(`/api/recovery-items/${id}/reject`, {
      method: "POST",
    }),
  resetDemoData: () =>
    fetchAPI<{ status: string; message: string }>("/api/demo/reset", {
      method: "POST",
    }),

  // Auth
  me: () => fetchAPI<{ status: string; user: User }>("/api/auth/me"),
  signup: async (data: { email: string; password: string; full_name: string }) => {
    const res = await fetchAPI<{ status: string; user: User; session_token: string }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (typeof window !== "undefined") {
      if (res.session_token) localStorage.setItem("revplug_session_token", res.session_token);
      if (res.user) localStorage.setItem("revplug_user", JSON.stringify(res.user));
    }
    return res;
  },
  login: async (data: { email: string; password: string }) => {
    const res = await fetchAPI<{ status: string; user: User; session_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (typeof window !== "undefined") {
      if (res.session_token) localStorage.setItem("revplug_session_token", res.session_token);
      if (res.user) localStorage.setItem("revplug_user", JSON.stringify(res.user));
    }
    return res;
  },
  logout: async () => {
    try {
      await fetchAPI<{ status: string; message: string }>("/api/auth/logout", {
        method: "POST",
      });
    } finally {
      if (typeof window !== "undefined") {
        localStorage.removeItem("revplug_session_token");
        localStorage.removeItem("revplug_user");
      }
    }
    return { status: "success", message: "Logged out" };
  },
  previewClearRecoveryItem: async (id: string) => {
    return fetchAPI<{
      recovery_item_id: string;
      recovery_case: number;
      decisions_count: number;
      attempts_count: number;
      outcomes_count: number;
      promises_count: number;
      jobs_count: number;
    }>(`/api/recovery-items/${id}/clear-preview`);
  },
  clearRecoveryItem: async (id: string) => {
    return fetchAPI<{
      status: string;
      recovery_item_id: string;
      cleared_counts: Record<string, number>;
    }>(`/api/recovery-items/${id}`, {
      method: "DELETE",
    });
  },

  // Timing Intelligence
  evaluateTiming: (itemId: string) => fetchAPI<TimingEvaluation>(`/api/timing/${itemId}`),
  timingSignals: (itemId: string) => fetchAPI<TimingSignalsResponse>(`/api/timing/${itemId}/signals`),
  rescheduleWait: (itemId: string, scheduledFor: string) =>
    fetchAPI<RescheduleWaitResponse>(`/api/timing/${itemId}/reschedule`, {
      method: "POST",
      body: JSON.stringify({ scheduled_for: scheduledFor } as RescheduleWaitRequest),
    }),

  // Policy Simulator
  policySimulatorCurrent: () =>
    fetchAPI<PolicyConfigSnapshotResponse>("/api/policy-simulator/current"),
  policySimulatorPreview: (payload: {
    proposed_policy: Record<string, any>;
    opportunity_ids?: string[];
  }) =>
    fetchAPI<PolicySimulatorPreviewResponse>("/api/policy-simulator/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface CandidateAction {
  action: string;
  recovery_probability: number;
  intervention_cost: number;
  gross_expected_recovery: number;
  net_expected_recovery: number;
  policy_status: "ALLOWED" | "BLOCKED";
  policy_rule?: string;
  selected?: boolean;
  reason?: string;
}

export interface NaiveBaselineResult {
  case_id: string;
  baseline_mode: string;
  action_taken: string;
  attempts_made: number;
  intervention_cost_minor: number;
  estimated_outcome: string;
  actual_recovered_minor: number;
  unnecessary_intervention: boolean;
  policy_violations: string[];
  has_policy_violations: boolean;
  summary: string;
}

export interface ProductDecisionPayload {
  decision: "RECOVER" | "WAIT" | "ESCALATE" | "STOP";
  reason_code: string;
  reason: string;
  selected_action: string | null;
  policy_status: string;
  requires_human_review: boolean;
  terminal: boolean;
  scheduled_for: string | null;
}

export interface CaseTrace {
  item_id: string;
  status: string;
  classification_method?: string;
  product_decision?: ProductDecisionPayload | null;
  amount_at_risk_minor: number;
  expected_recovery_minor: number;
  verified_recovery_minor: number;
  intervention_cost_minor: number;
  net_recovery_minor: number;
  stopped_reason?: string;
  decision_evidence?: string[];
  alternatives?: any[];
  context_snapshot: {
    hash: string;
    item_id: string;
    failure_category: string;
    amount_minor: number;
    attempt_count?: number;
  };
  diagnosis: Record<string, unknown>;
  ai_recommendation: {
    actor: string;
    selected_action: string | null;
    confidence: number;
    user_safe_reasoning?: string;
    evidence?: string[];
  };
  candidate_actions: CandidateAction[];
  policy_evaluations: {
    allowed: boolean;
    policy_rule: string;
    reason?: string;
  };
  safety_decision: {
    decision: string;
    allowed: boolean;
    reason?: string;
    reason_code?: string;
  };
  execution: {
    status: string;
    executed: boolean;
    action?: string;
    cost_minor?: number;
  };
  settlement_evidence: {
    verified: boolean;
    verified_amount_minor: number;
    method?: string;
  };
  timeline: Array<{
    id: string;
    event_type: string;
    actor: string;
    action: string;
    reason: string | null;
    timestamp: string;
    metadata: Record<string, unknown>;
  }>;
  replay_summary: Record<string, string>;
}

export interface ScientificBenchmarkReport {
  cases_per_seed: number;
  seeds: number[];
  total_seeds: number;
  revplug_wins_vs_safe: number;
  safe_wins_vs_revplug: number;
  naive_wins_vs_revplug: number;
  ties_vs_safe: number;
  revplug_win_rate_pct: number;
  mean_amount_at_risk: number;
  naive_mean_gross: number;
  naive_mean_net: number;
  naive_mean_violations: number;
  safe_mean_gross: number;
  safe_mean_net: number;
  safe_median_net: number;
  safe_std_net: number;
  safe_mean_violations: number;
  revplug_mean_gross: number;
  revplug_mean_net: number;
  revplug_median_net: number;
  revplug_std_net: number;
  revplug_mean_cost: number;
  revplug_mean_violations: number;
  revplug_mean_decision_quality: number;
  gross_lift_pct: number;
  net_lift_pct: number;
  net_lift_vs_naive_pct: number;
  net_diff_mean: number;
  confidence_interval_95_lower: number;
  confidence_interval_95_upper: number;
  best_seed: number | null;
  worst_seed: number | null;
  per_seed_summaries: Array<{
    seed: number;
    cases: number;
    amount_at_risk: number;
    baseline_naive_gross: number;
    baseline_naive_net: number;
    baseline_naive_violations: number;
    baseline_safe_gross: number;
    baseline_safe_net: number;
    baseline_safe_violations: number;
    revplug_gross: number;
    revplug_net: number;
    revplug_cost: number;
    revplug_violations: number;
    revplug_win_vs_safe: boolean;
    revplug_win_vs_naive: boolean;
    tie_vs_safe: boolean;
    decision_quality_score: number;
  }>;
}

export interface Customer360Profile {
  customer_id: string;
  total_lifetime_revenue_minor: number;
  current_amount_at_risk_minor: number;
  current_expected_recovery_minor: number;
  actually_recovered_lifetime_minor: number;
  historical_recovery_rate: number;
  total_cases_count: number;
  failed_payments_count: number;
  successful_recovery_count: number;
  active_cases_count: number;
  customer_value_tier: string;
  previous_opt_outs: boolean;
  current_subscription_state: string;
  recovery_status: string;
  payment_methods_used: string[];
  previous_recovery_actions: string[];
  channel_performance: Array<{
    channel_name: string;
    action_key: string;
    total_attempts: number;
    success_rate_pct: number;
  }>;
  contact_fatigue: {
    contacts_today: number;
    contacts_last_7d: number;
    contacts_last_30d: number;
    daily_limit: number;
    fatigue_risk: string;
  };
  current_issue: {
    item_id: string;
    amount_minor: number;
    root_cause: string;
    failure_reason: string;
    created_at: string | null;
    recommended_action: string;
    expected_net_recovery_minor: number;
  } | null;
  outstanding_invoices: Array<Record<string, any>>;
  promise_to_pay_history: Array<Record<string, any>>;
  recovery_history_timeline: Array<{
    id: string;
    timestamp: string;
    item_id: string;
    action: string;
    reason: string;
    amount_recovered_minor: number;
  }>;
  last_successful_payment_at: string | null;
  last_failed_payment_at: string | null;
  last_failed_reason: string | null;
  // New fields
  customer_decision: string | null;
  customer_decision_reason: string | null;
  active_opportunities: Array<{
    item_id: string;
    amount_minor: number;
    expected_recovery_minor: number;
    decision: string;
    selected_action: string | null;
    policy_state: string;
    execution_status: string;
    root_cause: string;
    incident_affected: boolean;
  }>;
  intervention_outcomes: Array<{
    intervention: string;
    attempts: number;
    successful: number;
    success_rate_pct: number;
  }>;
  policy_constraints: string[];
  active_incident_ids: string[];
  active_incident_count: number;
  recovery_pressure_summary: string;
  why_this_matters: string;
}

export type TimingSignalType =
  | "ACTIVE_PROMISE"
  | "RECENT_ATTEMPT"
  | "CONTACT_LIMIT_WINDOW"
  | "SYSTEMIC_INCIDENT"
  | "HISTORICAL_SUCCESS_WINDOW"
  | "PAYMENT_PATTERN"
  | "RETRY_COOLDOWN"
  | "NO_TIMING_ADVANTAGE"
  | "INSUFFICIENT_TIMING_DATA";

export interface TimingSignal {
  signal_type: TimingSignalType;
  active: boolean;
  reason_code: string;
  reason: string;
  evidence: string[];
  confidence: number;
  policy_status: string;
  blocked_until: string | null;
  metadata: Record<string, unknown>;
}

export interface TimingEvaluation {
  item_id: string;
  timing_decision: "WAIT" | "RECOVER" | "ESCALATE" | "STOP";
  reason_code: string;
  reason: string;
  scheduled_for: string | null;
  signals: TimingSignal[];
  evidence: string[];
  confidence: number;
  policy_status: string;
  wait_count: number;
  max_wait_count: number;
  max_wait_horizon_days: number;
  wait_remaining: number;
  at_max_waits: boolean;
  horizon_exceeded: boolean;
  blocked_until: string | null;
  evaluated_at: string;
  metadata: Record<string, unknown>;
  wait_eligible?: boolean;
  escalation_reason?: string | null;
  scheduler?: RecoverySchedulerSummary;
}

export interface RecoverySchedulerSummary {
  item_id: string;
  wait_count: number;
  wait_remaining: number;
  at_max_waits: boolean;
  last_wait_reason: string | null;
  last_scheduled_for: string | null;
  max_wait_count: number;
  max_wait_horizon_days: number;
  wait_history: Array<{
    wait_count: number;
    reason_code: string;
    reason: string;
    scheduled_for: string | null;
    evaluated_at: string;
    timing_decision: string;
  }>;
}

export interface TimingSignalsResponse {
  item_id: string;
  signals: TimingSignal[];
  evaluated_at: string;
}

export interface RescheduleWaitRequest {
  scheduled_for: string;
}

export interface RescheduleWaitResponse {
  item_id: string;
  rescheduled: boolean;
  evaluation: TimingEvaluation;
  scheduler: RecoverySchedulerSummary;
}

export interface PolicySimulatorPreviewRequest {
  proposed_policy: Record<string, any>;
  opportunity_ids?: string[];
}

export interface PolicySimulatorPreviewResponse {
  simulation_id: string;
  timestamp: string;
  current_policy_version: string;
  proposed_policy_version: string;
  opportunities_evaluated: number;
  unevaluable_count: number;
  unchanged_count: number;
  changed_count: number;
  current_distribution: Record<string, number>;
  proposed_distribution: Record<string, number>;
  current_expected_recovery_minor: number;
  proposed_expected_recovery_minor: number;
  expected_recovery_delta_minor: number;
  current_revenue_at_risk_minor: number;
  proposed_revenue_at_risk_minor: number;
  current_policy_violations: number;
  proposed_policy_violations: number;
  safety_conflicts: Array<{
    opportunity_id: string;
    type: string;
    current_decision: string;
    proposed_decision: string;
    rule: string;
    reason: string;
  }>;
  scope: string;
  opportunity_ids: string[];
  unevaluable_ids: string[];
  decision_diffs: Array<{
    opportunity_id: string;
    changed: boolean;
    change_type: string;
    policy_rule_responsible: string;
    current: {
      decision_type: string;
      allowed: boolean;
      reason_code: string;
      reason: string;
      rule: string;
      proposed_action: string | null;
      next_state: string | null;
      safety_context: Record<string, any>;
    };
    proposed: {
      decision_type: string;
      allowed: boolean;
      reason_code: string;
      reason: string;
      rule: string;
      proposed_action: string | null;
      next_state: string | null;
      safety_context: Record<string, any>;
    };
    financial_context: {
      amount_at_risk_minor: number;
      expected_recovery_minor: number;
    };
    safety_context: {
      current_rule: string;
      proposed_rule: string;
      current_reason_code: string;
      proposed_reason_code: string;
    };
  }>;
  error: string | null;
}

export interface PolicyConfigSnapshotResponse {
  version: string;
  updated_at: string;
  updated_by: string;
  max_retries: number;
  max_contacts_per_24h: number;
  min_expected_net_ev_minor: number;
  max_intervention_cost_minor: number;
  cooldown_retry_minutes: number;
  allowed_channels: string[];
  allowed_payment_methods: string[];
  escalation_thresholds_minor: number;
  failure_categories_blocked: string[];
  systemic_suppression_threshold_pct: number;
  preview_summary?: Record<string, any>;
}


