import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Run } from "@/types";

export function useRuns(limit?: number, status?: string) {
  const [data, setData] = useState<Run[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.getRuns(limit, status)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [limit, status]);

  return { data, loading, error };
}
