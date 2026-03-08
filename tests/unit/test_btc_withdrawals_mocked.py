# Standard library
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from db.btc_withdrawals import BtcWithdrawal


@pytest.fixture
def withdrawal_data() -> Dict[str, Any]:
    return {
        "id": "17751183",
        "fee": Decimal("0.0001"),
        "currency": "BTC",
        "amount": Decimal("0.00123"),
        "status": "CREATED",
        "timestamp": 1741000000000,
        "transfer_type": "WITHDRAWAL",
        "destination_adress": "bc1qexampleaddress",
    }


@pytest.fixture
def db_row() -> Dict[str, Any]:
    return {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "exchange_withdrawal_id": 17751183,
        "amount": "0.00123",
        "fee": "0.0001",
        "fee_czk": "150.00",
        "amount_czk": "1845.00",
        "currency": "BTC",
        "status": "CREATED",
        "transfer_type": "WITHDRAWAL",
        "destination_address": "bc1qexampleaddress",
        "exchange_timestamp": "2025-03-03T10:13:20+00:00",
        "created_at": "2025-03-03T10:13:21+00:00",
    }


class TestCreateWithdrawal:
    def test_success_returns_btc_withdrawal(
        self,
        withdrawal_data: Dict[str, Any],
        db_row: Dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(BtcWithdrawal, "post_to_db", return_value=db_row)
        result = BtcWithdrawal.create_withdrawal(
            withdrawal_data, amount_czk=Decimal("1845.00"), fee_czk=Decimal("150.00")
        )
        assert isinstance(result, BtcWithdrawal)

    def test_timestamp_converted_from_ms_to_utc_datetime(
        self,
        withdrawal_data: Dict[str, Any],
        db_row: Dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(BtcWithdrawal, "post_to_db", return_value=db_row)
        result = BtcWithdrawal.create_withdrawal(
            withdrawal_data, amount_czk=Decimal("1845.00"), fee_czk=Decimal("150.00")
        )
        expected = datetime.fromtimestamp(1741000000000 / 1000, tz=timezone.utc)
        assert result.exchange_timestamp == expected

    def test_exchange_id_is_int(
        self,
        withdrawal_data: Dict[str, Any],
        db_row: Dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(BtcWithdrawal, "post_to_db", return_value=db_row)
        result = BtcWithdrawal.create_withdrawal(
            withdrawal_data, amount_czk=Decimal("1845.00"), fee_czk=Decimal("150.00")
        )
        assert result.exchange_withdrawal_id == 17751183
        assert isinstance(result.exchange_withdrawal_id, int)

    def test_amount_and_fee_are_decimal(
        self,
        withdrawal_data: Dict[str, Any],
        db_row: Dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(BtcWithdrawal, "post_to_db", return_value=db_row)
        result = BtcWithdrawal.create_withdrawal(
            withdrawal_data, amount_czk=Decimal("1845.00"), fee_czk=Decimal("150.00")
        )
        assert isinstance(result.amount, Decimal)
        assert isinstance(result.fee, Decimal)

    def test_db_insert_exception_raises_runtime_error(
        self, withdrawal_data: Dict[str, Any], mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            BtcWithdrawal, "post_to_db", side_effect=Exception("DB down")
        )
        with pytest.raises(RuntimeError, match="DB insert"):
            BtcWithdrawal.create_withdrawal(
                withdrawal_data,
                amount_czk=Decimal("1845.00"),
                fee_czk=Decimal("150.00"),
            )

    def test_db_no_row_returned_raises_runtime_error(
        self, withdrawal_data: Dict[str, Any], mocker: MockerFixture
    ) -> None:
        mocker.patch.object(BtcWithdrawal, "post_to_db", return_value=None)
        with pytest.raises(RuntimeError, match="no row returned"):
            BtcWithdrawal.create_withdrawal(
                withdrawal_data,
                amount_czk=Decimal("1845.00"),
                fee_czk=Decimal("150.00"),
            )

    def test_status_always_created(
        self,
        withdrawal_data: Dict[str, Any],
        db_row: Dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        withdrawal_data["status"] = "FILLED"
        mocker.patch.object(BtcWithdrawal, "post_to_db", return_value=db_row)
        result = BtcWithdrawal.create_withdrawal(
            withdrawal_data, amount_czk=Decimal("1845.00"), fee_czk=Decimal("150.00")
        )
        assert result.status == "CREATED"
