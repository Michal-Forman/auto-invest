# Standard library
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from core.cron import main, run_for_user
from core.db.users import UserRecord
from core.funding import ExchangeFunding
from tests.conftest import _TEST_USER_RECORD, TEST_USER_ID


def _make_user(user_id: str) -> UserRecord:
    """Build a minimal UserRecord with the given id."""
    return UserRecord(
        id=user_id,
        t212_id_key="key",
        t212_private_key="priv",
        coinmate_client_id=1,
        coinmate_public_key="pub",
        coinmate_private_key="priv",
        pie_id=1,
        t212_weight=95,
        btc_weight=0.05,
        invest_amount=5000.0,
        invest_interval="0 9 * * *",
        balance_buffer=1.5,
        balance_alert_days=7,
        btc_withdrawal_treshold=500000,
        btc_external_adress="bc1qtest",
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


class TestMain:
    def test_calls_run_for_each_user(self, mocker: MockerFixture) -> None:
        """main() invokes run_for_user once per cron-enabled user."""
        user1 = _make_user("user-1")
        user2 = _make_user("user-2")
        mocker.patch("core.cron.UserRecord.get_cron_users", return_value=[user1, user2])
        mock_run = mocker.patch("core.cron.run_for_user")

        main()

        assert mock_run.call_count == 2
        mock_run.assert_any_call(user1)
        mock_run.assert_any_call(user2)

    def test_isolates_user_failures(self, mocker: MockerFixture) -> None:
        """A failure for one user does not prevent other users from running."""
        user1 = _make_user("user-1")
        user2 = _make_user("user-2")
        mocker.patch("core.cron.UserRecord.get_cron_users", return_value=[user1, user2])

        def _side_effect(user: UserRecord) -> None:
            if user.id == "user-1":
                raise RuntimeError("boom")

        mock_run = mocker.patch("core.cron.run_for_user", side_effect=_side_effect)

        main()  # must not raise

        assert mock_run.call_count == 2


@pytest.fixture
def mocks(mocker: MockerFixture, user_settings):  # type: ignore[misc]
    """Patch all heavy I/O dependencies inside run_for_user."""
    mocker.patch("core.cron.UserSettings.from_user", return_value=user_settings)
    mocker.patch("core.cron.Trading212", return_value=MagicMock())
    mocker.patch("core.cron.Coinmate", return_value=MagicMock())

    mock_instruments = MagicMock()
    mock_instruments.is_btc_withdrawal_treshold_exceeded.return_value = False
    mock_instruments.distribute_cash.return_value = {
        "cash_distribution": {"BTC": Decimal("500.0")},
        "multipliers": {"BTC": Decimal("1.0")},
    }
    mocker.patch("core.cron.Instruments", return_value=mock_instruments)

    mock_executor = MagicMock()
    mock_executor.place_orders.return_value = []
    mocker.patch("core.cron.Executor", return_value=mock_executor)

    mocker.patch("core.cron.Mailer", return_value=MagicMock())
    mocker.patch("core.cron.Order.update_orders")
    mocker.patch("core.cron.Run.update_runs")
    mocker.patch("core.cron.Run.process_new_run_data", return_value=MagicMock())
    mocker.patch("core.cron.Mail.last_balance_alert", return_value=None)
    mock_funding_status = mocker.patch("core.cron.funding_status", return_value=[])
    mocker.patch("core.cron.Mail.summary_sent_for_period", return_value=True)

    mock_run_instance = MagicMock()
    mock_run_instance.id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    mock_create_run = mocker.patch(
        "core.cron.Run.create_run", return_value=mock_run_instance
    )
    mock_run_exists_today = mocker.patch(
        "core.cron.Run.run_exists_today", return_value=False
    )
    mock_is_now_cron_time = mocker.patch(
        "core.cron.is_now_cron_time", return_value=True
    )

    return {
        "mock_funding_status": mock_funding_status,
        "mock_instruments": mock_instruments,
        "mock_executor": mock_executor,
        "mock_run_instance": mock_run_instance,
        "mock_create_run": mock_create_run,
        "mock_run_exists_today": mock_run_exists_today,
        "mock_is_now_cron_time": mock_is_now_cron_time,
    }


class TestRunForUser:
    def test_no_run_today_places_orders(self, mocks) -> None:  # type: ignore[misc]
        """When cron time matches and no run exists, orders are placed."""
        run_for_user(_TEST_USER_RECORD)

        mocks["mock_create_run"].assert_called_once()
        mocks["mock_executor"].place_orders.assert_called_once()

    def test_already_ran_today_skips_orders(self, mocks) -> None:  # type: ignore[misc]
        """When a run already exists today, no new orders are placed."""
        mocks["mock_run_exists_today"].return_value = True

        run_for_user(_TEST_USER_RECORD)

        mocks["mock_executor"].place_orders.assert_not_called()

    def test_not_cron_time_skips_orders(self, mocks) -> None:  # type: ignore[misc]
        """When the current time does not match the cron expression, no orders are placed."""
        mocks["mock_is_now_cron_time"].return_value = False

        run_for_user(_TEST_USER_RECORD)

        mocks["mock_executor"].place_orders.assert_not_called()

    def test_user_id_propagated_to_create_run(self, mocks) -> None:  # type: ignore[misc]
        """Run.create_run receives the correct user_id for the current user."""
        run_for_user(_TEST_USER_RECORD)

        call_kwargs = mocks["mock_create_run"].call_args.kwargs
        assert call_kwargs["user_id"] == TEST_USER_ID

    def test_user_id_propagated_to_update_orders(
        self, mocker: MockerFixture, mocks
    ) -> None:
        """Order.update_orders is called with the correct user_id."""
        mock_update_orders = mocker.patch("core.cron.Order.update_orders")

        run_for_user(_TEST_USER_RECORD)

        call_kwargs = mock_update_orders.call_args.kwargs
        assert call_kwargs["user_id"] == TEST_USER_ID


class TestInsufficientFunds:
    """A run that cannot be fully paid for must place nothing and be marked FAILED."""

    @staticmethod
    def _short(exchange: str = "COINMATE") -> ExchangeFunding:
        return ExchangeFunding(
            exchange=exchange,
            required_czk=Decimal("250"),
            available_czk=Decimal("200"),
        )

    def test_places_no_orders_when_an_exchange_is_short(self, mocks) -> None:  # type: ignore[misc]
        mocks["mock_funding_status"].return_value = [self._short()]

        run_for_user(_TEST_USER_RECORD)

        mocks["mock_executor"].place_orders.assert_not_called()

    def test_marks_run_failed_naming_the_exchange(self, mocks) -> None:  # type: ignore[misc]
        mocks["mock_funding_status"].return_value = [self._short()]

        run_for_user(_TEST_USER_RECORD)

        update = mocks["mock_run_instance"].update_in_db.call_args[0][0]
        assert update.status == "FAILED"
        assert "COINMATE" in (update.error or "")

    def test_records_what_the_run_would_have_bought(self, mocks) -> None:  # type: ignore[misc]
        mocks["mock_funding_status"].return_value = [self._short()]

        run_for_user(_TEST_USER_RECORD)

        update = mocks["mock_run_instance"].update_in_db.call_args[0][0]
        assert update.planned_total_czk == Decimal("500.0")
        assert update.distribution == {"BTC": Decimal("500.0")}
        assert update.finished_at is not None

    def test_a_healthy_exchange_is_aborted_too(self, mocks) -> None:  # type: ignore[misc]
        """Only Coinmate is short, but T212's orders must not go through either."""
        mocks["mock_funding_status"].return_value = [
            ExchangeFunding(
                exchange="T212",
                required_czk=Decimal("750"),
                available_czk=Decimal("5000"),
            ),
            self._short(),
        ]

        run_for_user(_TEST_USER_RECORD)

        mocks["mock_executor"].place_orders.assert_not_called()

    def test_sends_a_funding_alert_not_an_error_alert(
        self, mocker: MockerFixture, mocks
    ) -> None:
        mock_mailer = MagicMock()
        mocker.patch("core.cron.Mailer", return_value=mock_mailer)
        mocks["mock_funding_status"].return_value = [self._short()]

        run_for_user(_TEST_USER_RECORD)

        mock_mailer.send_error_alert.assert_not_called()
        assert mock_mailer.send_funding_alert.call_args.kwargs["event"] == "skipped"

    def test_no_confirmation_email_is_sent(self, mocker: MockerFixture, mocks) -> None:
        mock_mailer = MagicMock()
        mocker.patch("core.cron.Mailer", return_value=mock_mailer)
        mocks["mock_funding_status"].return_value = [self._short()]

        run_for_user(_TEST_USER_RECORD)

        mock_mailer.send_investment_confirmation.assert_not_called()
