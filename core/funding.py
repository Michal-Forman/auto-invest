# Standard library
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set

# Local
from core.coinmate import Coinmate
from core.precision import quantize_czk
from core.trading212 import Trading212

# Market prices drift between the yfinance quote used for sizing and the actual
# fill, and T212 adds an FX conversion fee on non-CZK instruments. Require a
# little more cash than the plan asks for so a run is never rejected mid-way.
EXECUTION_MARGIN = Decimal("1.015")

# Don't repeat the same warning every day while the user arranges a transfer.
ALERT_COOLDOWN_DAYS = 3

T212_EXCHANGE = "T212"
COINMATE_EXCHANGE = "COINMATE"


@dataclass(frozen=True)
class ExchangeFunding:
    """How much cash a single exchange needs versus what it holds.

    `runs` and `margin` let the same type express two questions: the hard gate
    ("can this one run be paid for at all", runs=1 with EXECUTION_MARGIN) and the
    early warning ("is the next week covered comfortably", runs=N with the user's
    balance_buffer).
    """

    exchange: str
    required_czk: Decimal
    available_czk: Decimal
    runs: int = 1
    margin: Decimal = EXECUTION_MARGIN

    @property
    def per_run_czk(self) -> Decimal:
        """Cash one run costs on this exchange, including the margin."""
        return quantize_czk(self.required_czk * self.margin)

    @property
    def needed_czk(self) -> Decimal:
        """Cash required to cover `runs` runs, including the margin."""
        return quantize_czk(self.per_run_czk * self.runs)

    @property
    def shortfall_czk(self) -> Decimal:
        """How much cash is missing. Zero when the exchange can cover the run."""
        return max(Decimal("0"), quantize_czk(self.needed_czk - self.available_czk))

    @property
    def is_short(self) -> bool:
        """True when this exchange cannot cover its share of the run."""
        return self.shortfall_czk > Decimal("0")


class InsufficientFundsError(RuntimeError):
    """Raised before any order is placed when an exchange cannot cover the run."""

    def __init__(self, shortfalls: List[ExchangeFunding]) -> None:
        self.shortfalls = shortfalls
        super().__init__(self._describe(shortfalls))

    @staticmethod
    def _describe(shortfalls: List[ExchangeFunding]) -> str:
        """Build a human-readable message naming every underfunded exchange."""
        return "; ".join(
            f"Insufficient funds on {f.exchange}: need {f.needed_czk} CZK, "
            f"have {quantize_czk(f.available_czk)} (short {f.shortfall_czk})"
            for f in shortfalls
        )


def split_by_exchange(cash_distribution: Dict[str, Decimal]) -> Dict[str, Decimal]:
    """Sum a cash distribution per exchange, mirroring how Executor routes orders."""
    totals: Dict[str, Decimal] = {
        T212_EXCHANGE: Decimal("0"),
        COINMATE_EXCHANGE: Decimal("0"),
    }
    for ticker, amount in cash_distribution.items():
        exchange = COINMATE_EXCHANGE if ticker == "BTC" else T212_EXCHANGE
        totals[exchange] += amount
    return totals


def funding_status(
    cash_distribution: Dict[str, Decimal],
    t212: Trading212,
    coinmate: Coinmate,
    runs: int = 1,
    margin: Decimal = EXECUTION_MARGIN,
) -> List[ExchangeFunding]:
    """Compare each exchange's live free cash against what `runs` runs would spend there.

    Exchanges with nothing to buy are left out entirely, so a portfolio without BTC
    never touches Coinmate.
    """
    required: Dict[str, Decimal] = split_by_exchange(cash_distribution)
    balance_getters = {
        T212_EXCHANGE: t212.balance,
        COINMATE_EXCHANGE: coinmate.balance,
    }

    statuses: List[ExchangeFunding] = []
    for exchange, get_balance in balance_getters.items():
        if required[exchange] <= Decimal("0"):
            continue
        statuses.append(
            ExchangeFunding(
                exchange=exchange,
                required_czk=quantize_czk(required[exchange]),
                available_czk=get_balance(),
                runs=max(1, runs),
                margin=margin,
            )
        )

    return statuses


def should_send_alert(
    short_exchanges: Set[str],
    last_alert_at: Optional[datetime],
    last_alert_exchanges: Set[str],
    now: datetime,
) -> bool:
    """Decide whether to send a low-funds warning.

    Alerts repeat at most once every ALERT_COOLDOWN_DAYS, but an exchange that
    has newly gone short bypasses the cooldown so it is never held back.
    """
    if not short_exchanges:
        return False
    if last_alert_at is None:
        return True
    if short_exchanges != last_alert_exchanges:
        return True
    return now - last_alert_at >= timedelta(days=ALERT_COOLDOWN_DAYS)


def should_send_recovery(
    short_exchanges: Set[str], last_alert_exchanges: Set[str]
) -> bool:
    """Return True when everything is funded again after a previous warning."""
    return not short_exchanges and bool(last_alert_exchanges)


if __name__ == "__main__":
    from core.db.users import UserRecord
    from core.instruments import Instruments
    from core.settings import UserSettings

    _user = UserRecord.get_cron_users()[0]
    _us = UserSettings.from_user(_user)
    _t212 = Trading212(_us.t212_id_key, _us.t212_private_key, env=_us.env)
    _coinmate = Coinmate(
        _us.coinmate_client_id or 0, _us.coinmate_public_key, _us.coinmate_private_key
    )
    _instruments = Instruments(
        t212=_t212, coinmate=_coinmate, portfolio_settings=_us.portfolio
    )
    _distribution = _instruments.distribute_cash()["cash_distribution"]

    for _status in funding_status(_distribution, _t212, _coinmate):
        _verdict = f"SHORT by {_status.shortfall_czk}" if _status.is_short else "OK"
        print(
            f"{_status.exchange:<10} required={_status.required_czk:>8} "
            f"needed={_status.needed_czk:>8} available={quantize_czk(_status.available_czk):>9}  {_verdict}"
        )
