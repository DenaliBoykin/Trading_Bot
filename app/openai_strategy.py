from __future__ import annotations

import json

import httpx

from app.models import TradeIdea


class OpenAIStrategy:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def generate_trade_idea(self, pair: str, latest_price: float) -> TradeIdea:
        prompt = (
            "You are a conservative crypto trading assistant. Return JSON only with keys: "
            "pair, side (buy/sell), confidence (0..1), rationale. "
            "Prefer no-trade if uncertain by setting confidence <= 0.55 and rationale explaining why. "
            f"Pair: {pair}, latest price: {latest_price}."
        )

        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-5-mini",
                    "input": prompt,
                    "max_output_tokens": 250,
                },
            )
            response.raise_for_status()
            body = response.json()

        text = body.get("output_text")
        if not text:
            output = body.get("output", [])
            if output:
                content = output[0].get("content", [])
                if content:
                    text = content[0].get("text")

        if not text:
            raise ValueError("OpenAI response did not include parseable text output")

        data = json.loads(text)
        return TradeIdea(**data)
