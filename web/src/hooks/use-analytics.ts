import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsAllocationItem } from "@/types";

const STALE = 15 * 60 * 1000;

export function useAnalytics() {
  const [runsQ, allocationQ, statusQ, portfolioQ] = useQueries({
    queries: [
      { queryKey: ["analytics", "runs"], queryFn: () => api.getAnalyticsRuns(), staleTime: STALE },
      { queryKey: ["analytics", "allocation"], queryFn: () => api.getAnalyticsAllocation(), staleTime: STALE },
      { queryKey: ["analytics", "status"], queryFn: () => api.getAnalyticsStatus(), staleTime: STALE },
      { queryKey: ["analytics", "portfolioValue"], queryFn: () => api.getPortfolioValue(), staleTime: STALE },
    ],
  });

  const loading = runsQ.isLoading || allocationQ.isLoading || statusQ.isLoading || portfolioQ.isLoading;
  const error = runsQ.isError || allocationQ.isError || statusQ.isError || portfolioQ.isError;

  const allocation: AnalyticsAllocationItem[] | null = allocationQ.data
    ? allocationQ.data.map((item) => ({ date: item.date, ...item.data }))
    : null;

  return {
    runs: runsQ.data ?? null,
    allocation,
    status: statusQ.data ?? null,
    portfolioValue: portfolioQ.data ?? null,
    loading,
    error,
  };
}
