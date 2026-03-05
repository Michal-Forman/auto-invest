# Standard library
from typing import Any
from unittest.mock import MagicMock

# Third-party
from freezegun import freeze_time
import pytest
from pytest_mock import MockerFixture

# Local
from db.mails import Mail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_supabase_mock(mocker: MockerFixture) -> tuple:
    """Patch db.mails.supabase with a fluent mock chain. Returns (mock_sb, mock_chain)."""
    mock_sb = mocker.patch("db.mails.supabase")
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


# ---------------------------------------------------------------------------
# Tests: Mail.summary_sent_for_period
# ---------------------------------------------------------------------------


class TestSummarySentForPeriod:
    def test_returns_true_when_record_exists(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{"id": "abc"}])

        assert Mail.summary_sent_for_period("2026-02") is True

    def test_returns_false_when_no_record(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        assert Mail.summary_sent_for_period("2026-02") is False

    def test_queries_correct_table_and_filters(self, mocker: MockerFixture) -> None:
        mock_sb, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        Mail.summary_sent_for_period("2026-03")

        mock_sb.table.assert_called_once_with("mails")
        mock_chain.select.assert_called_once_with("id")
        mock_chain.eq.assert_any_call("type", "monthly_summary")
        mock_chain.eq.assert_any_call("period", "2026-03")
        mock_chain.limit.assert_called_once_with(1)

    def test_returns_false_on_exception(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.side_effect = Exception("DB down")

        result = Mail.summary_sent_for_period("2026-02")

        assert result is False

    def test_returns_false_on_network_error(self, mocker: MockerFixture) -> None:
        mock_sb, _ = _build_supabase_mock(mocker)
        mock_sb.table.side_effect = ConnectionError("network error")

        assert Mail.summary_sent_for_period("2026-01") is False


# ---------------------------------------------------------------------------
# Tests: Mail.post_to_db
# ---------------------------------------------------------------------------


class TestPostToDB:
    def test_returns_inserted_row_on_success(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        row: dict[str, Any] = {"id": "uuid-1", "type": "error_alert", "subject": "Test"}
        mock_chain.execute.return_value = MagicMock(data=[row])

        mail = Mail(type="error_alert", subject="Test")
        result = mail.post_to_db()

        assert result == row

    def test_returns_none_on_empty_response(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        mail = Mail(type="error_alert", subject="Test")
        # Empty data raises IndexError internally → returns None
        result = mail.post_to_db()

        assert result is None

    def test_returns_none_on_exception(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.side_effect = Exception("DB error")

        mail = Mail(type="investment_confirmation", subject="Test")
        result = mail.post_to_db()

        assert result is None

    def test_inserts_correct_fields(self, mocker: MockerFixture) -> None:
        mock_sb, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{"id": "x"}])

        mail = Mail(type="monthly_summary", subject="Summary", period="2026-02")
        mail.post_to_db()

        mock_sb.table.assert_called_once_with("mails")
        inserted = mock_chain.insert.call_args[0][0]
        assert inserted["type"] == "monthly_summary"
        assert inserted["subject"] == "Summary"
        assert inserted["period"] == "2026-02"

    def test_does_not_insert_none_fields(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{"id": "x"}])

        mail = Mail(type="error_alert", subject="Err")  # period=None, sent_at=None
        mail.post_to_db()

        inserted = mock_chain.insert.call_args[0][0]
        assert "period" not in inserted
        assert "sent_at" not in inserted
        assert "id" not in inserted

    def test_post_to_db_calls_execute(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{"id": "x"}])

        Mail(type="error_alert", subject="Test").post_to_db()

        mock_chain.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Mail.balance_alert_sent_today
# ---------------------------------------------------------------------------


class TestBalanceAlertSentToday:
    @freeze_time("2026-03-05 12:00:00")
    def test_returns_true_when_record_exists(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[{"id": "abc"}])

        assert Mail.balance_alert_sent_today() is True

    @freeze_time("2026-03-05 12:00:00")
    def test_returns_false_when_no_record(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        assert Mail.balance_alert_sent_today() is False

    @freeze_time("2026-03-05 12:00:00")
    def test_queries_correct_table_and_filters(self, mocker: MockerFixture) -> None:
        mock_sb, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        Mail.balance_alert_sent_today()

        mock_sb.table.assert_called_once_with("mails")
        mock_chain.select.assert_called_once_with("id")
        mock_chain.eq.assert_any_call("type", "balance_alert")
        mock_chain.eq.assert_any_call("period", "2026-03-05")
        mock_chain.limit.assert_called_once_with(1)

    @freeze_time("2026-03-05 12:00:00")
    def test_returns_false_on_exception(self, mocker: MockerFixture) -> None:
        _, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.side_effect = Exception("DB down")

        assert Mail.balance_alert_sent_today() is False

    @freeze_time("2026-03-05 23:59:59")
    def test_uses_utc_date(self, mocker: MockerFixture) -> None:
        mock_sb, mock_chain = _build_supabase_mock(mocker)
        mock_chain.execute.return_value = MagicMock(data=[])

        Mail.balance_alert_sent_today()

        mock_chain.eq.assert_any_call("period", "2026-03-05")
