# Standard library
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock
from uuid import UUID

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from core.db.mails import Mail
from core.db.orders import Order
from core.db.runs import Run
from core.mailer import Mailer

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc)
_RUN_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _make_run(**overrides: Any) -> Run:
    defaults: Dict[str, Any] = {
        "id": _RUN_ID,
        "started_at": _NOW,
        "finished_at": _NOW,
        "status": "FINISHED",
        "invest_amount": 5000.0,
        "invest_interval": "0 9 * * *",
        "t212_default_weight": 95.0,
        "btc_default_weight": 0.05,
        "test": False,
    }
    defaults.update(overrides)
    return Run(**defaults)


def _make_order(**overrides: Any) -> Order:
    defaults: Dict[str, Any] = {
        "run_id": _RUN_ID,
        "exchange": "T212",
        "instrument_type": "ETF",
        "t212_ticker": "VWCEd_EQ",
        "yahoo_symbol": "VWCE.DE",
        "name": "Vanguard FTSE All-World",
        "currency": "EUR",
        "side": "BUY",
        "order_type": "MARKET",
        "fx_rate": 25.0,
        "price": 100.0,
        "quantity": 2.5,
        "total": 250.0,
        "total_czk": 6250.0,
        "extended_hours": False,
        "multiplier": 1.0,
        "submitted_at": _NOW,
        "status": "FILLED",
    }
    defaults.update(overrides)
    return Order(**defaults)


def _patch_mailer_send(mocker: MockerFixture) -> MagicMock:
    """Patch Mailer._send so no SMTP or disk I/O happens."""
    return mocker.patch.object(Mailer, "_send")


def _patch_mail_db(mocker: MockerFixture) -> MagicMock:
    """Patch Mail.post_to_db to avoid Supabase calls."""
    return mocker.patch.object(Mail, "post_to_db", return_value=None)


# ---------------------------------------------------------------------------
# Test: send_investment_confirmation integrates correctly with Run and Order
# ---------------------------------------------------------------------------


