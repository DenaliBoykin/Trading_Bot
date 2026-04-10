from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TradeIdea(BaseModel):
    pair: str
    side: str = Field(pattern="^(buy|sell)$")
    confidence: float = Field(ge=0, le=1)
    rationale: str


class RiskCheckedTrade(BaseModel):
    pair: str
    side: str
    usd_amount: float
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    risk_reward: float
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class TradeResult(BaseModel):
    status: str
    dry_run: bool
    txid: str | None = None
    reason: str | None = None


class HourlyCounter(BaseModel):
    hour_bucket: str
    count: int
