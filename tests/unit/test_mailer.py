# Standard library
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List
from unittest.mock import MagicMock, patch
from uuid import UUID

# Third-party
from freezegun import freeze_time
import pytest
from pytest_mock import MockerFixture

# Local
from db.orders import Order
from db.runs import Run
from mailer import (
    _FEE_RATIO_THRESHOLD,
    _FX_DRIFT_THRESHOLD,
    _SLIPPAGE_THRESHOLD,
    Mailer,
    _czech_account_to_iban,
    _make_spd_qr,
    _runs_in_next_30_days,
)

# ---------------------------------------------------------------------------
# Helpers
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


def _patch_smtp_and_logo(mocker: MockerFixture) -> MagicMock:
    """Patch smtplib.SMTP_SSL and logo file open so no real network/disk is needed."""
    mock_server = MagicMock()
    mock_smtp_cls = mocker.patch("mailer.smtplib.SMTP_SSL")
    mock_smtp_cls.return_value.__enter__.return_value = mock_server
    # Patch open only for the logo so templates still load from disk
    import builtins

    real_open = builtins.open

    def _selective_open(path: str, *args: Any, **kwargs: Any) -> Any:
        if "logo_white.png" in str(path):
            m = MagicMock()
            m.__enter__ = MagicMock(
                return_value=MagicMock(read=MagicMock(return_value=b"PNG"))
            )
            m.__exit__ = MagicMock(return_value=False)
            return m
        return real_open(path, *args, **kwargs)

    mocker.patch("builtins.open", side_effect=_selective_open)
    return mock_server


# ---------------------------------------------------------------------------
# Tests: _load_template
# ---------------------------------------------------------------------------


class TestLoadTemplate:
    def test_returns_template_object_for_investment_confirmation(self) -> None:
        tmpl = Mailer._load_template("investment_confirmation.html")
        # Template should contain the placeholder used in send_investment_confirmation
        assert "run_id_short" in tmpl.template

    def test_returns_template_object_for_error_alert(self) -> None:
        tmpl = Mailer._load_template("error_alert.html")
        assert "banner_message" in tmpl.template

    def test_returns_template_object_for_monthly_summary(self) -> None:
        tmpl = Mailer._load_template("monthly_summary.html")
        assert "month_label" in tmpl.template

    def test_returns_template_object_for_balance_alert(self) -> None:
        tmpl = Mailer._load_template("balance_alert.html")
        assert "date_label" in tmpl.template

    def test_raises_for_nonexistent_template(self) -> None:
        with pytest.raises(FileNotFoundError):
            Mailer._load_template("nonexistent.html")


# ---------------------------------------------------------------------------
# Tests: _send
# ---------------------------------------------------------------------------


