import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useConfig() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["config"],
    queryFn: () => api.getConfig(),
    staleTime: 60 * 60 * 1000,
  });
  return { data: data ?? null, loading: isLoading, error: isError };
}
