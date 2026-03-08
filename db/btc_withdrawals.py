# Future
from __future__ import annotations

# Standard library
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, ClassVar, Dict, Literal, Optional
from uuid import UUID

# Local
from db.base import BaseDBModel

Status = Literal["CREATED", "FILLED", "FAILED"]
# Local
from log import log


class BtcWithdrawal(BaseDBModel):
    # --- Identity ---
    TABLE: ClassVar[str] = "btc_withdrawals"
    id: Optional[UUID] = None

    exchange_withdrawal_id: int

    # --- Amounts ---
    amount: Decimal
    fee: Decimal
    fee_czk: Decimal
    amount_czk: Decimal

    # --- Metadata ---
    currency: str = "BTC"
    status: Status
    transfer_type: str
    destination_address: str

    exchange_timestamp: datetime

    created_at: Optional[datetime] = None

    # -------------------------
    # Helper methods for DB
    # -------------------------

    @staticmethod
    def create_withdrawal(
        withdrawal_data: Dict[str, Any], amount_czk: Decimal, fee_czk: Decimal
    ) -> BtcWithdrawal:
        """Build a BtcWithdrawal from btc_withdrawal_data() response, insert it into DB, and return the persisted row."""
        exchange_timestamp = datetime.fromtimestamp(
            withdrawal_data["timestamp"] / 1000, tz=timezone.utc
        )

        withdrawal = BtcWithdrawal(
            exchange_withdrawal_id=int(withdrawal_data["id"]),
            amount=Decimal(str(withdrawal_data["amount"])),
            fee=Decimal(str(withdrawal_data["fee"])),
            fee_czk=fee_czk,
            amount_czk=amount_czk,
            currency=withdrawal_data["currency"],
            status="CREATED",
            transfer_type=withdrawal_data["transfer_type"],
            destination_address=withdrawal_data["destination_adress"],
            exchange_timestamp=exchange_timestamp,
        )

        try:
            inserted: Optional[Dict[str, Any]] = withdrawal.post_to_db()
        except Exception as e:
            log.error(f"Failed to insert BTC withdrawal into database: {e}")
            raise RuntimeError("BTC withdrawal creation failed during DB insert") from e

        if not inserted:
            raise RuntimeError(
                "BTC withdrawal creation failed: no row returned from DB"
            )

        log.info(
            f"BTC withdrawal {withdrawal.exchange_withdrawal_id} recorded in database"
        )

        return withdrawal


if __name__ == "__main__":
    sample: Dict[str, Any] = {
        "id": "17751183",
        "fee": Decimal("0.0001"),
        "currency": "BTC",
        "amount": Decimal("0.00005"),
        "status": "CREATED",
        "timestamp": 1740000000000,
        "transfer_type": "WITHDRAWAL",
        "destination_adress": "bc1qexampleaddress",
    }

    result = BtcWithdrawal.create_withdrawal(
        sample, amount_czk=Decimal("1000.00"), fee_czk=Decimal("63.50")
    )
    print(result)
