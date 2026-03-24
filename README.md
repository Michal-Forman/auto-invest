# <img src="core/assets/logo_trans.png" alt="" height="44" valign="middle" /> auto-invest

A self-running investment engine that dollar-cost averages into a multi-asset portfolio — and automatically buys more when markets dip.

---

## What it does

Most retail investors manage their investments across multiple platforms — equities on one broker, crypto on another, each with its own interface, timing, and logic. There's no unified strategy, no automation, and no single source of truth. **auto-invest** solves that.

It is a self-running investment engine that unifies multiple asset classes and exchanges under a single, coherent strategy. On each scheduled run, it deploys a fixed amount of CZK simultaneously across ETFs, equities, and Bitcoin — all governed by the same logic, all triggered at the same time.

You define the strategy once — the weights, the schedule, the risk tolerance per instrument — and the engine handles everything from there. Every asset class moves together, every cycle, without logging into multiple platforms, remembering to rebalance, or timing anything manually.

Every order, fill, fee, exchange rate, and run summary is recorded in a Supabase database, giving you full auditability and a single source of truth for your entire portfolio's activity over time. The engine monitors exchange balances and sends low-balance alerts with QR codes for quick top-ups. When your BTC holdings exceed a configurable threshold, it automatically withdraws to your external wallet. A monthly summary email with anomaly detection (price slippage, high fees, FX drift) closes the loop.

---

## Supported exchanges

