from __future__ import annotations

import streamlit as st

from app.config import Settings
from app.storage import daily_pnl_usd, init_db
from app.trade_engine import TradeEngine


st.set_page_config(page_title="Kraken + OpenAI Trading Bot", layout="wide")
st.title("🔐 Kraken + OpenAI Trading Bot (Safety-First)")

init_db()
settings = Settings.from_env()
errors = settings.validate()

if errors:
    st.error("Configuration errors:\n- " + "\n- ".join(errors))
    st.stop()

try:
    engine = TradeEngine(settings)
except ValueError as exc:
    st.error(str(exc))
    st.info(
        "Tip: open `.env` and ensure `KRAKEN_API_SECRET` is copied exactly from Kraken. "
        "Keep DRY_RUN=true while testing."
    )
    st.stop()

st.sidebar.header("Runtime safety")
st.sidebar.write(f"Dry run mode: **{settings.dry_run}**")
st.sidebar.write(f"Max trade amount: **${settings.max_trade_usd:.2f}**")
st.sidebar.write(f"Max trades/hour: **{settings.max_trades_per_hour}**")
st.sidebar.write(f"Daily max loss: **{settings.max_daily_loss_pct}%**")
st.sidebar.write(f"Daily profit target: **{settings.daily_profit_target_pct}%**")

pnl = daily_pnl_usd()
st.metric("Today's realized PnL (USD)", f"${pnl:,.2f}")

pair = st.selectbox("Trading pair", settings.trade_pairs)

if st.button("Analyze market"):
    with st.spinner("Getting AI trade idea + risk checks..."):
        idea, decision = engine.propose_trade(pair)

    st.subheader("AI Trade Idea")
    st.write(idea.model_dump())

    if not decision.allowed:
        st.warning(f"Trade blocked: {decision.reason}")
    else:
        checked = decision.checked_trade
        st.success("Trade passed all risk checks.")
        st.write(checked.model_dump())

        st.markdown("### Human approval required")
        human_approval = st.checkbox("I approve this trade")
        if st.button("Execute approved trade"):
            if not human_approval:
                st.error("Approval checkbox is required before trade execution.")
            else:
                result = engine.execute_approved_trade(
                    pair=checked.pair,
                    side=checked.side,
                    entry_price=checked.entry_price,
                    usd_amount=checked.usd_amount,
                    stop_loss=checked.stop_loss_price,
                    take_profit=checked.take_profit_price,
                )
                st.write(result.model_dump())
