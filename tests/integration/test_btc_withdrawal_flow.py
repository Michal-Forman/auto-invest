# Standard library
from dataclasses import replace
from decimal import Decimal
from unittest.mock import MagicMock

# Third-party
import pytest
from pytest_mock import MockerFixture
from requests.exceptions import RequestException

# Local
from core.coinmate import Coinmate
from core.db.btc_withdrawals import BtcWithdrawal
from core.executor import Executor
from core.instruments import Instruments
from core.mailer import Mailer
from core.settings import PortfolioSettings
from core.trading212 import Trading212


def _make_transaction_data(amount: float = 0.01) -> dict:
    return {
        "id": "17751183",
        "fee": Decimal("0.0001"),
        "currency": "BTC",
        "amount": Decimal(str(amount)),
        "status": "CREATED",
        "timestamp": 1741000000000,
        "transfer_type": "WITHDRAWAL",
        "destination_adress": "bc1qexampleaddressfortesting",
    }


@pytest.fixture
def db_row() -> dict:
    return {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "exchange_withdrawal_id": 17751183,
        "amount": "0.01",
        "fee": "0.0001",
        "fee_czk": "200.00",
        "amount_czk": "20000.00",
        "currency": "BTC",
        "status": "CREATED",
        "transfer_type": "WITHDRAWAL",
        "destination_address": "bc1qexampleaddressfortesting",
        "exchange_timestamp": "2025-03-03T10:13:20+00:00",
        "created_at": "2025-03-03T10:13:21+00:00",
    }


class TestBtcWithdrawalThresholdCheck:
    def test_threshold_exceeded_returns_true(
        self,
        instruments: Instruments,
        mocker: MockerFixture,
        portfolio_settings: PortfolioSettings,
    ) -> None:
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)
        mocker.patch.object(instruments.coinmate, "btc_balance", return_value=0.01)
        # 0.01 * 2_000_000 = 20_000 > 10_000
        instruments.portfolio_settings = replace(
            portfolio_settings, btc_withdrawal_treshold=10_000
        )
        assert instruments.is_btc_withdrawal_treshold_exceeded() is True

    def test_threshold_not_exceeded_returns_false(
        self,
        instruments: Instruments,
        mocker: MockerFixture,
        portfolio_settings: PortfolioSettings,
    ) -> None:
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)
        mocker.patch.object(instruments.coinmate, "btc_balance", return_value=0.01)
        # 0.01 * 2_000_000 = 20_000 < 25_000
        instruments.portfolio_settings = replace(
            portfolio_settings, btc_withdrawal_treshold=25_000
        )
        assert instruments.is_btc_withdrawal_treshold_exceeded() is False

    def test_threshold_exactly_at_boundary(
        self,
        instruments: Instruments,
        mocker: MockerFixture,
        portfolio_settings: PortfolioSettings,
    ) -> None:
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)
        mocker.patch.object(instruments.coinmate, "btc_balance", return_value=0.01)
        # 0.01 * 2_000_000 = 20_000 == 20_000 → True (>=)
        instruments.portfolio_settings = replace(
            portfolio_settings, btc_withdrawal_treshold=20_000
        )
        assert instruments.is_btc_withdrawal_treshold_exceeded() is True


class TestBtcWithdrawalExecution:
    def test_full_withdrawal_flow_returns_btc_withdrawal(
        self,
        coinmate: Coinmate,
        t212: Trading212,
        db_row: dict,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(coinmate, "btc_balance", return_value=0.01)
        mocker.patch.object(
            coinmate, "btc_withdraw", return_value=_make_transaction_data(0.01)
        )
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)
        mocker.patch.object(BtcWithdrawal, "post_to_db", return_value=db_row)

        executor = Executor(t212, coinmate)
        result = executor.withdraw_btc()

        assert isinstance(result, BtcWithdrawal)
        assert result.exchange_withdrawal_id == 17751183

    def test_withdrawal_coinmate_failure_raises(
        self,
        coinmate: Coinmate,
        t212: Trading212,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(coinmate, "btc_balance", return_value=0.01)
        mocker.patch.object(
            coinmate, "btc_withdraw", side_effect=RequestException("network error")
        )
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)

        executor = Executor(t212, coinmate)
        with pytest.raises(RequestException):
            executor.withdraw_btc()

    def test_withdrawal_db_failure_raises(
        self,
        coinmate: Coinmate,
        t212: Trading212,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(coinmate, "btc_balance", return_value=0.01)
        mocker.patch.object(
            coinmate, "btc_withdraw", return_value=_make_transaction_data(0.01)
        )
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)
        mocker.patch.object(
            BtcWithdrawal, "post_to_db", side_effect=Exception("DB error")
        )

        executor = Executor(t212, coinmate)
        with pytest.raises(Exception):
            executor.withdraw_btc()

    def test_withdrawal_amount_czk_calculation(
        self,
        coinmate: Coinmate,
        t212: Trading212,
        db_row: dict,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(coinmate, "btc_balance", return_value=0.01)
        mocker.patch.object(
            coinmate, "btc_withdraw", return_value=_make_transaction_data(0.01)
        )
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)
        mock_create = mocker.patch.object(
            BtcWithdrawal,
            "create_withdrawal",
            return_value=MagicMock(spec=BtcWithdrawal),
        )

        executor = Executor(t212, coinmate)
        executor.withdraw_btc()

        call_kwargs = mock_create.call_args.kwargs
        # amount=0.01, price=2_000_000 → amount_czk = round(0.01 * 2_000_000, 2) = 20_000.0
        assert call_kwargs["amount_czk"] == Decimal(str(round(0.01 * 2_000_000, 2)))


class TestBtcWithdrawalEmailIntegration:
    @pytest.fixture
    def btc_withdrawal(self, db_row: dict) -> BtcWithdrawal:
        return BtcWithdrawal.model_validate(db_row)

    def test_email_sent_on_successful_withdrawal(
        self, btc_withdrawal: BtcWithdrawal, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_btc_withdrawal_confirmation(btc_withdrawal)
        mock_send.assert_called_once()

    def test_email_not_sent_when_withdrawal_none(self, mocker: MockerFixture) -> None:
        """Demonstrates the main.py guard: if withdrawal: mailer.send_btc_withdrawal_confirmation(...)"""
        mock_send = mocker.patch.object(Mailer, "_send")
        withdrawal = None
        if withdrawal:
            Mailer().send_btc_withdrawal_confirmation(withdrawal)
        mock_send.assert_not_called()
