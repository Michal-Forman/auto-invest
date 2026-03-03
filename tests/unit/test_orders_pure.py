# Standard library
from datetime import datetime, timezone
from typing import Any, Callable, Dict
from uuid import UUID

# Third-party
import pytest

# Local
from db.orders import Order, OrderUpdate


class TestGenerateIdempotencyKey:
    def test_same_inputs_produce_same_key(
        self, make_order: Callable[..., Order]
    ) -> None:
        order1 = make_order()
        order2 = make_order()
        assert order1.idempotency_key == order2.idempotency_key

    def test_different_run_id_produces_different_key(
        self, make_order: Callable[..., Order]
    ) -> None:
        order1 = make_order(run_id=UUID("11111111-1111-1111-1111-111111111111"))
        order2 = make_order(run_id=UUID("22222222-2222-2222-2222-222222222222"))
        assert order1.idempotency_key != order2.idempotency_key

    def test_different_quantity_produces_different_key(
        self, make_order: Callable[..., Order]
    ) -> None:
        order1 = make_order(quantity=1.0, total=100.0, total_czk=2500.0)
        order2 = make_order(quantity=2.0, total=200.0, total_czk=5000.0)
        assert order1.idempotency_key != order2.idempotency_key

    def test_key_is_64_char_hex(self, make_order: Callable[..., Order]) -> None:
        order = make_order()
        assert order.idempotency_key is not None
        assert len(order.idempotency_key) == 64
        assert all(c in "0123456789abcdef" for c in order.idempotency_key)


class TestProcessNewCoinmateData:
    def _make_data(self, **overrides: Any) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "amount": 0.001,
            "price": 2_000_000.0,
            "fee": 50.0,
            "createdTimestamp": 1_740_992_400_000,
            "orderId": "CM123",
        }
        base.update(overrides)
        return base

    def test_filled_status_when_amount_nonzero(self) -> None:
        update = Order._process_new_coinmate_data(self._make_data(amount=0.001))
        assert update.status == "FILLED"

    def test_failed_status_when_amount_zero(self) -> None:
        update = Order._process_new_coinmate_data(
            self._make_data(amount=0, price=0.0, fee=0.0)
        )
        assert update.status == "FAILED"

    def test_filled_total_calculated_correctly(self) -> None:
        # filled_total = amount * price - fee = 0.001 * 2_000_000 - 50 = 1950
        update = Order._process_new_coinmate_data(
            self._make_data(amount=0.001, price=2_000_000.0, fee=50.0)
        )
        assert update.filled_total == pytest.approx(1950.0)

    def test_timestamp_converted_to_utc_datetime(self) -> None:
        expected_dt = datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc)
        ts_ms = int(expected_dt.timestamp() * 1000)
        update = Order._process_new_coinmate_data(self._make_data(createdTimestamp=ts_ms))
        assert update.filled_at == expected_dt


class TestProcessNewT212Data:
    def test_cancelled_status(self) -> None:
        item: Dict[str, Any] = {
            "order": {"status": "CANCELLED", "filledQuantity": 0.0},
        }
        update = Order._process_new_t212_data(item)
        assert update.status == "CANCELLED"

    def test_filled_status_with_fill(self) -> None:
        item: Dict[str, Any] = {
            "order": {"status": "FILLED", "filledQuantity": 2.5},
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
        update = Order._process_new_t212_data(item)
        assert update.status == "FILLED"
        assert update.fill_fx_rate == pytest.approx(25.0)  # 1 / 0.04
        assert update.filled_total_czk == 250.0
        assert update.filled_total == pytest.approx(10.0)  # 250.0 / 25.0
        assert update.fee == 10.0
        assert update.fee_currency == "CZK"

    def test_submitted_status_without_fill(self) -> None:
        item: Dict[str, Any] = {
            "order": {"status": "FILLED", "filledQuantity": 0.0},
        }
        update = Order._process_new_t212_data(item)
        assert update.status == "SUBMITTED"
        assert update.fill_fx_rate is None
        assert update.filled_total_czk is None
        assert update.filled_total is None
