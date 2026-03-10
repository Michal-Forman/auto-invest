# Standard library
from uuid import UUID

# Third-party
from fastapi.testclient import TestClient
import pytest

# Local (api)
# Local
from api.main import app
from core.db.orders import Order
from core.db.runs import Run

client = TestClient(app)

RUN_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_list_runs_empty(mocker):
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    resp = client.get("/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_runs_returns_items(mocker, make_run):
    mocker.patch.object(
        Run,
        "get_all_runs",
        return_value=[make_run(planned_total_czk=5000.0, total_orders=3)],
    )
    resp = client.get("/runs")
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    assert "id" in item
    assert "created_at" in item
    assert "status" in item
    assert item["total_czk"] == 5000.0
    assert item["order_count"] == 3


def test_limit_param_forwarded(mocker):
    mock = mocker.patch.object(Run, "get_all_runs", return_value=[])
    client.get("/runs?limit=5")
    mock.assert_called_once_with(limit=5, status=None)


def test_status_param_forwarded(mocker):
    mock = mocker.patch.object(Run, "get_all_runs", return_value=[])
    client.get("/runs?status=FILLED")
    mock.assert_called_once_with(limit=50, status="FILLED")


def test_default_limit_is_50(mocker):
    mock = mocker.patch.object(Run, "get_all_runs", return_value=[])
    client.get("/runs")
    mock.assert_called_once_with(limit=50, status=None)


def test_total_czk_defaults_zero_when_none(mocker, make_run):
    mocker.patch.object(
        Run, "get_all_runs", return_value=[make_run(planned_total_czk=None)]
    )
    resp = client.get("/runs")
    assert resp.json()[0]["total_czk"] == 0.0


def test_order_count_defaults_zero_when_none(mocker, make_run):
    mocker.patch.object(Run, "get_all_runs", return_value=[make_run(total_orders=None)])
    resp = client.get("/runs")
    assert resp.json()[0]["order_count"] == 0


def test_run_detail_returns_embedded_orders(mocker, make_run, make_order):
    run = make_run(id=UUID(RUN_ID))
    mocker.patch.object(Run, "get_all_runs", return_value=[run])
    mocker.patch.object(Order, "get_orders_for_runs", return_value=[make_order()])
    resp = client.get(f"/runs/{RUN_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert "orders" in data
    assert len(data["orders"]) == 1


def test_run_detail_returns_404_when_not_found(mocker):
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    resp = client.get(f"/runs/{RUN_ID}")
    assert resp.status_code == 404


def test_run_detail_orders_empty_list(mocker, make_run):
    run = make_run(id=UUID(RUN_ID))
    mocker.patch.object(Run, "get_all_runs", return_value=[run])
    mocker.patch.object(Order, "get_orders_for_runs", return_value=[])
    resp = client.get(f"/runs/{RUN_ID}")
    assert resp.json()["orders"] == []


def test_order_display_name_fallback(mocker, make_run, make_order):
    run = make_run(id=UUID(RUN_ID))
    mocker.patch.object(Run, "get_all_runs", return_value=[run])
    mocker.patch.object(
        Order,
        "get_orders_for_runs",
        return_value=[make_order(t212_ticker="UNKNOWN_EQ")],
    )
    resp = client.get(f"/runs/{RUN_ID}")
    order = resp.json()["orders"][0]
    assert order["display_name"] == "UNKNOWN_EQ"
