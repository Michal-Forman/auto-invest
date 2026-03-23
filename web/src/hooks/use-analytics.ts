import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsAllocationItem, WarningItem } from "@/types";

const STALE = 15 * 60 * 1000;

export function useAnalytics() {
  const [runsQ, allocationQ, statusQ, portfolioQ, warningsQ] = useQueries({
    queries: [
      { queryKey: ["analytics", "runs"], queryFn: () => api.getAnalyticsRuns(), staleTime: STALE },
      { queryKey: ["analytics", "allocation"], queryFn: () => api.getAnalyticsAllocation(), staleTime: STALE },
      { queryKey: ["analytics", "status"], queryFn: () => api.getAnalyticsStatus(), staleTime: STALE },
      { queryKey: ["analytics", "portfolioValue"], queryFn: () => api.getPortfolioValue(), staleTime: STALE },
      { queryKey: ["analytics", "warnings"], queryFn: () => api.getWarnings(30), staleTime: STALE },
    ],
  });

  const loading = runsQ.isLoading || allocationQ.isLoading || statusQ.isLoading || portfolioQ.isLoading || warningsQ.isLoading;
  const error = runsQ.isError || allocationQ.isError || statusQ.isError || portfolioQ.isError || warningsQ.isError;

  const allocation: AnalyticsAllocationItem[] | null = allocationQ.data
    ? allocationQ.data.map((item) => ({ date: item.date, ...item.data }))
    : null;

  return {
    runs: runsQ.data ?? null,
    allocation,
    status: statusQ.data ?? null,
    portfolioValue: portfolioQ.data ?? null,
    warnings: warningsQ.data ?? null as WarningItem[] | null,
    loading,
    error,
  };
}
