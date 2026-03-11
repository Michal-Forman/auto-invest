# Standard library
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable, Dict
from unittest.mock import MagicMock
from uuid import UUID

# Third-party
from dotenv import dotenv_values

# Load test env vars before importing any local modules.
# dotenv_values reads .env.test without modifying os.environ directly,
# so we can use setdefault to not override values already set (e.g. from CI secrets).
_env_test = dotenv_values(Path(__file__).parent.parent / ".env.test")
for _key, _val in _env_test.items():
    if _val is not None:
        os.environ.setdefault(_key, _val)

# Ensure SUPABASE_JWT_SECRET is set for tests (api/dependencies.py reads it at call time)
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")

# Third-party
from fastapi.testclient import TestClient
import pytest

# Local
from api.cache import health_cache, instruments_cache
from api.dependencies import get_current_user_id
from api.main import app
from core.db.orders import Order
from core.db.runs import Run
from core.db.users import UserRecord
from core.instruments import Instruments
from core.settings import PortfolioSettings, UserSettings

TEST_USER_ID = "test-user-id"


@pytest.fixture
def portfolio_settings() -> PortfolioSettings:
    return PortfolioSettings(
        pie_id=1,
        t212_weight=95,
        btc_weight=0.05,
        invest_amount=5000.0,
        invest_interval="0 9 * * *",
        balance_buffer=1.5,
        balance_alert_days=7,
        btc_withdrawal_treshold=500000,
    )


@pytest.fixture
def user_settings(portfolio_settings: PortfolioSettings) -> UserSettings:
    return UserSettings(
        user_id=TEST_USER_ID,
        t212_id_key="test-t212-key",
        t212_private_key="test-t212-priv",
        coinmate_client_id=1,
        coinmate_public_key="test-pub",
        coinmate_private_key="test-priv",
        mail_recipient="test@example.com",
        t212_deposit_account=None,
        t212_deposit_vs=None,
        coinmate_deposit_account=None,
        coinmate_deposit_vs=None,
        btc_external_adress="bc1qexampleaddressfortesting",
        portfolio=portfolio_settings,
        env="dev",
    )


@pytest.fixture
def mock_t212() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_coinmate() -> MagicMock:
    return MagicMock()


@pytest.fixture
def instruments(
    mock_t212: MagicMock,
    mock_coinmate: MagicMock,
    portfolio_settings: PortfolioSettings,
) -> Instruments:
    return Instruments(mock_t212, mock_coinmate, portfolio_settings)


@pytest.fixture
def make_order() -> Callable[..., Order]:
    """Factory that builds a minimal valid Order, accepting field overrides."""

    def _factory(**overrides: Any) -> Order:
        defaults: Dict[str, Any] = {
            "run_id": UUID("12345678-1234-5678-1234-567812345678"),
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
            "submitted_at": datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc),
        }
        defaults.update(overrides)
        return Order(**defaults)

    return _factory


_TEST_USER_RECORD = UserRecord(
    id=TEST_USER_ID,
    t212_id_key="test-t212-key",
    t212_private_key="test-t212-priv",
    coinmate_client_id=1,
    coinmate_public_key="test-pub",
    coinmate_private_key="test-priv",
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
)


@pytest.fixture(autouse=True)
def override_auth():
    """Override JWT auth for all tests — returns a fixed test user_id."""
    app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture(autouse=True)
def override_user_record(monkeypatch):
    """Patch api.dependencies.get_user_record to avoid Supabase calls in all tests."""
    import api.dependencies as _deps

    monkeypatch.setattr(_deps, "get_user_record", lambda user_id: _TEST_USER_RECORD)


@pytest.fixture
def api_client(mock_t212: MagicMock, mock_coinmate: MagicMock):  # type: ignore[misc]
    """TestClient with T212/Coinmate dependency overrides (legacy fixture)."""
    yield TestClient(app)


@pytest.fixture(autouse=True)
def clear_api_caches() -> None:
    """Clear API caches before every test to prevent state leakage."""
    health_cache.clear()
    instruments_cache.clear()


@pytest.fixture
def make_run() -> Callable[..., Run]:
    """Factory that builds a minimal valid Run, accepting field overrides."""

    def _factory(**overrides: Any) -> Run:
        defaults: Dict[str, Any] = {
            "id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            "started_at": datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc),
            "finished_at": datetime(2026, 3, 3, 9, 5, 0, tzinfo=timezone.utc),
            "status": "FINISHED",
            "invest_amount": 5000.0,
            "invest_interval": "0 9 * * *",
            "t212_default_weight": 95.0,
            "btc_default_weight": 0.05,
            "test": False,
        }
        defaults.update(overrides)
        return Run(**defaults)

    return _factory
