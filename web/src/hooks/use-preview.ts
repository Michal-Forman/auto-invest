import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PreviewItem } from "@/types";

export function usePreview(amount: number) {
  const [data, setData] = useState<PreviewItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    const timer = setTimeout(() => {
      api.getPreview(amount)
        .then(setData)
        .catch(() => setError(true))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [amount]);

  return { data, loading, error };
}
