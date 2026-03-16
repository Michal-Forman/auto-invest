import type { Run, Order, Instrument, Config } from "../types";

export const mockConfig: Config = {
  invest_amount: 5000,
  t212_weight: 0.8,
  btc_weight: 0.2,
  invest_interval: "0 9 * * 1",
  environment: "dev",
  instruments: [],
};

export const mockRuns: Run[] = [
  { id: "r01", created_at: "2026-03-02T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r02", created_at: "2026-02-23T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r03", created_at: "2026-02-16T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r04", created_at: "2026-02-09T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 7 },
  { id: "r05", created_at: "2026-02-02T09:00:00Z", status: "FAILED", total_czk: 0, order_count: 0 },
  { id: "r06", created_at: "2026-01-26T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r07", created_at: "2026-01-19T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r08", created_at: "2026-01-12T09:00:00Z", status: "FINISHED", total_czk: 5000, order_count: 8 },
  { id: "r09", created_at: "2026-01-05T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r10", created_at: "2025-12-29T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r11", created_at: "2025-12-22T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
  { id: "r12", created_at: "2025-12-15T09:00:00Z", status: "FAILED", total_czk: 0, order_count: 0 },
  { id: "r13", created_at: "2025-12-08T09:00:00Z", status: "FILLED", total_czk: 5000, order_count: 8 },
];

export const mockOrders: Order[] = [
  // r01
  { id: "o001", run_id: "r01", ticker: "VWCE", display_name:"Vanguard FTSE All-World", exchange: "T212", czk_amount: 1200, quantity: 3.2, fill_price: 375.0, status: "FILLED" },
  { id: "o002", run_id: "r01", ticker: "IWDA", display_name:"iShares Core MSCI World", exchange: "T212", czk_amount: 900, quantity: 8.1, fill_price: 111.1, status: "FILLED" },
  { id: "o003", run_id: "r01", ticker: "EIMI", display_name:"iShares Core MSCI EM IMI", exchange: "T212", czk_amount: 450, quantity: 12.0, fill_price: 37.5, status: "FILLED" },
  { id: "o004", run_id: "r01", ticker: "IUSN", display_name:"iShares MSCI World Small Cap", exchange: "T212", czk_amount: 380, quantity: 22.4, fill_price: 16.96, status: "FILLED" },
  { id: "o005", run_id: "r01", ticker: "CSPX", display_name:"iShares Core S&P 500", exchange: "T212", czk_amount: 620, quantity: 1.4, fill_price: 442.86, status: "FILLED" },
  { id: "o006", run_id: "r01", ticker: "IQQH", display_name:"iShares Global Clean Energy", exchange: "T212", czk_amount: 250, quantity: 18.5, fill_price: 13.51, status: "FILLED" },
  { id: "o007", run_id: "r01", ticker: "2B7K", display_name:"iShares $ Corp Bond ESG", exchange: "T212", czk_amount: 200, quantity: 5.0, fill_price: 40.0, status: "FILLED" },
  { id: "o008", run_id: "r01", ticker: "BTC", display_name:"Bitcoin", exchange: "Coinmate", czk_amount: 1000, quantity: 0.00098, fill_price: 2550000, status: "FILLED" },
  // r02
  { id: "o009", run_id: "r02", ticker: "VWCE", display_name:"Vanguard FTSE All-World", exchange: "T212", czk_amount: 1150, quantity: 3.1, fill_price: 370.97, status: "FILLED" },
  { id: "o010", run_id: "r02", ticker: "IWDA", display_name:"iShares Core MSCI World", exchange: "T212", czk_amount: 880, quantity: 7.9, fill_price: 111.39, status: "FILLED" },
  { id: "o011", run_id: "r02", ticker: "EIMI", display_name:"iShares Core MSCI EM IMI", exchange: "T212", czk_amount: 470, quantity: 12.5, fill_price: 37.6, status: "FILLED" },
  { id: "o012", run_id: "r02", ticker: "IUSN", display_name:"iShares MSCI World Small Cap", exchange: "T212", czk_amount: 360, quantity: 21.2, fill_price: 16.98, status: "FILLED" },
  { id: "o013", run_id: "r02", ticker: "CSPX", display_name:"iShares Core S&P 500", exchange: "T212", czk_amount: 600, quantity: 1.35, fill_price: 444.44, status: "FILLED" },
  { id: "o014", run_id: "r02", ticker: "IQQH", display_name:"iShares Global Clean Energy", exchange: "T212", czk_amount: 280, quantity: 20.4, fill_price: 13.73, status: "FILLED" },
  { id: "o015", run_id: "r02", ticker: "2B7K", display_name:"iShares $ Corp Bond ESG", exchange: "T212", czk_amount: 260, quantity: 6.5, fill_price: 40.0, status: "FILLED" },
  { id: "o016", run_id: "r02", ticker: "BTC", display_name:"Bitcoin", exchange: "Coinmate", czk_amount: 1000, quantity: 0.00101, fill_price: 2475247, status: "FILLED" },
  // r08 (FINISHED — some not yet filled)
  { id: "o017", run_id: "r08", ticker: "VWCE", display_name:"Vanguard FTSE All-World", exchange: "T212", czk_amount: 1200, quantity: 3.3, fill_price: 363.64, status: "FILLED" },
  { id: "o018", run_id: "r08", ticker: "IWDA", display_name:"iShares Core MSCI World", exchange: "T212", czk_amount: 900, quantity: 8.2, fill_price: 109.76, status: "FILLED" },
  { id: "o019", run_id: "r08", ticker: "EIMI", display_name:"iShares Core MSCI EM IMI", exchange: "T212", czk_amount: 450, quantity: null, fill_price: null, status: "SUBMITTED" },
  { id: "o020", run_id: "r08", ticker: "CSPX", display_name:"iShares Core S&P 500", exchange: "T212", czk_amount: 620, quantity: null, fill_price: null, status: "SUBMITTED" },
  { id: "o021", run_id: "r08", ticker: "BTC", display_name:"Bitcoin", exchange: "Coinmate", czk_amount: 1000, quantity: 0.00109, fill_price: 2293578, status: "FILLED" },
];

export const mockInstruments: Instrument[] = [
  {
    ticker: "VWCE",
    display_name:"Vanguard FTSE All-World",
    exchange: "T212",
    cap_type: "soft",
    currency: "USD",
    instrument_type: "ETF",
    target_weight: 0.30,
    ath_price: 118.5,
    current_price: 112.3,
    drop_pct: 5.2,
    multiplier: 1.07,
    adjusted_weight: 0.285,
    next_czk: 1185,
  },
  {
    ticker: "IWDA",
    display_name:"iShares Core MSCI World",
    exchange: "T212",
    cap_type: "soft",
    currency: "USD",
    instrument_type: "ETF",
    target_weight: 0.20,
    ath_price: 95.2,
    current_price: 87.4,
    drop_pct: 8.2,
    multiplier: 1.09,
    adjusted_weight: 0.191,
    next_czk: 880,
  },
  {
    ticker: "CSPX",
    display_name:"iShares Core S&P 500",
    exchange: "T212",
    cap_type: "none",
    currency: "USD",
    instrument_type: "ETF",
    target_weight: 0.15,
    ath_price: 520.0,
    current_price: 445.0,
    drop_pct: 14.4,
    multiplier: 1.16,
    adjusted_weight: 0.153,
    next_czk: 710,
  },
  {
    ticker: "EIMI",
    display_name:"iShares Core MSCI EM IMI",
    exchange: "T212",
    cap_type: "soft",
    currency: "USD",
    instrument_type: "ETF",
    target_weight: 0.10,
    ath_price: 42.1,
    current_price: 32.5,
    drop_pct: 22.8,
    multiplier: 1.30,
    adjusted_weight: 0.114,
    next_czk: 510,
  },
  {
    ticker: "IUSN",
    display_name:"iShares MSCI World Small Cap",
    exchange: "T212",
    cap_type: "soft",
    currency: "USD",
    instrument_type: "ETF",
    target_weight: 0.08,
    ath_price: 19.8,
    current_price: 16.2,
    drop_pct: 18.2,
    multiplier: 1.22,
    adjusted_weight: 0.085,
    next_czk: 390,
  },
  {
    ticker: "IQQH",
    display_name:"iShares Global Clean Energy",
    exchange: "T212",
    cap_type: "hard",
    currency: "USD",
    instrument_type: "ETF",
    target_weight: 0.05,
    ath_price: 35.6,
    current_price: 12.9,
    drop_pct: 63.8,
    multiplier: 1.0,
    adjusted_weight: 0.044,
    next_czk: 175,
  },
  {
    ticker: "2B7K",
    display_name:"iShares $ Corp Bond ESG",
    exchange: "T212",
    cap_type: "none",
    currency: "USD",
    instrument_type: "ETF",
    target_weight: 0.04,
    ath_price: 41.5,
    current_price: 40.1,
    drop_pct: 3.4,
    multiplier: 1.04,
    adjusted_weight: 0.036,
    next_czk: 150,
  },
  {
    ticker: "BTC",
    display_name:"Bitcoin",
    exchange: "Coinmate",
    cap_type: "none",
    currency: "CZK",
    instrument_type: "Crypto",
    target_weight: 0.20,
    ath_price: 2850000,
    current_price: 2540000,
    drop_pct: 10.9,
    multiplier: 1.12,
    adjusted_weight: 0.196,
    next_czk: 1000,
  },
];

// Derived: chart-friendly run history for analytics
export const mockRunHistory = mockRuns
  .filter((r) => r.status === "FILLED" || r.status === "FINISHED")
  .slice(0, 10)
  .reverse()
  .map((r) => ({
    date: r.created_at.slice(0, 10),
    czk: r.total_czk,
  }));

// Per-instrument allocation over last runs (for stacked area)
export const mockAllocationHistory = mockRuns
  .filter((r) => r.status === "FILLED")
  .slice(0, 8)
  .reverse()
  .map((r) => ({
    date: r.created_at.slice(0, 10),
    VWCE: 24,
    IWDA: 18,
    CSPX: 14,
    EIMI: 10,
    IUSN: 8,
    IQQH: 6,
    "2B7K": 5,
    BTC: 15,
  }));

// Drop-from-ATH history per instrument
export const mockDropHistory = mockRuns
  .filter((r) => r.status === "FILLED")
  .slice(0, 8)
  .reverse()
  .map((r, i) => ({
    date: r.created_at.slice(0, 10),
    VWCE: 3 + i * 0.3,
    IWDA: 6 + i * 0.4,
    CSPX: 10 + i * 0.8,
    EIMI: 18 + i * 0.6,
    IQQH: 55 + i * 1.5,
    BTC: 8 + i * 0.5,
  }));

// Cumulative portfolio value over time
export const mockPortfolioGrowth = (() => {
  const sorted = [...mockRuns].reverse(); // oldest first
  let cumulative = 0;
  return sorted.map((r) => {
    cumulative += r.total_czk;
    return { date: r.created_at.slice(0, 10), total: cumulative };
  });
})();

// Status breakdown for pie
export const mockStatusBreakdown = [
  { status: "FILLED", count: 10 },
  { status: "FINISHED", count: 1 },
  { status: "FAILED", count: 2 },
  { status: "CREATED", count: 0 },
];
