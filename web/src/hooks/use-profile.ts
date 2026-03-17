import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { UserProfile } from "@/types";

export function useProfile() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.getProfile(),
    staleTime: 5 * 60 * 1000,
  });

  const { mutateAsync: updateProfile, isPending: updating } = useMutation({
    mutationFn: (updates: Partial<UserProfile>) => api.updateProfile(updates),
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile"], updated);
      queryClient.invalidateQueries({ queryKey: ["instruments"] });
      queryClient.invalidateQueries({ queryKey: ["config"] });
    },
  });

  return { data: data ?? null, loading: isLoading, error: isError, updateProfile, updating };
}
