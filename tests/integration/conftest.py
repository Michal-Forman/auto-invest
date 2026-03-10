# Standard library
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import MagicMock

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from core.coinmate import Coinmate
from core.mailer import Mailer
from core.settings import PortfolioSettings, UserSettings
from core.trading212 import Trading212


def _make_user_settings(**overrides: Any) -> UserSettings:
    defaults: Dict[str, Any] = {
        "user_id": "test-user-id",
        "t212_id_key": "test-t212-key",
        "t212_private_key": "test-t212-priv",
        "coinmate_client_id": 1,
        "coinmate_public_key": "test-pub",
        "coinmate_private_key": "test-priv",
        "my_mail": "test@example.com",
        "mail_recipient": "recipient@example.com",
        "mail_host": "smtp.example.com",
        "mail_port": 465,
        "mail_password": "secret",
        "t212_deposit_account": None,
        "t212_deposit_vs": None,
        "coinmate_deposit_account": None,
        "coinmate_deposit_vs": None,
        "btc_external_adress": "bc1qexampleaddressfortesting",
        "portfolio": PortfolioSettings(
            pie_id=1,
            t212_weight=95,
            btc_weight=0.05,
            invest_amount=5000.0,
            invest_interval="0 9 * * *",
            balance_buffer=1.5,
            balance_alert_days=7,
            btc_withdrawal_treshold=500000,
        ),
        "env": "dev",
    }
    defaults.update(overrides)
    return UserSettings(**defaults)


def make_mailer(**overrides: Any) -> Mailer:
    """Build a Mailer with test user settings."""
    return Mailer(_make_user_settings(**overrides))


def _make_chain() -> MagicMock:
    chain = MagicMock()
    for m in [
        "select",
        "insert",
        "update",
        "eq",
        "neq",
        "gte",
        "lt",
        "limit",
        "order",
        "upsert",
    ]:
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[], count=0)
    return chain


@pytest.fixture
def supabase_mocks(mocker: MockerFixture) -> SimpleNamespace:
    """Patch db.orders.supabase and db.runs.supabase with independent mock chains."""
    orders_chain = _make_chain()
    runs_chain = _make_chain()

    mock_orders_sb = mocker.patch("core.db.orders.supabase")
    mock_runs_sb = mocker.patch("core.db.runs.supabase")

    mock_orders_sb.table.return_value = orders_chain
    mock_runs_sb.table.side_effect = lambda name: (
        runs_chain if name == "runs" else orders_chain
    )

    return SimpleNamespace(orders_chain=orders_chain, runs_chain=runs_chain)


@pytest.fixture
def t212() -> Trading212:
    """Real Trading212 instance — individual methods patched per test."""
    return Trading212("test-key", "test-priv-key", env="dev")


@pytest.fixture
def coinmate() -> Coinmate:
    """Real Coinmate instance — individual methods patched per test."""
    return Coinmate(1, "test-pub", "test-priv")


@pytest.fixture
def portfolio_settings() -> PortfolioSettings:
    """Equal t212/btc weights so BTC allocation stays above the 25 CZK minimum."""
    return PortfolioSettings(
        pie_id=1,
        t212_weight=1,
        btc_weight=1,
        invest_amount=5000.0,
        invest_interval="0 9 * * *",
        balance_buffer=1.5,
        balance_alert_days=7,
        btc_withdrawal_treshold=500000,
    )


# ---------------------------------------------------------------------------
# Reusable API response shapes
# ---------------------------------------------------------------------------


@pytest.fixture
def t212_pie_response() -> dict:
    return {
        "req": {"method": "GET", "url": "...", "headers": [], "body": None},
        "res": {"instruments": [{"ticker": "VWCEd_EQ", "expectedShare": 1.0}]},
        "err": None,
    }


@pytest.fixture
def t212_order_place_response() -> dict:
    return {
        "req": {"method": "POST", "url": "...", "headers": [], "body": None},
        "res": {
            "id": 12345,
            "status": "FILLED",
            "filledQuantity": 1.5,
            "quantity": 1.5,
            "extendedHours": False,
        },
        "err": None,
    }


@pytest.fixture
def t212_history_item() -> dict:
    return {
        "order": {
            "id": 12345,
            "status": "FILLED",
            "filledQuantity": 1.5,
        },
        "fill": {
            "filledAt": "2026-03-03T10:00:00+00:00",
            "price": 100.0,
            "walletImpact": {
                "netValue": 1000.0,
                "fxRate": 0.04,  # code inverts: fill_fx_rate = 1/0.04 = 25.0
                "taxes": [{"quantity": 2.0, "currency": "EUR"}],
            },
        },
    }


@pytest.fixture
def coinmate_buy_response() -> dict:
    return {
        "req": {
            "method": "POST",
            "url": "...",
            "headers": [],
            "body": "FORM_DATA_REDACTED",
        },
        "res": {"error": False, "errorMessage": None, "data": 987654},
        "err": None,
    }


@pytest.fixture
def coinmate_history_response() -> dict:
    return {
        "req": {
            "method": "POST",
            "url": "...",
            "headers": [],
            "body": "FORM_DATA_REDACTED",
        },
        "res": {
            "error": False,
            "errorMessage": None,
            "data": [
                {
                    "orderId": 987654,
                    "amount": 0.001,
                    "price": 2_500_000.0,
                    "fee": 25.0,
                    "createdTimestamp": 1_740_000_000_000,
                }
            ],
        },
        "err": None,
    }
