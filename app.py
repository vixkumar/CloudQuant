import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from database import init_db, reset_db, DEFAULT_DB_PATH
from market_data import SUPPORTED_SYMBOLS, fetch_market_data
from strategy import evaluate_crossover_strategy
from trading_engine import TradingEngine

# Streamlit Page Config
st.set_page_config(
    page_title="CloudQuant | Minimal-Cost Paper Trading App",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database safely on start
init_db()
engine = TradingEngine()

# Custom CSS for clean, high-contrast, professional styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #e9ecef;
    }
    .disclaimer-banner {
        background-color: #fff3cd;
        color: #856404;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.88rem;
        margin-bottom: 12px;
        border: 1px solid #ffeeba;
    }
    .status-badge {
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.title("📈 CloudQuant")
    st.caption("FT-III Cloud Computing Demo Project")
    
    st.markdown("---")
    st.subheader("Market Configuration")
    selected_symbol = st.selectbox("Select Equity", SUPPORTED_SYMBOLS, index=0)
    data_period = st.selectbox("Historical Lookback", ["1mo", "3mo", "6mo", "1y"], index=2)
    force_offline_sample = st.checkbox("Force Sample-Data Mode (Offline Viva Safe)", value=False,
                                       help="Guarantees immediate zero-latency chart rendering without relying on external API.")

    st.markdown("---")
    st.subheader("Simulated Account Reset")
    with st.expander("Reset Simulation Database"):
        st.warning("This resets all virtual cash, holdings, and order history.")
        reset_capital = st.number_input("Reset Capital (₹)", min_value=10000.0, max_value=10000000.0, value=100000.0, step=10000.0)
        confirm_reset = st.checkbox("I confirm database reset")
        if st.button("Reset Account", type="secondary", disabled=not confirm_reset):
            reset_db(initial_cash=reset_capital)
            st.success("Database reset successfully!")
            st.rerun()

    st.markdown("---")
    st.caption("CloudQuant Architecture: AWS EC2 (t2/t3.micro Free Tier) + Python 3 + Streamlit + SQLite")

# ----------------- TOP BANNER -----------------
st.markdown("""
<div class="disclaimer-banner">
    ⚠️ <strong>SIMULATION ONLY:</strong> All balances, quotes, orders, and P&L metrics are virtual paper-trading values. 
    This application executes no real financial transactions and connects to no brokerage accounts.
</div>
""", unsafe_allow_html=True)

# ----------------- FETCH MARKET DATA -----------------
with st.spinner("Fetching market data..."):
    df_market, data_source_label, last_updated_time = fetch_market_data(
        selected_symbol, period=data_period, force_sample=force_offline_sample
    )

latest_close = float(df_market["Close"].iloc[-1]) if len(df_market) > 0 else 0.0
current_prices = {selected_symbol: latest_close}
portfolio = engine.get_portfolio_summary(current_prices=current_prices)

# ----------------- SECTION 1: DASHBOARD METRICS -----------------
st.header("1. Virtual Portfolio Dashboard")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Available Cash", f"₹{portfolio['cash_balance']:,.2f}")
col2.metric("Portfolio Value", f"₹{portfolio['total_portfolio_value']:,.2f}")
col3.metric("Unrealized P&L", f"₹{portfolio['unrealized_pnl']:+,.2f}")
col4.metric("Realized P&L", f"₹{portfolio['realized_pnl']:+,.2f}")
col5.metric("Filled Trades", f"{portfolio['total_trades']}")

# ----------------- SECTION 2: MARKET DATA & STRATEGY -----------------
st.header(f"2. Market Data & Strategy: {selected_symbol}")
st.caption(f"Data Source: **{data_source_label}** | Last Update: `{last_updated_time}` | Latest Close: **₹{latest_close:,.2f}**")

tab_chart, tab_strategy, tab_trade = st.tabs(["📊 Price & Technicals", "🤖 Strategy Signals & Execution", "📝 Manual Paper Trading"])

# --- TAB 1: CHART ---
with tab_chart:
    if len(df_market) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market['Close'], mode='lines', name='Close Price', line=dict(color='#1f77b4', width=2)))
        if 'SMA_Fast' in df_market.columns:
            fig.add_trace(go.Scatter(x=df_market.index, y=df_market['SMA_Fast'], mode='lines', name='SMA 10 (Fast)', line=dict(color='#ff7f0e', dash='dash')))
        if 'SMA_Slow' in df_market.columns:
            fig.add_trace(go.Scatter(x=df_market.index, y=df_market['SMA_Slow'], mode='lines', name='SMA 30 (Slow)', line=dict(color='#2ca02c', dash='dot')))
        
        fig.update_layout(
            title=f"{selected_symbol} Daily Price & Moving Average Crossover",
            xaxis_title="Date",
            yaxis_title="Price (₹ INR)",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Mini RSI Chart
        if 'RSI' in df_market.columns:
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df_market.index, y=df_market['RSI'], mode='lines', name='RSI (14)', line=dict(color='#9467bd', width=1.5)))
            rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
            rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
            rsi_fig.update_layout(
                title=f"{selected_symbol} 14-Day Relative Strength Index (RSI)",
                yaxis_title="RSI (0-100)",
                height=220,
                margin=dict(l=20, r=20, t=35, b=20),
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(rsi_fig, use_container_width=True)
    else:
        st.info("No market data available.")

# --- TAB 2: STRATEGY SIGNALS ---
with tab_strategy:
    strat_eval = evaluate_crossover_strategy(df_market, selected_symbol)
    
    st.subheader("Rule-Based Algorithmic Signal")
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    
    sig_color = "green" if strat_eval["signal"] == "BUY" else ("red" if strat_eval["signal"] == "SELL" else "orange")
    s_col1.markdown(f"**Current Signal:** :{sig_color}[**{strat_eval['signal']}**]")
    s_col2.metric("Fast SMA (10)", f"₹{strat_eval['fast_ma']}")
    s_col3.metric("Slow SMA (30)", f"₹{strat_eval['slow_ma']}")
    s_col4.metric("RSI (14)", f"{strat_eval['rsi']}")
    
    st.info(f"**Explainability & Rationale:** {strat_eval['rationale']}")

    st.markdown("---")
    st.subheader("Execute Strategy Signal")
    st.caption("Applies automated risk controls: checks cash reserves, prevents overselling, and rejects duplicate executions.")
    
    run_qty = st.number_input("Strategy Order Quantity", min_value=1, max_value=500, value=5, step=1)
    if st.button(f"⚡ Run Strategy on {selected_symbol}", type="primary"):
        run_res = engine.run_strategy_signal(strat_eval, default_qty=run_qty)
        if run_res["is_duplicate"]:
            st.warning(f"⚠️ {run_res['execution_note']}")
        elif run_res["executed_order_id"]:
            st.success(f"✅ {run_res['execution_note']}")
            st.rerun()
        else:
            st.info(f"ℹ️ {run_res['execution_note']}")

# --- TAB 3: MANUAL PAPER TRADING ---
with tab_trade:
    st.subheader(f"Place Manual Simulated Order for {selected_symbol}")
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        order_action = st.radio("Order Side", ["BUY", "SELL"], horizontal=True)
    with m_col2:
        trade_qty = st.number_input("Quantity", min_value=1, max_value=1000, value=10, step=1)
    with m_col3:
        est_total = trade_qty * latest_close
        st.metric("Estimated Total (₹)", f"₹{est_total:,.2f}")
        st.caption(f"Deterministic execution price: Last Close (₹{latest_close:,.2f})")

    if st.button(f"Submit Paper {order_action} Order", type="primary"):
        res = engine.execute_order(
            symbol=selected_symbol,
            order_type=order_action,
            quantity=trade_qty,
            price=latest_close,
            order_source="MANUAL"
        )
        if res["success"]:
            st.success(f"✅ {res['message']}")
            st.rerun()
        else:
            st.error(f"❌ {res['reason']}")

# ----------------- SECTION 3: HOLDINGS & ORDER HISTORY -----------------
st.header("3. Holdings & Audit Ledger")

h_col, o_col = st.columns([1, 1])

with h_col:
    st.subheader("Current Simulated Holdings")
    if portfolio["holdings"]:
        df_holdings = pd.DataFrame(portfolio["holdings"])
        st.dataframe(
            df_holdings[["symbol", "quantity", "average_buy_price", "current_price", "market_value", "unrealized_pnl"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("No open positions. Use the trade forms above to purchase simulated equities.")

with o_col:
    st.subheader("Recent Order History")
    orders = engine.get_recent_orders(limit=10)
    if orders:
        df_orders = pd.DataFrame(orders)
        st.dataframe(
            df_orders[["id", "symbol", "order_type", "order_source", "quantity", "price", "status", "created_at"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("No trade orders executed yet.")

# ----------------- FOOTER -----------------
st.markdown("---")
f_col1, f_col2 = st.columns([3, 1])
f_col1.caption("CloudQuant Academic Project | Coursework: FT-III Cloud Computing | Cloud Architecture: AWS Free Tier | Designed for $0.00 Running Cost")
f_col2.caption("Status: **Verified Local & Cloud Ready**")
