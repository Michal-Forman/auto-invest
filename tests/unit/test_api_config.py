# Third-party
from fastapi.testclient import TestClient

# Local (api)
# Local
from api.main import app

client = TestClient(app)


def test_returns_200_with_required_keys():
    resp = client.get("/config")
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "invest_amount",
        "t212_weight",
        "btc_weight",
        "invest_interval",
        "environment",
        "instruments",
    ):
        assert key in data


def test_instruments_list_not_empty():
    resp = client.get("/config")
    assert len(resp.json()["instruments"]) > 0


def test_each_instrument_has_required_fields():
    resp = client.get("/config")
    instruments = resp.json()["instruments"]
    required = {
        "ticker",
        "display_name",
        "yahoo_symbol",
        "currency",
        "instrument_type",
        "cap_type",
    }
    for inst in instruments:
        assert required.issubset(inst.keys())


def test_environment_is_dev():
    resp = client.get("/config")
    assert resp.json()["environment"] == "dev"


def test_btc_cap_type_is_hard():
    resp = client.get("/config")
    instruments = resp.json()["instruments"]
    btc = next(i for i in instruments if i["ticker"] == "BTC")
    assert btc["cap_type"] == "hard"
