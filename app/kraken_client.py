from __future__ import annotations

import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx


class KrakenClient:
    """Minimal Kraken client with explicit withdrawal protection.

    This client only exposes endpoints needed for market data and order placement.
    """

    API_BASE = "https://api.kraken.com"

    def __init__(self, api_key: str, api_secret_b64: str) -> None:
        self.api_key = api_key
        self.api_secret = base64.b64decode(api_secret_b64) if api_secret_b64 else b""

    def public(self, method: str, payload: dict[str, str] | None = None) -> dict:
        payload = payload or {}
        with httpx.Client(timeout=20) as client:
            response = client.post(f"{self.API_BASE}/0/public/{method}", data=payload)
            response.raise_for_status()
            return response.json()

    def private(self, method: str, payload: dict[str, str] | None = None) -> dict:
        if method.lower().startswith("withdraw"):
            raise PermissionError("Withdrawal endpoints are blocked for security reasons.")

        payload = payload or {}
        nonce = str(int(time.time() * 1000))
        payload["nonce"] = nonce
        body = urlencode(payload)
        path = f"/0/private/{method}"

        sha256 = hashlib.sha256((nonce + body).encode()).digest()
        signature = hmac.new(self.api_secret, path.encode() + sha256, hashlib.sha512).digest()
        sig_b64 = base64.b64encode(signature).decode()

        headers = {
            "API-Key": self.api_key,
            "API-Sign": sig_b64,
        }

        with httpx.Client(timeout=20) as client:
            response = client.post(f"{self.API_BASE}{path}", data=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def ticker_price(self, pair: str) -> float:
        result = self.public("Ticker", {"pair": pair})
        price = list(result["result"].values())[0]["c"][0]
        return float(price)

    def usd_balance(self) -> float:
        result = self.private("Balance")
        # Kraken cash key often ZUSD, fallback to 0.
        return float(result.get("result", {}).get("ZUSD", 0.0))

    def place_market_order(self, pair: str, side: str, volume: float) -> dict:
        return self.private(
            "AddOrder",
            {
                "ordertype": "market",
                "type": side,
                "pair": pair,
                "volume": f"{volume:.8f}",
                "validate": "false",
            },
        )
