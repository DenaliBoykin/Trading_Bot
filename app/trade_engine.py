from __future__ import annotations

from app.config import Settings
from app.kraken_client import KrakenClient
from app.models import TradeResult
from app.openai_strategy import OpenAIStrategy
from app.risk_manager import RiskManager
from app.storage import log_trade


class TradeEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.kraken = KrakenClient(settings.kraken_api_key, settings.kraken_api_secret)
        self.strategy = OpenAIStrategy(settings.openai_api_key)
        self.risk = RiskManager(settings)

    def propose_trade(self, pair: str):
        entry_price = self.kraken.ticker_price(pair)
        idea = self.strategy.generate_trade_idea(pair, entry_price)
        available = self.kraken.usd_balance() if not self.settings.dry_run else self.settings.max_trade_usd
        decision = self.risk.evaluate(idea, entry_price, available)
        return idea, decision

    def execute_approved_trade(self, pair: str, side: str, entry_price: float, usd_amount: float, stop_loss: float, take_profit: float) -> TradeResult:
        volume = usd_amount / entry_price

        if self.settings.dry_run:
            log_trade(pair, side, usd_amount, entry_price, stop_loss, take_profit, 0.0)
            return TradeResult(status="simulated", dry_run=True, reason="DRY_RUN mode active")

        res = self.kraken.place_market_order(pair, side, volume)
        txid = None
        if res.get("error"):
            return TradeResult(status="rejected", dry_run=False, reason="; ".join(res["error"]))

        txids = res.get("result", {}).get("txid", [])
        txid = txids[0] if txids else None

        log_trade(pair, side, usd_amount, entry_price, stop_loss, take_profit, 0.0)
        return TradeResult(status="submitted", dry_run=False, txid=txid)
