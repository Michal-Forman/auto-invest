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

# Third-party
import pytest

# Local
from core.db.orders import Order
from core.db.runs import Run
from core.instruments import Instruments
from core.settings import PortfolioSettings


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
