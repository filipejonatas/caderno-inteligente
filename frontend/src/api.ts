import type {
  AppConfig,
  B2BVisibility,
  CaseItem,
  DashboardData,
  DataQuality,
  FeedbackItem,
  ForecastRecommendationSummary,
  Overview,
  Priority,
  Run,
  ScenarioResult,
  SkuDetail,
} from './types';

const API_ROOT = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_ROOT}${path}`, init);
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor. Verifique se a API está disponível.');
  }

  if (!response.ok) {
    let detail = `A solicitação falhou (${response.status}).`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // The status code remains useful when the response has no JSON body.
    }
    throw new ApiError(detail, response.status);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError('O servidor retornou uma resposta inválida.', response.status);
  }
}

export async function loadDashboard(): Promise<DashboardData> {
  const [overview, priorities, runs, cases, b2b, config, feedback, quality] = await Promise.all([
    request<Overview>('/overview'),
    request<Priority[]>('/priorities'),
    request<Run[]>('/runs'),
    request<CaseItem[]>('/cases'),
    request<B2BVisibility>('/b2b2c/visibility'),
    request<AppConfig>('/config'),
    request<FeedbackItem[]>('/feedback'),
    request<DataQuality>('/data-quality'),
  ]);
  return { overview, priorities, runs, cases, b2b, config, feedback, quality };
}

export const api = {
  forecasts: () => request<ForecastRecommendationSummary[]>('/forecasts'),
  skuDetail: (sku: string) => request<SkuDetail>(`/priorities/${encodeURIComponent(sku)}`),
  createRun: () => request<{ id: number }>('/runs', { method: 'POST' }),
  createCase: (body: Record<string, unknown>) =>
    request<{ id: number }>('/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  updateCase: (id: number, body: Record<string, unknown>) =>
    request<{ status: string }>(`/cases/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  createFeedback: (body: Record<string, unknown>) =>
    request<{ status: string }>('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  scenario: (body: Record<string, unknown>) =>
    request<ScenarioResult>('/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
};
