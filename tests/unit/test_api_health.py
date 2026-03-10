# Third-party
from fastapi.testclient import TestClient
import pytest

# Local (api)
# Local
from api.main import app

client = TestClient(app)


def _patch_health(mocker, t212_result=None, t212_raises=None, coinmate_raises=None):
    """Patch get_t212 and get_coinmate in the health module. Returns (mock_t212_fn, mock_coinmate_fn)."""
    mock_t212_fn = mocker.patch("api.routers.health.get_t212")
    mock_coinmate_fn = mocker.patch("api.routers.health.get_coinmate")

    if t212_raises:
        mock_t212_fn.return_value.pies.side_effect = t212_raises
    else:
        mock_t212_fn.return_value.pies.return_value = t212_result or {
            "req": {},
            "res": {},
            "err": None,
        }

    if coinmate_raises:
        mock_coinmate_fn.return_value.ticker.side_effect = coinmate_raises
    else:
        mock_coinmate_fn.return_value.ticker.return_value = {"bid": "100"}

    return mock_t212_fn, mock_coinmate_fn


def test_both_ok_returns_all_true(mocker):
    _patch_health(mocker)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"api": True, "t212": True, "coinmate": True}


def test_t212_err_field_set(mocker):
    _patch_health(mocker, t212_result={"req": {}, "res": {}, "err": "timeout"})
    resp = client.get("/health")
    data = resp.json()
    assert data["t212"] is False
    assert data["coinmate"] is True


def test_t212_raises_exception(mocker):
    _patch_health(mocker, t212_raises=RuntimeError("boom"))
    resp = client.get("/health")
    data = resp.json()
    assert data["t212"] is False
    assert data["coinmate"] is True


def test_coinmate_raises(mocker):
    _patch_health(mocker, coinmate_raises=RuntimeError("boom"))
    resp = client.get("/health")
    data = resp.json()
    assert data["t212"] is True
    assert data["coinmate"] is False


def test_both_fail(mocker):
    _patch_health(
        mocker,
        t212_raises=RuntimeError("t212 down"),
        coinmate_raises=RuntimeError("coinmate down"),
    )
    resp = client.get("/health")
    data = resp.json()
    assert data["t212"] is False
    assert data["coinmate"] is False


def test_successful_response_is_cached(mocker):
    mock_t212_fn, _ = _patch_health(mocker)
    client.get("/health")
    client.get("/health")
    assert mock_t212_fn.return_value.pies.call_count == 1


def test_failed_response_not_cached(mocker):
    mock_t212_fn, _ = _patch_health(
        mocker, t212_result={"req": {}, "res": {}, "err": "timeout"}
    )
    client.get("/health")
    client.get("/health")
    assert mock_t212_fn.return_value.pies.call_count == 2


def test_partial_success_not_cached(mocker):
    mock_t212_fn, mock_coinmate_fn = _patch_health(
        mocker, coinmate_raises=RuntimeError("boom")
    )
    client.get("/health")
    client.get("/health")
    assert mock_t212_fn.return_value.pies.call_count == 2
    assert mock_coinmate_fn.return_value.ticker.call_count == 2
