import os
import pytest
import tempfile
from database import init_db, reset_db, get_connection
from trading_engine import TradingEngine
from market_data import generate_sample_data, calculate_indicators, fetch_market_data
from strategy import evaluate_crossover_strategy

@pytest.fixture
def temp_engine():
    # Create isolated temp database for each test
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path=path, initial_cash=100000.0)
    engine = TradingEngine(db_path=path)
    yield engine, path
    if os.path.exists(path):
        os.remove(path)

def test_database_initialization(temp_engine):
    engine, path = temp_engine
    summary = engine.get_portfolio_summary()
    assert summary["starting_capital"] == 100000.0
    assert summary["cash_balance"] == 100000.0
    assert summary["total_portfolio_value"] == 100000.0
    assert summary["total_trades"] == 0
    assert len(summary["holdings"]) == 0

def test_valid_buy_order(temp_engine):
    engine, _ = temp_engine
    # Buy 10 shares of RELIANCE.NS at 2500.0
    res = engine.execute_order("RELIANCE.NS", "BUY", 10, 2500.0)
    assert res["success"] is True
    
    summary = engine.get_portfolio_summary()
    assert summary["cash_balance"] == 100000.0 - 25000.0
    assert summary["total_trades"] == 1
    assert len(summary["holdings"]) == 1
    assert summary["holdings"][0]["quantity"] == 10
    assert summary["holdings"][0]["average_buy_price"] == 2500.0

def test_insufficient_funds_rejection(temp_engine):
    engine, _ = temp_engine
    # Attempt to buy more than 100,000 cash
    res = engine.execute_order("TCS.NS", "BUY", 100, 4000.0)
    assert res["success"] is False
    assert "Insufficient funds" in res["reason"]
    
    summary = engine.get_portfolio_summary()
    assert summary["cash_balance"] == 100000.0
    assert summary["total_trades"] == 0

def test_oversell_rejection(temp_engine):
    engine, _ = temp_engine
    # Buy 5 shares
    engine.execute_order("INFY.NS", "BUY", 5, 1500.0)
    
    # Attempt to sell 10 shares
    res = engine.execute_order("INFY.NS", "SELL", 10, 1600.0)
    assert res["success"] is False
    assert "Oversell rejected" in res["reason"]

def test_valid_sell_and_realized_pnl(temp_engine):
    engine, _ = temp_engine
    # Buy 10 shares at 1500 (Cost: 15,000)
    engine.execute_order("INFY.NS", "BUY", 10, 1500.0)
    
    # Sell 5 shares at 1700 (Proceeds: 8,500; Cost basis: 7,500; Realized PnL: +1,000)
    res = engine.execute_order("INFY.NS", "SELL", 5, 1700.0)
    assert res["success"] is True
    assert res["realized_pnl"] == 1000.0
    
    summary = engine.get_portfolio_summary()
    assert summary["realized_pnl"] == 1000.0
    assert summary["holdings"][0]["quantity"] == 5

def test_invalid_order_inputs(temp_engine):
    engine, _ = temp_engine
    assert engine.execute_order("INFY.NS", "BUY", 0, 1500.0)["success"] is False
    assert engine.execute_order("INFY.NS", "BUY", -5, 1500.0)["success"] is False
    assert engine.execute_order("INFY.NS", "BUY", 5, -1500.0)["success"] is False
    assert engine.execute_order("INFY.NS", "UNKNOWN", 5, 1500.0)["success"] is False

def test_strategy_and_duplicate_prevention(temp_engine):
    engine, _ = temp_engine
    strat_result = {
        "symbol": "RELIANCE.NS",
        "signal": "BUY",
        "fast_ma": 2800.0,
        "slow_ma": 2700.0,
        "rsi": 55.0,
        "close_price": 2850.0,
        "rationale": "Bullish test crossover"
    }
    
    # First execution should succeed
    res1 = engine.run_strategy_signal(strat_result, default_qty=5)
    assert res1["is_duplicate"] is False
    assert res1["executed_order_id"] is not None
    
    # Immediate second identical signal should be flagged duplicate
    res2 = engine.run_strategy_signal(strat_result, default_qty=5)
    assert res2["is_duplicate"] is True
    assert res2["executed_order_id"] is None

def test_offline_sample_data_and_indicators():
    df = generate_sample_data("RELIANCE.NS", days=60)
    assert len(df) > 30
    assert "Close" in df.columns
    
    df_ind = calculate_indicators(df, fast_period=5, slow_period=15, rsi_period=7)
    assert "SMA_Fast" in df_ind.columns
    assert "SMA_Slow" in df_ind.columns
    assert "RSI" in df_ind.columns
    
    strat = evaluate_crossover_strategy(df_ind, "RELIANCE.NS")
    assert strat["signal"] in ["BUY", "SELL", "HOLD"]
    assert "rationale" in strat
    assert len(strat["rationale"]) > 10

def test_fetch_market_data_fallback():
    df, status, update_time = fetch_market_data("RELIANCE.NS", force_sample=True)
    assert len(df) > 0
    assert "SAMPLE_DATA_FALLBACK" in status
    assert update_time is not None

def test_database_reset(temp_engine):
    engine, path = temp_engine
    engine.execute_order("TCS.NS", "BUY", 5, 3000.0)
    assert engine.get_portfolio_summary()["total_trades"] == 1
    
    reset_db(db_path=path, initial_cash=50000.0)
    summary = engine.get_portfolio_summary()
    assert summary["starting_capital"] == 50000.0
    assert summary["cash_balance"] == 50000.0
    assert summary["total_trades"] == 0
    assert len(summary["holdings"]) == 0
