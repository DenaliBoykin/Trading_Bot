from __future__ import annotations

import json

import httpx

from app.models import TradeIdea


class OpenAIStrategy:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip()
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is empty. Set it in your .env before running analysis.")

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

        text = self._extract_response_text(body)

        if not text:
            raise ValueError("OpenAI response did not include parseable text output")

        data = json.loads(self._strip_json_fences(text))
        return TradeIdea(**data)

    @staticmethod
    def _extract_response_text(body: dict) -> str | None:
        text = body.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()

        output = body.get("output", [])
        for item in output:
            content = item.get("content", [])
            for part in content:
                part_type = part.get("type")
                if part_type in {"output_text", "text"}:
                    part_text = part.get("text")
                    if isinstance(part_text, str) and part_text.strip():
                        return part_text.strip()

        choices = body.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                content_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        part_text = part.get("text")
                        if isinstance(part_text, str) and part_text.strip():
                            content_parts.append(part_text.strip())
                if content_parts:
                    return "\n".join(content_parts)

        return None

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return stripped
