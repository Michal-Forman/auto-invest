# Standard library
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import MagicMock
from uuid import UUID

# Third-party
from freezegun import freeze_time
import pytest
from pytest_mock import MockerFixture

# Local
from core.db.orders import Order
from core.db.runs import Run


def _run_row(
    finished_at: str = "2026-03-03T09:05:00+00:00",
    status: str = "FINISHED",
) -> dict:
    """Build a minimal valid DB row for a Run."""
    return {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "started_at": "2026-03-03T09:00:00+00:00",
        "finished_at": finished_at,
        "status": status,
        "invest_amount": 5000.0,
        "invest_interval": "0 9 * * *",
        "t212_default_weight": 95.0,
        "btc_default_weight": 0.05,
        "test": False,
    }


class TestRunFillTransition:
    def test_run_transitions_to_filled_when_all_orders_filled(
        self,
        supabase_mocks: SimpleNamespace,
    ) -> None:
        """FINISHED run with all orders filled → status set to FILLED with correct total."""
        supabase_mocks.runs_chain.execute.return_value = MagicMock(data=[_run_row()])
        supabase_mocks.orders_chain.execute.side_effect = [
            MagicMock(count=0, data=[]),  # _are_all_orders_filled
            MagicMock(
                data=[{"filled_total_czk": 4950.0}], count=1
            ),  # _sum_orders_filled_czk
        ]

        Run.update_runs()

        update_call = supabase_mocks.runs_chain.update.call_args[0][0]
        assert update_call["status"] == "FILLED"
        assert update_call["filled_total_czk"] == pytest.approx(4950.0)

    def test_run_stays_finished_when_orders_still_pending(
        self,
        supabase_mocks: SimpleNamespace,
    ) -> None:
        """FINISHED run with unfilled orders → no update fired."""
        supabase_mocks.runs_chain.execute.return_value = MagicMock(data=[_run_row()])
        supabase_mocks.orders_chain.execute.return_value = MagicMock(count=2, data=[])

        Run.update_runs()

        supabase_mocks.runs_chain.update.assert_not_called()


class TestRunExpiryTransition:
    @freeze_time("2026-03-03 09:00:00")
    def test_run_transitions_to_failed_after_14_days(
        self,
        supabase_mocks: SimpleNamespace,
    ) -> None:
        """FINISHED run older than 14 days → status set to FAILED."""
        # finished_at is 15 days before the frozen now → past the 14-day threshold
        old_finished_at = "2026-02-16T09:05:00+00:00"
        row = _run_row(finished_at=old_finished_at)

        supabase_mocks.runs_chain.execute.side_effect = [
            MagicMock(data=[row]),  # _get_finished_runs
            MagicMock(
                data=[{"status": "FAILED"}]
            ),  # update_in_db (sets in-memory status)
        ]
        # After in-memory status becomes FAILED, _try_mark_run_filled still runs;
        # make _are_all_orders_filled return count=2 so it exits early.
        supabase_mocks.orders_chain.execute.return_value = MagicMock(count=2, data=[])

        Run.update_runs()

        update_call = supabase_mocks.runs_chain.update.call_args_list[0][0][0]
        assert update_call["status"] == "FAILED"


class TestRunUpdateRoundTrip:
    def test_process_new_run_data_to_update_in_db_round_trip(
        self,
        make_run: Callable[..., Run],
        make_order: Callable[..., Order],
        supabase_mocks: SimpleNamespace,
    ) -> None:
        """process_new_run_data + update_in_db writes correct fields to the DB."""
        run = make_run()

        vwce_order = make_order(
            total_czk=3000.0,
            multiplier=1.5,
            status="FILLED",
        )
        btc_order = make_order(
            t212_ticker="BTC",
            exchange="COINMATE",
            instrument_type="CRYPTO",
            yahoo_symbol="BTC-USD",
            name="Bitcoin",
            currency="CZK",
            order_type="INSTANT",
            fx_rate=1.0,
            total_czk=2000.0,
            total=2000.0,
            multiplier=1.333,
            status="SUBMITTED",
        )

        run_update = Run.process_new_run_data([vwce_order, btc_order])
        run.update_in_db(run_update)

        update_call = supabase_mocks.runs_chain.update.call_args[0][0]
        assert update_call["status"] == "FINISHED"
        assert update_call["total_orders"] == 2
        assert update_call["distribution"] is not None
        assert "VWCEd_EQ" in update_call["distribution"]
        assert "BTC" in update_call["distribution"]
        assert update_call["planned_total_czk"] == pytest.approx(
            vwce_order.total_czk + btc_order.total_czk
        )
