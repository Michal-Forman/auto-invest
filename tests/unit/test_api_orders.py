# Third-party
from fastapi.testclient import TestClient
import pytest

# Local (api)
# Local
from api.main import app
from core.db.orders import Order

client = TestClient(app)


def test_returns_empty_list(mocker):
    mocker.patch.object(Order, "get_orders", return_value=[])
    resp = client.get("/orders")
    assert resp.status_code == 200
    assert resp.json() == []


def test_returns_orders(mocker, make_order):
    mocker.patch.object(Order, "get_orders", return_value=[make_order()])
    resp = client.get("/orders")
    assert len(resp.json()) == 1


def test_no_filters_passes_none(mocker):
    mock = mocker.patch.object(Order, "get_orders", return_value=[])
    client.get("/orders")
    mock.assert_called_once_with(ticker=None, exchange=None, status=None)


def test_ticker_filter_forwarded(mocker):
    mock = mocker.patch.object(Order, "get_orders", return_value=[])
    client.get("/orders?ticker=VWCEd_EQ")
    mock.assert_called_once_with(ticker="VWCEd_EQ", exchange=None, status=None)


def test_exchange_filter_forwarded(mocker):
    mock = mocker.patch.object(Order, "get_orders", return_value=[])
    client.get("/orders?exchange=T212")
    mock.assert_called_once_with(ticker=None, exchange="T212", status=None)


def test_status_filter_forwarded(mocker):
    mock = mocker.patch.object(Order, "get_orders", return_value=[])
    client.get("/orders?status=FILLED")
    mock.assert_called_once_with(ticker=None, exchange=None, status="FILLED")


def test_all_filters_combined(mocker):
    mock = mocker.patch.object(Order, "get_orders", return_value=[])
    client.get("/orders?ticker=BTC&exchange=COINMATE&status=SUBMITTED")
    mock.assert_called_once_with(ticker="BTC", exchange="COINMATE", status="SUBMITTED")


def test_optional_fields_null_when_none(mocker, make_order):
    mocker.patch.object(
        Order,
        "get_orders",
        return_value=[make_order(filled_quantity=None, fill_price=None)],
    )
    resp = client.get("/orders")
    item = resp.json()[0]
    assert item["quantity"] is None
    assert item["fill_price"] is None


def test_display_name_resolution(mocker, make_order):
    mocker.patch.object(
        Order, "get_orders", return_value=[make_order(t212_ticker="VWCEd_EQ")]
    )
    resp = client.get("/orders")
    assert resp.json()[0]["display_name"] == "Vanguard FTSE All-World UCITS ETF (Acc)"


def test_display_name_fallback_to_ticker(mocker, make_order):
    mocker.patch.object(
        Order, "get_orders", return_value=[make_order(t212_ticker="UNKNOWN_EQ")]
    )
    resp = client.get("/orders")
    assert resp.json()[0]["display_name"] == "UNKNOWN_EQ"
