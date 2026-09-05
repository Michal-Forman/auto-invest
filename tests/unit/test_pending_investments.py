# Standard library
import dataclasses
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable
from unittest.mock import MagicMock

# Third-party
from pytest_mock import MockerFixture

# Local
from core.db.runs import Run, RunUpdate
from core.db.users import UserRecord
from core.executor import Executor
from core.funding import OneTimeFundingCheck
from core.instruments import Instruments
from core.mailer import Mailer
from core.pending_investments import (
    PENDING_EXPIRY_DAYS,
    _retry_one,
    retry_pending_investments,
)

_USER_RECORD = UserRecord(
    id="test-user-id",
    t212_id_key="t212-key",
    t212_private_key="t212-priv",
    coinmate_client_id=1,
    coinmate_public_key="cm-pub",
    coinmate_private_key="cm-priv",
    pie_id=1,
    t212_weight=95,
    btc_weight=0.05,
    invest_amount=5000.0,
    invest_interval="0 9 * * *",
    balance_buffer=1.5,
    balance_alert_days=7,
    btc_withdrawal_treshold=500000,
    btc_external_adress="bc1qexampleaddressfortesting",
    email="test@example.com",
    t212_deposit_account=None,
    t212_deposit_vs=None,
    coinmate_deposit_account=None,
    coinmate_deposit_vs=None,
    cron_enabled=True,
    notifications_enabled=True,
    btc_withdrawals_enabled=True,
    trading212_enabled=True,
    coinmate_enabled=True,
)


def _patch_common(mocker: MockerFixture, user: UserRecord = _USER_RECORD) -> None:
    mocker.patch("core.pending_investments.UserRecord.from_db", return_value=user)
    mocker.patch("core.pending_investments.Trading212")
    mocker.patch("core.pending_investments.Coinmate")
    mocker.patch.object(
        Instruments,
        "distribute_cash",
        return_value={"cash_distribution": {"VWCEd_EQ": Decimal("500")}},
    )
    # No orders recorded against the run yet — the common case. Tests that exercise
    # the idempotency / partial-placement paths override this.
    mocker.patch("core.pending_investments.Order.get_orders_for_runs", return_value=[])


