# Standard library
import base64
import random
import time
from typing import Any, Dict, List, Optional, Union

# Third-party
import requests
from requests.exceptions import HTTPError, RequestException

# Local
from log import log


class Trading212:
    _auth_header: str
    host: str

    def __init__(self, api_id_key: str, api_private_key: str, env: str = "dev") -> None:
        """Initialize the T212 REST client with Basic Auth. Uses live host in prod, demo otherwise."""
        credentials: str = f"{api_id_key}:{api_private_key}"
        encoded: str = base64.b64encode(credentials.encode()).decode()

        self._auth_header = f"Basic {encoded}"
        self.host = (
            "https://live.trading212.com"
            if env == "prod"
            else "https://demo.trading212.com"
        )

    def _get_with_retry(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 6,
    ) -> Dict[str, Any]:
        """Perform a GET request with automatic 429 retry and exponential backoff."""
        headers: Dict[str, str] = {"Authorization": self._auth_header}

        for attempt in range(max_retries + 1):
            try:
                resp: requests.Response = requests.get(
                    url, headers=headers, params=params
                )
            except RequestException as e:
                return {"req": None, "res": None, "err": e}

            if resp.status_code == 429:
                if attempt == max_retries:
                    wrapped: Dict[str, Any] = self._process_response(resp)
                    wrapped["err"] = (
                        f"429 Too Many Requests after {max_retries} retries"
                    )
                    return wrapped
                self._sleep_for_retry(resp, attempt)
                continue

            return self._process_response(resp)

        raise RuntimeError(
            f"_get_with_retry exited retry loop without returning (max_retries={max_retries})"
        )

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        api_version: str = "v0",
    ) -> Dict[str, Any]:
        """Send an authenticated GET request and return the wrapped response."""
        return self._get_with_retry(
            f"{self.host}/api/{api_version}/{endpoint}", params=params
        )

    def _post(
        self, endpoint: str, data: Dict[str, Any], api_version: str = "v0"
    ) -> Dict[str, Any]:
        """Send an authenticated POST request with JSON body and return the wrapped response."""
        url: str = f"{self.host}/api/{api_version}/{endpoint}"
        headers: Dict[str, str] = {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
        }

        return self._process_response(requests.post(url, headers=headers, json=data))

    @staticmethod
    def _sleep_for_retry(resp: requests.Response, attempt: int) -> None:
        """Sleep before retrying a rate-limited request. Uses Retry-After header if available, otherwise exponential backoff with jitter."""
        retry_after: Optional[str] = resp.headers.get("Retry-After")
        if retry_after:
            try:
                time.sleep(float(retry_after))
                return
            except ValueError:
                pass

        # Exponential backoff with jitter
        base_delay: float = min(2**attempt, 60)  # cap at 60s
        time.sleep(base_delay + random.random())

    def _get_url(self, next_page_path: str, max_retries: int = 6) -> Dict[str, Any]:
        """Fetch a full URL (used for pagination) with automatic 429 retry and exponential backoff."""
        return self._get_with_retry(
            f"{self.host}{next_page_path}", max_retries=max_retries
        )

    @staticmethod
    def _process_response(resp: requests.Response) -> Dict[str, Any]:
        """Wrap a raw HTTP response into the standard {req, res, err} dict format."""
        req_data: Dict[str, Any] = {
            "method": resp.request.method,
            "url": resp.request.url,
            "headers": list(resp.request.headers.keys()),
            "body": (
                resp.request.body.decode()
                if isinstance(resp.request.body, bytes)
                else resp.request.body
            ),
        }

        try:
            resp.raise_for_status()
        except HTTPError as http_err:
            log.error(f"T212 response error: {http_err}")

            return {
                "req": req_data,
                "res": resp.json() if resp else None,
                "err": http_err,
            }

        return {
            "req": req_data,
            "res": resp.json(),
            "err": None,
        }

    # --------------
    # Public methods
    # --------------

    def portfolio(self) -> Dict[str, Any]:
        """Fetch all open equity positions."""
        return self._get("equity/portfolio")

    def equity_order_place_market(self, ticker: str, quantity: float) -> Dict[str, Any]:
        """Place a market buy/sell order for the given ticker and quantity."""
        return self._post(
            "equity/orders/market",
            data={"quantity": quantity, "ticker": ticker},
        )

    def pie(self, pie_id: int) -> Dict[str, Any]:
        """Fetch a single pie's configuration (instruments and target weights) by ID."""
        return self._get(f"equity/pies/{pie_id}")

    def pies(self) -> Dict[str, Any]:
        """Fetch all pies on the account."""
        return self._get("equity/pies")

    def positions(self, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch open positions. If ticker is provided, filters by ticker.
        Returns the raw wrapped response: {"req": ..., "res": [...], "err": ...}
        """
        params: Optional[Dict[str, str]] = (
            {"ticker": ticker.strip()} if ticker else None
        )
        return self._get("equity/positions", params=params)

    def get_current_price(self, ticker: str) -> float:
        """
        Returns currentPrice for an instrument you currently hold (open position).
        """
        ticker = ticker.strip()
        wrapped: Dict[str, Any] = self.positions(ticker=ticker)

        if wrapped.get("err"):
            raise ValueError(f"Error fetching positions for {ticker}: {wrapped['err']}")

        position_list: List[Dict[str, Any]] = wrapped["res"] or []
        if not position_list:
            raise ValueError(
                f"No open position for {ticker}. "
                "T212 API provides currentPrice via /equity/positions only for open positions."
            )

        return float(position_list[0]["currentPrice"])

    def _process_items(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all items from a paginated T212 response by following nextPagePath links."""
        res: List[Dict[str, Any]] = list(response["items"])
        count: int = 0
        amount_of_pages: int = (
            5  # this number * 50 is the total amount of orders we can access, but thanks to Trading 212 429 error increasing this number will increase the run time exponentially! So don't do it if you can. 5 seems to work pretty quick.
        )

        while count < amount_of_pages:
            next_page: Optional[str] = response.get("nextPagePath")
            if next_page is None:
                break
            wrapped: Dict[str, Any] = self._get_url(next_page)
            if wrapped.get("err"):
                raise RuntimeError(wrapped["err"])
            response = wrapped["res"]
            res += response["items"]
            count += 1

        return res

    def orders(
        self, cursor: int = 0, ticker: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch order history with full pagination (follows nextPagePath up to the configured page limit)."""
        params: Dict[str, Union[int, str]] = {"cursor": cursor, "limit": limit}
        if ticker:
            params["ticker"] = ticker

        wrapped: Dict[str, Any] = self._get("equity/history/orders", params=params)

        if wrapped.get("err"):
            raise RuntimeError(wrapped["err"])

        return self._process_items(wrapped["res"])

    def orders_page(
        self, cursor: int = 0, ticker: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch a single page of order history (no pagination). Used in non-prod to avoid rate limits."""
        params: Dict[str, Union[int, str]] = {"cursor": cursor, "limit": limit}
        if ticker:
            params["ticker"] = ticker

        wrapped: Dict[str, Any] = self._get("equity/history/orders", params=params)
        if wrapped.get("err"):
            raise RuntimeError(wrapped["err"])

        return wrapped["res"][
            "items"
        ]  # just the raw response with items + nextPagePath

    def equity_order(self, order_id: int) -> Dict[str, Any]:
        """Fetch a single equity order by its ID."""
        return self._get(f"equity/orders/{order_id}")

    def balance(self) -> float:
        """Fetch the available-to-trade cash balance from the account summary."""
        wrapped: Dict[str, Any] = self._get("equity/account/summary")
        if wrapped.get("err"):
            raise RequestException(f"Could not fetch balance: {wrapped['err']}")
        try:
            return float(wrapped["res"]["cash"]["availableToTrade"])
        except (KeyError, TypeError) as e:
            raise RequestException(f"Unexpected balance response structure: {e}")


if __name__ == "__main__":
    from settings import settings

    t212 = Trading212(settings.t212_id_key, settings.t212_private_key, env=settings.env)
    print(t212.balance())