| Exchange | Asset classes | Execution |
|----------|--------------|-----------|
| [Trading212](https://www.trading212.com/) | ETFs, equities | Market orders via REST API |
| [Coinmate](https://coinmate.io/) | Bitcoin (BTC/CZK) | Instant buy via REST API |

**Trading212** is used for the full equities and ETF portfolio. Allocations are driven by the weightings defined in your Trading212 Pie, which auto-invest fetches dynamically on each run. Supports both demo and live environments.

**Coinmate** handles Bitcoin purchases, settled directly in CZK — no FX conversion needed. Authentication uses HMAC-SHA256 signing. The architecture is designed to make adding further exchanges straightforward.

---

## Supported instruments

The engine currently supports the following instruments. You don't need to use all of them — pick any subset that fits your strategy. Add or remove instruments in `core/instrument_data.py`.

| Ticker | Name | Type | Currency | Cap |
|--------|------|------|----------|-----|
| `VWCEd_EQ` | Vanguard FTSE All-World UCITS ETF (Acc) | ETF | EUR | `none` |
| `CSPX_EQ` | iShares Core S&P 500 (Acc) | ETF | USD | `none` |
| `EMIMl_EQ` | iShares Core MSCI EM IMI (Acc) | ETF | GBX | `none` |
| `SC0Ud_EQ` | Invesco STOXX Europe 600 Optimised Banks (Acc) | ETF | EUR | `soft` |
| `XNAQl_EQ` | Xtrackers NASDAQ 100 (Acc) | ETF | GBP | `none` |
| `VERGl_EQ` | Vanguard FTSE Developed Europe ex UK (Acc) | ETF | GBP | `none` |
| `BX_US_EQ` | Blackstone | Stock | USD | `soft` |
| `KKR_US_EQ` | KKR & Co | Stock | USD | `soft` |
| `RBOTl_EQ` | iShares Automation & Robotics (Acc) | ETF | USD | `none` |
| `BTC` | Bitcoin | Crypto | CZK | `hard` |

Each entry in `core/instrument_data.py` maps a T212 ticker to its Yahoo Finance symbol, currency, type, display name, and cap mode.

---

## How the strategy works

The allocation isn't static. Each instrument gets a **dynamic multiplier** based on how far its current price is below its all-time high:

```
multiplier = 100 / (100 - drop%)
```

The further an asset has fallen, the larger its share of the investment that cycle. Three cap modes control how aggressive this boost can be:

| Cap type | Behaviour |
|----------|-----------|
| `none`   | No limit — full multiplier applied |
| `soft`   | Drop capped at 75% (max 4× boost) |
| `hard`   | Drop capped at 75%, resets to 1× if drop ≥ 90% |

After adjustment, all ratios are normalized so the total always equals the configured invest amount.

---

## Email notifications

The engine sends five types of email, all with HTML templates and an inline logo:

| Email | Trigger | Content |
|-------|---------|---------|
| **Investment confirmation** | After each successful run | Per-ticker breakdown with CZK amounts, multipliers, and exchanges |
| **Error alert** | On any exception (with or without run context) | Error message, full traceback, run ID if available |
| **Monthly summary** | First run of each month (for the previous month) | Totals per ticker, share %, anomaly warnings, failed runs/orders |
| **Balance alert** | When an exchange balance will run out within N days | Balance, spend/run, depletion date, SPD QR codes for quick top-up |
| **BTC withdrawal confirmation** | After an automatic BTC withdrawal | Amount, fee, CZK value, destination address, exchange ID |

Monthly summaries include **anomaly detection** — each filled order is checked against three thresholds:

- **Price slippage** — fill price deviates >3% from order price
- **High fees** — fee exceeds 0.6% of fill value
- **FX drift** — fill FX rate deviates >2% from submission FX rate

Balance alerts include **SPD QR codes** (Czech payment standard) for each exchange that has deposit account details configured, with a suggested top-up amount based on the next 30 days of scheduled runs.

Email deduplication is handled via the `mails` table — monthly summaries are sent once per period, balance alerts once per day.

---

## BTC withdrawal

When the CZK value of your Coinmate BTC balance exceeds `BTC_WITHDRAWAL_TRESHOLD`, the engine automatically:

1. Withdraws all available BTC to `BTC_EXTERNAL_ADRESS` via the Coinmate API
2. Records the withdrawal in the `btc_withdrawals` table (amount, fee, CZK value, destination, exchange ID)
3. Sends a confirmation email

This runs on every invocation, before the investment logic — so withdrawals happen regardless of whether a new investment is scheduled.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create `.env.dev` (for testing) and `.env.prod` (for live trading):

```env
# Exchange API keys
T212_ID_KEY=
T212_PRIVATE_KEY=
COINMATE_CLIENT_ID=
COINMATE_PUBLIC_KEY=
COINMATE_PRIVATE_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# Portfolio
PIE_ID=                     # Your Trading212 Pie ID
T212_WEIGHT=                # Integer weight for the T212 portion (e.g. 90)
BTC_WEIGHT=                 # Float weight for BTC (e.g. 10.0)
INVEST_AMOUNT=              # Total CZK to invest per run (e.g. 5000.0)
INVEST_INTERVAL=            # Cron expression (e.g. "0 9 1 * *")

# Balance alerts
BALANCE_BUFFER=             # Safety multiplier for spend projection (e.g. 1.1)
BALANCE_ALERT_DAYS=         # Alert if balance runs out within this many days (e.g. 14)

# BTC withdrawal
BTC_WITHDRAWAL_TRESHOLD=    # CZK threshold to trigger auto-withdrawal (e.g. 500000)
BTC_EXTERNAL_ADRESS=        # Destination BTC address for withdrawals

# Email (SMTP)
MY_MAIL=                    # Sender email address
MAIL_RECIPIENT=             # Recipient email address
MAIL_HOST=                  # SMTP host (e.g. smtp.gmail.com)
MAIL_PORT=                  # SMTP SSL port (e.g. 465)
MAIL_PASSWORD=              # SMTP password or app password

# Deposit account details (optional, enables QR codes in balance alerts)
T212_DEPOSIT_ACCOUNT=       # Czech account number (e.g. 19-123456789/0800)
T212_DEPOSIT_VS=            # Variable symbol for T212 deposits
COINMATE_DEPOSIT_ACCOUNT=   # Czech account number for Coinmate
COINMATE_DEPOSIT_VS=        # Variable symbol for Coinmate deposits
```

Switch to production mode by setting `ENV=prod`.

### 3. Set up the database

Apply the migrations in `supabase/migrations/` to your Supabase project. There are 5 migrations covering 4 tables (`orders`, `runs`, `mails`, `btc_withdrawals`).

---

## Running

### Locally

```bash
# Single run (dev mode, uses demo broker)
python3 -m core.cron

# Production (set ENV=prod in your environment or scheduler)
ENV=prod python3 -m core.cron
```

Schedule `python3 -m core.cron` with a system cron job. The script evaluates the `INVEST_INTERVAL` cron expression internally and skips execution if it's not the right time — so it's safe to run it frequently (e.g. every minute).

### GitHub Actions

The production deployment uses two GitHub Actions workflows:

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **Run** | `actions.yaml` | Daily at 09:00 UTC + manual | Executes `python -m core.cron` with production secrets/vars |
| **CI** | `ci.yaml` | Push/PR to `main` + manual | Runs formatting checks, import sorting, mypy, and the full test suite |

---

## Project structure

```
core/                    — All existing Python code (investment engine)
  main.py                — Entry point; orchestrates a full investment run
  instruments.py         — Fetches T212 pie weights, calculates ATH-adjusted ratios
  executor.py            — Places orders on T212 and Coinmate, handles BTC withdrawals
  instrument_data.py     — Static registry: tickers, currencies, names, cap types
  trading212.py          — Trading212 REST API client
  coinmate.py            — Coinmate REST API client (HMAC-SHA256 auth)
  mailer.py              — Email notifications (5 types, HTML templates, QR codes)
  settings.py            — Typed settings loaded from environment variables
  utils.py               — Cron-time checker, balance exhaustion forecasting
  log.py                 — Logging configuration
  db/
    client.py            — Supabase client singleton
    base.py              — Shared Pydantic base model with DB helpers
    orders.py            — Order model, DB persistence, fill reconciliation
    runs.py              — Run model, lifecycle management (CREATED→FINISHED→FILLED)
    mails.py             — Mail record model, deduplication queries
    btc_withdrawals.py   — BTC withdrawal model and DB persistence
  templates/emails/
    investment_confirmation.html
    error_alert.html
    monthly_summary.html
    balance_alert.html
    btc_withdrawal_confirmation.html
  assets/
    logo_trans.png       — Logo (transparent background, used in README)
    logo_white.png       — Logo (white background, used in emails)
api/                     — Placeholder for future FastAPI backend
web/                     — Placeholder for future Vite+React frontend
scripts/
  sort_imports.py        — Custom import sorter (isort + Black compatible)
tests/
  unit/                  — Unit tests (mocked DB and API calls)
  integration/           — Integration tests (full flow with mocked externals)
.github/workflows/
  ci.yaml                — CI pipeline (formatting, types, tests)
  actions.yaml           — Production runner (daily scheduled execution)
```

---

## Development

### Makefile targets

```bash
make format             # Format with Black
make sort               # Sort imports via scripts/sort_imports.py
make typecheck          # Type check with mypy
make test-unit          # Run unit tests
make test-integration   # Run integration tests (verbose)
make test               # typecheck + test-unit + test-integration
make deploy             # format + sort + test, then commit and push
```

### Test suite

The project has 378 tests (unit + integration) using `pytest`, `pytest-mock`, and `freezegun`. Tests mock all external dependencies (Supabase, T212 API, Coinmate API, SMTP) and cover the full investment lifecycle, order reconciliation, email generation, BTC withdrawals, and edge cases.

```bash
# Run everything
make test

# Run just unit tests
python3 -m pytest tests/unit/ -v

# Run a specific test file
python3 -m pytest tests/unit/test_instruments_pure.py -v
```

### Numeric precision

All monetary and financial values in the Python codebase use `decimal.Decimal` — never `float`. This avoids IEEE 754 rounding errors (e.g. `0.1 + 0.2 ≠ 0.3`) in code that places real orders.

| Domain | Decimal places | Example |
|--------|---------------|---------|
| CZK amounts | 2 | `5 000.00 CZK` |
| BTC quantity | 8 | `0.00123456 BTC` |
| Share quantity | 3 | `2.500 shares` (T212 wire only) |
| FX rates & prices | 4 | `23.4521 CZK/USD` |
| Internal ratios / multipliers | unrounded | used only in intermediate maths |

Helpers live in `core/precision.py`: `to_decimal()`, `quantize_czk()`, `quantize_btc()`, `quantize_shares()`, `quantize_fx()`. Quantization happens only at exchange API call boundaries and DB model validators — internal calculations keep full Decimal precision throughout.

---

### Ad-hoc testing

Each module has a `__main__` block for quick manual testing:

```bash
python3 -m core.instruments   # Test ratio calculation
python3 -m core.trading212    # Test T212 API calls
python3 -m core.coinmate      # Test Coinmate API calls
python3 -m core.mailer        # Send test emails
python3 -m core.db.orders     # Test order persistence
```

---

## CI/CD

### CI (`ci.yaml`)

Runs on every push and pull request to `main`. Steps:

1. Install dependencies from `requirements-dev.txt`
2. Check formatting with `black --check`
3. Check import sorting (run sorter, then `git diff --exit-code`)
4. Type check with `mypy`
5. Run unit tests
6. Run integration tests

### Production runner (`actions.yaml`)

Runs daily at 09:00 UTC (and on manual dispatch). Injects all secrets and environment variables from the GitHub `Main` environment, then executes `python -m core.cron` with `ENV=prod`.

---

## Database

Four tables in Supabase, managed via 5 migrations:

| Table | Purpose |
|-------|---------|
| `orders` | Every order placed (T212 + Coinmate). Tracks status from SUBMITTED → FILLED, fill prices, fees, FX rates. Idempotency key (SHA-256) prevents duplicates. |
| `runs` | One row per investment run. Lifecycle: CREATED → FINISHED → FILLED (all orders filled) or FAILED (expired after 14 days). |
| `mails` | Record of every email sent. Used for deduplication — monthly summaries once per period, balance alerts once per day. |
| `btc_withdrawals` | Each automatic BTC withdrawal: amount, fee, CZK value, destination address, exchange ID, timestamp. |

---

## Collaborating

This project is proprietary, but that doesn't mean the door is closed. If you have ideas for new exchanges, strategies, or improvements — or if you're simply curious about the project — feel free to reach out. Collaboration proposals, feedback, and technical discussions are genuinely welcome. The license protects the code; it doesn't mean I'm not open to discusion.

Interested in contributing or building on top of this? Reach out first — any collaboration requires explicit written agreement (see [LICENSE](LICENSE)).

### Contact

- Email: [michal.forman@proton.me](mailto:michal.forman@proton.me)
- LinkedIn: [linkedin.com/in/michal-forman](https://www.linkedin.com/in/michal-forman/)

### Branching conventions

All work must happen on a dedicated branch. Branch names follow this structure:

| Prefix | Use for |
|--------|---------|
| `feature/` | New functionality or instruments |
| `fix/` | Bug fixes and corrections |
| `refactor/` | Code restructuring without behaviour change |
| `chore/` | Dependency updates, tooling, config changes |
| `docs/` | Documentation only |

Examples: `feature/add-degiro-client`, `fix/coinmate-nonce-overflow`, `refactor/make-code-prettier`

Direct commits to `main` are not permitted. All changes go through a branch and must be reviewed before merging.

---

## License

This project is proprietary software. See [LICENSE](LICENSE) for terms.

Copyright © 2026 Michal Forman. All rights reserved.
