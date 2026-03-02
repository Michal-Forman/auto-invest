import base64
import random
import time
from typing import Any, Dict, List, Optional, Union

import requests
from requests.exceptions import HTTPError, RequestException

from log import log


class Trading212:
    """API client for trading212"""

    _auth_header: str
    host: str

    def __init__(self, api_id_key: str, api_private_key: str, env: str = "dev") -> None:
        credentials: str = f"{api_id_key}:{api_private_key}"
        encoded: str = base64.b64encode(credentials.encode()).decode()

        self._auth_header = f"Basic {encoded}"
        self.host = (
            "https://live.trading212.com"
            if env == "prod"
            else "https://demo.trading212.com"
        )

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        api_version: str = "v0",
    ) -> Dict[str, Any]:
        return self._process_response(
            requests.get(
                f"{self.host}/api/{api_version}/{endpoint}",
                headers={"Authorization": self._auth_header},
                params=params,
            )
        )

    def _post(
        self, endpoint: str, data: Dict[str, Any], api_version: str = "v0"
    ) -> Dict[str, Any]:
        url: str = f"{self.host}/api/{api_version}/{endpoint}"
        headers: Dict[str, str] = {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
        }

        response_data: Dict[str, Any] = self._process_response(
            requests.post(url, headers=headers, json=data)
        )
        return {
            "req": response_data.get("req"),
            "res": response_data.get("res"),
            "err": response_data.get("err"),
        }

    @staticmethod
    def _sleep_for_retry(resp: requests.Response, attempt: int) -> None:
        # Prefer server-provided hint
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
        url: str = f"{self.host}{next_page_path}"
        headers: Dict[str, str] = {"Authorization": self._auth_header}

        for attempt in range(max_retries + 1):
            try:
                resp: requests.Response = requests.get(url, headers=headers)
            except RequestException as e:
                return {"req": None, "res": None, "err": e}

            if resp.status_code == 429:
                if attempt == max_retries:
                    wrapped: Dict[str, Any] = self._process_response(resp)
                    wrapped["err"] = (
                        f"429 Too Many Requests after {max_retries} retries"
                    )
                    return wrapped

                # sleep before retry
                self._sleep_for_retry(resp, attempt)
                continue

            # success case
            return self._process_response(resp)

        raise RuntimeError(
            f"_get_url exited retry loop without returning (max_retries={max_retries})"
        )

    @staticmethod
    def _process_response(resp: requests.Response) -> Dict[str, Any]:
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
        """All open positions"""
        return self._get("equity/portfolio")

    def equity_order_place_market(self, ticker: str, quantity: float) -> Dict[str, Any]:
        """Place market order"""
        response_data: Dict[str, Any] = self._post(
            "equity/orders/market",
            data={"quantity": quantity, "ticker": ticker},
        )
        return {
            "req": response_data.get("req"),
            "res": response_data.get("res"),
            "err": response_data.get("err"),
        }

    def pie(self, id: int) -> Dict[str, Any]:
        """Fetch Pie by ID"""
        return self._get(f"/equity/pies/{id}")

    def pies(self) -> Dict[str, Any]:
        """Fetch all Pies"""
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
        res: List[Dict[str, Any]] = list(response["items"])
        count: int = 0
        amount_of_pages: int = (
            5  # this number * 50 is the total amount of orders we can access, but thanks to Trading 212 429 error increasing this number will increase the run time exponentially! So don't do it if u can. 5 Seems to work prety quick.
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
        params: Dict[str, Union[int, str]] = {"cursor": cursor, "limit": limit}
        if ticker:
            params["ticker"] = ticker

        wrapped: Dict[str, Any] = self._get("equity/history/orders", params=params)
        if wrapped.get("err"):
            raise RuntimeError(wrapped["err"])

        return wrapped["res"][
            "items"
        ]  # just the raw response with items + nextPagePath

    def equity_order(self, id: int) -> Dict[str, Any]:
        """Equity order by ID"""
        return self._get(f"equity/orders/{id}")


if __name__ == "__main__":
    from settings import settings

    t212 = Trading212(
        api_id_key=settings.t212_id_key,
        api_private_key=settings.t212_private_key,
        env=settings.env,
    )

    page = t212.orders_page()
    # print(len(page["items"]))
    # print(page["items"][0])
    # print(t212.equity_order(47212278194))
    # urint(t212.orders())
    # print(t212.pies())
    # print(t212.equity_order_place_market(ticker="VWCEd_EQ", quantity=1))
    print(t212.pies())
