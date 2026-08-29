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
  metadata: Record<string, unknown>;
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
  stopped_reason?: string;
  stopped_rule?: string;
}

export async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${text}`);
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

export const api = {
  health: () => fetchAPI<{ status: string }>("/health"),
  summary: () => fetchAPI<DashboardSummary>("/api/dashboard/summary"),
  items: () => fetchAPI<RecoveryItem[]>("/api/recovery-items"),
  itemDetail: (id: string) => fetchAPI<CaseDetail>(`/api/recovery-items/${id}`),
  evaluations: () => fetchAPI<EvaluationReport>("/api/evaluations"),
  pendingReviews: () => fetchAPI<RecoveryItem[]>("/api/reviews/pending"),
  auditEvents: () => fetchAPI<AuditEvent[]>("/api/audit-events"),
  customerDetail: (id: string) => fetchAPI<CustomerDetail>(`/api/customers/${id}`),
  customers: () => fetchAPI<CustomerDetail[]>("/api/customers"),
  
  // Promises
  promises: () => fetchAPI<PromiseToPay[]>("/api/promises"),
  createPromise: (data: { item_id: string; customer_id: string; amount_minor: number; promised_date: string }) => 
    fetchAPI<PromiseToPay>("/api/promises", { method: "POST", body: JSON.stringify(data) }),
  fulfillPromise: (id: string) => fetchAPI<PromiseToPay>(`/api/promises/${id}/fulfill`, { method: "POST" }),
  breakPromise: (id: string, reason?: string) => fetchAPI<PromiseToPay>(`/api/promises/${id}/break`, { 
    method: "POST", body: JSON.stringify({ reason }) 
  }),
  
  // Batches
  batches: () => fetchAPI<Batch[]>("/api/batches"),
  batchDetail: (id: string) => fetchAPI<Batch>(`/api/batches/${id}`),
  enqueueBatch: (id: string) => fetchAPI<{ status: string; jobs: number }>(`/api/batches/${id}/enqueue`, { method: "POST" }),
  datasets: () => fetchAPI<Array<{ label: string; description: string; item_count: number }>>("/api/demo/datasets"),
  runDataset: (label: string) => fetchAPI<{ status: string; batch_id: string }>(`/api/demo/datasets/${label}/run`, { method: "POST" }),
  
  // Time-Series
  tsRecovered: () => fetchAPI<TimeSeriesPoint[]>("/api/time-series/recovered-by-day"),
  tsRisk: () => fetchAPI<TimeSeriesPoint[]>("/api/time-series/revenue-at-risk-by-day"),
  tsAttempts: () => fetchAPI<TimeSeriesPoint[]>("/api/time-series/attempts-by-day"),
  tsStopped: () => fetchAPI<TimeSeriesPoint[]>("/api/time-series/stopped-by-reason"),
  
  // Lifecycle
  lifecycle: (id: string) => fetchAPI<Lifecycle>(`/api/recovery-items/${id}/lifecycle`),

  triggerDemo: (data: Record<string, unknown>) =>
    fetchAPI<SimulationResult>("/api/demo/payment-failure", {
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
};
