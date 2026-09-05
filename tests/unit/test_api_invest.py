# Standard library
import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

# Third-party
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

# Local
from api.main import app
from core.executor import Executor
from core.settings import UserSettings

client = TestClient(app)

# T212 side: VWCEd_EQ at 90% of a 5000 invest_amount and adj_weight — 4500 one-time,
# 4500 DCA reserve (next_czk). Coinmate side: BTC at 10% — 500 one-time, 500 reserve.
_BASE_RATIO_DATA: Dict[str, Any] = {
    "default_ratios": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "target_weights": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "ath_prices": {"VWCEd_EQ": 100.0, "BTC": 50000.0},
    "current_prices": {"VWCEd_EQ": 80.0, "BTC": 40000.0},
    "drop_pcts": {"VWCEd_EQ": 20.0, "BTC": 20.0},
    "multipliers": {"VWCEd_EQ": 1.25, "BTC": 1.25},
    "adj_weights": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "next_czk": {"VWCEd_EQ": 4500.0, "BTC": 500.0},
}


def _patch_common(
    mocker: MockerFixture,
    t212_balance: str = "5000",
    coinmate_balance: str = "5000",
    ratio_data: Optional[Dict[str, Any]] = None,
) -> None:
    mocker.patch(
        "api.routers.invest.build_ratio_data",
        return_value=ratio_data if ratio_data is not None else _BASE_RATIO_DATA,
    )
    mock_t212 = MagicMock()
    mock_t212.balance.return_value = Decimal(t212_balance)
    mocker.patch("api.routers.invest.get_t212_for_user", return_value=mock_t212)

    mock_coinmate = MagicMock()
    mock_coinmate.balance.return_value = Decimal(coinmate_balance)
    mocker.patch("api.routers.invest.get_coinmate_for_user", return_value=mock_coinmate)


def _patch_deposit_config(
    mocker: MockerFixture,
    user_settings: UserSettings,
    **overrides: Any,
) -> None:
    patched = dataclasses.replace(user_settings, **overrides)
    mocker.patch("api.routers.invest.get_user_settings_for_user", return_value=patched)


# ---------------------------------------------------------------------------
# Tests: GET /invest/funding-check
# ---------------------------------------------------------------------------


def test_sufficient_when_balances_cover_one_time_and_dca_reserve(
    mocker: MockerFixture,
) -> None:
    _patch_common(mocker, t212_balance="10000", coinmate_balance="2000")
    resp = client.get("/invest/funding-check?amount=1000")

    assert resp.status_code == 200
    data = resp.json()
    assert data["sufficient"] is True
    assert all(not e["is_short"] for e in data["exchanges"])


def test_insufficient_when_balance_covers_one_time_but_not_dca_reserve(
    mocker: MockerFixture,
) -> None:
    # One-time 1000 CZK -> 900 T212 / 100 Coinmate. T212 balance covers only that,
    # not the 4500 CZK next-DCA-run reserve on top.
    _patch_common(mocker, t212_balance="900", coinmate_balance="2000")
    resp = client.get("/invest/funding-check?amount=1000")

    assert resp.status_code == 200
    data = resp.json()
    assert data["sufficient"] is False
    t212_item = next(e for e in data["exchanges"] if e["exchange"] == "T212")
    assert t212_item["is_short"] is True
    assert t212_item["one_time_czk"] == 900.0
    assert t212_item["dca_reserve_czk"] == 4500.0


def test_uses_settings_invest_amount_when_amount_is_zero(mocker: MockerFixture) -> None:
    _patch_common(mocker, t212_balance="10000", coinmate_balance="2000")
    resp = client.get("/invest/funding-check")

    assert resp.status_code == 200
    # test UserSettings has invest_amount=5000.0; VWCEd_EQ adj_weight=0.9 -> 4500 one-time
    t212_item = next(e for e in resp.json()["exchanges"] if e["exchange"] == "T212")
    assert t212_item["one_time_czk"] == 4500.0


