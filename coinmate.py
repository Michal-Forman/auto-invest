# Future
from __future__ import annotations

# Standard library
from dataclasses import dataclass
import hashlib
import hmac
import time
from typing import Any, Dict, Optional

# Third-party
import requests

# Local
from log import log


class Coinmate:

    BASE_URL = "https://coinmate.io/api"

    def __init__(
        self, client_id: int, public_key: str, private_key: str, timeout_s: int = 20
    ) -> None:
        """Initialize the Coinmate REST client with HMAC-SHA256 authentication credentials."""
        self.client_id = client_id
        self.public_key = public_key
        self.private_key = private_key
        self.timeout_s = timeout_s
        self.session: requests.Session = requests.Session()
        self._last_nonce = 0

    def _nonce(self) -> str:
        """Return a monotonically increasing nonce (millisecond timestamp) required by Coinmate private endpoints."""
        # docs recommend unix timestamps; ms is standard
        n = int(time.time() * 1000)
        if n <= self._last_nonce:
            n = self._last_nonce + 1
        self._last_nonce = n
        return str(n)

    def _signature(self, nonce: str) -> str:
        """Compute the HMAC-SHA256 signature over (nonce + clientId + publicKey) using the private key."""
        # signatureInput = nonce + clientId + publicApiKey
        msg = f"{nonce}{self.client_id}{self.public_key}".encode("utf-8")
        key = self.private_key.encode("utf-8")
        return hmac.new(key, msg, digestmod=hashlib.sha256).hexdigest().upper()

    def _private_payload(
        self, extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build the authenticated form payload (clientId, publicKey, nonce, signature) with optional extra fields."""
        nonce: str = self._nonce()
        payload: Dict[str, Any] = {
            "clientId": self.client_id,
            "publicKey": self.public_key,
            "nonce": nonce,
            "signature": self._signature(nonce),
        }
        if extra:
            payload.update(extra)
        return payload

    def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a GET request to the Coinmate public API and return the parsed JSON response."""
        url = f"{self.BASE_URL}{path}"
        resp: requests.Response = self.session.get(
            url, params=params, timeout=self.timeout_s
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a form-encoded POST to Coinmate. Returns a wrapped dict with req (redacted body), res, and err keys."""

        url = f"{self.BASE_URL}{path}"
        resp: requests.Response = self.session.post(
            url, data=data, timeout=self.timeout_s
        )  # Coinmate uses form params
        resp.raise_for_status()

        req_data = {
            "method": resp.request.method,
            "url": resp.request.url,
            "headers": list(resp.request.headers.keys()),
            "body": "FORM_DATA_REDACTED",
        }

        out: Dict[str, Any] = resp.json()
        error: Any = out.get("error")
        if error:
            log.error(f"Coinmate response error: {error}")
            return {
                "req": req_data,
                "res": out if out else None,
                "err": out.get("errorMessage", "Some error, no further info"),
            }

        return {
            "req": req_data,
            "res": out,
            "err": None,
        }

    # ---------- Public endpoints ----------

    def ticker(self, currency_pair: str = "BTC_CZK") -> Dict[str, Any]:
        """Fetch the current ticker (bid, ask, last price, volume) for a currency pair."""
        return self._get("/ticker", params={"currencyPair": currency_pair})

    def transactions(
        self, currency_pair: str = "BTC_CZK", limit: int = 100
    ) -> Dict[str, Any]:
        """Fetch recent public transactions for a currency pair."""
        return self._get(
            "/transactions", params={"currencyPair": currency_pair, "limit": limit}
        )

    # ---------- Private endpoints ----------

    def buy_instant(
        self,
        total: float,
        currency_pair: str = "BTC_CZK",
        client_order_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute an instant buy for the given total amount in the quote currency. Returns wrapped req/res/err dict."""
        extra: Dict[str, Any] = {
            "total": str(total),
            "currencyPair": currency_pair,
        }
        if client_order_id is not None:
            extra["clientOrderId"] = str(client_order_id)

        return self._post("/buyInstant", data=self._private_payload(extra))

    def user_trades(
        self, currency_pair: str = "BTC_CZK", limit: int = 10
    ) -> Dict[str, Any]:
        """Fetch the authenticated user's recent trade history for a currency pair."""
        payload: Dict[str, Any] = self._private_payload(
            {
                "currencyPair": currency_pair,
                "limit": str(limit),
            }
        )
        return self._post("/tradeHistory", data=payload)

    def balance(self) -> float:
        """Fetch the available CZK balance for the authenticated account."""
        wrapped: Dict[str, Any] = self._post("/balances", data=self._private_payload())
        if wrapped.get("err"):
            raise RuntimeError(f"Could not fetch balance: {wrapped['err']}")
        try:
            return float(wrapped["res"]["data"]["CZK"]["balance"])
        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Unexpected balance response structure: {e}")


if __name__ == "__main__":
    from settings import settings

    coinmate = Coinmate(
        settings.coinmate_client_id,
        settings.coinmate_public_key,
        settings.coinmate_private_key,
    )
    print(coinmate.balance())
