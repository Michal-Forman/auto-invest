import type {
  Run,
  RunDetail,
  Order,
  Config,
  Instrument,
  AnalyticsRunItem,
  AnalyticsStatusItem,
  HoldingItem,
  PortfolioValueItem,
  WarningItem,
  UserProfile,
} from "@/types";
import { supabase } from "@/lib/supabase";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {};
}

async function apiFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }

  const headers = await getAuthHeaders();
  const res = await fetch(url.toString(), { headers });

  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}

async function apiPost<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const headers = await getAuthHeaders();
  const res = await fetch(url.toString(), { method: "POST", headers });
  if (res.status === 401) { window.location.href = "/login"; throw new Error("Unauthorized"); }
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}

async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
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

  getHealth(): Promise<{ api: boolean; t212: boolean; coinmate: boolean }> {
    return apiFetch<{ api: boolean; t212: boolean; coinmate: boolean }>("/health");
  },

  getConfig(): Promise<Config> {
    return apiFetch<Config>("/config");
  },

  getInstruments(): Promise<Instrument[]> {
    return apiFetch<Instrument[]>("/instruments");
  },

  getAnalyticsRuns(limit?: number): Promise<AnalyticsRunItem[]> {
    const params: Record<string, string> = {};
    if (limit !== undefined) params.limit = String(limit);
    return apiFetch<AnalyticsRunItem[]>("/analytics/runs", params);
  },

  getAnalyticsAllocation(limit?: number): Promise<Array<{ date: string; data: Record<string, number> }>> {
    const params: Record<string, string> = {};
    if (limit !== undefined) params.limit = String(limit);
    return apiFetch<Array<{ date: string; data: Record<string, number> }>>("/analytics/allocation", params);
  },

  getAnalyticsStatus(): Promise<AnalyticsStatusItem[]> {
    return apiFetch<AnalyticsStatusItem[]>("/analytics/status");
  },

  getPortfolioValue(): Promise<PortfolioValueItem[]> {
    return apiFetch<PortfolioValueItem[]>("/analytics/portfolio-value");
  },

  getHoldings(): Promise<HoldingItem[]> {
    return apiFetch<HoldingItem[]>("/analytics/holdings");
  },

  getWarnings(days?: number): Promise<WarningItem[]> {
    const params: Record<string, string> = {};
    if (days !== undefined) params.days = String(days);
    return apiFetch<WarningItem[]>("/analytics/warnings", params);
  },

  getProfile(): Promise<UserProfile> {
    return apiFetch<UserProfile>("/profile");
  },

  updateProfile(data: Partial<UserProfile>): Promise<UserProfile> {
    return apiPatch<UserProfile>("/profile", data);
  },

  placeInvestment(amount: number): Promise<{ run_id: string; total_czk: number }> {
    return apiPost("/invest", { amount: String(amount) });
  },
};
