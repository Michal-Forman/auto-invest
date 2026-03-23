import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsAllocationItem, WarningItem } from "@/types";

const STALE = 15 * 60 * 1000;

export function useAnalytics() {
  const [runsQ, allocationQ, statusQ, portfolioQ, warningsQ, profitLossQ, portfolioHistoryQ, strategyComparisonQ, holdingsRatioQ] = useQueries({
    queries: [
      { queryKey: ["analytics", "runs"], queryFn: () => api.getAnalyticsRuns(), staleTime: STALE },
      { queryKey: ["analytics", "allocation"], queryFn: () => api.getAnalyticsAllocation(), staleTime: STALE },
      { queryKey: ["analytics", "status"], queryFn: () => api.getAnalyticsStatus(), staleTime: STALE },
      { queryKey: ["analytics", "portfolioValue"], queryFn: () => api.getPortfolioValue(), staleTime: STALE },
      { queryKey: ["analytics", "warnings"], queryFn: () => api.getWarnings(30), staleTime: STALE },
      { queryKey: ["analytics", "profitLoss"], queryFn: () => api.getProfitLoss(), staleTime: STALE },
      { queryKey: ["analytics", "portfolioHistory"], queryFn: () => api.getPortfolioHistory(), staleTime: STALE },
      { queryKey: ["analytics", "strategyComparison"], queryFn: () => api.getStrategyComparison(), staleTime: STALE },
      { queryKey: ["analytics", "holdingsRatio"], queryFn: () => api.getHoldingsRatio(), staleTime: STALE },
    ],
  });

  const loading = runsQ.isLoading || allocationQ.isLoading || statusQ.isLoading || portfolioQ.isLoading || warningsQ.isLoading;
  const error = runsQ.isError || allocationQ.isError || statusQ.isError || portfolioQ.isError || warningsQ.isError || profitLossQ.isError || portfolioHistoryQ.isError || strategyComparisonQ.isError || holdingsRatioQ.isError;

  const allocation: AnalyticsAllocationItem[] | null = allocationQ.data
    ? allocationQ.data.map((item) => ({ date: item.date, ...item.data }))
    : null;

  return {
    runs: runsQ.data ?? null,
    allocation,
    status: statusQ.data ?? null,
    portfolioValue: portfolioQ.data ?? null,
    warnings: warningsQ.data ?? null as WarningItem[] | null,
    profitLoss: profitLossQ.data ?? null,
    portfolioHistory: portfolioHistoryQ.data ?? null,
    strategyComparison: strategyComparisonQ.data ?? null,
    holdingsRatio: holdingsRatioQ.data ?? null,
    profitLossLoading: profitLossQ.isLoading,
    portfolioHistoryLoading: portfolioHistoryQ.isLoading,
    strategyComparisonLoading: strategyComparisonQ.isLoading,
    holdingsRatioLoading: holdingsRatioQ.isLoading,
    loading,
    error,
  };
}
