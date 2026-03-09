import { useEffect, useState } from "react";

interface HealthState {
  loading: boolean;
  api: boolean;
  t212: boolean;
  coinmate: boolean;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({
    loading: true,
    api: false,
    t212: false,
    coinmate: false,
  });

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => {
        if (!res.ok) throw new Error("non-ok");
        return res.json();
      })
      .then((data) => {
        setState({ loading: false, api: data.api, t212: data.t212, coinmate: data.coinmate });
      })
      .catch(() => {
        setState({ loading: false, api: false, t212: false, coinmate: false });
      });
  }, []);

  return state;
}
