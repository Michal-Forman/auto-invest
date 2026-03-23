import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useHoldings() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["holdings"],
    queryFn: () => api.getHoldings(),
    staleTime: 15 * 60 * 1000,
  });
  return { data: data ?? null, loading: isLoading, error: isError };
}
