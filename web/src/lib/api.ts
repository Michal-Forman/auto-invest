import type {
  Run,
  RunDetail,
  Order,
  Config,
  Instrument,
  PreviewItem,
  AnalyticsRunItem,
  AnalyticsAllocationItem,
  AnalyticsStatusItem,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function apiFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  getRuns(limit?: number, status?: string): Promise<Run[]> {
    const params: Record<string, string> = {};
    if (limit !== undefined) params.limit = String(limit);
    if (status !== undefined) params.status = status;
    return apiFetch<Run[]>("/runs", params);
  },

  getRunDetail(id: string): Promise<RunDetail> {
    return apiFetch<RunDetail>(`/runs/${id}`);
  },

  getOrders(ticker?: string, exchange?: string, status?: string): Promise<Order[]> {
    const params: Record<string, string> = {};
    if (ticker !== undefined) params.ticker = ticker;
    if (exchange !== undefined) params.exchange = exchange;
    if (status !== undefined) params.status = status;
    return apiFetch<Order[]>("/orders", params);
  },

  getConfig(): Promise<Config> {
    return apiFetch<Config>("/config");
  },

  getInstruments(): Promise<Instrument[]> {
    return apiFetch<Instrument[]>("/instruments");
  },

  getPreview(amount?: number): Promise<PreviewItem[]> {
    const params: Record<string, string> = {};
    if (amount !== undefined) params.amount = String(amount);
    return apiFetch<PreviewItem[]>("/preview", params);
  },

  getAnalyticsRuns(limit?: number): Promise<AnalyticsRunItem[]> {
    const params: Record<string, string> = {};
    if (limit !== undefined) params.limit = String(limit);
    return apiFetch<AnalyticsRunItem[]>("/analytics/runs", params);
  },

  getAnalyticsAllocation(limit?: number): Promise<Array<{ date: string; data: Record<string, number> }>>  {
    const params: Record<string, string> = {};
    if (limit !== undefined) params.limit = String(limit);
    return apiFetch<Array<{ date: string; data: Record<string, number> }>>("/analytics/allocation", params);
  },

  getAnalyticsStatus(): Promise<AnalyticsStatusItem[]> {
    return apiFetch<AnalyticsStatusItem[]>("/analytics/status");
  },
};
