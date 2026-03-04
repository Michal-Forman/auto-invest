# Standard library
from dataclasses import dataclass
import os

# Third-party
from dotenv import load_dotenv

ENV: str = os.getenv("ENV", "dev")

if ENV == "prod":
    load_dotenv(".env.prod")
else:
    load_dotenv(".env.dev")


@dataclass(frozen=True)
class PortfolioSettings:
    pie_id: int
    t212_weight: int
    btc_weight: float
    invest_amount: float
    invest_interval: str

    @classmethod
    def from_env(cls) -> "PortfolioSettings":
        """Load portfolio settings from environment variables."""
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
    coinmate_client_id: int
    coinmate_public_key: str
    coinmate_private_key: str
    supabase_url: str
    supabase_key: str
    portfolio: PortfolioSettings
    env: str
    my_mail: str
    mail_recipient: str
    mail_host: str
    mail_port: int
    mail_password: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Load all application settings (API keys, Supabase, portfolio) from environment variables."""
        return cls(
            t212_id_key=os.environ["T212_ID_KEY"],
            t212_private_key=os.environ["T212_PRIVATE_KEY"],
            portfolio=PortfolioSettings.from_env(),
            coinmate_client_id=int(os.environ["COINMATE_CLIENT_ID"]),
            coinmate_public_key=os.environ["COINMATE_PUBLIC_KEY"],
            coinmate_private_key=os.environ["COINMATE_PRIVATE_KEY"],
            supabase_url=os.environ["SUPABASE_URL"],
            supabase_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
            env=os.getenv("ENV", "dev"),
            mail_host=os.environ["MAIL_HOST"],
            mail_port=int(os.environ["MAIL_PORT"]),
            mail_password=os.environ["MAIL_PASSWORD"],
            my_mail=os.environ["MY_MAIL"],
            mail_recipient=os.environ["MAIL_RECIPIENT"],
        )


settings: Settings = Settings.from_env()
