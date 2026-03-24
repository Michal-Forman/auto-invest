# Standard library
from decimal import Decimal
from typing import Any, Dict

# Third-party
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import yfinance as yf  # type: ignore[import-untyped]

# Local
import core.coinmate
from core.coinmate import Coinmate
from core.instrument_data import INSTRUMENT_CAPS, T212_TO_YF
from core.log import log
from core.precision import RATIO_TOLERANCE, to_decimal
from core.settings import PortfolioSettings
from core.trading212 import Trading212

SOFT_CAP_PERCENT = Decimal("75")
HARD_CAP_RESET_PERCENT = Decimal("90")
MIN_ORDER_CZK = Decimal("25")


class Instruments:
    def __init__(
        self,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
    ) -> None:
        """Initialize with a Trading212 client and portfolio configuration."""
        self.t212 = t212
        self.portfolio_settings = portfolio_settings
        self.coinmate = coinmate

    def _validate_t212_ratios(self, ratios: Dict[str, Decimal]) -> bool:
        """Return True if ratios sum to 1.0 (within tolerance)."""
        total = sum(ratios.values(), Decimal("0"))
        return abs(total - Decimal("1")) < RATIO_TOLERANCE

    def get_t212_ratios(self) -> Dict[str, Decimal]:
        """Fetch per-instrument target weight ratios from the T212 pie API. Returns raw ratios (not yet scaled by T212_WEIGHT)."""
        try:
            resp: Dict[str, Any] = self.t212.pie(self.portfolio_settings.pie_id or 0)
        except Exception as e:
            raise RuntimeError(f"failed to fetch t212 pie: {e}") from e

        if isinstance(resp, dict) and "res" in resp:
            err = resp.get("err")
            if err:
                raise ValueError(f"T212 pie request failed: {err}")
            resp = resp["res"]

            if "instruments" not in resp:
                raise ValueError("invalid t212 response: missing 'instruments' key")

        result: Dict[str, Decimal] = {}

        for instrument in resp["instruments"]:
            try:
                ticker = instrument["ticker"]
                expected_share = to_decimal(float(instrument["expectedShare"]))
            except KeyError as e:
                raise ValueError(f"malformed instrument data: missing {e}")

            result[ticker] = expected_share

        if not self._validate_t212_ratios(result):
            total = sum(result.values(), Decimal("0"))
            raise ValueError(f"t212 ratios do not sum to 1.0 (got {total:.8f})")

        return result

    def get_default_ratios(self) -> Dict[str, Decimal]:
        """Scale T212 ratios by T212_WEIGHT and append BTC at BTC_WEIGHT to produce the full portfolio ratios."""
        ratios: Dict[str, Decimal] = self.get_t212_ratios()
        t212_weight = to_decimal(self.portfolio_settings.t212_weight)
        ratios = {k: v * t212_weight for k, v in ratios.items()}
        btc_weight = to_decimal(self.portfolio_settings.btc_weight)
        if btc_weight != Decimal("0"):
            ratios["BTC"] = btc_weight
        return ratios

    @staticmethod
    def get_yahoo_symbol(t212_ticker: str) -> str:
        """Map a T212 ticker to its Yahoo Finance symbol. Raises ValueError if unmapped."""
        if t212_ticker not in T212_TO_YF:
            raise ValueError(f"No Yahoo mapping for {t212_ticker}")
        return T212_TO_YF[t212_ticker]

    @classmethod
    def get_ath(cls, t212_ticker: str) -> Decimal:
        """Return the all-time high close price for a ticker. BTC is computed in CZK, others via Yahoo Finance history."""
        if t212_ticker == "BTC":
            return cls._get_btc_ath()
        symbol = cls.get_yahoo_symbol(t212_ticker)
        ticker: yf.Ticker = yf.Ticker(symbol)

        hist: pd.DataFrame = ticker.history(period="max")

        if hist.empty:
            raise ValueError(f"No historical data for {symbol}")

        return to_decimal(float(hist["Close"].max()))

    @classmethod
    def get_current_price(cls, t212_ticker: str) -> Decimal:
        """Return the latest close price for a ticker. BTC is computed in CZK, others via Yahoo Finance 5-day history."""
        if t212_ticker == "BTC":
            return cls.get_btc_price()

        symbol = cls.get_yahoo_symbol(t212_ticker)

        t: yf.Ticker = yf.Ticker(symbol)
        hist: pd.DataFrame = t.history(period="5d")

        if hist.empty:
            raise ValueError(f"No price data for {t212_ticker} ({symbol})")

        return to_decimal(float(hist["Close"].iloc[-1]))

    @staticmethod
    def get_btc_price() -> Decimal:
        """Return the current BTC price in CZK (BTC-USD * USDCZK). Falls back to intraday history if fast_info is unavailable."""
        btc: yf.Ticker = yf.Ticker("BTC-USD")
        fx: yf.Ticker = yf.Ticker("USDCZK=X")

        try:
            btc_usd: Any = btc.fast_info.get("lastPrice")
        except Exception:
            btc_usd = None
        try:
            usdczk: Any = fx.fast_info.get("lastPrice")
        except Exception:
            usdczk = None

        # Fallback if fast_info missing
        if btc_usd is None:
            log.warning(
                "BTC-USD lastPrice not found in fast_info, falling back to history"
            )
            btc_hist = btc.history(period="1d", interval="1m")
            if btc_hist.empty:
                raise ValueError("BTC-USD history is empty, cannot determine price")
            btc_usd = float(btc_hist["Close"].iloc[-1])
        if usdczk is None:
            log.warning(
                "USDCZK=X lastPrice not found in fast_info, falling back to history"
            )
            fx_hist = fx.history(period="1d", interval="1m")
            if fx_hist.empty:
                raise ValueError("USDCZK=X history is empty, cannot determine FX rate")
            usdczk = float(fx_hist["Close"].iloc[-1])

        return to_decimal(float(btc_usd)) * to_decimal(float(usdczk))

    @staticmethod
    def _get_btc_ath() -> Decimal:
        """Return the BTC ATH in CZK by joining daily BTC-USD and USDCZK history and taking the max of (btc_usd * usdczk)."""
        btc: pd.DataFrame = yf.Ticker("BTC-USD").history(period="max")[["Close"]]
        btc.columns = ["btc_usd"]
        fx: pd.DataFrame = yf.Ticker("USDCZK=X").history(period="max")[["Close"]]
        fx.columns = ["usdczk"]

        if btc.empty or fx.empty:
            raise ValueError("Missing BTC-USD or USDCZK=X history")

        df: pd.DataFrame = btc.join(fx, how="inner").dropna()
        df["btc_czk"] = df["btc_usd"] * df["usdczk"]

        value: Any = df["btc_czk"].max()

        if value is None:
            raise ValueError("BTC CZK series empty")

        return to_decimal(float(np.asarray(value)))

    @classmethod
    def _adjust_ratio(cls, ticker: str, value: Decimal) -> Dict[str, Decimal]:
        """Compute the drop-from-ATH multiplier for a ticker and return the adjusted ratio value along with the multiplier."""
        ath: Decimal = cls.get_ath(ticker)
        current: Decimal = cls.get_current_price(ticker)
        drop: Decimal = (ath - current) / ath * Decimal("100")

        cap_type = INSTRUMENT_CAPS.get(ticker)
        if cap_type == "soft":
            drop = cls._soft_cap(drop)
        elif cap_type == "hard":
            drop = cls._hard_cap(drop)
        elif cap_type == "none":
            pass
        else:
            raise ValueError(f"Invalid cap type for {ticker}: {cap_type}")

        multiplier: Decimal = Decimal("100") / (Decimal("100") - drop)
        adjusted_value: Decimal = value * multiplier
        return {
            "multiplier": multiplier,
            "adjusted_value": adjusted_value,
        }

    def get_adjusted_ratios(self) -> Dict[str, Dict[str, Decimal]]:
        """Apply drop-from-ATH adjustments to all default ratios. Returns per-ticker multiplier and adjusted value."""
        ratios: Dict[str, Decimal] = self.get_default_ratios()
        adjusted_ratios: Dict[str, Dict[str, Decimal]] = {
            ticker: self._adjust_ratio(ticker, value)
            for ticker, value in ratios.items()
        }

        return adjusted_ratios

    @staticmethod
    def _soft_cap(drop: Decimal) -> Decimal:
        """Cap the drop percentage at 75%."""
        if drop >= SOFT_CAP_PERCENT:
            return SOFT_CAP_PERCENT
        return drop

    @classmethod
    def _hard_cap(cls, drop: Decimal) -> Decimal:
        """Cap the drop at 75% (soft cap), but reset to 0% if drop >= 90% (treat as recovered)."""
        if drop >= HARD_CAP_RESET_PERCENT:
            return Decimal("0")
        return cls._soft_cap(drop)

    def distribute_cash(self) -> Dict[str, Dict[str, Decimal]]:
        """Distribute INVEST_AMOUNT CZK across instruments using adjusted ratios. Returns cash_distribution and multipliers dicts, with minimum-investment thresholds enforced."""
        adjusted_ratios: Dict[str, Dict[str, Decimal]] = self.get_adjusted_ratios()

        total = sum(
            (v["adjusted_value"] for v in adjusted_ratios.values()), Decimal("0")
        )

        if total == 0:
            raise ValueError("Total adjusted ratio is zero, cannot distribute cash")

        normalized_ratios: Dict[str, Decimal] = {
            ticker: result["adjusted_value"] / total
            for ticker, result in adjusted_ratios.items()
        }

        invest_amount = to_decimal(self.portfolio_settings.invest_amount)
        distribution: Dict[str, Decimal] = {
            ticker: invest_amount * ratio for ticker, ratio in normalized_ratios.items()
        }
        validated_distribution: Dict[str, Decimal] = self._validate_cash_distribution(
            distribution
        )

        multipliers: Dict[str, Decimal] = {
            ticker: result["multiplier"] for ticker, result in adjusted_ratios.items()
        }

        validated_multipliers: Dict[str, Decimal] = {
            t: multipliers[t] for t in validated_distribution.keys()
        }

        return {
            "cash_distribution": validated_distribution,
            "multipliers": validated_multipliers,
        }

    def _validate_cash_distribution(
        self, distribution: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """Enforce minimum order size (25 CZK). Drops instruments below 12.5 CZK, bumps those between 12.5-25 CZK up to 25 CZK."""
        invest_amount = to_decimal(self.portfolio_settings.invest_amount)
        if (
            abs(sum(distribution.values(), Decimal("0")) - invest_amount)
            > RATIO_TOLERANCE
        ):
            raise ValueError(
                f"Cash distribution does not sum to invest amount: {distribution} (total: {sum(distribution.values(), Decimal('0'))})"
            )
        instruments_to_delete = []
        for ticker, amount in distribution.items():
            if amount < MIN_ORDER_CZK:
                if amount <= MIN_ORDER_CZK / 2:
                    log.warning(
                        f"Ticker: {ticker} was not bought since the order would not reach the minimum investment"
                    )
                    instruments_to_delete.append(ticker)
                else:
                    bonus = MIN_ORDER_CZK - amount
                    log.warning(
                        f"Ticker: {ticker} was bought for the minimum investment: {MIN_ORDER_CZK} czk, which is for {bonus} czk more than it was supposed to."
                    )
                    distribution[ticker] = MIN_ORDER_CZK

        for ticker in instruments_to_delete:
            del distribution[ticker]

        return distribution

    @staticmethod
    def get_fx_rate_to_czk(currency: str) -> Decimal:
        """Return the exchange rate from the given currency to CZK via Yahoo Finance. GBX is converted through GBP (divided by 100)."""
        if currency == "CZK":
            return Decimal("1")
        if currency == "GBX":
            pair = "GBPCZK=X"
            t = yf.Ticker(pair)
            hist = t.history(period="5d")

            if hist.empty:
                raise ValueError(f"No price data for {pair}")

            return to_decimal(float(hist["Close"].iloc[-1])) / Decimal("100")

        pair = f"{currency}CZK=X"
        t = yf.Ticker(pair)
        hist = t.history(period="5d")

        if hist.empty:
            raise ValueError(f"No price data for {pair}")

        return to_decimal(float(hist["Close"].iloc[-1]))

    def is_btc_withdrawal_treshold_exceeded(self) -> bool:
        treshold = self.portfolio_settings.btc_withdrawal_treshold
        btc_price: Decimal = self.get_btc_price()
        btc_held: Decimal = self.coinmate.btc_balance()
        btc_held_czk: Decimal = btc_held * btc_price
        if btc_held_czk >= treshold:
            return True
        else:
            return False


if __name__ == "__main__":
    from core.instrument_data import INSTRUMENT_CURRENCIES, INSTRUMENT_NAMES, T212_TO_YF

    print(0 == 0.0)
    print(0 == float(0))
