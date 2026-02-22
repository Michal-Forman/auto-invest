import os
import yfinance as yf
import pandas as pd
import numpy as np

from trading212 import Trading212
from settings import PortfolioSettings
from instrument_data import T212_TO_YF, INSTRUMENT_CAPS
from typing import Dict

class Instruments:
    def __init__(self, t212: Trading212, portfolio_settings: PortfolioSettings) -> None:
        self.t212 = t212
        self.portfolio_settings = portfolio_settings

    def _validate_t212_ratios(self, ratios: Dict[str, float]) -> bool:
        """Validate if the T212 ratios sum to 1.0 (100%)"""
        total = sum(ratios.values())
        return abs(total - 1.0) < 1e-6

    def get_t212_ratios(self) -> dict[str, float]:
        """Fetch the expected share ratios for each instrument in the T212 pie. The values are not multiplied by the T212 weight, as this is done in get_default_ratios."""
        try:
            resp = self.t212.pie(self.portfolio_settings.pie_id)
        except Exception as e:
            raise RuntimeError(f"failed to fetch t212 pie: {e}") from e

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
            raise ValueError(
                f"t212 ratios do not sum to 1.0 (got {total:.8f})"
            )

        return result

    def get_default_ratios(self) -> Dict[str, float]:
        """Calculate the final default ratios. Multiplies the T212 ratios by the T212 weight, and adds the BTC ratio."""
        ratios: Dict[str, float] = self.get_t212_ratios()
        ratios = {k: v * self.portfolio_settings.t212_weight for k, v in ratios.items()}
        ratios["BTC"] = self.portfolio_settings.btc_weight
        return ratios

    @staticmethod
    def get_yahoo_symbol(t212_ticker: str) -> str:
        if t212_ticker not in T212_TO_YF:
            raise ValueError(f"No Yahoo mapping for {t212_ticker}")
        return T212_TO_YF[t212_ticker]

    @classmethod
    def get_ath(cls, t212_ticker: str) -> float:
        if t212_ticker == "BTC":
            return cls._get_btc_ath()
        symbol = cls.get_yahoo_symbol(t212_ticker)
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period="max")

        if hist.empty:
            raise ValueError(f"No historical data for {symbol}")

        return hist["High"].max()

    @classmethod
    def get_current_price(cls, t212_ticker: str) -> float:
        """
        Returns latest close price for a given T212 ticker.
        """
        if t212_ticker == "BTC":
            return cls._get_btc_price()

        symbol = cls.get_yahoo_symbol(t212_ticker)

        t = yf.Ticker(symbol)
        hist = t.history(period="5d")

        if hist.empty:
            raise ValueError(f"No price data for {t212_ticker} ({symbol})")

        return float(hist["Close"].iloc[-1])

    @staticmethod
    def _get_btc_price() -> float:
        btc = yf.Ticker("BTC-USD")
        fx = yf.Ticker("USDCZK=X")

        btc_usd = btc.fast_info.get("lastPrice")
        usdczk = fx.fast_info.get("lastPrice")

        # Fallback if fast_info missing
        if btc_usd is None:
            print("Warning: BTC-USD lastPrice not found in fast_info, falling back to history")
            btc_usd = float(btc.history(period="1d", interval="1m")["Close"].iloc[-1])
        if usdczk is None:
            print("Warning: USDCZK=X lastPrice not found in fast_info, falling back to history")
            usdczk = float(fx.history(period="1d", interval="1m")["Close"].iloc[-1])

        return float(btc_usd) * float(usdczk)


    @staticmethod
    def _get_btc_ath() -> float:
        btc = yf.Ticker("BTC-USD").history(period="max")[["Close"]]
        btc.columns = ["btc_usd"]
        fx  = yf.Ticker("USDCZK=X").history(period="max")[["Close"]]
        fx.columns = ["usdczk"]

        if btc.empty or fx.empty:
            raise ValueError("Missing BTC-USD or USDCZK=X history")

        df = btc.join(fx, how="inner").dropna()
        df["btc_czk"] = df["btc_usd"] * df["usdczk"]

        value = df["btc_czk"].max()

        if value is None:
            raise ValueError("BTC CZK series empty")

        return float(np.asarray(value))
    
    @classmethod
    def _adjust_ratio(cls, ticker, value) -> float:
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


        adjusted_value = value * (100 / (100 - drop))
        print(f"{ticker} previous value: {value} adjusted_value: {adjusted_value} drop: {drop}%")
        return adjusted_value


    
    def get_adjusted_ratios(self) -> Dict[str, float]:
        ratios = self.get_default_ratios()
        adjusted_ratios = {ticker: self._adjust_ratio(ticker, value) for ticker, value in ratios.items()}
        return adjusted_ratios
    
    @staticmethod
    def _soft_cap(drop: float) -> float:
        if drop >= 75:
            return 75
        else:
            return drop

    @classmethod
    def _hard_cap(cls, drop: float) -> float:
        if drop >= 90:
            return 0
        else:
            return cls._soft_cap(drop)

    def distribute_cash(self) -> Dict[str, float]:
        adjusted_ratios = self.get_adjusted_ratios()
        total = sum(adjusted_ratios.values())
        if total == 0:
            raise ValueError("Total adjusted ratio is zero, cannot distribute cash")
        normalized_ratios = {ticker: value / total for ticker, value in adjusted_ratios.items()}
        distribution = {ticker: self.portfolio_settings.invest_amount * ratio for ticker, ratio in normalized_ratios.items()}
        validated_distribution = self._validate_cash_distribution(distribution)
        return validated_distribution

    def _validate_cash_distribution(self, distribution) -> Dict[str, float]:
        if abs(sum(distribution.values()) - self.portfolio_settings.invest_amount) > 1e-6:
            raise ValueError(f"Cash distribution does not sum to invest amount: {distribution} (total: {sum(distribution.values())})")
        instruments_to_delete = []
        for ticker, amount in distribution.items():
            minimum_investment = 25
            if amount < minimum_investment:
                if amount <= minimum_investment / 2:
                    amount = 0.0
                else:
                    amount = minimum_investment

                if amount == 0.0:
                    instruments_to_delete.append(ticker)
        for ticker in instruments_to_delete:
            del distribution[ticker]

        return distribution



if __name__ == "__main__":

    print("ATHs")
    for ticker in T212_TO_YF.keys():
        try:
            ath = Instruments.get_ath(ticker)
            print(f"{ticker}: {ath}")
        except Exception as e:
            print(f"{ticker}: ERROR -> {e}")

    print("Current Prices")
    for ticker in T212_TO_YF.keys():
        try:
            ath = Instruments.get_current_price(ticker)
            print(f"{ticker}: {ath}")
        except Exception as e:
            print(f"{ticker}: ERROR -> {e}")

    print("BTC Price in CZK")
    print(Instruments._get_btc_price())
    print("BTC ATH in CZK")
    print(Instruments._get_btc_ath())


        
