from __future__ import annotations

import json
from typing import Any

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
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "trade_idea",
                            "schema": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["pair", "side", "confidence", "rationale"],
                                "properties": {
                                    "pair": {"type": "string"},
                                    "side": {"type": "string", "enum": ["buy", "sell"]},
                                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                    "rationale": {"type": "string"},
                                },
                            },
                        }
                    },
                },
            )
            response.raise_for_status()
            body = response.json()

        text = self._extract_response_text(body)

        if not text:
            debug_status = body.get("status", "unknown")
            raise ValueError(
                "OpenAI response did not include parseable text output "
                f"(status={debug_status}, keys={list(body.keys())})"
            )

        data = self._coerce_json_object(text)
        return TradeIdea(**data)

    @staticmethod
    def _extract_response_text(body: dict) -> str | None:
        text = body.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        if isinstance(text, dict):
            nested_text = text.get("text") or text.get("value")
            if isinstance(nested_text, str) and nested_text.strip():
                return nested_text.strip()

        output = body.get("output", [])
        for item in output:
            content = item.get("content", [])
            for part in content:
                part_type = part.get("type")
                if part_type in {"output_text", "text"}:
                    part_text = part.get("text") or part.get("value")
                    if isinstance(part_text, dict):
                        part_text = part_text.get("value") or part_text.get("text")
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
                        part_text = part.get("text") or part.get("value")
                        if isinstance(part_text, dict):
                            part_text = part_text.get("value") or part_text.get("text")
                        if isinstance(part_text, str) and part_text.strip():
                            content_parts.append(part_text.strip())
                if content_parts:
                    return "\n".join(content_parts)

        # Final fallback: walk all nested fields and return the first text blob that
        # looks like a trade-idea JSON object.
        json_like = OpenAIStrategy._find_json_like_text(body)
        if json_like:
            return json_like

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

    @staticmethod
    def _find_json_like_text(value: Any) -> str | None:
        def looks_like_trade_json(candidate: str) -> bool:
            candidate = candidate.strip()
            if not candidate.startswith("{"):
                return False
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                return False
            required = {"pair", "side", "confidence", "rationale"}
            return isinstance(parsed, dict) and required.issubset(parsed.keys())

        if isinstance(value, str):
            stripped = OpenAIStrategy._strip_json_fences(value)
            if looks_like_trade_json(stripped):
                return stripped
            return None

        if isinstance(value, dict):
            for nested in value.values():
                found = OpenAIStrategy._find_json_like_text(nested)
                if found:
                    return found
            return None

        if isinstance(value, list):
            for nested in value:
                found = OpenAIStrategy._find_json_like_text(nested)
                if found:
                    return found
            return None

        return None

    @staticmethod
    def _coerce_json_object(text: str) -> dict[str, Any]:
        cleaned = OpenAIStrategy._strip_json_fences(text)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("OpenAI response text did not contain a valid JSON object")