class TestInvestmentConfirmationIntegration:
    def test_sends_one_email_per_investment_run(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        orders = [
            _make_order(t212_ticker="VWCE", total_czk=3000.0),
            _make_order(t212_ticker="BTC", total_czk=2000.0),
        ]
        dist = {"VWCE": 3000.0, "BTC": 2000.0}
        mults = {"VWCE": 1.0, "BTC": 1.5}

        Mailer().send_investment_confirmation(run, orders, dist, mults)

        assert mock_send.call_count == 1

    def test_total_czk_in_email_matches_distribution_sum(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        dist = {"VWCE": 3500.0, "BTC": 1500.0}

        Mailer().send_investment_confirmation(run, [], dist, {})

        plain = mock_send.call_args[0][1]
        assert "5000" in plain

    def test_exchange_from_order_appears_in_html(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        orders = [
            _make_order(t212_ticker="VWCE", exchange="T212"),
            _make_order(t212_ticker="BTC", exchange="COINMATE"),
        ]
        dist = {"VWCE": 4000.0, "BTC": 1000.0}

        Mailer().send_investment_confirmation(run, orders, dist, {})

        html = mock_send.call_args[0][2]
        assert "T212" in html
        assert "COINMATE" in html

    def test_mail_is_persisted_to_db_after_send(self, mocker: MockerFixture) -> None:
        """After a successful SMTP send, a Mail record is written to the DB."""
        import builtins

        real_open = builtins.open

        def _open_selective(path: str, *args: Any, **kwargs: Any) -> Any:
            if "logo_white.png" in str(path):
                m = MagicMock()
                m.__enter__ = MagicMock(
                    return_value=MagicMock(read=MagicMock(return_value=b"PNG"))
                )
                m.__exit__ = MagicMock(return_value=False)
                return m
            return real_open(path, *args, **kwargs)

        mocker.patch("builtins.open", side_effect=_open_selective)
        mock_server = MagicMock()
        mock_smtp = mocker.patch("core.mailer.smtplib.SMTP_SSL")
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_post = _patch_mail_db(mocker)

        run = _make_run()
        Mailer().send_investment_confirmation(run, [], {"VWCE": 5000.0}, {})

        mock_post.assert_called_once()

    def test_run_id_truncated_to_8_chars_in_html(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run(id=UUID("12345678-abcd-efab-cdef-012345678901"))

        Mailer().send_investment_confirmation(run, [], {"VWCE": 5000.0}, {})

        html = mock_send.call_args[0][2]
        assert "12345678" in html
        assert "…" in html


# ---------------------------------------------------------------------------
# Test: send_error_alert integrates with Run
# ---------------------------------------------------------------------------


class TestErrorAlertIntegration:
    def test_error_without_run_still_sends(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        try:
            raise ValueError("standalone error")
        except ValueError as e:
            Mailer().send_error_alert(e)
        mock_send.assert_called_once()

    def test_error_with_run_sends_run_context_in_html(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        try:
            raise RuntimeError("investment failed")
        except RuntimeError as e:
            Mailer().send_error_alert(e, run=run)
        html = mock_send.call_args[0][2]
        assert "Run ID" in html
        assert str(_RUN_ID)[:8] in html

    def test_error_alert_mail_type_is_correct(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        try:
            raise Exception("err")
        except Exception as e:
            Mailer().send_error_alert(e)
        assert mock_send.call_args.kwargs["mail_type"] == "error_alert"

    def test_traceback_is_included_in_plain(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        try:
            raise TypeError("type error test")
        except TypeError as e:
            Mailer().send_error_alert(e)
        plain = mock_send.call_args[0][1]
        # format_exc returns NoneType when called outside except — but we're inside it
        assert "TypeError" in plain


# ---------------------------------------------------------------------------
# Test: send_monthly_summary integrates with runs, orders, and Mail.summary_sent_for_period
# ---------------------------------------------------------------------------


class TestMonthlySummaryIntegration:
    def test_summary_includes_all_tickers_with_totals(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        orders = [
            _make_order(t212_ticker="VWCE", total_czk=2000.0, status="FILLED"),
            _make_order(t212_ticker="BTC", total_czk=1000.0, status="FILLED"),
            _make_order(t212_ticker="CSPX", total_czk=500.0, status="FILLED"),
        ]
        Mailer().send_monthly_summary([run], orders)
        html = mock_send.call_args[0][2]
        assert "VWCE" in html
        assert "BTC" in html
        assert "CSPX" in html

    def test_summary_period_kwarg_is_set(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run(started_at=datetime(2026, 1, 15, 9, 0, 0, tzinfo=timezone.utc))
        Mailer().send_monthly_summary([run], [])
        assert mock_send.call_args[1].get("period") == "2026-01"

    def test_summary_sent_for_period_gates_main_flow(
        self, mocker: MockerFixture
    ) -> None:
        """Mail.summary_sent_for_period returning True should prevent another summary being sent."""
        mock_send = _patch_mailer_send(mocker)
        mocker.patch.object(Mail, "summary_sent_for_period", return_value=True)

        # Simulate the main.py guard:
        period = "2026-02"
        if not Mail.summary_sent_for_period(period):
            Mailer().send_monthly_summary([_make_run()], [])

        mock_send.assert_not_called()

    def test_summary_sends_when_not_yet_sent_for_period(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        mocker.patch.object(Mail, "summary_sent_for_period", return_value=False)

        period = "2026-02"
        run = _make_run(started_at=datetime(2026, 2, 5, 9, 0, 0, tzinfo=timezone.utc))
        if not Mail.summary_sent_for_period(period):
            Mailer().send_monthly_summary([run], [])

        mock_send.assert_called_once()

    def test_warnings_from_orders_appear_in_summary_html(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        # Large slippage order
        order = _make_order(status="FILLED", price=100.0, fill_price=115.0)
        Mailer().send_monthly_summary([run], [order])
        html = mock_send.call_args[0][2]
        assert "Price slippage" in html

    def test_failed_run_in_html_issues_section(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        failed = _make_run(
            id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            status="FAILED",
            error="expired without all orders filling",
        )
        Mailer().send_monthly_summary([run], [], failed_runs=[failed])
        html = mock_send.call_args[0][2]
        assert "FAILED RUN" in html
        assert "expired without all orders filling" in html

    def test_partially_filled_order_appears_in_issues(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        run = _make_run()
        partial = _make_order(status="PARTIALLY_FILLED", error="Only 50% filled")  # type: ignore[arg-type]
        Mailer().send_monthly_summary([run], [partial])
        html = mock_send.call_args[0][2]
        assert "PARTIALLY_FILLED" in html

    def test_num_runs_matches_successful_runs_count(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        runs = [_make_run() for _ in range(4)]
        Mailer().send_monthly_summary(runs, [])
        plain = mock_send.call_args[0][1]
        assert "4" in plain

    def test_summary_not_sent_when_both_run_lists_empty(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        Mailer().send_monthly_summary([], [], failed_runs=[])
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Mail.summary_sent_for_period guards monthly sends correctly
# ---------------------------------------------------------------------------


class TestMailSummaryGuard:
    def test_summary_sent_for_period_false_when_no_db_record(
        self, mocker: MockerFixture
    ) -> None:
        mock_sb = mocker.patch("core.db.mails.supabase")
        mock_chain = MagicMock()
        mock_sb.table.return_value = mock_chain
        for m in ["select", "eq", "limit"]:
            getattr(mock_chain, m).return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])

        assert Mail.summary_sent_for_period("2026-02") is False

    def test_summary_sent_for_period_true_when_db_record_exists(
        self, mocker: MockerFixture
    ) -> None:
        mock_sb = mocker.patch("core.db.mails.supabase")
        mock_chain = MagicMock()
        mock_sb.table.return_value = mock_chain
        for m in ["select", "eq", "limit"]:
            getattr(mock_chain, m).return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{"id": "some-uuid"}])

        assert Mail.summary_sent_for_period("2026-02") is True

    def test_summary_sent_for_period_returns_false_on_db_error(
        self, mocker: MockerFixture
    ) -> None:
        mock_sb = mocker.patch("core.db.mails.supabase")
        mock_sb.table.side_effect = RuntimeError("supabase unavailable")

        assert Mail.summary_sent_for_period("2026-02") is False


# ---------------------------------------------------------------------------
# Test: send_balance_alert integrates with Mail guard and QR topup section
# ---------------------------------------------------------------------------


def _make_balance_alert(**overrides: Any) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "exchange": "T212",
        "balance": 3000.0,
        "spend_per_run": 1500.0,
        "runs_out_on": datetime(2026, 3, 7, 9, 0, 0, tzinfo=timezone.utc),
        "days_until_broke": 4,
    }
    defaults.update(overrides)
    return defaults


class TestBalanceAlertIntegration:
    def test_sends_one_email_for_multiple_exchanges(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        alerts = [
            _make_balance_alert(exchange="T212"),
            _make_balance_alert(
                exchange="COINMATE", spend_per_run=250.0, days_until_broke=2
            ),
        ]
        Mailer().send_balance_alert(alerts)
        assert mock_send.call_count == 1

    def test_both_exchanges_appear_in_plain_text(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        Mailer().send_balance_alert(
            [
                _make_balance_alert(exchange="T212"),
                _make_balance_alert(exchange="COINMATE"),
            ]
        )
        plain = mock_send.call_args[0][1]
        assert "T212" in plain
        assert "COINMATE" in plain

    def test_balance_alert_sent_today_guard_prevents_duplicate(
        self, mocker: MockerFixture
    ) -> None:
        """Simulates the main.py guard: if already sent today, skip."""
        mock_send = _patch_mailer_send(mocker)
        mocker.patch.object(Mail, "balance_alert_sent_today", return_value=True)

        if not Mail.balance_alert_sent_today():
            Mailer().send_balance_alert([_make_balance_alert()])

        mock_send.assert_not_called()

    def test_balance_alert_sends_when_not_yet_sent_today(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        mocker.patch.object(Mail, "balance_alert_sent_today", return_value=False)

        if not Mail.balance_alert_sent_today():
            Mailer().send_balance_alert([_make_balance_alert()])

        mock_send.assert_called_once()

    def test_urgent_days_uses_red_color_in_html(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        Mailer().send_balance_alert([_make_balance_alert(days_until_broke=1)])
        html = mock_send.call_args[0][2]
        assert "#dc2626" in html

    def test_non_urgent_days_uses_amber_color_in_html(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        Mailer().send_balance_alert([_make_balance_alert(days_until_broke=5)])
        html = mock_send.call_args[0][2]
        assert "#b45309" in html

    def test_mail_type_and_period_are_correct(self, mocker: MockerFixture) -> None:
        mock_send = _patch_mailer_send(mocker)
        Mailer().send_balance_alert([_make_balance_alert()])
        kwargs = mock_send.call_args.kwargs
        assert kwargs["mail_type"] == "balance_alert"
        from datetime import datetime as _dt

        _dt.strptime(kwargs["period"], "%Y-%m-%d")  # raises if invalid format

    def test_qr_topup_section_present_when_deposit_config_set(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        mock_settings = MagicMock()
        mock_settings.t212_deposit_account = "19-123456789/0800"
        mock_settings.t212_deposit_vs = "12345"
        mock_settings.coinmate_deposit_account = None
        mock_settings.coinmate_deposit_vs = None
        mock_settings.portfolio.invest_interval = "0 9 * * *"
        mocker.patch("core.mailer.settings", mock_settings)
        mocker.patch("core.mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("core.mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert([_make_balance_alert(exchange="T212")])

        html = mock_send.call_args[0][2]
        assert "Suggested top-up:" in html
        assert "19-123456789/0800" in html

    def test_qr_topup_section_absent_when_no_deposit_config(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = _patch_mailer_send(mocker)
        mock_settings = MagicMock()
        mock_settings.t212_deposit_account = None
        mock_settings.t212_deposit_vs = None
        mock_settings.coinmate_deposit_account = None
        mock_settings.coinmate_deposit_vs = None
        mock_settings.portfolio.invest_interval = "0 9 * * *"
        mocker.patch("core.mailer.settings", mock_settings)
        mocker.patch("core.mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert([_make_balance_alert(exchange="T212")])

        html = mock_send.call_args[0][2]
        # "Suggested top-up:" only appears inside an actual topup card
        assert "Suggested top-up:" not in html

    def test_mail_is_persisted_to_db_after_smtp_send(
        self, mocker: MockerFixture
    ) -> None:
        """After successful SMTP send, Mail record is written to DB."""
        import builtins

        real_open = builtins.open

        def _open_selective(path: str, *args: Any, **kwargs: Any) -> Any:
            if "logo_white.png" in str(path):
                m = MagicMock()
                m.__enter__ = MagicMock(
                    return_value=MagicMock(read=MagicMock(return_value=b"PNG"))
                )
                m.__exit__ = MagicMock(return_value=False)
                return m
            return real_open(path, *args, **kwargs)

        mocker.patch("builtins.open", side_effect=_open_selective)
        mock_server = MagicMock()
        mock_smtp = mocker.patch("core.mailer.smtplib.SMTP_SSL")
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_post = _patch_mail_db(mocker)

        Mailer().send_balance_alert([_make_balance_alert()])

        mock_post.assert_called_once()
