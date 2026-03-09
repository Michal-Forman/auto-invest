# Standard library
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from core.coinmate import Coinmate
from core.db.orders import Order
from core.trading212 import Trading212


def _submitted_order_row(
    order_id: str,
    ticker: str,
    exchange: str,
    *,
    instrument_type: str = "ETF",
    yahoo_symbol: str = "VWCE.DE",
    currency: str = "EUR",
    order_type: str = "MARKET",
) -> dict:
    """Build a minimal valid DB row for a SUBMITTED order."""
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "run_id": "22222222-2222-2222-2222-222222222222",
        "exchange": exchange,
        "instrument_type": instrument_type,
        "t212_ticker": ticker,
        "yahoo_symbol": yahoo_symbol,
        "name": "Test Instrument",
        "currency": currency,
        "side": "BUY",
        "order_type": order_type,
        "fx_rate": 25.0,
        "price": 100.0,
        "quantity": 1.5,
        "total": 150.0,
        "total_czk": 3750.0,
        "extended_hours": False,
        "multiplier": 1.5,
        "status": "SUBMITTED",
        "external_order_id": order_id,
        "submitted_at": "2026-03-03T09:00:00+00:00",
        "idempotency_key": "a" * 64,
    }


class TestT212OrderMatching:
    def test_t212_order_matched_and_filled_with_correct_fx_rate(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        supabase_mocks: SimpleNamespace,
        t212_history_item: dict,
    ) -> None:
        """SUBMITTED T212 order matched by external_order_id; fill fields and inverted FX written to DB."""
        order_row = _submitted_order_row("12345", "VWCEd_EQ", "T212")
        supabase_mocks.orders_chain.execute.side_effect = [
            MagicMock(data=[order_row]),  # get_submitted_orders
            MagicMock(data=[]),  # update_in_db
        ]

        mocker.patch.object(t212, "orders_page", return_value=[t212_history_item])
        mocker.patch.object(
            coinmate,
            "user_trades",
            return_value={"req": {}, "res": {"error": False, "data": []}, "err": None},
        )

        Order.update_orders(t212, coinmate)

        update_call = supabase_mocks.orders_chain.update.call_args[0][0]
        assert update_call["status"] == "FILLED"
        assert update_call["fill_fx_rate"] == pytest.approx(25.0)  # 1/0.04
        assert update_call["filled_total_czk"] == pytest.approx(1000.0)
        assert update_call.get("fee_czk") is None  # EUR fee, not CZK

    def test_unmatched_t212_order_falls_back_to_equity_order_api(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        supabase_mocks: SimpleNamespace,
    ) -> None:
        """When order is absent from orders_page, falls back to equity_order(int(id))."""
        order_row = _submitted_order_row("5678", "VWCEd_EQ", "T212")
        supabase_mocks.orders_chain.execute.side_effect = [
            MagicMock(data=[order_row]),  # get_submitted_orders
        ]

        mocker.patch.object(t212, "orders_page", return_value=[])
        mock_equity_order = mocker.patch.object(
            t212,
            "equity_order",
            return_value={"req": {}, "res": {"status": "SUBMITTED"}, "err": None},
        )
        mocker.patch.object(
            coinmate,
            "user_trades",
            return_value={"req": {}, "res": {"error": False, "data": []}, "err": None},
        )

        Order.update_orders(t212, coinmate)

        # Must be called with int — proves external_order_id was a numeric string
        mock_equity_order.assert_called_once_with(5678)
        # No fill data → no DB update
        supabase_mocks.orders_chain.update.assert_not_called()


class TestCoinmateOrderMatching:
    def test_coinmate_order_matched_and_fill_total_computed(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        supabase_mocks: SimpleNamespace,
        coinmate_history_response: dict,
    ) -> None:
        """SUBMITTED BTC order matched by orderId; filled_total = amount*price - fee."""
        order_row = _submitted_order_row(
            "987654",
            "BTC",
            "COINMATE",
            instrument_type="CRYPTO",
            yahoo_symbol="BTC-USD",
            currency="CZK",
            order_type="INSTANT",
        )
        supabase_mocks.orders_chain.execute.side_effect = [
            MagicMock(data=[order_row]),  # get_submitted_orders
            MagicMock(data=[]),  # update_in_db
        ]

        mocker.patch.object(t212, "orders_page", return_value=[])
        mocker.patch.object(
            coinmate, "user_trades", return_value=coinmate_history_response
        )

        Order.update_orders(t212, coinmate)

        update_call = supabase_mocks.orders_chain.update.call_args[0][0]
        assert update_call["status"] == "FILLED"
        assert update_call["filled_total"] == pytest.approx(
            2475.0
        )  # 0.001*2_500_000 - 25
        assert update_call["fill_fx_rate"] == pytest.approx(1.0)
        assert update_call["fee_czk"] == pytest.approx(25.0)  # CZK fee


class TestMixedOrders:
    def test_mixed_t212_and_coinmate_orders_both_updated(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        supabase_mocks: SimpleNamespace,
        t212_history_item: dict,
        coinmate_history_response: dict,
    ) -> None:
        """Two SUBMITTED orders (BTC + T212) both get matched; two DB updates fire."""
        t212_row = _submitted_order_row("12345", "VWCEd_EQ", "T212")
        btc_row = _submitted_order_row(
            "987654",
            "BTC",
            "COINMATE",
            instrument_type="CRYPTO",
            yahoo_symbol="BTC-USD",
            currency="CZK",
            order_type="INSTANT",
        )
        # Override id so the two orders are distinct in DB
        btc_row = {**btc_row, "id": "33333333-3333-3333-3333-333333333333"}

        supabase_mocks.orders_chain.execute.side_effect = [
            MagicMock(data=[t212_row, btc_row]),  # get_submitted_orders
            MagicMock(data=[]),  # update_in_db (T212 order)
            MagicMock(data=[]),  # update_in_db (BTC order)
        ]

        mocker.patch.object(t212, "orders_page", return_value=[t212_history_item])
        mocker.patch.object(
            coinmate, "user_trades", return_value=coinmate_history_response
        )

        Order.update_orders(t212, coinmate)

        assert supabase_mocks.orders_chain.update.call_count == 2
        all_statuses = [
            call[0][0]["status"]
            for call in supabase_mocks.orders_chain.update.call_args_list
        ]
        assert set(all_statuses) == {"FILLED"}
