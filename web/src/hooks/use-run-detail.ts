import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { RunDetail } from "@/types";

export function useRunDetail(id: string | undefined) {
  const [data, setData] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(false);
    api.getRunDetail(id)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  return { data, loading, error };
}
