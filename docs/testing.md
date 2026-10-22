# Test Plan & Verification Results — CloudQuant

## Summary of Automated Test Execution

All tests were executed locally using `pytest` against Python 3.10 and an isolated SQLite test database.

**Test Run Command:**
```bash
.venv/bin/pytest -v test_trading_engine.py
```

**Results:** `10 passed in 24.75s` (100% pass rate).

---

## Detailed Test Cases & Observed Outcomes

| Test ID | Test Function | Purpose / Risk Control Verified | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `test_database_initialization` | Verifies default capital (₹1,00,000), 0 trades, empty holdings on clean DB. | Capital = 100k, trades = 0, holdings = [] | **PASS** |
| **TC-02** | `test_valid_buy_order` | Verifies cash reduction, average buy price calculation, and order ledger insertion. | Cash reduced to 75k, 10 shares held at avg 2500 | **PASS** |
| **TC-03** | `test_insufficient_funds_rejection` | Rejects BUY order when required capital exceeds available cash balance. | Order status REJECTED; cash unchanged | **PASS** |
| **TC-04** | `test_oversell_rejection` | Rejects SELL order when requested quantity exceeds held shares. | Order status REJECTED; holdings unchanged | **PASS** |
| **TC-05** | `test_valid_sell_and_realized_pnl` | Verifies sale proceeds, cost basis reduction, and realized P&L accounting (+₹1,000). | Realized P&L = +₹1,000.00; cash updated | **PASS** |
| **TC-06** | `test_invalid_order_inputs` | Validates non-zero positive quantities, positive prices, and recognized order types. | Invalid inputs rejected with clear error messages | **PASS** |
| **TC-07** | `test_strategy_and_duplicate_prevention` | Prevents duplicate algorithmic orders from triggering on the same price tick. | 1st order executed; 2nd identical order skipped | **PASS** |
| **TC-08** | `test_offline_sample_data_and_indicators` | Verifies deterministic synthetic price series, SMA 10, SMA 30, and RSI 14 calculation. | Dataframe populated; SMA/RSI generated; signal evaluated | **PASS** |
| **TC-09** | `test_fetch_market_data_fallback` | Verifies automatic fallback to sample data when external API is unreachable or forced. | `SAMPLE_DATA_FALLBACK` status returned | **PASS** |
| **TC-10** | `test_database_reset` | Verifies reset confirmation safely purges ledger and restores virtual starting capital. | DB reset to starting capital (₹50k); ledger cleared | **PASS** |