def test_no_topup_details_when_short_but_deposit_config_missing(
    mocker: MockerFixture, user_settings: UserSettings
) -> None:
    _patch_common(mocker, t212_balance="100", coinmate_balance="2000")
    _patch_deposit_config(mocker, user_settings)  # deposit fields default to None
    resp = client.get("/invest/funding-check?amount=1000")

    t212_item = next(e for e in resp.json()["exchanges"] if e["exchange"] == "T212")
    assert t212_item["is_short"] is True
    assert t212_item["suggested_topup_czk"] is not None
    assert t212_item["account"] is None
    assert t212_item["qr_data_uri"] is None


def test_topup_details_present_when_short_and_deposit_config_set(
    mocker: MockerFixture, user_settings: UserSettings
) -> None:
    _patch_common(mocker, t212_balance="100", coinmate_balance="2000")
    _patch_deposit_config(
        mocker,
        user_settings,
        t212_deposit_account="19-123456789/0800",
        t212_deposit_vs="12345",
    )
    resp = client.get("/invest/funding-check?amount=1000")

    t212_item = next(e for e in resp.json()["exchanges"] if e["exchange"] == "T212")
    assert t212_item["account"] == "19-123456789/0800"
    assert t212_item["vs"] == "12345"
    assert t212_item["qr_data_uri"].startswith("data:image/png;base64,")
    # Suggested top-up is rounded up to the nearest 100 CZK.
    assert t212_item["suggested_topup_czk"] % 100 == 0


def test_exchange_without_anything_needed_is_omitted(mocker: MockerFixture) -> None:
    data = {
        **_BASE_RATIO_DATA,
        "adj_weights": {"VWCEd_EQ": 1.0},
        "next_czk": {"VWCEd_EQ": 5000.0},
    }
    _patch_common(
        mocker, t212_balance="10000", coinmate_balance="10000", ratio_data=data
    )
    resp = client.get("/invest/funding-check?amount=1000")

    exchanges = {e["exchange"] for e in resp.json()["exchanges"]}
    assert exchanges == {"T212"}


# ---------------------------------------------------------------------------
# Tests: POST /invest — blocked by insufficient funding
# ---------------------------------------------------------------------------


def test_place_investment_blocked_returns_402_without_creating_a_run(
    mocker: MockerFixture,
) -> None:
    _patch_common(mocker, t212_balance="100", coinmate_balance="2000")
    mock_create_run = mocker.patch("api.routers.invest.Run.create_run")

    resp = client.post("/invest?amount=1000")

    assert resp.status_code == 402
    assert resp.json()["detail"]["sufficient"] is False
    mock_create_run.assert_not_called()


def test_place_investment_proceeds_when_sufficient(mocker: MockerFixture) -> None:
    _patch_common(mocker, t212_balance="10000", coinmate_balance="2000")

    mock_run = MagicMock()
    mock_run.id = "run-1"
    mocker.patch("api.routers.invest.Run.create_run", return_value=mock_run)
    mocker.patch("api.routers.invest.Run.process_new_run_data")

    mock_order = MagicMock()
    mock_order.total_czk = 1000
    mocker.patch.object(Executor, "place_orders", return_value=[mock_order])

    resp = client.post("/invest?amount=1000")

    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-1"
    mock_run.update_in_db.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: POST /invest/pending — "I've sent the money"
# ---------------------------------------------------------------------------


