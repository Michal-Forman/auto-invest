import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useRuns(limit?: number, status?: string) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["runs", limit, status],
    queryFn: () => api.getRuns(limit, status),
    staleTime: 5 * 60 * 1000,
  });
  return { data: data ?? null, loading: isLoading, error: isError };
}
