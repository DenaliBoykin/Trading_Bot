# Kraken + OpenAI Trading Bot (Safety-First)

A Python app that proposes and (only with human approval) executes Kraken spot trades using OpenAI-assisted trade ideas.

## Important note on Python version
You requested **Python 9.14.4**, but Python major version 9 does not exist.
This project is configured for **Python 3.10+** in `pyproject.toml`.

## What this bot enforces
- Blocks withdrawal endpoints in code (`Withdraw*` is denied).
- Max trade size: **$200**.
- Max **5 trades/hour**.
- Daily max loss: **15%** (stops trading for day).
- Daily profit target: **30%** (stops trading for day).
- Stop loss + take profit calculation with minimum risk/reward **1:3**.
- Human approval required before each trade submission.
- Defaults to `DRY_RUN=true` for safety.

## Architecture
- `app/kraken_client.py` — Signed Kraken API client, withdrawal protection.
- `app/openai_strategy.py` — OpenAI call for trade ideas.
- `app/risk_manager.py` — Hard risk checks and limits.
- `app/trade_engine.py` — Proposal + execution flow.
- `app/ui_streamlit.py` — Clean Streamlit dashboard.
- `app/storage.py` — SQLite trade journal for hourly/day guardrails.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Fill `.env`:
- `KRAKEN_API_KEY`
- `KRAKEN_API_SECRET`
- `OPENAI_API_KEY`

## Kraken API key permissions (critical)
Create a Kraken API key that allows only:
- Query funds/balance
- Create and cancel orders

Do **not** enable withdrawal permissions on the key.

## Run app
```bash
streamlit run app/ui_streamlit.py
```

## Security recommendations
1. Keep `DRY_RUN=true` until you have validated behavior.
2. Use IP allowlisting for Kraken API keys.
3. Rotate API keys periodically.
4. Do not commit `.env` to git.
5. Start with a low-risk sub-account.
6. Monitor logs and trade journal (`trading_bot.db`) daily.

## Downloadable
This repository is ready to download as a ZIP and run locally.
