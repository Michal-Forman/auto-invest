# Standard library
import hashlib
import hmac
from typing import Any, Dict
from unittest.mock import MagicMock

# Third-party
from freezegun import freeze_time
import pytest
from pytest_mock import MockerFixture
import requests

# Local
from coinmate import Coinmate


@pytest.fixture
def coinmate() -> Coinmate:
    return Coinmate(
        client_id=12345,
        public_key="test-pub",
        private_key="test-priv",
        timeout_s=20,
    )


def _make_post_response(json_data: Dict[str, Any]) -> MagicMock:
    """Build a mock session.post response with the required request attributes."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    mock_resp.request.method = "POST"
    mock_resp.request.url = "https://coinmate.io/api/test"
    mock_resp.request.headers = {"Content-Type": "application/x-www-form-urlencoded"}
    return mock_resp


class TestInit:
    def test_stores_credentials_and_timeout(self) -> None:
        cm = Coinmate(client_id=999, public_key="pub", private_key="priv", timeout_s=30)
        assert cm.client_id == 999
        assert cm.public_key == "pub"
        assert cm.private_key == "priv"
        assert cm.timeout_s == 30


class TestNonce:
    def test_nonce_is_millisecond_timestamp(self, coinmate: Coinmate) -> None:
        import time

        with freeze_time("2026-03-03 09:00:00"):
            nonce = coinmate._nonce()
            expected = str(int(time.time() * 1000))
        assert nonce == expected

    def test_nonce_increments_when_called_at_same_millisecond(
        self, coinmate: Coinmate
    ) -> None:
        with freeze_time("2026-03-03 09:00:00"):
            nonce1 = coinmate._nonce()
            nonce2 = coinmate._nonce()
        assert int(nonce2) == int(nonce1) + 1


class TestSignature:
    def test_signature_is_uppercase_hmac_sha256(self, coinmate: Coinmate) -> None:
        nonce = "1741000800000"
        msg = f"{nonce}{coinmate.client_id}{coinmate.public_key}".encode("utf-8")
        key = coinmate.private_key.encode("utf-8")
        expected = hmac.new(key, msg, digestmod=hashlib.sha256).hexdigest().upper()
        assert coinmate._signature(nonce) == expected


class TestPrivatePayload:
    def test_payload_contains_required_fields(self, coinmate: Coinmate) -> None:
        payload = coinmate._private_payload()
        assert "clientId" in payload
        assert "publicKey" in payload
        assert "nonce" in payload
        assert "signature" in payload

    def test_extra_fields_merged_into_payload(self, coinmate: Coinmate) -> None:
        payload = coinmate._private_payload(
            {"total": "500.00", "currencyPair": "BTC_CZK"}
        )
        assert payload["total"] == "500.00"
        assert payload["currencyPair"] == "BTC_CZK"


class TestGet:
    def test_get_calls_correct_url_with_params(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": "result"}
        mock_get = mocker.patch.object(coinmate.session, "get", return_value=mock_resp)

        result = coinmate._get("/ticker", params={"currencyPair": "BTC_CZK"})

        mock_get.assert_called_once_with(
            "https://coinmate.io/api/ticker",
            params={"currencyPair": "BTC_CZK"},
            timeout=20,
        )
        assert result == {"data": "result"}

    def test_get_raises_on_http_error(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
        mocker.patch.object(coinmate.session, "get", return_value=mock_resp)

        with pytest.raises(requests.HTTPError):
            coinmate._get("/ticker")


class TestPost:
    def test_post_success_wraps_response(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        json_data: Dict[str, Any] = {"error": False, "data": "order123"}
        mock_resp = _make_post_response(json_data)
        mocker.patch.object(coinmate.session, "post", return_value=mock_resp)

        result = coinmate._post("/buyInstant", data={"total": "500"})

        assert result["err"] is None
        assert result["res"] == json_data

    def test_post_error_response_sets_err(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        json_data: Dict[str, Any] = {
            "error": True,
            "errorMessage": "Insufficient funds",
        }
        mock_resp = _make_post_response(json_data)
        mocker.patch.object(coinmate.session, "post", return_value=mock_resp)

        result = coinmate._post("/buyInstant", data={"total": "500"})

        assert result["err"] == "Insufficient funds"

    def test_post_body_always_redacted(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        json_data: Dict[str, Any] = {"error": False, "data": "ok"}
        mock_resp = _make_post_response(json_data)
        mocker.patch.object(coinmate.session, "post", return_value=mock_resp)

        result = coinmate._post("/balances", data={"secret": "password"})

        assert result["req"]["body"] == "FORM_DATA_REDACTED"


class TestPublicEndpoints:
    def test_ticker_calls_correct_endpoint(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_get = mocker.patch.object(
            coinmate, "_get", return_value={"last": 1_000_000}
        )
        coinmate.ticker("BTC_CZK")
        mock_get.assert_called_once_with("/ticker", params={"currencyPair": "BTC_CZK"})

    def test_transactions_calls_correct_endpoint_with_limit(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_get = mocker.patch.object(coinmate, "_get", return_value={"data": []})
        coinmate.transactions("BTC_CZK", limit=50)
        mock_get.assert_called_once_with(
            "/transactions",
            params={"currencyPair": "BTC_CZK", "limit": 50},
        )


class TestPrivateEndpoints:
    def test_balances_calls_balances_endpoint(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_post = mocker.patch.object(
            coinmate,
            "_post",
            return_value={
                "err": None,
                "res": {"data": {"CZK": {"balance": "1000.0"}}},
                "req": {},
            },
        )
        mocker.patch.object(
            coinmate, "_private_payload", return_value={"payload": "data"}
        )
        coinmate.balance()
        mock_post.assert_called_once_with("/balances", data={"payload": "data"})

    def test_buy_instant_includes_total_and_pair(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_post = mocker.patch.object(
            coinmate, "_post", return_value={"err": None, "res": {}, "req": {}}
        )
        coinmate.buy_instant(500.0, "BTC_CZK")
        data = mock_post.call_args.kwargs["data"]
        assert data["total"] == "500.0"
        assert data["currencyPair"] == "BTC_CZK"

    def test_buy_instant_includes_client_order_id_when_provided(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_post = mocker.patch.object(
            coinmate, "_post", return_value={"err": None, "res": {}, "req": {}}
        )
        coinmate.buy_instant(500.0, "BTC_CZK", client_order_id=42)
        data = mock_post.call_args.kwargs["data"]
        assert data["clientOrderId"] == "42"

    def test_buy_instant_omits_client_order_id_when_none(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_post = mocker.patch.object(
            coinmate, "_post", return_value={"err": None, "res": {}, "req": {}}
        )
        coinmate.buy_instant(500.0, "BTC_CZK", client_order_id=None)
        data = mock_post.call_args.kwargs["data"]
        assert "clientOrderId" not in data

    def test_user_trades_calls_trade_history_endpoint(
        self, coinmate: Coinmate, mocker: MockerFixture
    ) -> None:
        mock_post = mocker.patch.object(
            coinmate, "_post", return_value={"err": None, "res": {}, "req": {}}
        )
        coinmate.user_trades("BTC_CZK", limit=10)
        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == "/tradeHistory"
