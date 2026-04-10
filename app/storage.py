from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


DB_PATH = Path("trading_bot.db")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS executed_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                side TEXT NOT NULL,
                usd_amount REAL NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                submitted_at TEXT NOT NULL,
                pnl_usd REAL DEFAULT 0
            );
            """
        )


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def count_current_hour_trades() -> int:
    now = datetime.now(tz=timezone.utc)
    bucket = now.strftime("%Y-%m-%d %H")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM executed_trades WHERE substr(submitted_at,1,13)=?",
            (bucket,),
        ).fetchone()
    return int(row[0]) if row else 0


def daily_pnl_usd() -> float:
    now = datetime.now(tz=timezone.utc)
    day_prefix = now.strftime("%Y-%m-%d")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(pnl_usd),0) FROM executed_trades WHERE substr(submitted_at,1,10)=?",
            (day_prefix,),
        ).fetchone()
    return float(row[0]) if row else 0.0


def log_trade(
    pair: str,
    side: str,
    usd_amount: float,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    pnl_usd: float = 0.0,
) -> None:
    timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO executed_trades (
                pair, side, usd_amount, entry_price, stop_loss, take_profit, submitted_at, pnl_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (pair, side, usd_amount, entry_price, stop_loss, take_profit, timestamp, pnl_usd),
        )
        conn.commit()
