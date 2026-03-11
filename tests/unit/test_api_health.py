# Standard library
from unittest.mock import MagicMock

# Third-party
from fastapi.testclient import TestClient
import pytest

# Local
from api.main import app

client = TestClient(app)


def _patch_health(mocker, t212_ok=True, coinmate_raises=None):
    """Patch Trading212.ping and requests.get in the health module."""
    mocker.patch("api.routers.health.Trading212.ping", return_value=t212_ok)
    mock_requests_get = mocker.patch(
        "api.routers.health.requests.get",
        return_value=MagicMock(status_code=200),
    )
    if coinmate_raises:
        mock_requests_get.side_effect = coinmate_raises
    return mock_requests_get


def test_both_ok_returns_all_true(mocker):
    _patch_health(mocker)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"api": True, "t212": True, "coinmate": True}


def test_t212_raises_exception(mocker):
    _patch_health(mocker, t212_ok=False)
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
    _patch_health(mocker, t212_ok=False, coinmate_raises=RuntimeError("coinmate down"))
    resp = client.get("/health")
    data = resp.json()
    assert data["t212"] is False
    assert data["coinmate"] is False


def test_successful_response_is_cached(mocker):
    mock_ping = mocker.patch("api.routers.health.Trading212.ping", return_value=True)
    mocker.patch(
        "api.routers.health.requests.get",
        return_value=MagicMock(status_code=200),
    )
    client.get("/health")
    client.get("/health")
    assert mock_ping.call_count == 1


def test_failed_response_not_cached(mocker):
    mock_ping = mocker.patch("api.routers.health.Trading212.ping", return_value=False)
    mocker.patch(
        "api.routers.health.requests.get",
        return_value=MagicMock(status_code=200),
    )
    client.get("/health")
    client.get("/health")
    assert mock_ping.call_count == 2


def test_partial_success_not_cached(mocker):
    mock_ping = mocker.patch("api.routers.health.Trading212.ping", return_value=True)
    mock_requests_get = mocker.patch(
        "api.routers.health.requests.get",
        side_effect=RuntimeError("boom"),
    )
    client.get("/health")
    client.get("/health")
    assert mock_ping.call_count == 2
    assert mock_requests_get.call_count == 2
