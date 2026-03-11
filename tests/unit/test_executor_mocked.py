# Standard library
from decimal import Decimal
from typing import Any, Dict
from unittest.mock import MagicMock
from uuid import UUID

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from core.db.btc_withdrawals import BtcWithdrawal
from core.db.orders import Order
from core.executor import Executor
from core.instruments import Instruments


@pytest.fixture
def mock_coinmate() -> MagicMock:
    return MagicMock()


@pytest.fixture
def executor(
    mock_t212: MagicMock,
    mock_coinmate: MagicMock,
) -> Executor:
    return Executor(mock_t212, mock_coinmate)


@pytest.fixture
def run_id() -> UUID:
    return UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class TestPlaceBtcOrder:
    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        mocker.patch.object(Order, "post_to_db", return_value={})
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)

    def test_submitted_on_success(
        self, executor: Executor, run_id: UUID, mock_coinmate: MagicMock
    ) -> None:
        mock_coinmate.buy_instant.return_value = {
            "req": None,
            "res": {"error": False, "data": "CM99"},
            "err": None,
        }
        order = executor._place_btc_order(500.0, 1.0, run_id)
        assert order.status == "SUBMITTED"
        assert order.external_order_id == "CM99"

    def test_failed_on_error_true(
        self, executor: Executor, run_id: UUID, mock_coinmate: MagicMock
    ) -> None:
        mock_coinmate.buy_instant.return_value = {
            "req": None,
            "res": {"error": True, "data": None},
            "err": None,
        }
        order = executor._place_btc_order(500.0, 1.0, run_id)
        assert order.status == "FAILED"

    def test_failed_on_no_response(
        self, executor: Executor, run_id: UUID, mock_coinmate: MagicMock
    ) -> None:
        mock_coinmate.buy_instant.return_value = {
            "req": None,
            "res": None,
            "err": "timeout",
        }
        order = executor._place_btc_order(500.0, 1.0, run_id)
        assert order.status == "FAILED"

    def test_quantity_is_amount_over_price(
        self, executor: Executor, run_id: UUID, mock_coinmate: MagicMock
    ) -> None:
        mock_coinmate.buy_instant.return_value = {
            "req": None,
            "res": {"error": False, "data": "CM100"},
            "err": None,
        }
        order = executor._place_btc_order(500.0, 1.0, run_id)
        assert order.quantity == pytest.approx(round(500.0 / 2_000_000, 8))

    def test_logs_error_when_post_to_db_raises(
        self,
        executor: Executor,
        run_id: UUID,
        mock_coinmate: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_coinmate.buy_instant.return_value = {
            "req": None,
            "res": {"error": False, "data": "CM99"},
            "err": None,
        }
        mocker.patch.object(Order, "post_to_db", side_effect=RuntimeError("DB down"))
        mock_log_error = mocker.patch("core.executor.log.error")

        executor._place_btc_order(500.0, 1.0, run_id)

        mock_log_error.assert_called_once()
        assert "Failed to insert BTC order" in mock_log_error.call_args[0][0]

    def test_logs_info_on_successful_db_insert(
        self,
        executor: Executor,
        run_id: UUID,
        mock_coinmate: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_coinmate.buy_instant.return_value = {
            "req": None,
            "res": {"error": False, "data": "CM99"},
            "err": None,
        }
        mocker.patch.object(Order, "post_to_db", return_value={"id": "some-uuid"})
        mock_log_info = mocker.patch("core.executor.log.info")

        executor._place_btc_order(500.0, 1.0, run_id)

        info_calls = [str(c) for c in mock_log_info.call_args_list]
        assert any("BTC order recorded" in c for c in info_calls)


class TestPlaceT212Order:
    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        mocker.patch.object(Order, "post_to_db", return_value={})
        mocker.patch.object(Instruments, "get_fx_rate_to_czk", return_value=25.0)
        mocker.patch.object(Instruments, "get_current_price", return_value=100.0)

    def _t212_response(
        self, filled_qty: float, qty: float, order_id: str = "T212-1"
    ) -> Dict[str, Any]:
        return {
            "req": None,
            "res": {
                "filledQuantity": filled_qty,
                "quantity": qty,
                "extendedHours": False,
                "id": order_id,
            },
            "err": None,
        }

    def test_filled_when_fully_matched(
        self, executor: Executor, run_id: UUID, mock_t212: MagicMock
    ) -> None:
        mock_t212.equity_order_place_market.return_value = self._t212_response(2.0, 2.0)
        order = executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)
        assert order.status == "FILLED"

    def test_submitted_when_unfilled(
        self, executor: Executor, run_id: UUID, mock_t212: MagicMock
    ) -> None:
        mock_t212.equity_order_place_market.return_value = self._t212_response(
            0, 2.0, "T212-2"
        )
        order = executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)
        assert order.status == "SUBMITTED"

    def test_partially_filled(
        self, executor: Executor, run_id: UUID, mock_t212: MagicMock
    ) -> None:
        mock_t212.equity_order_place_market.return_value = self._t212_response(
            1.0, 2.0, "T212-3"
        )
        order = executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)
        assert order.status == "PARTIALLY_FILLED"

    def test_failed_when_no_response(
        self, executor: Executor, run_id: UUID, mock_t212: MagicMock
    ) -> None:
        mock_t212.equity_order_place_market.return_value = {
            "req": None,
            "res": None,
            "err": None,
        }
        order = executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)
        assert order.status == "FAILED"

    def test_shares_calculated_from_fx_and_price(
        self, executor: Executor, run_id: UUID, mock_t212: MagicMock
    ) -> None:
        # amount=5000, fx=25, price=100 → shares = 5000/25/100 = 2.0
        mock_t212.equity_order_place_market.return_value = self._t212_response(
            2.0, 2.0, "T212-4"
        )
        order = executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)
        assert order.quantity == pytest.approx(2.0)

    def test_logs_warning_when_filled_quantity_is_unknown(
        self,
        executor: Executor,
        run_id: UUID,
        mock_t212: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # filledQuantity < 0 triggers UNKNOWN branch
        mock_t212.equity_order_place_market.return_value = self._t212_response(
            -1.0, 2.0
        )
        mock_log_warning = mocker.patch("core.executor.log.warning")

        order = executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)

        assert order.status == "UNKNOWN"
        warning_calls = [str(c) for c in mock_log_warning.call_args_list]
        assert any("Unexpected filledQuantity" in c for c in warning_calls)

    def test_logs_error_when_post_to_db_raises(
        self,
        executor: Executor,
        run_id: UUID,
        mock_t212: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_t212.equity_order_place_market.return_value = self._t212_response(0, 2.0)
        mocker.patch.object(Order, "post_to_db", side_effect=RuntimeError("DB down"))
        mock_log_error = mocker.patch("core.executor.log.error")

        executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)

        mock_log_error.assert_called_once()
        assert "Failed to insert" in mock_log_error.call_args[0][0]

    def test_logs_info_on_successful_db_insert(
        self,
        executor: Executor,
        run_id: UUID,
        mock_t212: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_t212.equity_order_place_market.return_value = self._t212_response(2.0, 2.0)
        mocker.patch.object(Order, "post_to_db", return_value={"id": "some-uuid"})
        mock_log_info = mocker.patch("core.executor.log.info")

        executor._place_t212_order("VWCEd_EQ", 5000.0, 1.0, run_id)

        info_calls = [str(c) for c in mock_log_info.call_args_list]
        assert any("order recorded" in c for c in info_calls)


class TestPlaceOrders:
    def test_btc_routed_to_coinmate(
        self, executor: Executor, run_id: UUID, mocker: MockerFixture
    ) -> None:
        mock_btc = mocker.patch.object(
            Executor, "_place_btc_order", return_value=MagicMock()
        )
        mocker.patch.object(Executor, "_place_t212_order", return_value=MagicMock())
        executor.place_orders({"BTC": 500.0}, {"BTC": 1.0}, run_id)
        mock_btc.assert_called_once()

    def test_t212_tickers_routed_to_t212(
        self, executor: Executor, run_id: UUID, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(Executor, "_place_btc_order", return_value=MagicMock())
        mock_t212_order = mocker.patch.object(
            Executor, "_place_t212_order", return_value=MagicMock()
        )
        executor.place_orders({"VWCEd_EQ": 4500.0}, {"VWCEd_EQ": 1.0}, run_id)
        mock_t212_order.assert_called_once()

    def test_mixed_returns_all_orders(
        self, executor: Executor, run_id: UUID, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(Executor, "_place_btc_order", return_value=MagicMock())
        mocker.patch.object(Executor, "_place_t212_order", return_value=MagicMock())
        result = executor.place_orders(
            {"BTC": 250.0, "VWCEd_EQ": 4750.0},
            {"BTC": 1.0, "VWCEd_EQ": 1.0},
            run_id,
        )
        assert len(result) == 2


class TestWithdrawBtc:
    @pytest.fixture
    def mock_transaction_data(self) -> Dict[str, Any]:
        return {
            "id": "17751183",
            "fee": Decimal("0.0001"),
            "currency": "BTC",
            "amount": Decimal("0.005"),
            "status": "CREATED",
            "timestamp": 1741000000000,
            "transfer_type": "WITHDRAWAL",
            "destination_adress": "bc1qtest",
        }

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mock_coinmate: MagicMock,
        mock_transaction_data: Dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        mock_coinmate.btc_balance.return_value = 0.005
        mock_coinmate.btc_withdraw.return_value = mock_transaction_data
        mocker.patch.object(Instruments, "get_btc_price", return_value=2_000_000.0)
        mocker.patch.object(
            BtcWithdrawal,
            "create_withdrawal",
            return_value=MagicMock(spec=BtcWithdrawal),
        )

    def test_returns_btc_withdrawal_on_success(self, executor: Executor) -> None:
        result = executor.withdraw_btc()
        assert isinstance(result, BtcWithdrawal)

    def test_raises_on_coinmate_error(
        self, executor: Executor, mock_coinmate: MagicMock
    ) -> None:
        mock_coinmate.btc_balance.side_effect = Exception("network error")
        with pytest.raises(Exception):
            executor.withdraw_btc()

    def test_raises_on_db_error(
        self, executor: Executor, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            BtcWithdrawal, "create_withdrawal", side_effect=RuntimeError("DB failed")
        )
        with pytest.raises(RuntimeError):
            executor.withdraw_btc()

    def test_uses_full_balance_for_amount(
        self, executor: Executor, mock_coinmate: MagicMock
    ) -> None:
        executor.withdraw_btc()
        call_kwargs = mock_coinmate.btc_withdraw.call_args.kwargs
        assert call_kwargs["amount"] == 0.005

    def test_uses_settings_address(
        self, mock_t212: MagicMock, mock_coinmate: MagicMock
    ) -> None:
        ex = Executor(mock_t212, mock_coinmate, btc_external_adress="bc1qtestaddress")
        ex.withdraw_btc()
        call_kwargs = mock_coinmate.btc_withdraw.call_args.kwargs
        assert call_kwargs["btc_adress"] == "bc1qtestaddress"

    def test_amount_czk_computed_from_actual_amount_and_price(
        self, executor: Executor, mocker: MockerFixture
    ) -> None:
        # amount=0.005, price=2_000_000 → amount_czk = 10_000.00
        mock_create = mocker.patch.object(
            BtcWithdrawal,
            "create_withdrawal",
            return_value=MagicMock(spec=BtcWithdrawal),
        )
        executor.withdraw_btc()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["amount_czk"] == Decimal("10000.0")
