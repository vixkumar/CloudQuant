import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from database import get_connection, DEFAULT_DB_PATH

class TradingEngine:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_portfolio_summary(self, current_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Returns the complete portfolio balance, holdings, and P&L metrics."""
        current_prices = current_prices or {}
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT starting_capital, cash_balance, realized_pnl FROM portfolio_state WHERE id = 1;")
        state = cur.fetchone()
        if not state:
            starting_capital = 100000.0
            cash_balance = 100000.0
            realized_pnl = 0.0
        else:
            starting_capital = float(state["starting_capital"])
            cash_balance = float(state["cash_balance"])
            realized_pnl = float(state["realized_pnl"])

        cur.execute("SELECT symbol, quantity, average_buy_price FROM holdings WHERE quantity > 0;")
        holdings_rows = cur.fetchall()
        
        holdings = []
        invested_value = 0.0
        current_holdings_value = 0.0
        
        for row in holdings_rows:
            sym = row["symbol"]
            qty = int(row["quantity"])
            avg_price = float(row["average_buy_price"])
            curr_price = float(current_prices.get(sym, avg_price))
            
            val = qty * curr_price
            cost = qty * avg_price
            unrealized = val - cost
            unrealized_pct = (unrealized / cost * 100) if cost > 0 else 0.0
            
            invested_value += cost
            current_holdings_value += val
            
            holdings.append({
                "symbol": sym,
                "quantity": qty,
                "average_buy_price": avg_price,
                "current_price": curr_price,
                "market_value": round(val, 2),
                "unrealized_pnl": round(unrealized, 2),
                "unrealized_pnl_pct": round(unrealized_pct, 2)
            })

        cur.execute("SELECT COUNT(*) AS total_trades FROM orders WHERE status = 'FILLED';")
        total_trades = cur.fetchone()["total_trades"]
        conn.close()

        total_portfolio_value = cash_balance + current_holdings_value
        unrealized_pnl = current_holdings_value - invested_value
        total_pnl = (total_portfolio_value - starting_capital)

        return {
            "starting_capital": round(starting_capital, 2),
            "cash_balance": round(cash_balance, 2),
            "holdings_market_value": round(current_holdings_value, 2),
            "total_portfolio_value": round(total_portfolio_value, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_trades": total_trades,
            "holdings": holdings
        }

    def execute_order(
        self,
        symbol: str,
        order_type: str,
        quantity: int,
        price: float,
        order_source: str = "MANUAL"
    ) -> Dict[str, Any]:
        """
        Executes a paper BUY or SELL order under strict risk management.
        """
        order_type = order_type.upper()
        if order_type not in ["BUY", "SELL"]:
            return {"success": False, "reason": f"Invalid order type '{order_type}'."}
        
        if quantity <= 0:
            return {"success": False, "reason": "Quantity must be greater than 0."}
            
        if price <= 0:
            return {"success": False, "reason": "Price must be greater than 0."}

        total_cost = round(quantity * price, 2)
        now_str = datetime.utcnow().isoformat()
        
        conn = get_connection(self.db_path)
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT starting_capital, cash_balance, realized_pnl FROM portfolio_state WHERE id = 1;")
                state = cur.fetchone()
                cash_balance = float(state["cash_balance"])
                realized_pnl = float(state["realized_pnl"])

                cur.execute("SELECT quantity, average_buy_price FROM holdings WHERE symbol = ?;", (symbol,))
                holding = cur.fetchone()
                held_qty = int(holding["quantity"]) if holding else 0
                avg_price = float(holding["average_buy_price"]) if holding else 0.0

                if order_type == "BUY":
                    if total_cost > cash_balance:
                        # Reject due to insufficient cash
                        cur.execute("""
                            INSERT INTO orders (symbol, order_type, order_source, quantity, price, total_value, status, reason, created_at)
                            VALUES (?, 'BUY', ?, ?, ?, ?, 'REJECTED', 'Insufficient cash balance', ?);
                        """, (symbol, order_source, quantity, price, total_cost, now_str))
                        return {
                            "success": False,
                            "reason": f"Insufficient funds: Required ₹{total_cost:,.2f}, Available ₹{cash_balance:,.2f}."
                        }

                    # Execute BUY
                    new_cash = round(cash_balance - total_cost, 2)
                    new_qty = held_qty + quantity
                    new_avg = round(((held_qty * avg_price) + total_cost) / new_qty, 2)

                    cur.execute("""
                        INSERT INTO orders (symbol, order_type, order_source, quantity, price, total_value, status, reason, created_at)
                        VALUES (?, 'BUY', ?, ?, ?, ?, 'FILLED', 'Order executed successfully', ?);
                    """, (symbol, order_source, quantity, price, total_cost, now_str))
                    order_id = cur.lastrowid

                    cur.execute("UPDATE portfolio_state SET cash_balance = ?, updated_at = ? WHERE id = 1;", (new_cash, now_str))
                    cur.execute("""
                        INSERT INTO holdings (symbol, quantity, average_buy_price, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(symbol) DO UPDATE SET
                            quantity = excluded.quantity,
                            average_buy_price = excluded.average_buy_price,
                            updated_at = excluded.updated_at;
                    """, (symbol, new_qty, new_avg, now_str))

                    return {
                        "success": True,
                        "order_id": order_id,
                        "message": f"Successfully BOUGHT {quantity} shares of {symbol} at ₹{price:,.2f} (Total: ₹{total_cost:,.2f})."
                    }

                elif order_type == "SELL":
                    if quantity > held_qty:
                        # Reject overselling
                        cur.execute("""
                            INSERT INTO orders (symbol, order_type, order_source, quantity, price, total_value, status, reason, created_at)
                            VALUES (?, 'SELL', ?, ?, ?, ?, 'REJECTED', 'Insufficient shares held', ?);
                        """, (symbol, order_source, quantity, price, total_cost, now_str))
                        return {
                            "success": False,
                            "reason": f"Oversell rejected: Attempted to sell {quantity} shares, but only hold {held_qty} shares."
                        }

                    # Execute SELL
                    proceeds = total_cost
                    cost_basis = round(quantity * avg_price, 2)
                    pnl_on_sale = round(proceeds - cost_basis, 2)
                    
                    new_cash = round(cash_balance + proceeds, 2)
                    new_realized_pnl = round(realized_pnl + pnl_on_sale, 2)
                    new_qty = held_qty - quantity

                    cur.execute("""
                        INSERT INTO orders (symbol, order_type, order_source, quantity, price, total_value, status, reason, created_at)
                        VALUES (?, 'SELL', ?, ?, ?, ?, 'FILLED', 'Order executed successfully', ?);
                    """, (symbol, order_source, quantity, price, total_cost, now_str))
                    order_id = cur.lastrowid

                    cur.execute("""
                        UPDATE portfolio_state
                        SET cash_balance = ?, realized_pnl = ?, updated_at = ?
                        WHERE id = 1;
                    """, (new_cash, new_realized_pnl, now_str))

                    if new_qty == 0:
                        cur.execute("DELETE FROM holdings WHERE symbol = ?;", (symbol,))
                    else:
                        cur.execute("""
                            UPDATE holdings SET quantity = ?, updated_at = ? WHERE symbol = ?;
                        """, (new_qty, now_str, symbol))

                    return {
                        "success": True,
                        "order_id": order_id,
                        "realized_pnl": pnl_on_sale,
                        "message": f"Successfully SOLD {quantity} shares of {symbol} at ₹{price:,.2f} (Realized P&L: ₹{pnl_on_sale:+,.2f})."
                    }
        finally:
            conn.close()

    def run_strategy_signal(self, strategy_result: Dict[str, Any], default_qty: int = 5) -> Dict[str, Any]:
        """
        Executes a strategy signal with anti-duplicate execution controls.
        """
        symbol = strategy_result["symbol"]
        signal = strategy_result["signal"]
        close_price = strategy_result["close_price"]
        rationale = strategy_result["rationale"]
        
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        
        # Check last strategy run for this symbol to prevent duplicate spam execution
        cur.execute("""
            SELECT signal, close_price, created_at FROM strategy_runs
            WHERE symbol = ?
            ORDER BY id DESC LIMIT 1;
        """, (symbol,))
        last_run = cur.fetchone()
        conn.close()

        is_duplicate = False
        if last_run and last_run["signal"] == signal and abs(float(last_run["close_price"]) - close_price) < 0.01:
            is_duplicate = True

        executed_order_id = None
        execution_note = "Signal logged. No automatic trade executed."
        
        if not is_duplicate:
            if signal == "BUY":
                exec_res = self.execute_order(
                    symbol=symbol,
                    order_type="BUY",
                    quantity=default_qty,
                    price=close_price,
                    order_source="STRATEGY"
                )
                if exec_res["success"]:
                    executed_order_id = exec_res.get("order_id")
                    execution_note = f"Auto-executed BUY {default_qty} shares: {exec_res['message']}"
                else:
                    execution_note = f"Auto-BUY blocked: {exec_res['reason']}"
            elif signal == "SELL":
                # Check how many held
                conn = get_connection(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT quantity FROM holdings WHERE symbol = ?;", (symbol,))
                row = cur.fetchone()
                conn.close()
                held = row["quantity"] if row else 0
                if held > 0:
                    sell_qty = min(default_qty, held)
                    exec_res = self.execute_order(
                        symbol=symbol,
                        order_type="SELL",
                        quantity=sell_qty,
                        price=close_price,
                        order_source="STRATEGY"
                    )
                    if exec_res["success"]:
                        executed_order_id = exec_res.get("order_id")
                        execution_note = f"Auto-executed SELL {sell_qty} shares: {exec_res['message']}"
                    else:
                        execution_note = f"Auto-SELL blocked: {exec_res['reason']}"
                else:
                    execution_note = "SELL signal received, but no shares currently held to liquidate."
        else:
            execution_note = "Duplicate signal skipped: Identical signal and price already processed."

        # Record strategy run in database
        conn = get_connection(self.db_path)
        with conn:
            conn.execute("""
                INSERT INTO strategy_runs (symbol, signal, fast_ma, slow_ma, rsi, close_price, rationale, executed_order_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                symbol,
                signal,
                strategy_result.get("fast_ma"),
                strategy_result.get("slow_ma"),
                strategy_result.get("rsi"),
                close_price,
                rationale,
                executed_order_id,
                datetime.utcnow().isoformat()
            ))
        conn.close()

        return {
            "signal": signal,
            "symbol": symbol,
            "close_price": close_price,
            "executed_order_id": executed_order_id,
            "execution_note": execution_note,
            "is_duplicate": is_duplicate
        }

    def get_recent_orders(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?;", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_recent_strategy_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM strategy_runs ORDER BY id DESC LIMIT ?;", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
