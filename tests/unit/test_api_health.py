# Third-party
from fastapi.testclient import TestClient
import pytest

# Local
from api.main import app

client = TestClient(app)


def _patch_health(mocker, t212_raises=None, coinmate_raises=None):
    """Patch get_t212_for_user and get_coinmate_for_user in the health module."""
    mock_t212 = mocker.MagicMock()
    if t212_raises:
        mock_t212.balance.side_effect = t212_raises
    mock_get_t212 = mocker.patch(
        "api.routers.health.get_t212_for_user", return_value=mock_t212
    )

    mock_coinmate = mocker.MagicMock()
    if coinmate_raises:
        mock_coinmate.balance.side_effect = coinmate_raises
    mocker.patch("api.routers.health.get_coinmate_for_user", return_value=mock_coinmate)

    return mock_get_t212, mock_t212


def test_both_ok_returns_all_true(mocker):
    _patch_health(mocker)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"api": True, "t212": True, "coinmate": True}


def test_t212_raises_exception(mocker):
    _patch_health(mocker, t212_raises=RuntimeError("auth failed"))
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
    mock_get_t212, mock_t212 = _patch_health(mocker)
    client.get("/health")
    client.get("/health")
    assert mock_t212.balance.call_count == 1


def test_failed_response_not_cached(mocker):
    mock_get_t212, mock_t212 = _patch_health(mocker, t212_raises=RuntimeError("down"))
    client.get("/health")
    client.get("/health")
    assert mock_t212.balance.call_count == 2


def test_partial_success_not_cached(mocker):
    mock_get_t212, mock_t212 = _patch_health(
        mocker, coinmate_raises=RuntimeError("boom")
    )
    client.get("/health")
    client.get("/health")
    assert mock_t212.balance.call_count == 2
