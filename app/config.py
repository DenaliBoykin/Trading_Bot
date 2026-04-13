from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from typing import List

from dotenv import load_dotenv


load_dotenv()


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    kraken_api_key: str
    kraken_api_secret: str
    openai_api_key: str
    trade_pairs: List[str]
    max_trade_usd: float
    max_trades_per_hour: int
    max_daily_loss_pct: float
    daily_profit_target_pct: float
    risk_reward_min: float
    stop_loss_pct: float
    take_profit_pct: float
    dry_run: bool


    @classmethod
    def from_env(cls) -> "Settings":
        pairs = getenv("TRADE_PAIRS", "XXBTZUSD").split(",")
        return cls(
            kraken_api_key=getenv("KRAKEN_API_KEY", ""),
            kraken_api_secret=getenv("KRAKEN_API_SECRET", ""),
            openai_api_key=getenv("OPENAI_API_KEY", ""),
            trade_pairs=[pair.strip() for pair in pairs if pair.strip()],
            max_trade_usd=float(getenv("MAX_TRADE_USD", "200")),
            max_trades_per_hour=int(getenv("MAX_TRADES_PER_HOUR", "5")),
            max_daily_loss_pct=float(getenv("MAX_DAILY_LOSS_PCT", "15")),
            daily_profit_target_pct=float(getenv("DAILY_PROFIT_TARGET_PCT", "30")),
            risk_reward_min=float(getenv("RISK_REWARD_MIN", "3")),
            stop_loss_pct=float(getenv("STOP_LOSS_PCT", "1.0")),
            take_profit_pct=float(getenv("TAKE_PROFIT_PCT", "3.0")),
            dry_run=_bool(getenv("DRY_RUN"), True),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.openai_api_key.strip():
            errors.append("OPENAI_API_KEY is required to analyze market ideas")
        if self.max_trade_usd > 200:
            errors.append("MAX_TRADE_USD must be <= 200")
        if self.max_trades_per_hour > 5:
            errors.append("MAX_TRADES_PER_HOUR must be <= 5")
        if self.max_daily_loss_pct > 15:
            errors.append("MAX_DAILY_LOSS_PCT must be <= 15")
        if self.risk_reward_min < 3:
            errors.append("RISK_REWARD_MIN must be >= 3")
        if self.take_profit_pct / max(self.stop_loss_pct, 0.0001) < self.risk_reward_min:
            errors.append("TP/SL ratio does not satisfy minimum risk-reward requirement")
        return errors
