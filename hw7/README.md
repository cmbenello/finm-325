# FINM 325 — Homework 7: Market Data Rolling Analytics

## Overview
This project benchmarks **Pandas** and **Polars** for financial time-series analytics, focusing on rolling computations, ingestion efficiency, and parallel processing performance.

We work with high-frequency market data (e.g., `AAPL`) containing timestamped prices and symbols. The system computes moving averages, volatility, and rolling Sharpe ratios under different compute backends.

---

## Repository Structure

```
.
├── data/                     # Input CSV market data
├── reports/                  # Output charts and performance summaries
├── data_loader.py            # Data ingestion (Pandas & Polars)
├── metrics.py                # Rolling analytics (MA, volatility, Sharpe)
├── parallel.py               # Threaded & multiprocess rolling computation
├── reporting.py              # Report generation, plotting, and aggregation
├── portfolio.py              # Portfolio aggregation helpers
├── main.py                   # CLI entry point
├── tests/                    # Unit tests for correctness and consistency
└── performance_report.md     # Benchmark results and analysis
```

---

## Installation

```bash
# Clone repository
git clone <repo-url>
cd hw7

# Recommended: create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Dependencies include `pandas`, `polars`, `numpy`, `matplotlib`, and `psutil`.  
For memory profiling, the optional dependency `memory_profiler` can be installed.

---

## Usage

You can run the full benchmark workflow with:

```bash
python3 main.py --data data/market_data-1.csv --symbol AAPL
```

This will:
1. Load data in both Pandas and Polars
2. Compute rolling metrics (MA20, volatility, Sharpe)
3. Run threaded and multiprocess parallel versions
4. Save all plots and summaries in the `reports/` folder

---

## Profiling and Extended Usage

Users can enable memory profiling via the new `--profile` flag, which reports peak memory usage using `memory_profiler`.

Example usage:

```bash
python3 main.py --data data/market_data-1.csv --symbol AAPL --profile
```

This will print both the performance summary and peak memory usage in MiB.

---

## Output

After running, you’ll see:
- **AAPL_price_ma20.png** — price and 20-period moving average
- **AAPL_sharpe20.png** — rolling Sharpe ratio
- **times_basic.png** — Pandas vs Polars ingestion/rolling time comparison
- **times_parallel.png** — Threaded vs Multiprocess performance
- **performance_summary.csv** — timing and memory metrics
- **performance_report.md** — written analysis and plots

---

## Key Findings

- **Polars** is ~4–7× faster than Pandas for ingestion and rolling metrics.
- **Threaded execution** is consistently faster than multiprocess due to lower serialization overhead.
- **Memory deltas** show Polars is generally more memory-efficient but occasionally spikes during large frame materialization.
- Pandas multiprocess shows a negative RSS delta, likely reflecting released memory post-fork.

---

## Testing

To verify all modules:

```bash
pytest -q
```

All six core tests should pass (metrics, parallel consistency, loader equivalence, and portfolio aggregation).

Profiling is not covered by unit tests but can be manually verified using the `--profile` flag.

---
