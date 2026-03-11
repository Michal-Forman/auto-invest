import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useInstruments() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["instruments"],
    queryFn: () => api.getInstruments(),
    staleTime: 15 * 60 * 1000,
  });
  return { data: data ?? null, loading: isLoading, error: isError };
}
