import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useHealth() {
  const { data, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    staleTime: 5 * 60 * 1000,
  });
  return {
    loading: isLoading,
    api: data?.api ?? false,
    t212: data?.t212 ?? false,
    coinmate: data?.coinmate ?? false,
  };
}
