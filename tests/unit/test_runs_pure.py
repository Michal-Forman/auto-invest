# Standard library
from decimal import Decimal
from typing import Callable

# Third-party
import pytest

# Local
from core.db.orders import Order
from core.db.runs import Run


class TestProcessNewRunData:
    def test_total_order_count(self, make_order: Callable[..., Order]) -> None:
        orders = [
            make_order(t212_ticker="VWCEd_EQ"),
            make_order(t212_ticker="BTC"),
            make_order(t212_ticker="CSPX_EQ"),
        ]
        update = Run.process_new_run_data(orders)
        assert update.total_orders == 3

    def test_successful_and_failed_counts(
        self, make_order: Callable[..., Order]
    ) -> None:
        orders = [
            make_order(t212_ticker="VWCEd_EQ", status="SUBMITTED"),
            make_order(t212_ticker="BTC", status="FILLED"),
            make_order(t212_ticker="CSPX_EQ", status="FAILED"),
        ]
        update = Run.process_new_run_data(orders)
        assert update.successful_orders == 2
        assert update.failed_orders == 1

    def test_planned_total_czk(self, make_order: Callable[..., Order]) -> None:
        orders = [
            make_order(t212_ticker="VWCEd_EQ", total_czk=1000.0),
            make_order(t212_ticker="BTC", total_czk=2000.0),
            make_order(t212_ticker="CSPX_EQ", total_czk=1500.0),
        ]
        update = Run.process_new_run_data(orders)
        assert update.planned_total_czk == Decimal("4500")

    def test_distribution_dict(self, make_order: Callable[..., Order]) -> None:
        orders = [
            make_order(t212_ticker="VWCEd_EQ", total_czk=3000.0),
            make_order(t212_ticker="BTC", total_czk=2000.0),
        ]
        update = Run.process_new_run_data(orders)
        assert update.distribution == {
            "VWCEd_EQ": Decimal("3000"),
            "BTC": Decimal("2000"),
        }

    def test_multipliers_dict(self, make_order: Callable[..., Order]) -> None:
        orders = [
            make_order(t212_ticker="VWCEd_EQ", multiplier=1.5),
            make_order(t212_ticker="BTC", multiplier=2.0),
        ]
        update = Run.process_new_run_data(orders)
        assert update.multipliers == {
            "VWCEd_EQ": Decimal("1.5"),
            "BTC": Decimal("2.0"),
        }

    def test_errors_joined_with_semicolon(
        self, make_order: Callable[..., Order]
    ) -> None:
        orders = [
            make_order(t212_ticker="VWCEd_EQ", error="timeout"),
            make_order(t212_ticker="BTC", error="rejected"),
            make_order(t212_ticker="CSPX_EQ"),
        ]
        update = Run.process_new_run_data(orders)
        assert update.error == "timeout; rejected"

    def test_no_errors_is_none(self, make_order: Callable[..., Order]) -> None:
        orders = [make_order(t212_ticker="VWCEd_EQ"), make_order(t212_ticker="BTC")]
        update = Run.process_new_run_data(orders)
        assert update.error is None

    def test_status_is_always_finished(self, make_order: Callable[..., Order]) -> None:
        orders = [make_order()]
        update = Run.process_new_run_data(orders)
        assert update.status == "FINISHED"
