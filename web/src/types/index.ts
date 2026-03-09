export type RunStatus = "CREATED" | "FINISHED" | "FILLED" | "FAILED";
export type OrderStatus = "SUBMITTED" | "FILLED" | "FAILED" | "CANCELLED";
export type Exchange = "T212" | "Coinmate";
export type CapType = "none" | "soft" | "hard";

export interface Run {
  id: string;
  created_at: string;
  status: RunStatus;
  total_czk: number;
  order_count: number;
}

export interface Order {
  id: string;
  run_id: string;
  ticker: string;
  name: string;
  exchange: Exchange;
  czk_amount: number;
  quantity: number | null;
  fill_price: number | null;
  status: OrderStatus;
}

export interface Instrument {
  ticker: string;
  name: string;
  exchange: Exchange;
  cap_type: CapType;
  target_weight: number;
  ath_price: number;
  current_price: number;
  drop_pct: number;
  multiplier: number;
  adjusted_weight: number;
  next_czk: number;
}

export interface Config {
  invest_amount: number;
  t212_weight: number;
  btc_weight: number;
  cron: string;
  environment: "dev" | "prod";
}
