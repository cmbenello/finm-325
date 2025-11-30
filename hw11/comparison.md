

# Format Comparison: SQLite3 vs Parquet

## File Size
- **SQLite3** (`market_data.db`): 688 kb
- **Parquet** (`market_data/`): 339 kb

Parquet is roughly **50% smaller**, consistent with columnar compression and efficient encoding of repeated values.

## Query Performance

### 1. Ticker + Date Range (AAPL 5‑minute rolling basis)
- **SQLite:** 0.004146 s
- **Parquet:** 0.004617 s

SQLite is slightly faster for this targeted lookup. It performs an efficient selective scan over indexed rows, while Parquet loads a partition and incurs pandas overhead.

### 2. Rolling 5‑Day Volatility (All Tickers)
- Parquet shows faster performance due to selective column loading and compressed columnar I/O.

## Interpretation

### When SQLite3 is Better
- Small, focused lookups (single ticker, short window)
- SQL joins and relational queries
- Prototyping components of a trading system
- Easy portability: one `.db` file works everywhere

### When Parquet is Better
- Analytics workflows in pandas / NumPy
- Feature engineering and factor computation
- Full‑dataset scans (volatility, returns, aggregations)
- Interoperability with PyArrow, DuckDB, Spark, Dask

## Summary
SQLite excels at **precise, selective queries** and relational structure, while Parquet excels at **analytics, backtesting, and columnar performance**. Realistic research and trading systems often combine both: Parquet for historical bars and analytics, SQLite (or other SQL engines) for metadata, configuration, and relational components.