# Future
from __future__ import annotations

# Standard library
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Local
from core.db.client import supabase
from core.log import log


@dataclass(frozen=True)
class UserRecord:
    """Mirror of public.users table row."""

    id: str

    # Exchange credentials
    t212_id_key: str
    t212_private_key: str
    coinmate_client_id: Optional[int]
    coinmate_public_key: str
    coinmate_private_key: str

    # Portfolio
    pie_id: Optional[int]
    t212_weight: Optional[int]
    btc_weight: Optional[float]
    invest_amount: Optional[float]
    invest_interval: Optional[str]
    balance_buffer: Optional[float]
    balance_alert_days: Optional[int]
    btc_withdrawal_treshold: Optional[int]
    btc_external_adress: str

    # Synced from auth.users via DB trigger
    email: str

    # Deposit (optional)
    t212_deposit_account: Optional[str]
    t212_deposit_vs: Optional[str]
    coinmate_deposit_account: Optional[str]
    coinmate_deposit_vs: Optional[str]

    # Control
    cron_enabled: bool
    notifications_enabled: bool
    btc_withdrawals_enabled: bool
    trading212_enabled: bool
    coinmate_enabled: bool

    @staticmethod
    def from_db(user_id: str) -> "UserRecord":
        """Fetch a single user row from Supabase by user_id."""
        response: Any = (
            supabase.table("users").select("*").eq("id", user_id).single().execute()
        )
        return UserRecord._from_row(response.data)

    @staticmethod
    def get_cron_users() -> List["UserRecord"]:
        """Return all users where cron_enabled = True."""
        response: Any = (
            supabase.table("users").select("*").eq("cron_enabled", True).execute()
        )
        return [UserRecord._from_row(row) for row in response.data or []]

    @staticmethod
    def _from_row(row: Dict[str, Any]) -> "UserRecord":
        """Build a UserRecord from a raw Supabase row dict."""
        return UserRecord(
            id=row["id"],
            t212_id_key=row.get("t212_id_key") or "",
            t212_private_key=row.get("t212_private_key") or "",
            coinmate_client_id=row.get("coinmate_client_id"),
            coinmate_public_key=row.get("coinmate_public_key") or "",
            coinmate_private_key=row.get("coinmate_private_key") or "",
            pie_id=row.get("pie_id"),
            t212_weight=int(row["t212_weight"]) if row.get("t212_weight") is not None else None,
            btc_weight=float(row["btc_weight"]) if row.get("btc_weight") is not None else None,
            invest_amount=float(row["invest_amount"]) if row.get("invest_amount") is not None else None,
            invest_interval=row.get("invest_interval") or None,
            balance_buffer=float(row["balance_buffer"]) if row.get("balance_buffer") is not None else None,
            balance_alert_days=int(row["balance_alert_days"]) if row.get("balance_alert_days") is not None else None,
            btc_withdrawal_treshold=int(row["btc_withdrawal_treshold"]) if row.get("btc_withdrawal_treshold") is not None else None,
            btc_external_adress=row.get("btc_external_adress") or "",
            email=row.get("email") or "",
            t212_deposit_account=row.get("t212_deposit_account"),
            t212_deposit_vs=row.get("t212_deposit_vs"),
            coinmate_deposit_account=row.get("coinmate_deposit_account"),
            coinmate_deposit_vs=row.get("coinmate_deposit_vs"),
            cron_enabled=bool(row.get("cron_enabled", False)),
            notifications_enabled=bool(row.get("notifications_enabled", True)),
            btc_withdrawals_enabled=bool(row.get("btc_withdrawals_enabled", False)),
            trading212_enabled=bool(row.get("trading212_enabled", False)),
            coinmate_enabled=bool(row.get("coinmate_enabled", False)),
        )


if __name__ == "__main__":
    users = UserRecord.get_cron_users()
    for u in users:
        log.info(f"User {u.id}: invest_amount={u.invest_amount}")
