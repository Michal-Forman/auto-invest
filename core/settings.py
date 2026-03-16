# Future
from __future__ import annotations

# Standard library
from dataclasses import dataclass
import os
from typing import TYPE_CHECKING, Optional

# Third-party
from dotenv import load_dotenv

if TYPE_CHECKING:
    from core.db.users import UserRecord

ENV: str = os.getenv("ENV", "dev")

if ENV == "prod":
    load_dotenv(".env.prod")
else:
    load_dotenv(".env.dev")


@dataclass(frozen=True)
class Settings:
    """System-level settings loaded from environment."""

    supabase_url: str
    supabase_key: str
    env: str
    my_mail: str
    mail_host: str
    mail_port: int
    mail_password: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Load system settings from environment variables."""
        return cls(
            supabase_url=os.environ["SUPABASE_URL"],
            supabase_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
            env=os.getenv("ENV", "dev"),
            my_mail=os.getenv("MY_MAIL", ""),
            mail_host=os.getenv("MAIL_HOST", ""),
            mail_port=int(os.getenv("MAIL_PORT", "465")),
            mail_password=os.getenv("MAIL_PASSWORD", ""),
        )


settings: Settings = Settings.from_env()


@dataclass(frozen=True)
class PortfolioSettings:
    """Per-user portfolio configuration."""

    pie_id: Optional[int]
    t212_weight: int
    btc_weight: float
    invest_amount: float
    invest_interval: str
    balance_buffer: float
    balance_alert_days: int
    btc_withdrawal_treshold: int

    @classmethod
    def from_user(cls, user: UserRecord) -> "PortfolioSettings":
        """Build portfolio settings from a UserRecord. Raises ValueError if required fields are not configured."""
        required = {
            "t212_weight": user.t212_weight,
            "btc_weight": user.btc_weight,
            "invest_amount": user.invest_amount,
            "invest_interval": user.invest_interval,
            "balance_buffer": user.balance_buffer,
            "balance_alert_days": user.balance_alert_days,
            "btc_withdrawal_treshold": user.btc_withdrawal_treshold,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise ValueError(f"User {user.id} is missing required portfolio settings: {', '.join(missing)}")
        return cls(
            pie_id=user.pie_id,
            t212_weight=int(user.t212_weight),  # type: ignore[arg-type]
            btc_weight=float(user.btc_weight),  # type: ignore[arg-type]
            invest_amount=float(user.invest_amount),  # type: ignore[arg-type]
            invest_interval=str(user.invest_interval),  # type: ignore[arg-type]
            balance_buffer=float(user.balance_buffer),  # type: ignore[arg-type]
            balance_alert_days=int(user.balance_alert_days),  # type: ignore[arg-type]
            btc_withdrawal_treshold=int(user.btc_withdrawal_treshold),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class UserSettings:
    """All per-user settings derived from a UserRecord."""

    user_id: str
    t212_id_key: str
    t212_private_key: str
    coinmate_client_id: Optional[int]
    coinmate_public_key: str
    coinmate_private_key: str
    mail_recipient: str
    t212_deposit_account: Optional[str]
    t212_deposit_vs: Optional[str]
    coinmate_deposit_account: Optional[str]
    coinmate_deposit_vs: Optional[str]
    btc_external_adress: str
    portfolio: PortfolioSettings
    env: str

    @classmethod
    def from_user(cls, user: UserRecord) -> "UserSettings":
        """Build user-specific settings from a UserRecord."""
        return cls(
            user_id=user.id,
            t212_id_key=user.t212_id_key,
            t212_private_key=user.t212_private_key,
            coinmate_client_id=user.coinmate_client_id,
            coinmate_public_key=user.coinmate_public_key,
            coinmate_private_key=user.coinmate_private_key,
            mail_recipient=user.email,
            t212_deposit_account=user.t212_deposit_account,
            t212_deposit_vs=user.t212_deposit_vs,
            coinmate_deposit_account=user.coinmate_deposit_account,
            coinmate_deposit_vs=user.coinmate_deposit_vs,
            btc_external_adress=user.btc_external_adress,
            portfolio=PortfolioSettings.from_user(user),
            env=settings.env,
        )
