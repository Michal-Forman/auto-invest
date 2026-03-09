import { useQuery } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("non-ok");
  return res.json() as Promise<{ api: boolean; t212: boolean; coinmate: boolean }>;
}

export function useHealth() {
  const { data, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    staleTime: 5 * 60 * 1000,
  });
  return {
    loading: isLoading,
    api: data?.api ?? false,
    t212: data?.t212 ?? false,
    coinmate: data?.coinmate ?? false,
  };
}
