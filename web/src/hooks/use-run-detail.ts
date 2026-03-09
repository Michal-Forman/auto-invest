import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useRunDetail(id: string | undefined) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.getRunDetail(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
  return { data: data ?? null, loading: isLoading, error: isError };
}
