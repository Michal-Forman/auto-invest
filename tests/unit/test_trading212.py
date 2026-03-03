# Standard library
from typing import Any, Dict, List
from unittest.mock import MagicMock

# Third-party
import pytest
import requests
from pytest_mock import MockerFixture

# Local
from trading212 import Trading212


@pytest.fixture
def t212() -> Trading212:
    return Trading212(api_id_key="test-id", api_private_key="test-priv", env="dev")


def _make_response(
    status_code: int = 200,
    json_data: Any = None,
    headers: Any = None,
    body: Any = None,
) -> MagicMock:
    """Build a mock requests.Response with required attributes."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data if json_data is not None else {}
    mock_resp.headers = headers or {}
    mock_resp.request.method = "GET"
    mock_resp.request.url = "https://demo.trading212.com/api/v0/test"
    mock_resp.request.headers = {"Authorization": "Basic dGVzdC1pZDp0ZXN0LXByaXY="}
    mock_resp.request.body = body
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Error", response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


class TestInit:
    def test_basic_auth_header_encoded(self) -> None:
        import base64

        t = Trading212(api_id_key="myid", api_private_key="mypriv", env="dev")
        expected = "Basic " + base64.b64encode(b"myid:mypriv").decode()
        assert t._auth_header == expected

    def test_host_is_live_in_prod(self) -> None:
        t = Trading212(api_id_key="id", api_private_key="priv", env="prod")
        assert t.host == "https://live.trading212.com"

    def test_host_is_demo_in_dev(self) -> None:
        t = Trading212(api_id_key="id", api_private_key="priv", env="dev")
        assert t.host == "https://demo.trading212.com"


class TestProcessResponse:
    def test_success_response_wrapping(self, t212: Trading212) -> None:
        mock_resp = _make_response(200, json_data={"key": "value"})
        result = t212._process_response(mock_resp)
        assert result["err"] is None
        assert result["res"] == {"key": "value"}
        assert result["req"]["method"] == "GET"

    def test_http_error_wrapping(self, t212: Trading212) -> None:
        mock_resp = _make_response(429, json_data={"message": "rate limited"})
        result = t212._process_response(mock_resp)
        assert result["err"] is not None
        assert isinstance(result["err"], requests.exceptions.HTTPError)

    def test_bytes_body_decoded(self, t212: Trading212) -> None:
        mock_resp = _make_response(200, body=b'{"ticker":"AAPL"}')
        result = t212._process_response(mock_resp)
        assert result["req"]["body"] == '{"ticker":"AAPL"}'


class TestSleepForRetry:
    def test_uses_retry_after_header_when_present(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mock_sleep = mocker.patch("trading212.time.sleep")
        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = "5"
        t212._sleep_for_retry(mock_resp, attempt=0)
        mock_sleep.assert_called_once_with(5.0)

    def test_uses_exponential_backoff_when_no_header(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mock_sleep = mocker.patch("trading212.time.sleep")
        mocker.patch("trading212.random.random", return_value=0.0)
        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = None
        t212._sleep_for_retry(mock_resp, attempt=2)
        # 2**2 = 4, + 0.0 jitter
        mock_sleep.assert_called_once_with(pytest.approx(4.0))

    def test_invalid_retry_after_falls_back_to_backoff(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mock_sleep = mocker.patch("trading212.time.sleep")
        mocker.patch("trading212.random.random", return_value=0.0)
        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = "not-a-number"
        t212._sleep_for_retry(mock_resp, attempt=1)
        # falls back: 2**1 = 2, + 0.0 jitter
        mock_sleep.assert_called_once_with(pytest.approx(2.0))


class TestGetWithRetry:
    def test_success_on_first_attempt(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mock_resp = _make_response(200, json_data={"data": "ok"})
        mocker.patch("trading212.requests.get", return_value=mock_resp)
        result = t212._get_with_retry("https://demo.trading212.com/api/v0/test")
        assert result["err"] is None
        assert result["res"] == {"data": "ok"}

    def test_retries_on_429_then_succeeds(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mock_429 = _make_response(429)
        mock_429.headers = MagicMock()
        mock_429.headers.get.return_value = "0"
        mock_200 = _make_response(200, json_data={"data": "ok"})
        mocker.patch("trading212.requests.get", side_effect=[mock_429, mock_200])
        mock_sleep = mocker.patch("trading212.time.sleep")

        result = t212._get_with_retry("https://demo.trading212.com/api/v0/test")

        assert result["err"] is None
        mock_sleep.assert_called_once()

    def test_returns_error_after_max_retries_exceeded(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mock_429 = _make_response(429)
        mock_429.headers = MagicMock()
        mock_429.headers.get.return_value = "0"
        mocker.patch("trading212.requests.get", return_value=mock_429)
        mocker.patch("trading212.time.sleep")

        result = t212._get_with_retry(
            "https://demo.trading212.com/api/v0/test", max_retries=2
        )

        assert result["err"] is not None
        assert "429" in str(result["err"])

    def test_returns_error_on_request_exception(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trading212.requests.get",
            side_effect=requests.exceptions.RequestException("connection failed"),
        )
        result = t212._get_with_retry("https://demo.trading212.com/api/v0/test")
        assert result["err"] is not None
        assert result["req"] is None


class TestPublicMethods:
    @pytest.fixture(autouse=True)
    def setup(self, t212: Trading212, mocker: MockerFixture) -> None:
        self.mock_get = mocker.patch.object(
            t212, "_get", return_value={"req": None, "res": {}, "err": None}
        )
        self.mock_post = mocker.patch.object(
            t212, "_post", return_value={"req": None, "res": {}, "err": None}
        )
        self.t212 = t212

    def test_portfolio_calls_correct_endpoint(self) -> None:
        self.t212.portfolio()
        self.mock_get.assert_called_once_with("equity/portfolio")

    def test_equity_order_place_market_posts_ticker_and_quantity(self) -> None:
        self.t212.equity_order_place_market("AAPL_US_EQ", 2.5)
        self.mock_post.assert_called_once_with(
            "equity/orders/market",
            data={"quantity": 2.5, "ticker": "AAPL_US_EQ"},
        )

    def test_pie_calls_correct_endpoint(self) -> None:
        self.t212.pie(42)
        self.mock_get.assert_called_once_with("equity/pies/42")

    def test_pies_calls_correct_endpoint(self) -> None:
        self.t212.pies()
        self.mock_get.assert_called_once_with("equity/pies")

    def test_positions_with_ticker_passes_param(self) -> None:
        self.t212.positions(ticker="VWCEd_EQ")
        self.mock_get.assert_called_once_with(
            "equity/positions", params={"ticker": "VWCEd_EQ"}
        )

    def test_positions_without_ticker_passes_no_param(self) -> None:
        self.t212.positions()
        self.mock_get.assert_called_once_with("equity/positions", params=None)

    def test_equity_order_calls_correct_endpoint(self) -> None:
        self.t212.equity_order(99)
        self.mock_get.assert_called_once_with("equity/orders/99")


class TestGetCurrentPrice:
    def test_returns_price_for_open_position(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            t212,
            "positions",
            return_value={"res": [{"currentPrice": 100.5}], "err": None},
        )
        result = t212.get_current_price("VWCEd_EQ")
        assert result == pytest.approx(100.5)

    def test_raises_on_api_error(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            t212,
            "positions",
            return_value={"res": None, "err": "HTTP 429"},
        )
        with pytest.raises(ValueError, match="Error fetching positions"):
            t212.get_current_price("VWCEd_EQ")

    def test_raises_when_no_open_position(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            t212,
            "positions",
            return_value={"res": [], "err": None},
        )
        with pytest.raises(ValueError, match="No open position"):
            t212.get_current_price("VWCEd_EQ")


class TestProcessItems:
    def test_single_page_no_next_page(self, t212: Trading212) -> None:
        response: Dict[str, Any] = {
            "items": [{"id": 1}, {"id": 2}],
        }
        result = t212._process_items(response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_follows_next_page_path(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        first_response: Dict[str, Any] = {
            "items": [{"id": 1}],
            "nextPagePath": "/api/v0/equity/history/orders?cursor=50",
        }
        second_page: Dict[str, Any] = {"items": [{"id": 2}]}
        mocker.patch.object(
            t212,
            "_get_url",
            return_value={"req": None, "res": second_page, "err": None},
        )
        result = t212._process_items(first_response)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_raises_on_page_fetch_error(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        first_response: Dict[str, Any] = {
            "items": [{"id": 1}],
            "nextPagePath": "/api/v0/equity/history/orders?cursor=50",
        }
        mocker.patch.object(
            t212,
            "_get_url",
            return_value={"req": None, "res": None, "err": "timeout"},
        )
        with pytest.raises(RuntimeError):
            t212._process_items(first_response)


class TestOrders:
    def test_orders_returns_all_paginated_items(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        items: List[Dict[str, Any]] = [{"order": {"id": 1}}, {"order": {"id": 2}}]
        mocker.patch.object(
            t212,
            "_get",
            return_value={"req": None, "res": {"items": items}, "err": None},
        )
        result = t212.orders()
        assert len(result) == 2

    def test_orders_raises_on_api_error(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            t212,
            "_get",
            return_value={"req": None, "res": None, "err": "rate limited"},
        )
        with pytest.raises(RuntimeError):
            t212.orders()

    def test_orders_page_returns_items_without_pagination(
        self, t212: Trading212, mocker: MockerFixture
    ) -> None:
        items: List[Dict[str, Any]] = [{"order": {"id": 1}}]
        # nextPagePath present but orders_page should not follow it
        mocker.patch.object(
            t212,
            "_get",
            return_value={
                "req": None,
                "res": {"items": items, "nextPagePath": "/api/v0/next"},
                "err": None,
            },
        )
        result = t212.orders_page()
        assert len(result) == 1
