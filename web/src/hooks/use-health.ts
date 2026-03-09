import { useEffect, useState } from "react";

type ExchangeStatus = "ok" | "error" | "unknown";

interface HealthState {
  api: "ok" | "error" | "loading";
  t212: ExchangeStatus;
  coinmate: ExchangeStatus;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({
    api: "loading",
    t212: "unknown",
    coinmate: "unknown",
  });

  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    fetch(`${API_BASE}/health`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error("non-ok");
        return res.json();
      })
      .then((data) => {
        if (!alive) return;
        setState({
          api: "ok",
          t212: data.t212 === "ok" ? "ok" : "error",
          coinmate: data.coinmate === "ok" ? "ok" : "error",
        });
      })
      .catch(() => {
        if (!alive) return;
        setState({ api: "error", t212: "unknown", coinmate: "unknown" });
      })
      .finally(() => clearTimeout(timeout));

    return () => {
      alive = false;
      controller.abort();
      clearTimeout(timeout);
    };
  }, []);

  return state;
}
