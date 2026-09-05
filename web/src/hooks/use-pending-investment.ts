import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function usePendingInvestment() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["pending-investment"],
    queryFn: () => api.getPendingInvestment(),
    staleTime: 60 * 1000,
  });

  const { mutateAsync: registerPending, isPending: registering } = useMutation({
    mutationFn: (amount: number) => api.registerPendingInvestment(amount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending-investment"] });
    },
  });

  const { mutateAsync: cancelPending, isPending: cancelling } = useMutation({
    mutationFn: () => api.cancelPendingInvestment(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending-investment"] });
    },
  });

  return {
    data: data ?? null,
    loading: isLoading,
    error: isError,
    registerPending,
    registering,
    cancelPending,
    cancelling,
  };
}
