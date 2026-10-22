# CloudQuant: Cloud-Based Algorithmic Trading & Portfolio Management

> **Coursework Project: FT-III Cloud Computing**  
> *Target Cloud Cost: $0.00 / month (AWS 12-Month Free Tier)*

CloudQuant is a minimal-cost, educational paper-trading simulator and algorithmic strategy evaluation platform. It simulates equity trading on Indian stocks (NSE) using rule-based technical indicators (Moving Average Crossover + RSI), enforces risk controls, and persists state in SQLite.

---

## Key Features

1. **Simulated Portfolio Dashboard:** Tracks virtual cash, portfolio market value, realized and unrealized P&L, and trade count.
2. **Deterministic Paper Trading:** Place simulated BUY/SELL orders at historical closing prices. Enforces strict risk checks (no overselling, cash availability).
3. **Algorithmic Strategy & Explainability:** Dual Moving Average Crossover (Fast SMA 10 vs Slow SMA 30) with RSI filter. Provides natural language rationale for every signal.
4. **Anti-Duplicate Risk Guard:** Automatically prevents duplicate executions of identical signals on unchanged market ticks.
5. **Offline Viva Mode:** Built-in synthetic sample data generator ensures uninterrupted viva demonstrations if external market APIs fail.
6. **Zero-Cost AWS Architecture:** Deployed on Amazon EC2 (`t2.micro` / `t3.micro`) using public IPv4 free tier allowances.

---

## Local Setup & Quickstart

```bash
# 1. Clone or navigate to the project directory
cd "/Users/vishalkumar/Desktop/CC Project"

# 2. Activate Python virtual environment
source .venv/bin/activate

# 3. Run automated tests
pytest -v test_trading_engine.py

# 4. Launch Streamlit application
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Project Structure

```
├── app.py                   # Streamlit UI dashboard & charts
├── database.py              # SQLite schema, migrations, and reset logic
├── market_data.py           # yfinance fetcher + offline sample fallback
├── strategy.py              # Moving average crossover strategy + explainability
├── trading_engine.py        # Risk controls, ledger, and paper order execution
├── test_trading_engine.py   # Pytest test suite (10/10 passing tests)
├── requirements.txt         # Pinned Python dependencies
├── deploy/
│   ├── cloudquant.service   # Systemd service unit for EC2 auto-start
│   └── setup_ec2.sh         # EC2 deployment provisioning script
└── docs/                    # Coursework academic deliverables
    ├── architecture.md      # System architecture and Mermaid diagram
    ├── deployment.md        # Step-by-step AWS EC2 deployment guide
    ├── security.md          # Cloud security, IAM, and networking
    ├── testing.md           # Test cases and execution evidence
    ├── cost-analysis.md     # Free Tier verification and $0.00 cost model
    ├── viva-preparation.md  # Viva questions & model answers
    └── demo-checklist.md    # 5-minute live viva demo script
```
