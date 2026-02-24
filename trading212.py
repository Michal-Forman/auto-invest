import logging
from datetime import datetime
import requests
from requests.exceptions import HTTPError
import base64
from typing import Optional, Dict, Any

class Trading212:
    """API client for trading212"""

    def __init__(self, api_id_key: str, api_private_key: str, demo: bool = True):
        credentials = f"{api_id_key}:{api_private_key}"
        encoded = base64.b64encode(credentials.encode()).decode()

        self._auth_header = f"Basic {encoded}"
        self.host = "https://live.trading212.com"

    def _get(self, endpoint: str, params=None, api_version: str = "v0"):
        return self._process_response(
            requests.get(
                f"{self.host}/api/{api_version}/{endpoint}",
                headers={"Authorization": self._auth_header},
                params=params,
            )
        )

    def _post(self, endpoint: str, data: dict, api_version: str = "v0") -> Dict[str, Any]:
        endpoint = f"{self.host}/api/{api_version}/{endpoint}"
        headers= {
                "Authorization": self._auth_header,
                "Content-Type": "application/json",
        }

        response_data = self._process_response(requests.post(endpoint, headers=headers, json=data))
        req = response_data.get("req")
        res = response_data.get("res")
        err = response_data.get("err")

        return {
                "req": req,
                "res": res,
                "err": err,
                }

    def _get_url(
        self,
        url,
    ):
        return self._process_response(
            requests.get(
                f"{self.host}/{url}",
                headers={"Authorization": self._auth_header},
            )
        )

    def _delete_url(
        self,
        url,
    ):
        return self._process_response(
            requests.delete(
                f"{self.host}/{url}",
                headers={"Authorization": self._auth_header},
            )
        )

    @staticmethod
    def _process_response(resp) -> Dict[str, Any]:

        req_data = {
        "method": resp.request.method,
        "url": resp.request.url,
        "headers": list(resp.request.headers.keys()),
        "body": resp.request.body.decode() if resp.request.body else None,
        }

        try:
            resp.raise_for_status()
        except HTTPError as http_err:
            logging.error(resp.text)
            return {
                "req": req_data,
                "res": resp.json() if resp else None,
                "err": http_err
            }

        return {
                "req": req_data,
                "res": resp.json(),
                "err": None
                } 

    @staticmethod
    def _validate_time_validity(time_validity: str):
        if time_validity not in ["GTC", "DAY"]:
            raise ValueError("time_validity must be one of GTC or DAY")

    @staticmethod
    def _validate_date(date_text: str):
        try:
            # Attempt to parse the date string
            datetime.strptime(date_text, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DDTHH:MM:SSZ")
    
    @staticmethod
    def _validate_dividend_cash_action(dividend_cash_action:str):
        valid_actions = ["REINVEST", "TO_ACCOUNT_CASH"]
        if dividend_cash_action not in valid_actions:
            raise ValueError(f"dividendCashAction must be one of {valid_actions}")

    @staticmethod
    def _validate_icon(icon:str):
        valid_icons = [
            "Home", "PiggyBank", "Iceberg", "Airplane", "RV", "Unicorn", "Whale", "Convertable", "Family",
            "Coins", "Education", "BillsAndCoins", "Bills", "Water","Wind", "Car", "Briefcase", "Medical",
            "Landscape", "Child", "Vault", "Travel", "Cabin", "Apartments", "Burger", "Bus", "Energy", 
            "Factory", "Global", "Leaf", "Materials", "Pill", "Ring", "Shipping", "Storefront", "Tech", "Umbrella"]

        if icon not in valid_icons:
            raise ValueError(f"icon must be one of {valid_icons}")
    
    @staticmethod
    def _validate_instrument_shares(instrument_shares):
        if not isinstance(instrument_shares, dict):
            raise TypeError("instrument_shares must be a dictionary")
        if not instrument_shares:
            raise ValueError("instrument_shares cannot be empty")
        for key, value in instrument_shares.items():
            if not isinstance(key, str):
                raise TypeError("Instrument identifiers must be strings")
            if not isinstance(value, (int, float)):
                raise TypeError("Number of shares must be a number")
            if value <= 0:
                raise ValueError("Number of shares must be greater than zero")

    # --------------
    # Public methods
    # --------------

    def portfolio(self):
        """All open positions"""
        return self._get("equity/portfolio")

    def equity_order_place_market(
        self,
        ticker: str, 
        quantity: float
        ) -> Dict[str, Any]:

        """Place market order"""

        response_data = self._post(f"equity/orders/market", data={"quantity": quantity, "ticker": ticker})
        req = response_data.get("req")
        res = response_data.get("res")
        err = response_data.get("err")

        return {
                "req": req,
                "res": res,
                "err": err
        }

    def pie(self, id:int):
        """Fetch Pie by ID"""
        return self._get(f"/equity/pies/{id}")

    def pies(self):
        """Fetch all Pies"""
        return self._get("equity/pies")

    def positions(self, ticker: Optional[str] = None):
            """
            Fetch open positions. If ticker is provided, filters by ticker.
            """
            params = {"ticker": ticker.strip()} if ticker else None
            return self._get("equity/positions", params=params)

    def get_current_price(self, ticker: str) -> float:
        """
        Returns currentPrice for an instrument you currently hold (open position).
        """
        ticker = ticker.strip()
        positions = self.positions(ticker=ticker)

        if not positions:
            raise ValueError(
                f"No open position for {ticker}. "
                "T212 API provides currentPrice via /equity/positions only for open positions."
            )

        return float(positions[0]["currentPrice"])


if __name__ == "__main__":
    from settings import settings

    t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
    print(t212.get_current_price("CSPX_EQ"))
