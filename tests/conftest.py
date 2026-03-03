# Standard library
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict
from unittest.mock import MagicMock
from uuid import UUID

# Set all required env vars before importing any local modules.
# setdefault won't override values already in os.environ (e.g. from a shell),
# but since load_dotenv hasn't run yet at conftest-load time, this guarantees
# CI environments without .env.dev still get a valid settings singleton.
for _key, _val in {
    "T212_ID_KEY": "test-key",
    "T212_PRIVATE_KEY": "test-priv-key",
    "PIE_ID": "1",
    "T212_WEIGHT": "95",
    "BTC_WEIGHT": "0.05",
    "INVEST_AMOUNT": "5000.0",
    "INVEST_INTERVAL": "0 9 * * *",
    "COINMATE_CLIENT_ID": "1",
    "COINMATE_PUBLIC_KEY": "test-pub",
    "COINMATE_PRIVATE_KEY": "test-priv",
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test.service.key",
}.items():
    os.environ.setdefault(_key, _val)

# Third-party
import pytest

# Local
from db.orders import Order
from db.runs import Run
from instruments import Instruments
from settings import PortfolioSettings


@pytest.fixture
def portfolio_settings() -> PortfolioSettings:
    return PortfolioSettings(
        pie_id=1,
        t212_weight=95,
        btc_weight=0.05,
        invest_amount=5000.0,
        invest_interval="0 9 * * *",
    )


@pytest.fixture
def mock_t212() -> MagicMock:
    return MagicMock()


@pytest.fixture
def instruments(mock_t212: MagicMock, portfolio_settings: PortfolioSettings) -> Instruments:
    return Instruments(mock_t212, portfolio_settings)


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
