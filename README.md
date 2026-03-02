# auto-invest

> A self-running investment engine that dollar-cost averages into a multi-asset portfolio — and automatically buys more when markets dip.

---

## What it does

Most retail investors manage their investments across multiple platforms — equities on one broker, crypto on another, each with its own interface, timing, and logic. There's no unified strategy, no automation, and no single source of truth. **auto-invest** solves that.

It is a self-running investment engine that unifies multiple asset classes and exchanges under a single, coherent strategy. On each scheduled run, it deploys a fixed amount of CZK simultaneously across ETFs, equities, and Bitcoin — all governed by the same logic, all triggered at the same time.

You define the strategy once — the weights, the schedule, the risk tolerance per instrument — and the engine handles everything from there. Every asset class moves together, every cycle, without logging into multiple platforms, remembering to rebalance, or timing anything manually.

Every order, fill, fee, exchange rate, and run summary is recorded in a Supabase database, giving you full auditability and a single source of truth for your entire portfolio's activity over time.

---

## Supported exchanges

| Exchange | Asset classes | Execution |
|----------|--------------|-----------|
| [Trading212](https://www.trading212.com/) | ETFs, equities | Market orders via REST API |
| [Coinmate](https://coinmate.io/) | Bitcoin (BTC/CZK) | Instant buy via REST API |

**Trading212** is used for the full equities and ETF portfolio. Allocations are driven by the weightings defined in your Trading212 Pie, which auto-invest fetches dynamically on each run. Supports both demo and live environments.

**Coinmate** handles Bitcoin purchases, settled directly in CZK — no FX conversion needed. Authentication uses HMAC-SHA256 signing. The architecture is designed to make adding further exchanges straightforward.

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

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create `.env.dev` (for testing) and `.env.prod` (for live trading):

```env
# Trading212
T212_ID_KEY=
T212_PRIVATE_KEY=

# Coinmate
COINMATE_CLIENT_ID=
COINMATE_PUBLIC_KEY=
COINMATE_PRIVATE_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# Portfolio
PIE_ID=               # Your Trading212 Pie ID
T212_WEIGHT=          # Integer weight for the T212 portion (e.g. 90)
BTC_WEIGHT=           # Float weight for BTC (e.g. 10.0)
INVEST_AMOUNT=        # Total CZK to invest per run (e.g. 5000.0)
INVEST_INTERVAL=      # Cron expression (e.g. "0 9 1 * *" for 9am on the 1st of each month)
```

Switch to production mode by setting `ENV=prod`.

### 3. Set up the database

Apply the migration in `supabase/migrations/` to your Supabase project.

---

## Running

```bash
# Single run (dev mode, uses demo broker)
python3 main.py

# Production (set ENV=prod in your environment or scheduler)
ENV=prod python3 main.py
```

Schedule `main.py` with a system cron job. The script evaluates the `INVEST_INTERVAL` cron expression internally and skips execution if it's not the right time — so it's safe to run it frequently (e.g. every minute).

---

## Project structure

```
main.py             — Entry point; orchestrates a full investment run
instruments.py      — Fetches T212 pie weights, calculates ATH-adjusted ratios
executor.py         — Places orders on Trading212 and Coinmate
instrument_data.py  — Static registry: tickers, currencies, names, cap types
trading212.py       — Trading212 REST API client
coinmate.py         — Coinmate REST API client (HMAC-SHA256 auth)
settings.py         — Typed settings loaded from environment variables
utils.py            — Cron-time checker
log.py              — Logging configuration
db/
  client.py         — Supabase client singleton
  orders.py         — Order model, DB persistence, fill reconciliation
  runs.py           — Run model, lifecycle management (CREATED→FINISHED→FILLED)
```

---

## Development

```bash
make sort      # Sort imports
make format    # Format with Black
```

Each module has a `__main__` block for quick ad-hoc testing:

```bash
python3 instruments.py   # Test ratio calculation
python3 trading212.py    # Test T212 API calls
python3 coinmate.py      # Test Coinmate API calls
python3 db/orders.py     # Test order persistence
```

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
