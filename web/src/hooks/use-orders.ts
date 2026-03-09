import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useOrders() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api.getOrders(),
    staleTime: 5 * 60 * 1000,
  });
  return { data: data ?? null, loading: isLoading, error: isError };
}
