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
  display_name: string;
  exchange: Exchange;
  czk_amount: number;
  quantity: number | null;
  fill_price: number | null;
  status: OrderStatus;
}

export interface RunDetail extends Run {
  orders: Order[];
}

export interface Instrument {
  ticker: string;
  display_name: string;
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

export interface InstrumentRegistryItem {
  ticker: string;
  display_name: string;
  yahoo_symbol: string;
  currency: string;
  instrument_type: string;
  cap_type: CapType;
}

export interface Config {
  invest_amount: number;
  t212_weight: number;
  btc_weight: number;
  invest_interval: string;
  environment: "dev" | "prod";
  instruments: InstrumentRegistryItem[];
}

export interface PreviewItem {
  ticker: string;
  display_name: string;
  target_weight: number;
  drop_pct: number;
  multiplier: number;
  adjusted_weight: number;
  czk_amount: number;
  note: string;
}

export interface AnalyticsRunItem {
  date: string;
  czk: number;
  status: string;
}

export interface AnalyticsAllocationItem {
  date: string;
  [ticker: string]: string | number;
}

export interface AnalyticsStatusItem {
  status: string;
  count: number;
}

export interface PortfolioValueItem {
  date: string;
  value: number;
}

export interface UserProfile {
  t212_id_key: string;
  t212_private_key: string;
  coinmate_client_id: number | null;
  coinmate_public_key: string;
  coinmate_private_key: string;
  pie_id: number | null;
  t212_weight: number;
  btc_weight: number;
  invest_amount: number;
  invest_interval: string;
  balance_buffer: number;
  balance_alert_days: number;
  btc_withdrawal_treshold: number;
  btc_external_adress: string;
  t212_deposit_account: string | null;
  t212_deposit_vs: string | null;
  coinmate_deposit_account: string | null;
  coinmate_deposit_vs: string | null;
  cron_enabled: boolean;
  notifications_enabled: boolean;
}
