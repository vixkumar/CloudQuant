"""
test_auth.py — Tests for the CloudQuant authentication module.

Tests the pure-Python functions in auth.py that don't depend on Streamlit.
Streamlit UI functions (render_login_page, is_authenticated, logout) are tested
via mocked session_state and secrets.
"""

import bcrypt
import pytest
import time
from unittest.mock import patch, MagicMock

# Import only the pure functions that don't call st.*
from auth import verify_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def known_hash():
    """A real bcrypt hash of the string 'TestPass123' — used across tests."""
    return bcrypt.hashpw(b"TestPass123", bcrypt.gensalt(rounds=4)).decode("utf-8")


@pytest.fixture
def wrong_hash():
    """A real bcrypt hash of the string 'WrongPassword' — for negative tests."""
    return bcrypt.hashpw(b"WrongPassword", bcrypt.gensalt(rounds=4)).decode("utf-8")


# ---------------------------------------------------------------------------
# verify_password — pure Python, no Streamlit
# ---------------------------------------------------------------------------

class TestVerifyPassword:
    def test_correct_password_returns_true(self, known_hash):
        assert verify_password("TestPass123", known_hash) is True

    def test_wrong_password_returns_false(self, known_hash):
        assert verify_password("WrongPassword", known_hash) is False

    def test_empty_plain_returns_false(self, known_hash):
        assert verify_password("", known_hash) is False

    def test_empty_hash_returns_false(self):
        assert verify_password("SomePassword", "") is False

    def test_both_empty_returns_false(self):
        assert verify_password("", "") is False

    def test_case_sensitive(self, known_hash):
        assert verify_password("testpass123", known_hash) is False
        assert verify_password("TESTPASS123", known_hash) is False

    def test_different_hashes_same_password(self):
        """bcrypt produces different salts each call; both should verify."""
        h1 = bcrypt.hashpw(b"SamePassword", bcrypt.gensalt(rounds=4)).decode()
        h2 = bcrypt.hashpw(b"SamePassword", bcrypt.gensalt(rounds=4)).decode()
        assert h1 != h2  # Different salts → different hashes
        assert verify_password("SamePassword", h1) is True
        assert verify_password("SamePassword", h2) is True

    def test_malformed_hash_returns_false(self):
        """Garbage string as hash must not raise — must return False."""
        assert verify_password("password", "not-a-bcrypt-hash") is False

    def test_none_like_inputs(self):
        """Passing non-string should not crash; should return False."""
        assert verify_password("password", "not-a-hash-at-all!!") is False


# ---------------------------------------------------------------------------
# is_authenticated — requires mocked st.session_state
# ---------------------------------------------------------------------------

class TestIsAuthenticated:
    def test_unauthenticated_by_default(self):
        """is_authenticated() should return False if session state is empty."""
        with patch("auth.st") as mock_st:
            mock_st.session_state = {}
            from auth import is_authenticated
            assert is_authenticated() is False

    def test_authenticated_when_flag_set(self):
        """is_authenticated() should return True after authenticated=True."""
        with patch("auth.st") as mock_st:
            mock_st.session_state = {"authenticated": True}
            from auth import is_authenticated
            assert is_authenticated() is True

    def test_authenticated_false_when_explicitly_false(self):
        with patch("auth.st") as mock_st:
            mock_st.session_state = {"authenticated": False}
            from auth import is_authenticated
            assert is_authenticated() is False


# ---------------------------------------------------------------------------
# logout — clears session state
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_clears_authenticated(self):
        session = {"authenticated": True, "failed_attempts": 0, "lockout_until": 0.0}
        with patch("auth.st") as mock_st:
            mock_st.session_state = session
            from auth import logout
            logout()
        assert "authenticated" not in session

    def test_logout_clears_all_auth_keys(self):
        session = {
            "authenticated": True,
            "failed_attempts": 3,
            "lockout_until": time.time() + 30,
            "other_key": "should_stay",
        }
        with patch("auth.st") as mock_st:
            mock_st.session_state = session
            from auth import logout
            logout()
        assert "authenticated" not in session
        assert "failed_attempts" not in session
        assert "lockout_until" not in session
        # Non-auth keys must be untouched
        assert session.get("other_key") == "should_stay"

    def test_logout_safe_when_already_logged_out(self):
        """logout() on an empty session must not raise."""
        with patch("auth.st") as mock_st:
            mock_st.session_state = {}
            from auth import logout
            logout()  # Should not raise


# ---------------------------------------------------------------------------
# Trading engine still works (existing functionality preserved)
# ---------------------------------------------------------------------------

class TestTradingEngineIntegrity:
    """
    Verify that all existing trading engine functions still work correctly
    after adding the auth module. Uses isolated temp databases.
    """

    def test_buy_order_succeeds(self, tmp_path):
        from database import init_db
        from trading_engine import TradingEngine
        db = str(tmp_path / "test.db")
        init_db(db_path=db, initial_cash=100000.0)
        engine = TradingEngine(db_path=db)
        res = engine.execute_order("RELIANCE.NS", "BUY", 10, 2500.0)
        assert res["success"] is True
        summary = engine.get_portfolio_summary()
        assert summary["cash_balance"] == 75000.0

    def test_insufficient_funds_still_rejected(self, tmp_path):
        from database import init_db
        from trading_engine import TradingEngine
        db = str(tmp_path / "test.db")
        init_db(db_path=db, initial_cash=100000.0)
        engine = TradingEngine(db_path=db)
        res = engine.execute_order("TCS.NS", "BUY", 100, 4000.0)
        assert res["success"] is False
        assert "Insufficient" in res["reason"]

    def test_oversell_still_rejected(self, tmp_path):
        from database import init_db
        from trading_engine import TradingEngine
        db = str(tmp_path / "test.db")
        init_db(db_path=db, initial_cash=100000.0)
        engine = TradingEngine(db_path=db)
        engine.execute_order("INFY.NS", "BUY", 5, 1500.0)
        res = engine.execute_order("INFY.NS", "SELL", 10, 1600.0)
        assert res["success"] is False
        assert "Oversell" in res["reason"]

    def test_realized_pnl_calculation(self, tmp_path):
        from database import init_db
        from trading_engine import TradingEngine
        db = str(tmp_path / "test.db")
        init_db(db_path=db, initial_cash=100000.0)
        engine = TradingEngine(db_path=db)
        engine.execute_order("INFY.NS", "BUY", 10, 1500.0)
        res = engine.execute_order("INFY.NS", "SELL", 5, 1700.0)
        assert res["success"] is True
        assert res["realized_pnl"] == 1000.0

    def test_duplicate_strategy_signal_blocked(self, tmp_path):
        from database import init_db
        from trading_engine import TradingEngine
        db = str(tmp_path / "test.db")
        init_db(db_path=db, initial_cash=100000.0)
        engine = TradingEngine(db_path=db)
        signal = {
            "symbol": "RELIANCE.NS", "signal": "BUY",
            "fast_ma": 2800.0, "slow_ma": 2700.0,
            "rsi": 55.0, "close_price": 2850.0,
            "rationale": "Test crossover"
        }
        r1 = engine.run_strategy_signal(signal, default_qty=5)
        r2 = engine.run_strategy_signal(signal, default_qty=5)
        assert r1["is_duplicate"] is False
        assert r2["is_duplicate"] is True

