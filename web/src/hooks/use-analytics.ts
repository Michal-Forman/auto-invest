import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalyticsRunItem, AnalyticsAllocationItem, AnalyticsStatusItem, PortfolioValueItem } from "@/types";

interface AnalyticsState {
  runs: AnalyticsRunItem[] | null;
  allocation: AnalyticsAllocationItem[] | null;
  status: AnalyticsStatusItem[] | null;
  portfolioValue: PortfolioValueItem[] | null;
  loading: boolean;
  error: boolean;
}

export function useAnalytics() {
  const [state, setState] = useState<AnalyticsState>({
    runs: null,
    allocation: null,
    status: null,
    portfolioValue: null,
    loading: true,
    error: false,
  });

  useEffect(() => {
    setState((s) => ({ ...s, loading: true, error: false }));
    Promise.all([
      api.getAnalyticsRuns(),
      api.getAnalyticsAllocation(),
      api.getAnalyticsStatus(),
      api.getPortfolioValue(),
    ])
      .then(([runs, rawAllocation, status, portfolioValue]) => {
        const allocation: AnalyticsAllocationItem[] = rawAllocation.map((item) => ({
          date: item.date,
          ...item.data,
        }));
        setState({ runs, allocation, status, portfolioValue, loading: false, error: false });
      })
      .catch(() => setState((s) => ({ ...s, loading: false, error: true })));
  }, []);

  return state;
}
