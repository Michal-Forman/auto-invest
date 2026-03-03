# Standard library
from datetime import datetime, timezone
from typing import Any, Callable, Dict
from unittest.mock import MagicMock
from uuid import UUID

# Third-party
from freezegun import freeze_time
import pytest
from pytest_mock import MockerFixture

# Local
from db.runs import Run, RunUpdate


def _build_supabase_mock(mocker: MockerFixture) -> tuple:
    """Patch db.runs.supabase with a fluent mock chain. Returns (mock_sb, mock_chain)."""
    mock_sb = mocker.patch("db.runs.supabase")
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


def _run_row(run: Run) -> Dict[str, Any]:
    """Serialize a Run to a JSON-compatible dict for use as a mock DB row."""
    return run.model_dump(mode="json")


class TestPostToDB:
    def test_post_to_db_returns_run_with_id(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        row = _run_row(run)
        mock_chain.execute.return_value = MagicMock(data=[row])

        result = run._post_to_db()

        assert result == row

    def test_post_to_db_returns_none_on_empty_response(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        result = run._post_to_db()

        assert result is None


class TestUpdateInDb:
    def test_update_in_db_sends_correct_fields(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        updated_row = {**_run_row(run), "status": "FILLED", "filled_total_czk": 4950.0}
        mock_chain.execute.return_value = MagicMock(data=[updated_row])

        run_update = RunUpdate(status="FILLED", filled_total_czk=4950.0)
        run.update_in_db(run_update)

        mock_chain.update.assert_called_once_with(
            {"status": "FILLED", "filled_total_czk": 4950.0}
        )

    def test_update_in_db_skips_none_fields(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        updated_row = {**_run_row(run), "status": "FAILED"}
        mock_chain.execute.return_value = MagicMock(data=[updated_row])

        run_update = RunUpdate(status="FAILED")
        run.update_in_db(run_update)

        call_data = mock_chain.update.call_args[0][0]
        assert "status" in call_data
        # None fields should be excluded
        assert "filled_total_czk" not in call_data
        assert "planned_total_czk" not in call_data


class TestCreateRun:
    def test_create_run_returns_run_with_id(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        row: Dict[str, Any] = {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "started_at": "2026-03-03T09:00:00+00:00",
            "status": "CREATED",
            "invest_amount": 5000.0,
            "invest_interval": "0 9 * * *",
            "t212_default_weight": 95.0,
            "btc_default_weight": 0.05,
            "total_orders": 0,
            "successful_orders": 0,
            "failed_orders": 0,
            "test": False,
        }
        mock_chain.execute.return_value = MagicMock(data=[row])

        run_start = datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc)
        run = Run.create_run(run_start)

        assert run.id == UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        assert run.status == "CREATED"

    def test_create_run_raises_on_db_failure(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.side_effect = RuntimeError("connection refused")

        run_start = datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(RuntimeError, match="Run creation failed"):
            Run.create_run(run_start)


class TestAreAllOrdersFilled:
    def test_returns_true_when_count_is_zero(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(count=0)

        assert run._are_all_orders_filled() is True

    def test_returns_false_when_count_nonzero(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(count=2)

        assert run._are_all_orders_filled() is False


class TestSumOrdersFilledCzk:
    def test_returns_sum_from_db(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(
            data=[{"filled_total_czk": 2500.0}, {"filled_total_czk": 1000.0}]
        )

        result = run._sum_orders_filled_czk()
        assert result == pytest.approx(3500.0)

    def test_returns_zero_when_no_filled_orders(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        result = run._sum_orders_filled_czk()
        assert result == pytest.approx(0.0)


class TestMarkRunFilled:
    def test_marks_run_as_filled_and_updates_amounts(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run(status="FINISHED")
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{}])

        run._mark_run_filled(4950.0)

        mock_chain.update.assert_called_once_with(
            {"status": "FILLED", "filled_total_czk": 4950.0}
        )
        assert run.status == "FILLED"
        assert run.filled_total_czk == pytest.approx(4950.0)

    def test_updates_status_to_filled(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run(status="FINISHED")
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{}])

        run._mark_run_filled(100.0)

        assert run.status == "FILLED"


class TestTryMarkRunFilled:
    def test_calls_mark_filled_when_all_orders_filled(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        mocker.patch.object(run, "_are_all_orders_filled", return_value=True)
        mocker.patch.object(run, "_sum_orders_filled_czk", return_value=4950.0)
        mock_mark = mocker.patch.object(run, "_mark_run_filled")

        result = run._try_mark_run_filled()

        assert result is True
        mock_mark.assert_called_once_with(4950.0)

    def test_does_nothing_when_orders_still_pending(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run()
        mocker.patch.object(run, "_are_all_orders_filled", return_value=False)
        mock_mark = mocker.patch.object(run, "_mark_run_filled")

        result = run._try_mark_run_filled()

        assert result is False
        mock_mark.assert_not_called()


class TestTryMarkRunFailedIfExpired:
    @freeze_time("2026-03-18 09:00:00")  # 15 days after finished_at
    def test_marks_failed_after_14_days(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run(
            status="FINISHED",
            finished_at=datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc),
        )
        # Patch at class level to avoid Pydantic's frozen-instance attribute restrictions
        mock_update = mocker.patch.object(Run, "update_in_db")

        run._try_mark_run_failed_if_expired()

        mock_update.assert_called_once()
        call_arg: RunUpdate = mock_update.call_args[0][0]
        assert call_arg.status == "FAILED"

    @freeze_time("2026-03-13 09:00:00")  # 10 days after finished_at
    def test_does_not_mark_failed_before_14_days(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run(
            status="FINISHED",
            finished_at=datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc),
        )
        mock_update = mocker.patch.object(Run, "update_in_db")

        run._try_mark_run_failed_if_expired()

        mock_update.assert_not_called()


class TestGetFinishedRuns:
    def test_returns_list_of_finished_runs(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        run = make_run(status="FINISHED")
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[_run_row(run)])

        result = Run._get_finished_runs()

        assert len(result) == 1
        assert isinstance(result[0], Run)
        assert result[0].status == "FINISHED"

    def test_returns_empty_list_when_no_runs(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        result = Run._get_finished_runs()
        assert result == []


class TestUpdateRuns:
    def test_calls_try_mark_on_each_run(self, mocker: MockerFixture) -> None:
        mock_run1 = MagicMock()
        mock_run2 = MagicMock()
        mocker.patch.object(
            Run, "_get_finished_runs", return_value=[mock_run1, mock_run2]
        )

        Run.update_runs()

        mock_run1._try_mark_run_failed_if_expired.assert_called_once()
        mock_run1._try_mark_run_filled.assert_called_once()
        mock_run2._try_mark_run_failed_if_expired.assert_called_once()
        mock_run2._try_mark_run_filled.assert_called_once()

    def test_logs_error_and_continues_on_exception(self, mocker: MockerFixture) -> None:
        mock_run1 = MagicMock()
        mock_run1._try_mark_run_failed_if_expired.side_effect = RuntimeError("DB error")
        mock_run2 = MagicMock()
        mocker.patch.object(
            Run, "_get_finished_runs", return_value=[mock_run1, mock_run2]
        )

        # Should not raise
        Run.update_runs()

        # Second run should still be processed
        mock_run2._try_mark_run_failed_if_expired.assert_called_once()


class TestRunExistsToday:
    def test_returns_false_in_non_prod(self, mocker: MockerFixture) -> None:
        # settings.env == "dev" in tests; query runs but result is ignored
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{"id": "some-id"}])

        result = Run.run_exists_today()

        assert result is False

    @freeze_time("2026-03-03 09:00:00")
    def test_returns_true_when_run_found_in_prod(self, mocker: MockerFixture) -> None:
        from settings import settings as real_settings

        mock_settings = MagicMock()
        mock_settings.env = "prod"
        mock_settings.portfolio = real_settings.portfolio
        mocker.patch("db.runs.settings", mock_settings)

        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{"id": "some-id"}])

        result = Run.run_exists_today()

        assert result is True
