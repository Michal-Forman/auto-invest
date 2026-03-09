import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalyticsRunItem, AnalyticsAllocationItem, AnalyticsStatusItem } from "@/types";

interface AnalyticsState {
  runs: AnalyticsRunItem[] | null;
  allocation: AnalyticsAllocationItem[] | null;
  status: AnalyticsStatusItem[] | null;
  loading: boolean;
  error: boolean;
}

export function useAnalytics() {
  const [state, setState] = useState<AnalyticsState>({
    runs: null,
    allocation: null,
    status: null,
    loading: true,
    error: false,
  });

  useEffect(() => {
    setState((s) => ({ ...s, loading: true, error: false }));
    Promise.all([api.getAnalyticsRuns(), api.getAnalyticsAllocation(), api.getAnalyticsStatus()])
      .then(([runs, rawAllocation, status]) => {
        const allocation: AnalyticsAllocationItem[] = rawAllocation.map((item) => ({
          date: item.date,
          ...item.data,
        }));
        setState({ runs, allocation, status, loading: false, error: false });
      })
      .catch(() => setState((s) => ({ ...s, loading: false, error: true })));
  }, []);

  return state;
}
