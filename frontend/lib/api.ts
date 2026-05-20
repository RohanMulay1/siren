const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API}${path}`, { next: { revalidate: 0 } });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T | null> {
  try {
    const r = await fetch(`${API}${path}`, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export interface HealthResponse {
  status: string;
  qdrant_incidents: number;
  environment: string;
  version: string;
}

export interface Incident {
  incident_id: string;
  severity: 'P1' | 'P2' | 'P3' | 'P4';
  affected_service: string;
  workflow_status: string;
  root_cause: string | null;
  created_at: string | null;
  resolved_at: string | null;
}

export interface ActionPlan {
  action_id: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  classification: 'READ' | 'REVERSIBLE' | 'DESTRUCTIVE';
  rationale: string;
  approved: boolean | null;
}

export interface IncidentState {
  incident_id: string;
  severity: string;
  affected_service: string;
  incident_summary: string;
  workflow_status: string;
  root_cause: string | null;
  root_cause_confidence: number;
  investigation_iterations: number;
  action_plan: ActionPlan[];
  current_action_index: number;
  remediation_verified: boolean;
  postmortem_id: string | null;
  qdrant_vector_id: string | null;
}

export interface MttrPoint {
  created_at: string;
  mttr: number;
  service: string;
  severity: string;
  category: string;
  description: string;
}

export interface MemoryStats {
  total: number;
  categories: Record<string, number>;
  services: Record<string, number>;
  severities: Record<string, number>;
  mttr_series: MttrPoint[];
}
