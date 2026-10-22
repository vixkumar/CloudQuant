import pandas as pd
from typing import Dict, Any

def evaluate_crossover_strategy(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    Evaluates Moving Average Crossover Strategy on the latest market data.
    Rule:
    - BUY: Fast SMA crosses above or is above Slow SMA, and RSI < 70 (not overbought).
    - SELL: Fast SMA crosses below or is below Slow SMA, and RSI > 30 (not oversold).
    - HOLD: Neutral conditions or insufficient spread.
    """
    if df is None or len(df) < 2:
        return {
            "symbol": symbol,
            "signal": "HOLD",
            "fast_ma": 0.0,
            "slow_ma": 0.0,
            "rsi": 50.0,
            "close_price": 0.0,
            "rationale": "Insufficient historical data to compute moving averages."
        }
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    close = float(latest["Close"])
    fast_ma = float(latest.get("SMA_Fast", close))
    slow_ma = float(latest.get("SMA_Slow", close))
    rsi = float(latest.get("RSI", 50.0))
    
    prev_fast = float(prev.get("SMA_Fast", close))
    prev_slow = float(prev.get("SMA_Slow", close))
    
    # Check crossover condition
    bullish_cross = (prev_fast <= prev_slow) and (fast_ma > slow_ma)
    bearish_cross = (prev_fast >= prev_slow) and (fast_ma < slow_ma)
    bullish_trend = fast_ma > slow_ma
    bearish_trend = fast_ma < slow_ma
    
    if bullish_cross or (bullish_trend and rsi < 65):
        signal = "BUY"
        rationale = (
            f"Bullish momentum: Fast SMA ({fast_ma:.2f}) is above Slow SMA ({slow_ma:.2f}) "
            f"with healthy RSI ({rsi:.1f} < 65), indicating upward trend without extreme overbought risk."
        )
    elif bearish_cross or (bearish_trend and rsi > 35):
        signal = "SELL"
        rationale = (
            f"Bearish momentum: Fast SMA ({fast_ma:.2f}) is below Slow SMA ({slow_ma:.2f}) "
            f"with RSI ({rsi:.1f} > 35), indicating downward trend or exhaustion."
        )
    else:
        signal = "HOLD"
        rationale = (
            f"Neutral posture: Fast SMA ({fast_ma:.2f}) vs Slow SMA ({slow_ma:.2f}) "
            f"with RSI ({rsi:.1f}) in middle zone; risk controls advise holding current position."
        )
        
    return {
        "symbol": symbol,
        "signal": signal,
        "fast_ma": round(fast_ma, 2),
        "slow_ma": round(slow_ma, 2),
        "rsi": round(rsi, 2),
        "close_price": round(close, 2),
        "rationale": rationale
    }