class TestSend:
    def test_send_calls_smtp_login_and_send_message(
        self, mocker: MockerFixture
    ) -> None:
        mock_server = _patch_smtp_and_logo(mocker)
        mocker.patch("mailer.Mail.post_to_db")

        mailer = Mailer()
        mailer._send("Subject", "plain", "<html>body</html>", "error_alert")

        mock_server.login.assert_called_once_with(mailer.my_mail, mailer.mail_password)
        mock_server.send_message.assert_called_once()

    def test_send_persists_to_db_after_success(self, mocker: MockerFixture) -> None:
        _patch_smtp_and_logo(mocker)
        mock_post = mocker.patch("mailer.Mail.post_to_db")

        mailer = Mailer()
        mailer._send(
            "Subject", "plain", "<html/>", "investment_confirmation", period="2026-03"
        )

        mock_post.assert_called_once()

    def test_send_does_not_persist_to_db_on_smtp_failure(
        self, mocker: MockerFixture
    ) -> None:
        _patch_smtp_and_logo(mocker)
        mock_post = mocker.patch("mailer.Mail.post_to_db")
        # Make SMTP_SSL context manager raise on send_message
        mock_server = MagicMock()
        mock_server.send_message.side_effect = Exception("SMTP failure")
        mock_smtp_cls = mocker.patch("mailer.smtplib.SMTP_SSL")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        mailer = Mailer()
        with pytest.raises(Exception, match="SMTP failure"):
            mailer._send("Subject", "plain", "<html/>", "error_alert")

        mock_post.assert_not_called()

    def test_send_raises_on_smtp_failure(self, mocker: MockerFixture) -> None:
        _patch_smtp_and_logo(mocker)
        mocker.patch("mailer.Mail.post_to_db")
        mock_server = MagicMock()
        mock_server.login.side_effect = OSError("Connection refused")
        mock_smtp_cls = mocker.patch("mailer.smtplib.SMTP_SSL")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        mailer = Mailer()
        with pytest.raises(OSError):
            mailer._send("Subject", "plain", "<html/>", "error_alert")

    def test_send_sets_correct_email_headers(self, mocker: MockerFixture) -> None:
        mock_server = _patch_smtp_and_logo(mocker)
        mocker.patch("mailer.Mail.post_to_db")

        mailer = Mailer()
        mailer._send("My Subject", "plain", "<html/>", "error_alert")

        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["Subject"] == "My Subject"
        assert sent_msg["From"] == mailer.my_mail
        assert sent_msg["To"] == mailer.mail_recipient

    def test_send_passes_period_to_mail(self, mocker: MockerFixture) -> None:
        _patch_smtp_and_logo(mocker)
        captured: list = []

        def _capture_post(self_mail: Any) -> None:  # type: ignore[misc]
            captured.append(self_mail)

        mocker.patch("mailer.Mail.post_to_db", _capture_post)

        mailer = Mailer()
        mailer._send("Subject", "plain", "<html/>", "monthly_summary", period="2026-02")

        # Mail.post_to_db is an instance method patched at class level; check via Mail constructor
        # Instead verify via mock call args on the Mail class
        # Re-patch properly:
        mocker.stopall()

        _patch_smtp_and_logo(mocker)
        mock_mail_cls = mocker.patch("mailer.Mail")
        mock_mail_instance = MagicMock()
        mock_mail_cls.return_value = mock_mail_instance

        mailer._send("Subject", "plain", "<html/>", "monthly_summary", period="2026-02")

        mock_mail_cls.assert_called_once_with(
            type="monthly_summary", subject="Subject", period="2026-02"
        )
        mock_mail_instance.post_to_db.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: send_investment_confirmation
# ---------------------------------------------------------------------------


