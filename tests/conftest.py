# Standard library
import os
from unittest.mock import MagicMock

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
def instruments(portfolio_settings: PortfolioSettings) -> Instruments:
    mock_t212 = MagicMock()
    return Instruments(mock_t212, portfolio_settings)
