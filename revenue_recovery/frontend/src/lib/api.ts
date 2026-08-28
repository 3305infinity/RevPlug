const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface DashboardSummary {
  total_items: number;
  total_amount_minor: number;
  recovered_count: number;
  recovered_amount_minor: number;
  expected_recovery_value: number;
  recovery_rate: number;
  escalated_count: number;
  pending_count: number;
  executed_count: number;
  attempts_total: number;
  attempts_successful: number;
  attempts_failed: number;
  decisions_total: number;
  policy_allowed: number;
  policy_denied: number;
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
  expected_recovery_value: number | null;
  metadata: Record<string, unknown>;
}

export interface CaseDetail extends RecoveryItem {
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
  audit_events: Array<{
    id: string;
    recovery_item_id: string;
    actor: string;
    action: string;
    reason: string | null;
    metadata: Record<string, unknown>;
    timestamp: string;
  }>;
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
  policy_allowed?: boolean;
  execution_status?: string;
  attempt_number?: number;
  retry_scheduled?: boolean;
  escalation_reason?: string;
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

export const api = {
  health: () => fetchAPI<{ status: string }>("/health"),
  summary: () => fetchAPI<DashboardSummary>("/api/dashboard/summary"),
  items: () => fetchAPI<RecoveryItem[]>("/api/recovery-items"),
  itemDetail: (id: string) => fetchAPI<CaseDetail>(`/api/recovery-items/${id}`),
  evaluations: () => fetchAPI<EvaluationReport>("/api/evaluations"),
  pendingReviews: () => fetchAPI<RecoveryItem[]>("/api/reviews/pending"),
  triggerDemo: (data: Record<string, unknown>) =>
    fetchAPI<SimulationResult>("/api/demo/payment-failure", {
      method: "POST",
      body: JSON.stringify(data),
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
};