def test_register_pending_places_immediately_when_sufficient(
    mocker: MockerFixture,
) -> None:
    _patch_common(mocker, t212_balance="10000", coinmate_balance="2000")
    mocker.patch("api.routers.invest.Run.get_pending_runs", return_value=[])

    mock_run = MagicMock()
    mock_run.id = "run-1"
    mocker.patch("api.routers.invest.Run.create_run", return_value=mock_run)
    mocker.patch("api.routers.invest.Run.process_new_run_data")

    mock_order = MagicMock()
    mock_order.total_czk = 1000
    mocker.patch.object(Executor, "place_orders", return_value=[mock_order])

    resp = client.post("/invest/pending?amount=1000")

    assert resp.status_code == 200
    data = resp.json()
    assert data["placed"] is True
    assert data["invest"]["run_id"] == "run-1"
    assert data["pending"] is None


def test_register_pending_creates_pending_run_when_insufficient(
    mocker: MockerFixture,
) -> None:
    _patch_common(mocker, t212_balance="100", coinmate_balance="2000")
    mocker.patch("api.routers.invest.Run.get_pending_runs", return_value=[])

    mock_run = MagicMock()
    mock_run.id = "run-2"
    mock_run.started_at = datetime.now(timezone.utc)
    mock_run.planned_total_czk = Decimal("1000")
    mocker.patch("api.routers.invest.Run.create_run", return_value=mock_run)

    resp = client.post("/invest/pending?amount=1000")

    assert resp.status_code == 200
    data = resp.json()
    assert data["placed"] is False
    assert data["invest"] is None
    assert data["pending"]["run_id"] == "run-2"
    assert data["pending"]["funding"]["sufficient"] is False
    mock_run.update_in_db.assert_called_once()
    update_arg = mock_run.update_in_db.call_args[0][0]
    assert update_arg.status == "PENDING"
    assert update_arg.distribution is not None


def test_register_pending_returns_409_when_already_pending(
    mocker: MockerFixture,
) -> None:
    _patch_common(mocker, t212_balance="100", coinmate_balance="2000")
    mocker.patch("api.routers.invest.Run.get_pending_runs", return_value=[MagicMock()])
    mock_create_run = mocker.patch("api.routers.invest.Run.create_run")

    resp = client.post("/invest/pending?amount=1000")

    assert resp.status_code == 409
    mock_create_run.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: GET /invest/pending
# ---------------------------------------------------------------------------


def test_get_pending_investment_returns_null_when_none(mocker: MockerFixture) -> None:
    mocker.patch("api.routers.invest.Run.get_pending_runs", return_value=[])

    resp = client.get("/invest/pending")

    assert resp.status_code == 200
    assert resp.json() is None


def test_get_pending_investment_returns_live_funding_snapshot(
    mocker: MockerFixture,
) -> None:
    _patch_common(mocker, t212_balance="100", coinmate_balance="2000")
    mock_run = MagicMock()
    mock_run.id = "run-3"
    mock_run.started_at = datetime.now(timezone.utc)
    mock_run.planned_total_czk = Decimal("900")
    mock_run.distribution = {"VWCEd_EQ": 900.0}
    mocker.patch("api.routers.invest.Run.get_pending_runs", return_value=[mock_run])

    resp = client.get("/invest/pending")

    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "run-3"
    assert data["funding"]["sufficient"] is False


# ---------------------------------------------------------------------------
# Tests: POST /invest/pending/cancel
# ---------------------------------------------------------------------------


def test_cancel_pending_investment_marks_cancelled(mocker: MockerFixture) -> None:
    mock_run = MagicMock()
    mock_run.id = "run-4"
    mock_run.started_at = datetime.now(timezone.utc)
    mock_run.planned_total_czk = Decimal("900")
    mocker.patch("api.routers.invest.Run.get_pending_runs", return_value=[mock_run])

    resp = client.post("/invest/pending/cancel")

    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-4"
    update_arg = mock_run.update_in_db.call_args[0][0]
    assert update_arg.status == "CANCELLED"


def test_cancel_pending_investment_404_when_none(mocker: MockerFixture) -> None:
    mocker.patch("api.routers.invest.Run.get_pending_runs", return_value=[])

    resp = client.post("/invest/pending/cancel")

    assert resp.status_code == 404