class TestRetryOnePending:
    def test_expires_run_past_the_deadline(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        _patch_common(mocker)
        mocker.patch(
            "core.pending_investments.one_time_funding_status",
            return_value=[],
        )
        mock_send_expired = mocker.patch.object(
            Mailer,
            "send_pending_investment_expired",
        )
        run = make_run(
            status="PENDING",
            investment_type="one_time",
            user_id="test-user-id",
            started_at=datetime.now(timezone.utc)
            - timedelta(days=PENDING_EXPIRY_DAYS, hours=1),
            distribution={"VWCEd_EQ": 500.0},
            multipliers={"VWCEd_EQ": 1.0},
        )
        mock_update = mocker.patch.object(Run, "update_in_db")

        _retry_one(run)

        update_arg: RunUpdate = mock_update.call_args[0][0]
        assert update_arg.status == "FAILED"
        assert update_arg.error is not None and "Expired" in update_arg.error
        mock_send_expired.assert_called_once()

    def test_still_short_leaves_run_untouched(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        _patch_common(mocker)
        mocker.patch(
            "core.pending_investments.one_time_funding_status",
            return_value=[
                OneTimeFundingCheck(
                    exchange="T212",
                    available_czk=Decimal("100"),
                    one_time_czk=Decimal("500"),
                    dca_reserve_czk=Decimal("500"),
                )
            ],
        )
        run = make_run(
            status="PENDING",
            investment_type="one_time",
            user_id="test-user-id",
            started_at=datetime.now(timezone.utc),
            distribution={"VWCEd_EQ": 500.0},
            multipliers={"VWCEd_EQ": 1.0},
        )
        mock_update = mocker.patch.object(Run, "update_in_db")

        _retry_one(run)

        mock_update.assert_not_called()

    def test_places_order_and_sends_confirmation_when_funded(
        self, make_run: Callable[..., Run], make_order, mocker: MockerFixture
    ) -> None:
        _patch_common(mocker)
        mocker.patch(
            "core.pending_investments.one_time_funding_status",
            return_value=[
                OneTimeFundingCheck(
                    exchange="T212",
                    available_czk=Decimal("5000"),
                    one_time_czk=Decimal("500"),
                    dca_reserve_czk=Decimal("500"),
                )
            ],
        )
        order = make_order(total_czk=Decimal("500"))
        mocker.patch.object(
            Executor,
            "place_orders",
            return_value=[order],
        )
        mock_confirmation = mocker.patch.object(
            Mailer,
            "send_investment_confirmation",
        )
        run = make_run(
            status="PENDING",
            investment_type="one_time",
            user_id="test-user-id",
            started_at=datetime.now(timezone.utc),
            distribution={"VWCEd_EQ": 500.0},
            multipliers={"VWCEd_EQ": 1.0},
        )
        mock_update = mocker.patch.object(Run, "update_in_db")

        _retry_one(run)

        update_arg: RunUpdate = mock_update.call_args[0][0]
        assert update_arg.status == "FINISHED"
        mock_confirmation.assert_called_once()

    def test_marks_failed_and_alerts_when_placement_raises(
        self, make_run: Callable[..., Run], mocker: MockerFixture
    ) -> None:
        _patch_common(mocker)
        mocker.patch(
            "core.pending_investments.one_time_funding_status",
            return_value=[
                OneTimeFundingCheck(
                    exchange="T212",
                    available_czk=Decimal("5000"),
                    one_time_czk=Decimal("500"),
                    dca_reserve_czk=Decimal("500"),
                )
            ],
        )
        mocker.patch.object(
            Executor,
            "place_orders",
            side_effect=RuntimeError("exchange rejected order"),
        )
        mock_error_alert = mocker.patch.object(
            Mailer,
            "send_error_alert",
        )
        run = make_run(
            status="PENDING",
            investment_type="one_time",
            user_id="test-user-id",
            started_at=datetime.now(timezone.utc),
            distribution={"VWCEd_EQ": 500.0},
            multipliers={"VWCEd_EQ": 1.0},
        )
        mock_update = mocker.patch.object(Run, "update_in_db")

        _retry_one(run)

        update_arg: RunUpdate = mock_update.call_args[0][0]
        assert update_arg.status == "FAILED"
        mock_error_alert.assert_called_once()

    def test_no_mail_sent_when_notifications_disabled(
        self, make_run: Callable[..., Run], make_order, mocker: MockerFixture
    ) -> None:
        user = dataclasses.replace(_USER_RECORD, notifications_enabled=False)
        _patch_common(mocker, user=user)
        mocker.patch(
            "core.pending_investments.one_time_funding_status",
            return_value=[
                OneTimeFundingCheck(
                    exchange="T212",
                    available_czk=Decimal("5000"),
                    one_time_czk=Decimal("500"),
                    dca_reserve_czk=Decimal("500"),
                )
            ],
        )
        order = make_order(total_czk=Decimal("500"))
        mocker.patch.object(
            Executor,
            "place_orders",
            return_value=[order],
        )
        mock_mailer_class = mocker.patch("core.pending_investments.Mailer")
        run = make_run(
            status="PENDING",
            investment_type="one_time",
            user_id="test-user-id",
            started_at=datetime.now(timezone.utc),
            distribution={"VWCEd_EQ": 500.0},
            multipliers={"VWCEd_EQ": 1.0},
        )
        mocker.patch.object(Run, "update_in_db")

        _retry_one(run)

        mock_mailer_class.assert_not_called()

    def test_finalizes_without_replacing_when_orders_already_exist(
        self, make_run: Callable[..., Run], make_order, mocker: MockerFixture
    ) -> None:
        _patch_common(mocker)
        order = make_order(total_czk=Decimal("500"))
        mocker.patch(
            "core.pending_investments.Order.get_orders_for_runs",
            return_value=[order],
        )
        mock_place = mocker.patch.object(Executor, "place_orders")
        mock_confirmation = mocker.patch.object(Mailer, "send_investment_confirmation")
        mock_funding = mocker.patch("core.pending_investments.one_time_funding_status")
        run = make_run(
            status="PENDING",
            investment_type="one_time",
            user_id="test-user-id",
            started_at=datetime.now(timezone.utc),
            distribution={"VWCEd_EQ": 500.0},
            multipliers={"VWCEd_EQ": 1.0},
        )
        mock_update = mocker.patch.object(Run, "update_in_db")

        _retry_one(run)

        mock_place.assert_not_called()
        mock_funding.assert_not_called()
        update_arg: RunUpdate = mock_update.call_args[0][0]
        assert update_arg.status == "FINISHED"
        mock_confirmation.assert_called_once()

    def test_partial_placement_marks_finished_not_failed(
        self, make_run: Callable[..., Run], make_order, mocker: MockerFixture
    ) -> None:
        _patch_common(mocker)
        mocker.patch(
            "core.pending_investments.one_time_funding_status",
            return_value=[
                OneTimeFundingCheck(
                    exchange="T212",
                    available_czk=Decimal("5000"),
                    one_time_czk=Decimal("500"),
                    dca_reserve_czk=Decimal("500"),
                )
            ],
        )
        mocker.patch.object(
            Executor,
            "place_orders",
            side_effect=RuntimeError("DB write failed after exchange order"),
        )
        order = make_order(total_czk=Decimal("500"))
        # First call (idempotency guard) sees nothing; the post-failure call sees the
        # order that did reach the exchange.
        mocker.patch(
            "core.pending_investments.Order.get_orders_for_runs",
            side_effect=[[], [order]],
        )
        mock_error_alert = mocker.patch.object(Mailer, "send_error_alert")
        run = make_run(
            status="PENDING",
            investment_type="one_time",
            user_id="test-user-id",
            started_at=datetime.now(timezone.utc),
            distribution={"VWCEd_EQ": 500.0},
            multipliers={"VWCEd_EQ": 1.0},
        )
        mock_update = mocker.patch.object(Run, "update_in_db")

        _retry_one(run)

        update_arg: RunUpdate = mock_update.call_args[0][0]
        assert update_arg.status == "FINISHED"
        mock_error_alert.assert_called_once()
        assert "partially placed" in mock_error_alert.call_args.kwargs["banner_message"]


class TestRetryPendingInvestments:
    def test_iterates_every_pending_run_and_isolates_failures(
        self, mocker: MockerFixture
    ) -> None:
        run1 = MagicMock()
        run2 = MagicMock()
        mocker.patch(
            "core.pending_investments.Run.get_pending_runs",
            return_value=[run1, run2],
        )
        mock_retry_one = mocker.patch(
            "core.pending_investments._retry_one",
            side_effect=[RuntimeError("boom"), None],
        )

        retry_pending_investments()

        assert mock_retry_one.call_count == 2
