# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What This Project Does

`auto-invest` is a Python script that runs on a schedule (via cron) to automatically invest a fixed amount of CZK each period across a portfolio of ETFs/stocks (via Trading212) and BTC (via Coinmate). It uses a drop-from-ATH strategy to dynamically increase allocation to instruments that are further below their all-time high.

## Commands

**Format and sort imports:**
```bash
make sort       # sorts imports via scripts/sort_imports.py
make format     # formats with Black
```

**Run the main script:**
```bash
python3 -m core.cron
```

**Run an individual module directly** (each has a `__main__` block for ad-hoc testing):
```bash
python3 -m core.instruments
python3 -m core.executor
python3 -m core.trading212
python3 -m core.coinmate
python3 -m core.db.orders
python3 -m core.db.runs
```

**Type check:**
```bash
python3 -m mypy --explicit-package-bases core/
```

**Environment:** The script reads from `.env.dev` (default) or `.env.prod` (when `ENV=prod`). Required env vars are declared in `core/settings.py`.

## Architecture

### Execution Flow (`core/cron.py`)
1. Initialize `Trading212`, `Coinmate`, `Instruments`, `Executor`
2. Update existing SUBMITTED orders and FINISHED runs in the DB (always runs)
3. If the cron expression matches the current UTC minute AND no run exists today → execute investment:
   - `Instruments.distribute_cash()` → calculates how much CZK to invest in each ticker
   - `Executor.place_orders()` → places market orders on T212 and Coinmate
   - `Run.update_in_db()` → persists the run summary

### Investment Logic (`core/instruments.py`)
- Fetches per-ticker target weights from the T212 pie via API
- Multiplies T212 weights by `T212_WEIGHT` and appends BTC at `BTC_WEIGHT`
- For each ticker, calculates `drop = (ATH - current) / ATH * 100` and derives a multiplier:
  - `"none"` cap: raw multiplier (no limit on boost)
  - `"soft"` cap: drop capped at 75%
  - `"hard"` cap: drop capped at 75% unless ≥90%, in which case multiplier resets to 1× (treats instrument as recovered)
- Normalizes adjusted ratios so distribution sums to `INVEST_AMOUNT` CZK
- Drops instruments below 12.5 CZK; bumps instruments between 12.5–25 CZK up to the 25 CZK minimum

### Exchange Clients
- **`core/trading212.py`** – REST client using Basic Auth. Uses `demo.trading212.com` in dev, `live.trading212.com` in prod. All responses wrapped as `{"req": ..., "res": ..., "err": ...}`. Handles 429 with exponential backoff when paginating order history.
- **`core/coinmate.py`** – REST client using HMAC-SHA256 signature auth. Uses form-encoded POST for private endpoints. Body of private POST requests is redacted in the stored request log.

### Database (`core/db/`)
- **`client.py`** – Supabase client singleton
- **`orders.py`** – Pydantic `Order` model + `OrderUpdate`. Auto-generates SHA-256 idempotency key on creation. Handles matching submitted orders to filled data from T212 and Coinmate history APIs.
- **`runs.py`** – Pydantic `Run` model + `RunUpdate`. A run transitions: `CREATED → FINISHED → FILLED` (all orders filled) or `FAILED` (expired after 14 days without all orders filling). In non-prod, `run_exists_today()` always returns `False`.

### Static Data (`core/instrument_data.py`)
Central registry mapping T212 tickers to Yahoo Finance symbols, currencies, instrument types, display names, and cap type (`none`/`soft`/`hard`). **Add new instruments here** when expanding the portfolio.

### Settings (`core/settings.py`)
Frozen dataclasses `Settings` and `PortfolioSettings` loaded from env at import time. The `settings` singleton is imported throughout the codebase.

## Frontend Conventions

### Number Formatting
Always use `formatNumber(value)` from `@/lib/utils` to display numeric values in the UI. It formats numbers with **non-breaking spaces as thousand separators** (e.g. `1 234 567`). Never use `.toLocaleString()` or `.toFixed(0)` for display values — use `formatNumber` instead. For values with decimals, pass the precision: `formatNumber(value, 2)`.

### Tooltips
Always use an `<Info>` icon (from `lucide-react`) as the tooltip trigger — never dotted underlines or other patterns. The established pattern (used in profile settings) is:

```tsx
import { Info } from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";

<Tooltip>
  <TooltipTrigger>
    <Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" />
  </TooltipTrigger>
  <TooltipContent side="top" className="max-w-xs text-xs">
    Explanation text here
  </TooltipContent>
</Tooltip>
```

Wrap in `<TooltipProvider>` if not already provided by a parent. For table column headers, place the label and `<Info>` icon in an `inline-flex items-center gap-1` wrapper.

## Numeric Precision Standards

All monetary and financial values use `decimal.Decimal` (never `float`). Import helpers from `core.precision`.

| Domain | Decimal places | Helper | Notes |
|--------|---------------|--------|-------|
| CZK amounts | 2 | `quantize_czk()` | All monetary values |
| BTC quantity | 8 | `quantize_btc()` | Crypto standard; used in DB |
| Share quantity (T212 wire) | 3 | `quantize_shares()` | T212 API requirement at wire only; DB stores at 8 dp |
| FX rates & prices | 4 | `quantize_fx()` | Forex standard (e.g. 23.4521 CZK/USD) |
| Internal ratios/multipliers | No quantization | — | Full Decimal precision during computation; never stored as numeric columns |

**Rules:**
- Convert incoming `float` values via `to_decimal()` from `core.precision` (goes through `str()` to avoid float imprecision)
- Quantize only at wire boundaries (exchange API calls) and DB model validators
- `sum()` over Decimal always needs a start value: `sum((x for x in items), Decimal("0"))`
- Tolerance checks use `RATIO_TOLERANCE = Decimal("1E-6")`, not float `1e-6`
- DB columns are PostgreSQL `numeric` (exact). `_convert_decimals()` in `base.py` serializes `Decimal → float` before sending to PostgREST. PostgREST returns `numeric` columns as strings, which Pydantic coerces to `Decimal` automatically.

## Code Style

- Imports are grouped in order: `# Standard library`, `# Third-party`, `# Local` — maintain this convention.
- Use `make sort` + `make format` before committing (the `deploy` target does both).
- Type annotations are required on variables assigned from function/method calls (e.g. `result: Dict[str, Any] = some_func()`). Skip annotations for obvious types (literals, simple assignments) and for short-lived locals where the type is clear from context (e.g. yfinance Ticker objects in a 5-line block). Don't force annotations that create awkward code (e.g. pre-declaring types just to avoid mypy redefinition errors).
- Run `python3 -m mypy . --explicit-package-bases` to type check.
