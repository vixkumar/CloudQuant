import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "cloudquant.db")
DEFAULT_INITIAL_CASH = 100000.0  # INR 1,00,000 virtual capital

def get_connection(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path=DEFAULT_DB_PATH, initial_cash=DEFAULT_INITIAL_CASH):
    """Initializes the database schema safely without overwriting existing data."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                starting_capital REAL NOT NULL,
                cash_balance REAL NOT NULL,
                realized_pnl REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                symbol TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL,
                average_buy_price REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL, -- BUY or SELL
                order_source TEXT NOT NULL, -- MANUAL or STRATEGY
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                status TEXT NOT NULL, -- FILLED or REJECTED
                reason TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL, -- BUY, SELL, HOLD
                fast_ma REAL,
                slow_ma REAL,
                rsi REAL,
                close_price REAL NOT NULL,
                rationale TEXT NOT NULL,
                executed_order_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (executed_order_id) REFERENCES orders (id)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy_symbol ON strategy_runs(symbol);")

        cur = conn.cursor()
        cur.execute("SELECT id FROM portfolio_state WHERE id = 1;")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO portfolio_state (id, starting_capital, cash_balance, realized_pnl, updated_at)
                VALUES (1, ?, ?, 0.0, ?);
            """, (initial_cash, initial_cash, datetime.utcnow().isoformat()))
    conn.close()

def reset_db(db_path=DEFAULT_DB_PATH, initial_cash=DEFAULT_INITIAL_CASH):
    """Resets all holdings, orders, strategy runs, and re-initializes capital."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("DELETE FROM strategy_runs;")
        conn.execute("DELETE FROM orders;")
        conn.execute("DELETE FROM holdings;")
        conn.execute("DELETE FROM portfolio_state;")
        conn.execute("""
            INSERT INTO portfolio_state (id, starting_capital, cash_balance, realized_pnl, updated_at)
            VALUES (1, ?, ?, 0.0, ?);
        """, (initial_cash, initial_cash, datetime.utcnow().isoformat()))
    conn.close()
