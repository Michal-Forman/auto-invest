# Standard library
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List
from unittest.mock import MagicMock
from uuid import UUID

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from core.db.orders import Order, OrderUpdate


def _build_supabase_mock(mocker: MockerFixture) -> tuple:
    """Patch db.base.supabase and db.orders.supabase with a fluent mock chain. Returns (mock_sb, mock_chain)."""
    mock_sb = mocker.patch("core.db.base.supabase")
    mocker.patch("core.db.orders.supabase", mock_sb)
    mock_chain = MagicMock()
    mock_sb.table.return_value = mock_chain
    for method in [
        "select",
        "insert",
        "update",
        "eq",
        "neq",
        "gte",
        "lt",
        "limit",
        "order",
    ]:
        getattr(mock_chain, method).return_value = mock_chain
    return mock_sb, mock_chain


def _order_row(order: Order) -> Dict[str, Any]:
    """Serialize an Order to a JSON-compatible dict for use as a mock DB row."""
    d = order.model_dump(mode="json")
    d["id"] = str(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
    d["created_at"] = "2026-03-03T09:00:00+00:00"
    return d


class TestValidateBusinessRules:
    def test_limit_order_without_limit_price_raises(
        self, make_order: Callable[..., Order]
    ) -> None:
        with pytest.raises(ValueError, match="LIMIT order must have limit_price"):
            make_order(order_type="LIMIT", limit_price=None)


class TestToInsertDict:
    def test_returns_dict_with_all_required_fields(
        self, make_order: Callable[..., Order]
    ) -> None:
        order = make_order()
        d = order._to_insert_dict()
        for field in ["run_id", "exchange", "t212_ticker", "idempotency_key"]:
            assert field in d

    def test_excludes_none_fields(self, make_order: Callable[..., Order]) -> None:
        order = make_order()
        d = order._to_insert_dict()
        # id is None until inserted → should be excluded
        assert "id" not in d


class TestPostToDB:
    def test_post_to_db_returns_inserted_order(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        order = make_order()
        _, mock_chain = _build_supabase_mock(mocker)
        row = _order_row(order)
        mock_chain.execute.return_value = MagicMock(data=[row])

        result = order.post_to_db()

        assert result == row
        assert order.id == UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    def test_post_to_db_returns_none_on_idempotency_conflict(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        order = make_order()
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        result = order.post_to_db()

        assert result is None

    def test_post_to_db_raises_on_unexpected_error(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        order = make_order()
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError, match="DB error"):
            order.post_to_db()


class TestUpdateInDb:
    def test_update_in_db_sends_only_non_none_fields(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        order = make_order(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
        _, mock_chain = _build_supabase_mock(mocker)
        row = _order_row(order)
        mock_chain.execute.return_value = MagicMock(data=[row])

        update = OrderUpdate(status="FILLED", filled_quantity=Decimal("2.5"))
        order.update_in_db(update)

        call_data = mock_chain.update.call_args[0][0]
        assert "status" in call_data
        assert "filled_quantity" in call_data
        # None fields should be excluded
        assert "filled_at" not in call_data
        assert "fee" not in call_data

    def test_update_in_db_calls_supabase_update(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        order = make_order(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
        _, mock_chain = _build_supabase_mock(mocker)
        row = _order_row(order)
        mock_chain.execute.return_value = MagicMock(data=[row])

        order.update_in_db(OrderUpdate(status="FILLED"))

        mock_chain.update.assert_called_once()


class TestGetSubmittedOrders:
    def test_returns_list_of_submitted_orders(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        order = make_order()
        _, mock_chain = _build_supabase_mock(mocker)
        row = _order_row(order)
        mock_chain.execute.return_value = MagicMock(data=[row])

        result = Order.get_submitted_orders()

        assert len(result) == 1
        assert isinstance(result[0], Order)

    def test_returns_empty_list_when_none(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        result = Order.get_submitted_orders()

        assert result == []


def _coinmate_history(order_id: str) -> Dict[str, Any]:
    """Build a minimal valid Coinmate user_trades response."""
    return {
        "req": None,
        "res": {
            "error": False,
            "data": [
                {
                    "orderId": order_id,
                    "amount": 0.001,
                    "price": 2_000_000.0,
                    "fee": 50.0,
                    "createdTimestamp": 1_741_000_800_000,
                }
            ],
        },
        "err": None,
    }


def _t212_history(order_id: str) -> List[Dict[str, Any]]:
    """Build a minimal valid T212 orders_page response."""
    return [
        {
            "order": {
                "id": order_id,
                "status": "FILLED",
                "filledQuantity": 2.5,
            },
            "fill": {
                "walletImpact": {
                    "fxRate": 0.04,
                    "taxes": [{"quantity": 10.0, "currency": "CZK"}],
                    "netValue": 250.0,
                },
                "filledAt": "2026-03-03T09:00:00Z",
                "price": 100.0,
            },
        }
    ]


class TestUpdateOrders:
    def test_coinmate_order_matched_and_updated(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        btc_order = make_order(
            t212_ticker="BTC",
            exchange="COINMATE",
            external_order_id="CM123",
            status="SUBMITTED",
        )
        mocker.patch.object(Order, "get_submitted_orders", return_value=[btc_order])
        mock_update = mocker.patch.object(Order, "update_in_db", return_value={})

        mock_coinmate = MagicMock()
        mock_coinmate.user_trades.return_value = _coinmate_history("CM123")
        mock_t212 = MagicMock()
        mock_t212.orders_page.return_value = []

        Order.update_orders(mock_t212, mock_coinmate)

        mock_update.assert_called_once()

    def test_t212_order_matched_in_history(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        t212_order = make_order(
            t212_ticker="VWCEd_EQ",
            exchange="T212",
            external_order_id="T212-456",
            status="SUBMITTED",
        )
        mocker.patch.object(Order, "get_submitted_orders", return_value=[t212_order])
        mock_update = mocker.patch.object(Order, "update_in_db", return_value={})

        mock_coinmate = MagicMock()
        mock_coinmate.user_trades.return_value = {
            "req": None,
            "res": {"error": False, "data": []},
            "err": None,
        }
        mock_t212 = MagicMock()
        mock_t212.orders_page.return_value = _t212_history("T212-456")

        Order.update_orders(mock_t212, mock_coinmate)

        mock_update.assert_called_once()

    def test_t212_order_falls_back_to_equity_order(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        # T212 external_order_id must be a numeric string (cast to int in update_orders)
        t212_order = make_order(
            t212_ticker="VWCEd_EQ",
            exchange="T212",
            external_order_id="789",
            status="SUBMITTED",
        )
        mocker.patch.object(Order, "get_submitted_orders", return_value=[t212_order])
        mock_update = mocker.patch.object(Order, "update_in_db", return_value={})

        mock_coinmate = MagicMock()
        mock_coinmate.user_trades.return_value = {
            "req": None,
            "res": {"error": False, "data": []},
            "err": None,
        }
        mock_t212 = MagicMock()
        mock_t212.orders_page.return_value = []  # not in history
        mock_t212.equity_order.return_value = {
            "req": None,
            "res": {"id": "789"},
            "err": None,  # still pending, no error
        }

        Order.update_orders(mock_t212, mock_coinmate)

        mock_t212.equity_order.assert_called_once_with(789)
        mock_update.assert_not_called()  # still pending → no DB update

    def test_unmatched_order_stays_submitted(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        btc_order = make_order(
            t212_ticker="BTC",
            exchange="COINMATE",
            external_order_id="CM999",
            status="SUBMITTED",
        )
        mocker.patch.object(Order, "get_submitted_orders", return_value=[btc_order])
        mock_update = mocker.patch.object(Order, "update_in_db", return_value={})

        mock_coinmate = MagicMock()
        mock_coinmate.user_trades.return_value = {
            "req": None,
            "res": {"error": False, "data": []},  # no matching order
            "err": None,
        }
        mock_t212 = MagicMock()
        mock_t212.orders_page.return_value = []

        Order.update_orders(mock_t212, mock_coinmate)

        mock_update.assert_not_called()
        assert btc_order.status == "SUBMITTED"

    def test_logs_error_and_continues_on_exception(
        self, make_order: Callable[..., Order], mocker: MockerFixture
    ) -> None:
        btc_order = make_order(
            t212_ticker="BTC",
            exchange="COINMATE",
            external_order_id="CM123",
            status="SUBMITTED",
        )
        t212_order = make_order(
            t212_ticker="VWCEd_EQ",
            exchange="T212",
            external_order_id="T212-123",
            status="SUBMITTED",
        )
        mocker.patch.object(
            Order, "get_submitted_orders", return_value=[btc_order, t212_order]
        )
        mock_update = mocker.patch.object(Order, "update_in_db")
        mock_update.side_effect = [RuntimeError("DB error"), {}]

        mock_coinmate = MagicMock()
        mock_coinmate.user_trades.return_value = _coinmate_history("CM123")
        mock_t212 = MagicMock()
        mock_t212.orders_page.return_value = _t212_history("T212-123")

        # Should not raise despite first update failing
        Order.update_orders(mock_t212, mock_coinmate)

        # Both matched orders had update_in_db called
        assert mock_update.call_count == 2
