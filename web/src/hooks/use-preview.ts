import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function usePreview(amount: number) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["preview", amount],
    queryFn: () => api.getPreview(amount),
    staleTime: 15 * 60 * 1000,
  });
  return { data: data ?? null, loading: isLoading, error: isError };
}
