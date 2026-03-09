import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Config } from "@/types";

export function useConfig() {
  const [data, setData] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.getConfig()
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
