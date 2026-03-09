import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Instrument } from "@/types";

export function useInstruments() {
  const [data, setData] = useState<Instrument[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.getInstruments()
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
