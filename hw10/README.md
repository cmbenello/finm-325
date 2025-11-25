# FINM‑325 — Homework 10

This project implements a full intraday trading workflow, from data acquisition and cleaning to strategy design, backtesting, and live paper‑trading via Alpaca. The repository is organized into several independent but connected modules, each corresponding to a required part of the assignment.

## Part 1 — Data Download, Cleaning, and Strategy

### 1. Intraday Data Acquisition
- Equity data fetched using `yfinance`.
- Optional crypto data support (via Binance API).
- Saved as standardized CSV:
  - `Datetime, Open, High, Low, Close, Volume`.

### 2. Data Cleaning
- Missing/duplicate rows removed.
- Timestamp parsing and indexing.
- Added derived features:
  - Returns
  - Moving averages
  - Additional signals as needed.

### 3. Strategy Implementation
A trading strategy is implemented as a Python class exposing:
- Signal generation (`generate_signals`)
- Position sizing
- Optional configurable parameters

The default strategy is a simple moving‑average crossover.

## Part 2 — Backtesting Framework Components

### Gateway
Simulates a live data feed by streaming historical rows incrementally.

### OrderBook
A minimal priority‑queue order book supporting:
- Order insertion
- Cancellation
- Price‑time priority matching

### OrderManager
Handles:
- Capital checks
- Position‑limit checks
- Recording of submitted orders

### MatchingEngine
Simulates fills through configurable randomness:
- Full fills
- Partial fills
- Rejections

## Part 3 — Backtesting Engine

A full end‑to‑end simulation framework:
- Feeds historical market data
- Strategy generates trades
- Matching engine simulates fills
- Tracks:
  - Equity curve
  - P&L
  - Sharpe ratio
  - Drawdowns
  - Win/loss stats

Includes visualization tools:
- Equity curve
- Buy‑and‑hold benchmark
- Random‑strategy Monte Carlo envelope (faint 2σ/3σ bands)

## Part 4 — Alpaca Paper‑Trading Integration

A live trading loop using Alpaca’s paper API:
- Downloads real intraday bars (`IEX` feed)
- Computes live strategy signals
- Places paper orders via Alpaca
- Maintains a rolling OHLCV window
- Runs continuously at a configurable polling interval

> **Note:** API keys must be set manually inside `alpaca_trader.py` or via environment variables. Never commit real keys.

## Running Everything

### Backtest
```
python3 -m src.run_backtest
```

### Live Paper Trader
```
python3 -m src.run_alpaca_paper
```

### Data Download
```
python3 -m src.run_part1
```

## Project Structure
```
src/
  download_market_data.py
  clean_data.py
  strategy.py
  gateway.py
  order_book.py
  order_manager.py
  matching_engine.py
  backtester.py
  performance.py
  alpaca_data.py
  alpaca_trader.py
  run_backtest.py
  run_part1.py
  run_part2_demo.py
  run_alpaca_paper.py
```

## Notes
- All trading is **paper‑only**.
- Alpaca IEX feed is used due to SIP restrictions.
- Code is organized so each module can be extended independently.