class TestSendInvestmentConfirmation:
    def test_calls_send_with_correct_subject(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        orders = [_make_order(t212_ticker="VWCEd_EQ", exchange="T212")]
        dist = {"VWCEd_EQ": 5000.0}
        mults = {"VWCEd_EQ": 1.0}

        Mailer().send_investment_confirmation(run, orders, dist, mults)

        mock_send.assert_called_once()
        subject = mock_send.call_args[0][0]
        assert "Investment complete" in subject

    def test_plain_text_contains_run_id(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        Mailer().send_investment_confirmation(
            run, [], {"VWCEd_EQ": 1000.0}, {"VWCEd_EQ": 1.2}
        )
        plain = mock_send.call_args[0][1]
        assert str(_RUN_ID) in plain

    def test_plain_text_contains_total_czk(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        dist = {"VWCE": 3000.0, "BTC": 2000.0}
        Mailer().send_investment_confirmation(run, [], dist, {})
        plain = mock_send.call_args[0][1]
        assert "5000" in plain

    def test_html_contains_ticker(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        dist = {"VWCEd_EQ": 4000.0, "BTC": 1000.0}
        Mailer().send_investment_confirmation(run, [], dist, {"VWCEd_EQ": 1.5})
        html = mock_send.call_args[0][2]
        assert "VWCEd_EQ" in html
        assert "BTC" in html

    def test_html_shows_boosted_multiplier_in_green(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        dist = {"VWCE": 5000.0}
        mults = {"VWCE": 1.5}
        Mailer().send_investment_confirmation(run, [], dist, mults)
        html = mock_send.call_args[0][2]
        assert "#16a34a" in html  # green color for mult > 1.0

    def test_html_shows_exchange_from_orders(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        order = _make_order(t212_ticker="VWCE", exchange="COINMATE")
        dist = {"VWCE": 5000.0}
        Mailer().send_investment_confirmation(run, [order], dist, {})
        html = mock_send.call_args[0][2]
        assert "COINMATE" in html

    def test_mail_type_is_investment_confirmation(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        Mailer().send_investment_confirmation(run, [], {"VWCE": 1000.0}, {})
        assert mock_send.call_args.kwargs["mail_type"] == "investment_confirmation"

    def test_rows_sorted_by_czk_descending(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        dist = {"SMALL": 100.0, "BIG": 4000.0, "MID": 900.0}
        Mailer().send_investment_confirmation(run, [], dist, {})
        html = mock_send.call_args[0][2]
        # BIG should appear before MID before SMALL in HTML
        assert html.index("BIG") < html.index("MID") < html.index("SMALL")


# ---------------------------------------------------------------------------
# Tests: send_error_alert
# ---------------------------------------------------------------------------


class TestSendErrorAlert:
    def test_subject_contains_error_indicator(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        try:
            raise ValueError("something failed")
        except ValueError as e:
            Mailer().send_error_alert(e)
        subject = mock_send.call_args[0][0]
        assert "ERROR" in subject

    def test_plain_contains_error_repr(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        try:
            raise ValueError("boom")
        except ValueError as e:
            Mailer().send_error_alert(e)
        plain = mock_send.call_args[0][1]
        assert "ValueError" in plain
        assert "boom" in plain

    def test_plain_contains_run_info_when_run_provided(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        try:
            raise RuntimeError("db error")
        except RuntimeError as e:
            Mailer().send_error_alert(e, run=run)
        plain = mock_send.call_args[0][1]
        assert str(_RUN_ID) in plain

    def test_plain_contains_generic_message_without_run(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        try:
            raise RuntimeError("unexpected")
        except RuntimeError as e:
            Mailer().send_error_alert(e)
        plain = mock_send.call_args[0][1]
        assert "unexpected error" in plain.lower()

    def test_html_contains_run_id_block_when_run_provided(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        try:
            raise RuntimeError("oops")
        except RuntimeError as e:
            Mailer().send_error_alert(e, run=run)
        html = mock_send.call_args[0][2]
        assert "Run ID" in html
        assert str(_RUN_ID)[:8] in html

    def test_html_has_no_run_block_without_run(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        try:
            raise RuntimeError("oops")
        except RuntimeError as e:
            Mailer().send_error_alert(e)
        html = mock_send.call_args[0][2]
        assert "Run ID" not in html

    def test_mail_type_is_error_alert(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        try:
            raise ValueError("err")
        except ValueError as e:
            Mailer().send_error_alert(e)
        assert mock_send.call_args.kwargs["mail_type"] == "error_alert"

    def test_plain_contains_traceback(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        try:
            raise ValueError("traceback test")
        except ValueError as e:
            Mailer().send_error_alert(e)
        plain = mock_send.call_args[0][1]
        assert "Traceback" in plain


# ---------------------------------------------------------------------------
# Tests: _compute_warnings (pure static method)
# ---------------------------------------------------------------------------


class TestComputeWarnings:
    def test_no_warnings_for_normal_order(self) -> None:
        o = _make_order(
            status="FILLED",
            price=100.0,
            fill_price=100.5,  # 0.5% slippage — below 3% threshold
            fee_czk=5.0,
            filled_total_czk=5000.0,  # 0.1% fee — below 0.5%
            fill_fx_rate=25.0,
            fx_rate=25.0,
        )
        assert Mailer._compute_warnings([o]) == []

    def test_price_slippage_warning_above_threshold(self) -> None:
        o = _make_order(
            status="FILLED",
            price=100.0,
            fill_price=105.0,  # 5% slippage
        )
        warnings = Mailer._compute_warnings([o])
        assert len(warnings) == 1
        assert warnings[0]["type"] == "Price slippage"
        assert "above" in warnings[0]["detail"]

    def test_price_slippage_below_warn_when_fill_below_price(self) -> None:
        o = _make_order(
            status="FILLED",
            price=100.0,
            fill_price=90.0,  # 10% below
        )
        warnings = Mailer._compute_warnings([o])
        assert any(
            w["type"] == "Price slippage" and "below" in w["detail"] for w in warnings
        )

    def test_high_fee_warning(self) -> None:
        o = _make_order(
            status="FILLED",
            fee_czk=100.0,
            filled_total_czk=1000.0,  # 10% fee
        )
        warnings = Mailer._compute_warnings([o])
        assert any(w["type"] == "High fee" for w in warnings)

    def test_fx_shift_warning(self) -> None:
        o = _make_order(
            status="FILLED",
            currency="EUR",
            fx_rate=25.0,
            fill_fx_rate=20.0,  # large drift
        )
        warnings = Mailer._compute_warnings([o])
        assert any(w["type"] == "FX shift" for w in warnings)

    def test_no_fx_warning_for_czk_orders(self) -> None:
        o = _make_order(
            status="FILLED",
            currency="CZK",
            fx_rate=1.0,
            fill_fx_rate=0.8,  # would be large drift but CZK order
        )
        warnings = Mailer._compute_warnings([o])
        assert not any(w["type"] == "FX shift" for w in warnings)

    def test_skips_non_filled_orders(self) -> None:
        o = _make_order(
            status="SUBMITTED",
            price=100.0,
            fill_price=200.0,  # would trigger slippage if FILLED
        )
        assert Mailer._compute_warnings([o]) == []

    def test_groups_repeated_warnings_for_same_ticker(self) -> None:
        o1 = _make_order(
            status="FILLED", t212_ticker="VWCE", price=100.0, fill_price=110.0
        )
        o2 = _make_order(
            status="FILLED", t212_ticker="VWCE", price=100.0, fill_price=115.0
        )
        warnings = Mailer._compute_warnings([o1, o2])
        vwce_slip = [
            w
            for w in warnings
            if w["ticker"] == "VWCE" and w["type"] == "Price slippage"
        ]
        assert len(vwce_slip) == 1
        assert "2×" in vwce_slip[0]["detail"]

    def test_groups_averages_pct_correctly(self) -> None:
        o1 = _make_order(
            status="FILLED", t212_ticker="BTC", price=100.0, fill_price=110.0
        )
        o2 = _make_order(
            status="FILLED", t212_ticker="BTC", price=100.0, fill_price=120.0
        )
        warnings = Mailer._compute_warnings([o1, o2])
        btc = [w for w in warnings if w["ticker"] == "BTC"][0]
        # avg slippage = (10 + 20) / 2 = 15%
        assert "15.0" in btc["detail"]

    def test_multiple_warning_types_for_same_order(self) -> None:
        o = _make_order(
            status="FILLED",
            price=100.0,
            fill_price=110.0,  # slippage
            fee_czk=200.0,
            filled_total_czk=1000.0,  # high fee
            currency="EUR",
            fx_rate=25.0,
            fill_fx_rate=20.0,  # fx shift
        )
        warnings = Mailer._compute_warnings([o])
        types = {w["type"] for w in warnings}
        assert "Price slippage" in types
        assert "High fee" in types
        assert "FX shift" in types

    def test_empty_orders_list(self) -> None:
        assert Mailer._compute_warnings([]) == []

    def test_fx_better_direction(self) -> None:
        o = _make_order(
            status="FILLED",
            currency="USD",
            fx_rate=20.0,
            fill_fx_rate=25.0,  # better (more CZK per USD)
        )
        warnings = Mailer._compute_warnings([o])
        fx_w = [w for w in warnings if w["type"] == "FX shift"]
        assert fx_w and "better" in fx_w[0]["detail"]


# ---------------------------------------------------------------------------
# Tests: send_monthly_summary
# ---------------------------------------------------------------------------


class TestSendMonthlySummary:
    def test_returns_early_when_no_runs(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_monthly_summary([], [])
        mock_send.assert_not_called()

    def test_subject_contains_month_label(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        Mailer().send_monthly_summary([run], [])
        subject = mock_send.call_args[0][0]
        assert "March 2026" in subject

    def test_plain_contains_total_czk(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        orders = [
            _make_order(t212_ticker="VWCE", total_czk=3000.0, status="FILLED"),
            _make_order(t212_ticker="BTC", total_czk=2000.0, status="FILLED"),
        ]
        Mailer().send_monthly_summary([run], orders)
        plain = mock_send.call_args[0][1]
        assert "5000" in plain

    def test_plain_shows_no_issues_when_clean(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        Mailer().send_monthly_summary([run], [])
        plain = mock_send.call_args[0][1]
        assert "No issues" in plain

    def test_plain_shows_failed_run_info(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        failed = _make_run(
            status="FAILED",
            error="Timed out",
            id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        )
        Mailer().send_monthly_summary([run], [], failed_runs=[failed])
        plain = mock_send.call_args[0][1]
        assert "FAILED" in plain
        assert "Timed out" in plain

    def test_plain_shows_failed_order_info(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        bad_order = _make_order(status="FAILED", error="Insufficient funds")  # type: ignore[arg-type]
        Mailer().send_monthly_summary([run], [bad_order])
        plain = mock_send.call_args[0][1]
        assert "Insufficient funds" in plain

    def test_html_contains_no_warnings_block_when_clean(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        Mailer().send_monthly_summary([run], [])
        html = mock_send.call_args[0][2]
        assert "No warnings" in html

    def test_html_contains_warnings_table_when_warnings_present(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        # Order with large slippage
        order = _make_order(status="FILLED", price=100.0, fill_price=120.0)
        Mailer().send_monthly_summary([run], [order])
        html = mock_send.call_args[0][2]
        assert "Price slippage" in html

    def test_html_contains_no_issues_block_when_clean(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        Mailer().send_monthly_summary([run], [])
        html = mock_send.call_args[0][2]
        assert "No issues found" in html

    def test_html_contains_issues_table_with_failed_run(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        failed = _make_run(status="FAILED", error="Order expired")
        Mailer().send_monthly_summary([run], [], failed_runs=[failed])
        html = mock_send.call_args[0][2]
        assert "FAILED RUN" in html
        assert "Order expired" in html

    def test_mail_type_is_monthly_summary(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        Mailer().send_monthly_summary([run], [])
        assert mock_send.call_args.kwargs["mail_type"] == "monthly_summary"

    def test_period_kwarg_matches_anchor_run_month(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run(started_at=datetime(2026, 2, 5, 9, 0, 0, tzinfo=timezone.utc))
        Mailer().send_monthly_summary([run], [])
        # period passed as keyword
        assert mock_send.call_args[1].get("period") == "2026-02"

    def test_excludes_failed_orders_from_ticker_totals(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run = _make_run()
        good = _make_order(t212_ticker="VWCE", total_czk=3000.0, status="FILLED")
        bad = _make_order(t212_ticker="VWCE", total_czk=9999.0, status="FAILED")  # type: ignore[arg-type]
        Mailer().send_monthly_summary([run], [good, bad])
        plain = mock_send.call_args[0][1]
        assert "3000" in plain
        assert "12999" not in plain  # bad order should not inflate total

    def test_anchor_run_uses_earliest_start_date(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        run1 = _make_run(started_at=datetime(2026, 3, 15, 9, 0, 0, tzinfo=timezone.utc))
        run2 = _make_run(started_at=datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc))
        Mailer().send_monthly_summary([run1, run2], [])
        subject = mock_send.call_args[0][0]
        assert "March 2026" in subject

    def test_only_failed_runs_no_successful_runs(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        failed = _make_run(status="FAILED")
        Mailer().send_monthly_summary([], [], failed_runs=[failed])
        mock_send.assert_called_once()
        plain = mock_send.call_args[0][1]
        assert "FAILED" in plain


# ---------------------------------------------------------------------------
# Tests: send_balance_alert
# ---------------------------------------------------------------------------


def _make_alert(**overrides: Any) -> dict:
    """Build a minimal alert dict for send_balance_alert tests."""
    defaults: dict = {
        "exchange": "T212",
        "balance": 3000.0,
        "spend_per_run": 1500.0,
        "runs_out_on": datetime(2026, 3, 7, 9, 0, 0, tzinfo=timezone.utc),
        "days_until_broke": 4,
    }
    defaults.update(overrides)
    return defaults


class TestSendBalanceAlert:
    def test_calls_send_with_low_balance_subject(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert()])
        subject = mock_send.call_args[0][0]
        assert "balance" in subject.lower()

    def test_plain_contains_exchange_name(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert(exchange="T212")])
        plain = mock_send.call_args[0][1]
        assert "T212" in plain

    def test_plain_contains_runs_out_date(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        runs_out = datetime(2026, 3, 7, 9, 0, 0, tzinfo=timezone.utc)
        Mailer().send_balance_alert([_make_alert(runs_out_on=runs_out)])
        plain = mock_send.call_args[0][1]
        assert "2026-03-07" in plain

    def test_plain_contains_days_until_broke(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert(days_until_broke=3)])
        plain = mock_send.call_args[0][1]
        assert "3" in plain

    def test_html_contains_exchange_name(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert(exchange="COINMATE")])
        html = mock_send.call_args[0][2]
        assert "COINMATE" in html

    def test_html_uses_red_color_for_urgent_days(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert(days_until_broke=1)])
        html = mock_send.call_args[0][2]
        assert "#dc2626" in html

    def test_html_uses_amber_color_for_non_urgent_days(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert(days_until_broke=5)])
        html = mock_send.call_args[0][2]
        assert "#b45309" in html

    def test_mail_type_is_balance_alert(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert()])
        assert mock_send.call_args.kwargs["mail_type"] == "balance_alert"

    def test_period_kwarg_is_todays_date(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert()])
        period = mock_send.call_args.kwargs.get("period")
        assert period is not None
        # Should be a valid YYYY-MM-DD date string
        from datetime import datetime as _dt

        _dt.strptime(period, "%Y-%m-%d")  # raises if format invalid

    def test_multiple_exchanges_in_plain(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        alerts = [
            _make_alert(exchange="T212"),
            _make_alert(exchange="COINMATE"),
        ]
        Mailer().send_balance_alert(alerts)
        plain = mock_send.call_args[0][1]
        assert "T212" in plain
        assert "COINMATE" in plain

    def test_html_contains_balance_value(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert(balance=4567.89)])
        html = mock_send.call_args[0][2]
        assert "4\u00a0567.89" in html  # formatted with non-breaking space thousands sep

    def test_html_contains_spend_per_run_value(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        Mailer().send_balance_alert([_make_alert(spend_per_run=1234.56)])
        html = mock_send.call_args[0][2]
        assert "1\u00a0234.56" in html


# ---------------------------------------------------------------------------
# Tests: _czech_account_to_iban (pure function)
# ---------------------------------------------------------------------------


class TestCzechAccountToIban:
    def test_returns_string_starting_with_cz(self) -> None:
        assert _czech_account_to_iban("19-123456789/0800").startswith("CZ")

    def test_iban_has_correct_length(self) -> None:
        # CZ IBAN: "CZ" + 2 check digits + 20 BBAN = 24 chars
        assert len(_czech_account_to_iban("19-123456789/0800")) == 24

    def test_account_without_prefix(self) -> None:
        iban = _czech_account_to_iban("123456789/0800")
        assert iban.startswith("CZ")
        assert len(iban) == 24

    def test_different_base_numbers_give_different_ibans(self) -> None:
        iban1 = _czech_account_to_iban("123456789/0800")
        iban2 = _czech_account_to_iban("987654321/0800")
        assert iban1 != iban2

    def test_check_digits_are_valid_numerals(self) -> None:
        iban = _czech_account_to_iban("19-123456789/0800")
        assert iban[2:4].isdigit()

    def test_deterministic_for_same_input(self) -> None:
        assert _czech_account_to_iban("19-2000145399/0800") == _czech_account_to_iban(
            "19-2000145399/0800"
        )

    def test_different_bank_codes_produce_different_ibans(self) -> None:
        iban1 = _czech_account_to_iban("123456789/0800")
        iban2 = _czech_account_to_iban("123456789/2010")
        assert iban1 != iban2


# ---------------------------------------------------------------------------
# Tests: _make_spd_qr (pure function)
# ---------------------------------------------------------------------------


class TestMakeSpdQr:
    def test_returns_bytes(self) -> None:
        result = _make_spd_qr("19-123456789/0800", "12345", 1000.0)
        assert isinstance(result, bytes)

    def test_returns_png_magic_bytes(self) -> None:
        result = _make_spd_qr("19-123456789/0800", "12345", 1000.0)
        assert result[:4] == b"\x89PNG"

    def test_different_amounts_produce_different_qrs(self) -> None:
        qr1 = _make_spd_qr("19-123456789/0800", "12345", 1000.0)
        qr2 = _make_spd_qr("19-123456789/0800", "12345", 2000.0)
        assert qr1 != qr2

    def test_different_accounts_produce_different_qrs(self) -> None:
        qr1 = _make_spd_qr("19-123456789/0800", "12345", 1000.0)
        qr2 = _make_spd_qr("987654321/0800", "12345", 1000.0)
        assert qr1 != qr2

    def test_different_variable_symbols_produce_different_qrs(self) -> None:
        qr1 = _make_spd_qr("19-123456789/0800", "11111", 1000.0)
        qr2 = _make_spd_qr("19-123456789/0800", "99999", 1000.0)
        assert qr1 != qr2


# ---------------------------------------------------------------------------
# Tests: _runs_in_next_30_days (pure function)
# ---------------------------------------------------------------------------


class TestRunsInNext30Days:
    @freeze_time("2026-03-03 00:00:00")
    def test_daily_cron_returns_30(self) -> None:
        count = _runs_in_next_30_days("0 9 * * *")
        assert count == 30

    @freeze_time("2026-03-03 00:00:00")
    def test_weekly_cron_returns_4_or_5(self) -> None:
        count = _runs_in_next_30_days("0 9 * * 1")  # every Monday
        assert 4 <= count <= 5

    @freeze_time("2026-03-03 00:00:00")
    def test_biweekly_cron_fires_twice_per_week(self) -> None:
        count = _runs_in_next_30_days("0 9 * * 1,4")  # Mon + Thu
        assert 8 <= count <= 10

    @freeze_time("2026-03-03 00:00:00")
    def test_monthly_cron_returns_1(self) -> None:
        # 1st of each month: only 2026-04-01 falls within 30 days
        count = _runs_in_next_30_days("0 9 1 * *")
        assert count == 1

    @freeze_time("2026-03-03 00:00:00")
    def test_twice_daily_cron_still_counts_once_per_day(self) -> None:
        # max-once-per-day deduplication
        once_daily = _runs_in_next_30_days("0 9 * * *")
        twice_daily = _runs_in_next_30_days("0 9,21 * * *")
        assert once_daily == twice_daily == 30


# ---------------------------------------------------------------------------
# Tests: send_balance_alert – QR / top-up section
# ---------------------------------------------------------------------------


class TestSendBalanceAlertTopupSection:
    """Tests for the deposit QR code and top-up section of send_balance_alert."""

    def _patch_settings(
        self,
        mocker: MockerFixture,
        *,
        t212_account: str | None = None,
        t212_vs: str | None = None,
        coinmate_account: str | None = None,
        coinmate_vs: str | None = None,
    ) -> MagicMock:
        mock_settings = MagicMock()
        mock_settings.t212_deposit_account = t212_account
        mock_settings.t212_deposit_vs = t212_vs
        mock_settings.coinmate_deposit_account = coinmate_account
        mock_settings.coinmate_deposit_vs = coinmate_vs
        mock_settings.portfolio.invest_interval = "0 9 * * *"
        mocker.patch("mailer.settings", mock_settings)
        return mock_settings

    def test_extra_images_contains_qr_when_deposit_config_present(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(mocker, t212_account="19-123456789/0800", t212_vs="12345")
        mocker.patch("mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert([_make_alert(exchange="T212")])

        extra_images = mock_send.call_args.kwargs.get("extra_images")
        assert extra_images is not None
        assert "qr_T212" in extra_images

    def test_extra_images_is_none_when_no_deposit_config(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(mocker)  # all None
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert([_make_alert(exchange="T212")])

        extra_images = mock_send.call_args.kwargs.get("extra_images")
        assert extra_images is None

    def test_topup_section_in_html_when_deposit_config_present(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(mocker, t212_account="19-123456789/0800", t212_vs="12345")
        mocker.patch("mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert([_make_alert(exchange="T212")])

        html = mock_send.call_args[0][2]
        assert "Suggested top-up:" in html
        assert "19-123456789/0800" in html
        assert "12345" in html

    def test_topup_section_absent_when_no_deposit_config(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(mocker)  # all None
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert([_make_alert(exchange="T212")])

        html = mock_send.call_args[0][2]
        # "Suggested top-up:" only appears inside an actual topup card
        assert "Suggested top-up:" not in html

    def test_suggested_amount_rounds_up_to_nearest_100(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(mocker, t212_account="19-123456789/0800", t212_vs="12345")
        mock_qr = mocker.patch("mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        # ceil(4 * 333.0 / 100) * 100 = ceil(13.32) * 100 = 1400
        Mailer().send_balance_alert([_make_alert(exchange="T212", spend_per_run=333.0)])

        _, _, amount = mock_qr.call_args[0]
        assert amount == 1400.0

    def test_suggested_amount_exact_multiple_of_100_not_bumped(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(mocker, t212_account="19-123456789/0800", t212_vs="12345")
        mock_qr = mocker.patch("mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        # ceil(4 * 250.0 / 100) * 100 = ceil(10.0) * 100 = 1000
        Mailer().send_balance_alert([_make_alert(exchange="T212", spend_per_run=250.0)])

        _, _, amount = mock_qr.call_args[0]
        assert amount == 1000.0

    def test_both_exchanges_generate_separate_qr_codes(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(
            mocker,
            t212_account="19-123456789/0800",
            t212_vs="12345",
            coinmate_account="987654321/2060",
            coinmate_vs="99999",
        )
        mock_qr = mocker.patch("mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert(
            [_make_alert(exchange="T212"), _make_alert(exchange="COINMATE")]
        )

        extra_images = mock_send.call_args.kwargs.get("extra_images")
        assert extra_images is not None
        assert "qr_T212" in extra_images
        assert "qr_COINMATE" in extra_images
        assert mock_qr.call_count == 2

    def test_unknown_exchange_skips_qr_generation(self, mocker: MockerFixture) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        self._patch_settings(mocker)  # all None
        mock_qr = mocker.patch("mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert([_make_alert(exchange="KRAKEN")])

        mock_qr.assert_not_called()
        extra_images = mock_send.call_args.kwargs.get("extra_images")
        assert extra_images is None

    def test_partial_deposit_config_only_generates_qr_for_configured_exchange(
        self, mocker: MockerFixture
    ) -> None:
        mock_send = mocker.patch.object(Mailer, "_send")
        # Only T212 has deposit config; COINMATE does not
        self._patch_settings(mocker, t212_account="19-123456789/0800", t212_vs="12345")
        mock_qr = mocker.patch("mailer._make_spd_qr", return_value=b"PNG")
        mocker.patch("mailer._runs_in_next_30_days", return_value=4)

        Mailer().send_balance_alert(
            [_make_alert(exchange="T212"), _make_alert(exchange="COINMATE")]
        )

        assert mock_qr.call_count == 1
        extra_images = mock_send.call_args.kwargs.get("extra_images")
        assert extra_images is not None
        assert "qr_T212" in extra_images
        assert "qr_COINMATE" not in extra_images
