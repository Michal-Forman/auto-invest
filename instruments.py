import os
import yfinance as yf
from ticker_map import T212_TO_YF

from trading212 import Trading212
from settings import PortfolioSettings, portfolio_settings
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
        ratios = {k: v * portfolio_settings.t212_weight for k, v in ratios.items()}
        ratios["BTC"] = portfolio_settings.btc_weight
        return ratios

    @staticmethod
    def get_yahoo_symbol(t212_ticker: str) -> str:
        if t212_ticker not in T212_TO_YF:
            raise ValueError(f"No Yahoo mapping for {t212_ticker}")
        return T212_TO_YF[t212_ticker]

    @classmethod
    def get_ath(cls, t212_ticker: str) -> float:
        symbol = cls.get_yahoo_symbol(t212_ticker)
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period="max")

        if hist.empty:
            raise ValueError(f"No historical data for {symbol}")

        return hist["High"].max()

if __name__ == "__main__":

    for ticker in T212_TO_YF.keys():
        try:
            ath = Instruments.get_ath(ticker)
            print(f"{ticker}: {ath}")
        except Exception as e:
            print(f"{ticker}: ERROR -> {e}")




        
