from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

class Coinmate:

    BASE_URL = "https://coinmate.io/api"

    def __init__(self, client_id: int, public_key: str, private_key: str, timeout_s: int = 20) -> None:
        self.client_id = client_id
        self.public_key = public_key
        self.private_key = private_key
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self._last_nonce = 0

    def _nonce(self) -> str:
        # docs recommend unix timestamps; ms is standard
        n = int(time.time() * 1000)
        if n <= self._last_nonce:
            n = self._last_nonce + 1
        self._last_nonce = n
        return str(n)

    def _signature(self, nonce: str) -> str:
        # signatureInput = nonce + clientId + publicApiKey
        msg = f"{nonce}{self.client_id}{self.public_key}".encode("utf-8")
        key = self.private_key.encode("utf-8")
        return hmac.new(key, msg, digestmod=hashlib.sha256).hexdigest().upper()

    def _private_payload(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        nonce = self._nonce()
        payload: Dict[str, Any] = {
            "clientId": self.client_id,
            "publicKey": self.public_key,
            "nonce": nonce,
            "signature": self._signature(nonce),
        }
        if extra:
            payload.update(extra)
        return payload

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        resp = self.session.post(url, data=data, timeout=self.timeout_s)  # Coinmate uses form params
        resp.raise_for_status()

        out = resp.json()
        if out.get("error"):
            raise RuntimeError(out.get("errorMessage") or f"Coinmate error: {out}")
        return out

    # ---------- Public endpoints ----------

    def ticker(self, currency_pair: str = "BTC_CZK") -> Dict[str, Any]:
        return self._get("/ticker", params={"currencyPair": currency_pair})

    def transactions(self, currency_pair: str = "BTC_CZK", limit: int = 100) -> Dict[str, Any]:
        # public "Transactions" endpoint; exact params may vary, keep minimal
        return self._get("/transactions", params={"currencyPair": currency_pair, "limit": limit})

    # ---------- Private endpoints ----------

    def balances(self) -> Dict[str, Any]:
        return self._post("/balances", data=self._private_payload())

    def buy_instant(self, total: float, currency_pair: str = "BTC_CZK", client_order_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Buy instant order:
          POST /buyInstant
          required: total, currencyPair
        """
        extra: Dict[str, Any] = {
            "total": str(total),
            "currencyPair": currency_pair,
        }
        if client_order_id is not None:
            extra["clientOrderId"] = str(client_order_id)

        return self._post("/buyInstant", data=self._private_payload(extra))

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from settings import settings

    coinmate = Coinmate(settings.coinmate_client_id, settings.coinmate_public_key, settings.coinmate_private_key)
    print(coinmate.ticker())
    print("test private function")
    print(coinmate.balances())


