from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.models import RiskCheckedTrade, TradeIdea
from app.storage import count_current_hour_trades, daily_pnl_usd


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    checked_trade: RiskCheckedTrade | None = None


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def can_trade_today(self, starting_equity_usd: float) -> tuple[bool, str]:
        pnl = daily_pnl_usd()
        loss_limit = -(starting_equity_usd * (self.settings.max_daily_loss_pct / 100))
        profit_goal = starting_equity_usd * (self.settings.daily_profit_target_pct / 100)

        if pnl <= loss_limit:
            return False, "Daily loss limit reached. Trading disabled until next UTC day."
        if pnl >= profit_goal:
            return False, "Daily profit target reached. Trading disabled until next UTC day."
        return True, "Daily limits OK"

    def evaluate(
        self,
        idea: TradeIdea,
        entry_price: float,
        available_usd: float,
    ) -> RiskDecision:
        if idea.confidence < 0.56:
            return RiskDecision(False, "Model confidence too low")

        hourly_count = count_current_hour_trades()
        if hourly_count >= self.settings.max_trades_per_hour:
            return RiskDecision(False, "Hourly trade limit reached")

        usd_amount = min(self.settings.max_trade_usd, available_usd)
        if usd_amount < 10:
            return RiskDecision(False, "Insufficient USD balance")

        sl_mult = self.settings.stop_loss_pct / 100
        tp_mult = self.settings.take_profit_pct / 100

        if idea.side == "buy":
            stop_loss = entry_price * (1 - sl_mult)
            take_profit = entry_price * (1 + tp_mult)
        else:
            stop_loss = entry_price * (1 + sl_mult)
            take_profit = entry_price * (1 - tp_mult)

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr = reward / max(risk, 1e-8)

        if rr < self.settings.risk_reward_min:
            return RiskDecision(False, f"Risk/reward ratio too low: {rr:.2f}")

        checked = RiskCheckedTrade(
            pair=idea.pair,
            side=idea.side,
            usd_amount=usd_amount,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            risk_reward=rr,
        )
        return RiskDecision(True, "Approved by risk checks", checked)
