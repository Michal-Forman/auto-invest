import type { PreviewItem } from "@/types";
import { useInstruments } from "./use-instruments";

const MIN_ORDER = 25;
const DROP_THRESHOLD = 12.5;

export function usePreview(amount: number) {
  const { data: instruments, loading, error } = useInstruments();

  const data: PreviewItem[] | null = instruments
    ? instruments.map((inst) => {
        const raw = amount * inst.adjusted_weight;
        let czk_amount: number;
        let note: string;
        if (raw < DROP_THRESHOLD) {
          czk_amount = 0;
          note = "dropped";
        } else if (raw < MIN_ORDER) {
          czk_amount = MIN_ORDER;
          note = "bumped";
        } else {
          czk_amount = raw;
          note = "normal";
        }
        return {
          ticker: inst.ticker,
          display_name: inst.display_name,
          target_weight: inst.target_weight,
          drop_pct: inst.drop_pct,
          multiplier: inst.multiplier,
          adjusted_weight: inst.adjusted_weight,
          czk_amount,
          note,
        };
      })
    : null;

  return { data, loading, error };
}
