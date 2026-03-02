# Standard library
import os
from typing import Any, Dict

# Third-party
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import yfinance as yf  # type: ignore[import-untyped]

# Local
from instrument_data import INSTRUMENT_CAPS, T212_TO_YF
from log import log
from settings import PortfolioSettings
from trading212 import Trading212


class Instruments:
    def __init__(self, t212: Trading212, portfolio_settings: PortfolioSettings) -> None:
        """Initialize with a Trading212 client and portfolio configuration."""
        self.t212 = t212
        self.portfolio_settings = portfolio_settings

    def _validate_t212_ratios(self, ratios: Dict[str, float]) -> bool:
        """Return True if ratios sum to 1.0 (within floating-point tolerance)."""
        total = sum(ratios.values())
        return abs(total - 1.0) < 1e-6

    def get_t212_ratios(self) -> dict[str, float]:
        """Fetch per-instrument target weight ratios from the T212 pie API. Returns raw ratios (not yet scaled by T212_WEIGHT)."""
        try:
            resp: Dict[str, Any] = self.t212.pie(self.portfolio_settings.pie_id)
        except Exception as e:
            raise RuntimeError(f"failed to fetch t212 pie: {e}") from e

        if isinstance(resp, dict) and "res" in resp:
            err = resp.get("err")
            if err:
                raise ValueError(f"T212 pie request failed: {err}")
            resp = resp["res"]

            if "instruments" not in resp:
                raise ValueError("invalid t212 response: missing 'instruments' key")

        result: dict[str, float] = {}

        for instrument in resp["instruments"]:
            try:
                ticker = instrument["ticker"]
                expected_share = float(instrument["expectedShare"])
            except KeyError as e:
                raise ValueError(f"malformed instrument data: missing {e}")

            result[ticker] = expected_share

        if not self._validate_t212_ratios(result):
            total = sum(result.values())
            raise ValueError(f"t212 ratios do not sum to 1.0 (got {total:.8f})")

        return result

    def get_default_ratios(self) -> Dict[str, float]:
        """Scale T212 ratios by T212_WEIGHT and append BTC at BTC_WEIGHT to produce the full portfolio ratios."""
        ratios: Dict[str, float] = self.get_t212_ratios()
        ratios = {k: v * self.portfolio_settings.t212_weight for k, v in ratios.items()}
        ratios["BTC"] = self.portfolio_settings.btc_weight
        return ratios

    @staticmethod
    def get_yahoo_symbol(t212_ticker: str) -> str:
        """Map a T212 ticker to its Yahoo Finance symbol. Raises ValueError if unmapped."""
        if t212_ticker not in T212_TO_YF:
            raise ValueError(f"No Yahoo mapping for {t212_ticker}")
        return T212_TO_YF[t212_ticker]

    @classmethod
    def get_ath(cls, t212_ticker: str) -> float:
        """Return the all-time high close price for a ticker. BTC is computed in CZK, others via Yahoo Finance history."""
        if t212_ticker == "BTC":
            return cls._get_btc_ath()
        symbol = cls.get_yahoo_symbol(t212_ticker)
        ticker: yf.Ticker = yf.Ticker(symbol)

        hist: pd.DataFrame = ticker.history(period="max")

        if hist.empty:
            raise ValueError(f"No historical data for {symbol}")

        return hist["Close"].max()

    @classmethod
    def get_current_price(cls, t212_ticker: str) -> float:
        """Return the latest close price for a ticker. BTC is computed in CZK, others via Yahoo Finance 5-day history."""
        if t212_ticker == "BTC":
            return cls.get_btc_price()

        symbol = cls.get_yahoo_symbol(t212_ticker)

        t: yf.Ticker = yf.Ticker(symbol)
        hist: pd.DataFrame = t.history(period="5d")

        if hist.empty:
            raise ValueError(f"No price data for {t212_ticker} ({symbol})")

        return float(hist["Close"].iloc[-1])

    @staticmethod
    def get_btc_price() -> float:
        """Return the current BTC price in CZK (BTC-USD * USDCZK). Falls back to intraday history if fast_info is unavailable."""
        btc: yf.Ticker = yf.Ticker("BTC-USD")
        fx: yf.Ticker = yf.Ticker("USDCZK=X")

        btc_usd: Any = btc.fast_info.get("lastPrice")
        usdczk: Any = fx.fast_info.get("lastPrice")

        # Fallback if fast_info missing
        if btc_usd is None:
            log.warn(
                "Warning: BTC-USD lastPrice not found in fast_info, falling back to history"
            )
            btc_usd = float(btc.history(period="1d", interval="1m")["Close"].iloc[-1])
        if usdczk is None:
            log.warn(
                "Warning: USDCZK=X lastPrice not found in fast_info, falling back to history"
            )
            usdczk = float(fx.history(period="1d", interval="1m")["Close"].iloc[-1])

        return float(btc_usd) * float(usdczk)

    @staticmethod
    def _get_btc_ath() -> float:
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

        return float(np.asarray(value))

    @classmethod
    def _adjust_ratio(cls, ticker: str, value: float) -> Dict[str, float]:
        """Compute the drop-from-ATH multiplier for a ticker and return the adjusted ratio value along with the multiplier."""
        ath: float = cls.get_ath(ticker)
        current: float = cls.get_current_price(ticker)
        drop = (ath - current) / ath * 100

        cap_type = INSTRUMENT_CAPS.get(ticker)
        if cap_type == "soft":
            drop = cls._soft_cap(drop)
        elif cap_type == "hard":
            drop = cls._hard_cap(drop)
        elif cap_type == "none":
            pass
        else:
            raise ValueError(f"Invalid cap type for {ticker}: {cap_type}")

        multiplier = 100 / (100 - drop)
        adjusted_value = value * multiplier
        return {
            "multiplier": multiplier,
            "adjusted_value": adjusted_value,
        }

    def get_adjusted_ratios(self) -> Dict[str, Dict[str, float]]:
        """Apply drop-from-ATH adjustments to all default ratios. Returns per-ticker multiplier and adjusted value."""
        ratios: Dict[str, float] = self.get_default_ratios()
        adjusted_ratios: Dict[str, Dict[str, float]] = {
            ticker: self._adjust_ratio(ticker, value)
            for ticker, value in ratios.items()
        }

        return adjusted_ratios

    @staticmethod
    def _soft_cap(drop: float) -> float:
        """Cap the drop percentage at 75%."""
        if drop >= 75:
            return 75
        else:
            return drop

    @classmethod
    def _hard_cap(cls, drop: float) -> float:
        """Cap the drop at 75% (soft cap), but reset to 0% if drop >= 90% (treat as recovered)."""
        if drop >= 90:
            return 0
        else:
            return cls._soft_cap(drop)

    def distribute_cash(self) -> Dict[str, Dict[str, float]]:
        """Distribute INVEST_AMOUNT CZK across instruments using adjusted ratios. Returns cash_distribution and multipliers dicts, with minimum-investment thresholds enforced."""
        adjusted_ratios: Dict[str, Dict[str, float]] = self.get_adjusted_ratios()

        total = sum(v["adjusted_value"] for v in adjusted_ratios.values())

        if total == 0:
            raise ValueError("Total adjusted ratio is zero, cannot distribute cash")

        normalized_ratios = {
            ticker: result["adjusted_value"] / total
            for ticker, result in adjusted_ratios.items()
        }

        distribution: Dict[str, float] = {
            ticker: self.portfolio_settings.invest_amount * ratio
            for ticker, ratio in normalized_ratios.items()
        }
        validated_distribution: Dict[str, float] = self._validate_cash_distribution(
            distribution
        )

        multipliers: Dict[str, float] = {
            ticker: result["multiplier"] for ticker, result in adjusted_ratios.items()
        }

        validated_multipliers: Dict[str, float] = {
            t: multipliers[t] for t in validated_distribution.keys()
        }

        return {
            "cash_distribution": validated_distribution,
            "multipliers": validated_multipliers,
        }

    def _validate_cash_distribution(
        self, distribution: Dict[str, float]
    ) -> Dict[str, float]:
        """Enforce minimum order size (25 CZK). Drops instruments below 12.5 CZK, bumps those between 12.5-25 CZK up to 25 CZK."""
        if (
            abs(sum(distribution.values()) - self.portfolio_settings.invest_amount)
            > 1e-6
        ):
            raise ValueError(
                f"Cash distribution does not sum to invest amount: {distribution} (total: {sum(distribution.values())})"
            )
        instruments_to_delete = []
        for ticker, amount in distribution.items():
            minimum_investment = 25
            if amount < minimum_investment:
                if amount <= minimum_investment / 2:
                    log.warning(
                        f"Ticker: {ticker} was not bought since the order would not reach the minimum investment"
                    )
                    instruments_to_delete.append(ticker)
                else:
                    bonus = minimum_investment - amount
                    log.warning(
                        f"Ticker: {ticker} was bought for the minimum investment: {minimum_investment} czk, which is for {bonus} czk more than it was supposed to."
                    )
                    distribution[ticker] = minimum_investment
                    amount = minimum_investment

        for ticker in instruments_to_delete:
            del distribution[ticker]

        return distribution

    @staticmethod
    def get_fx_rate_to_czk(currency: str) -> float:
        """Return the exchange rate from the given currency to CZK via Yahoo Finance. GBX is converted through GBP (divided by 100)."""
        if currency == "CZK":
            return 1.0
        if currency == "GBX":
            pair = f"GBPCZK=X"
            t = yf.Ticker(pair)
            hist = t.history(period="5d")

            if hist.empty:
                raise ValueError(f"No price data for {pair}")

            return float(hist["Close"].iloc[-1]) / 100.0

        pair = f"{currency}CZK=X"
        t = yf.Ticker(pair)
        hist = t.history(period="5d")

        if hist.empty:
            raise ValueError(f"No price data for {pair}")

        return float(hist["Close"].iloc[-1])


if __name__ == "__main__":
    # Local
    from settings import settings

    t212 = Trading212(
        api_id_key=settings.t212_id_key,
        api_private_key=settings.t212_private_key,
        env=settings.env,
    )

    instruments = Instruments(t212, portfolio_settings=settings.portfolio)
    # print(Instruments.get_current_price("XNAQl_EQ"))
    # print(Instruments.get_ath("XNAQl_EQ"))
    # print(Instruments.get_fx_rate_to_czk("EUR"))
    print(instruments.get_t212_ratios())
