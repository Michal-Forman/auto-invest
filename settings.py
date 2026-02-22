from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass(frozen=True)
class PortfolioSettings:
    pie_id: int
    t212_weight: int
    btc_weight: float
    invest_amount: float
    invest_interval: str

    @classmethod
    def from_env(cls) -> "PortfolioSettings":
        return cls(
            pie_id=int(os.environ["PIE_ID"]),
            t212_weight=int(os.environ["T212_WEIGHT"]),
            btc_weight=float(os.environ["BTC_WEIGHT"]),
            invest_amount=float(os.environ["INVEST_AMOUNT"]),
            invest_interval=os.getenv("INVEST_INTERVAL", "monthly"),
        )

@dataclass(frozen=True)
class Settings:
    t212_id_key: str
    t212_private_key: str
    portfolio: PortfolioSettings

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            t212_id_key=os.environ["T212_ID_KEY"],
            t212_private_key=os.environ["T212_PRIVATE_KEY"],
            portfolio=PortfolioSettings.from_env(),
        )

settings = Settings.from_env()
portfolio_settings = PortfolioSettings.from_env()
