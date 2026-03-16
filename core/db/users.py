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
    t212_weight: int
    btc_weight: float
    invest_amount: float
    invest_interval: str
    balance_buffer: float
    balance_alert_days: int
    btc_withdrawal_treshold: int
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
            t212_weight=int(row.get("t212_weight", 90)),
            btc_weight=float(row.get("btc_weight", 10.0)),
            invest_amount=float(row.get("invest_amount", 5000.0)),
            invest_interval=row.get("invest_interval") or "0 9 1 * *",
            balance_buffer=float(row.get("balance_buffer", 500.0)),
            balance_alert_days=int(row.get("balance_alert_days", 5)),
            btc_withdrawal_treshold=int(row.get("btc_withdrawal_treshold", 500000)),
            btc_external_adress=row.get("btc_external_adress") or "",
            email=row.get("email") or "",
            t212_deposit_account=row.get("t212_deposit_account"),
            t212_deposit_vs=row.get("t212_deposit_vs"),
            coinmate_deposit_account=row.get("coinmate_deposit_account"),
            coinmate_deposit_vs=row.get("coinmate_deposit_vs"),
            cron_enabled=bool(row.get("cron_enabled", True)),
            notifications_enabled=bool(row.get("notifications_enabled", True)),
            btc_withdrawals_enabled=bool(row.get("btc_withdrawals_enabled", True)),
            trading212_enabled=bool(row.get("trading212_enabled", True)),
            coinmate_enabled=bool(row.get("coinmate_enabled", True)),
        )


if __name__ == "__main__":
    users = UserRecord.get_cron_users()
    for u in users:
        log.info(f"User {u.id}: invest_amount={u.invest_amount}")
