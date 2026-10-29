import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

SUPPORTED_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS"
]

SAMPLE_BASE_PRICES = {
    "RELIANCE.NS": 2850.0,
    "TCS.NS": 3950.0,
    "INFY.NS": 1620.0,
    "HDFCBANK.NS": 1540.0
}

def generate_sample_data(symbol: str, days: int = 120) -> pd.DataFrame:
    """Generates deterministic synthetic daily price history for demonstration."""
    base_price = SAMPLE_BASE_PRICES.get(symbol, 1500.0)
    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(days, -1, -1)]
    # Filter for weekdays
    dates = [d for d in dates if d.weekday() < 5]
    
    np.random.seed(abs(hash(symbol)) % 10000)
    returns = np.random.normal(0.0008, 0.015, size=len(dates))
    price_series = base_price * np.cumprod(1 + returns)
    
    df = pd.DataFrame({
        "Date": dates,
        "Open": price_series * (1 + np.random.uniform(-0.005, 0.005, len(dates))),
        "High": price_series * (1 + np.random.uniform(0.005, 0.02, len(dates))),
        "Low": price_series * (1 - np.random.uniform(0.005, 0.02, len(dates))),
        "Close": price_series,
        "Volume": np.random.randint(500000, 3000000, len(dates))
    })
    df.set_index("Date", inplace=True)
    return df

def calculate_indicators(df: pd.DataFrame, fast_period: int = 10, slow_period: int = 30, rsi_period: int = 14) -> pd.DataFrame:
    """Calculates SMA Fast, SMA Slow, and RSI."""
    df = df.copy()
    df["SMA_Fast"] = df["Close"].rolling(window=fast_period).mean()
    df["SMA_Slow"] = df["Close"].rolling(window=slow_period).mean()
    
    # Calculate RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    
    avg_gain = gain.rolling(window=rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period, min_periods=rsi_period).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(50.0)
    return df

def fetch_market_data(symbol: str, period: str = "6mo", force_sample: bool = False) -> tuple[pd.DataFrame, str, str]:
    """
    Fetches price data from yfinance. If network fails or force_sample=True, falls back to sample data.
    Returns: (DataFrame, source_status, last_update_time)
    """
    last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if force_sample:
        df = generate_sample_data(symbol, days=150)
        df = calculate_indicators(df)
        return df, "SAMPLE_DATA_FALLBACK (Offline Demonstration Mode)", last_update

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        if df is None or len(df) < 15:
            # Fallback
            df = generate_sample_data(symbol, days=150)
            df = calculate_indicators(df)
            return df, "SAMPLE_DATA_FALLBACK (yfinance returned insufficient data)", last_update
        
        # Clean index
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        df = calculate_indicators(df)
        return df, "LIVE_YFINANCE (Historical Daily Prices)", last_update
    except Exception as e:
        df = generate_sample_data(symbol, days=150)
        df = calculate_indicators(df)
        return df, f"SAMPLE_DATA_FALLBACK (Network Error: {str(e)[:40]})", last_update
