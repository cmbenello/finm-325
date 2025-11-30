# FINM 325 – HW11: Market Data Storage and Querying

This assignment implements a full workflow for loading, validating, storing, and querying multi-ticker OHLCV market data. The project uses both SQLite3 and Parquet to highlight the practical differences between relational and columnar storage formats in financial data analysis.

The repository includes modules for ingestion, SQL-based querying, columnar analytics, benchmarking, and automated tests.

---

## Project Structure

```
hw11/
│
├── data_loader.py
├── sqlite_storage.py
├── parquet_storage.py
├── benchmark_queries.py
├── schema.sql
├── market_data_multi.csv
├── tickers.csv
│
├── query_tasks.md
├── comparison.md
│
└── tests/
    └── test_.py
```

---

## Setup

### 1. Install Dependencies
```bash
pip install pandas pyarrow pytest
```

### 2. Ensure input data files exist
- `market_data_multi.csv`
- `tickers.csv`
- `schema.sql`

---

## Usage

### 1. Load & Validate Data
```python
from src.data_loader import load_and_validate_market_data

df = load_and_validate_market_data("market_data_multi.csv", "tickers.csv")
print(df.head())
```

### 2. Build SQLite Database
```python
from src.sqlite_storage import ingest_from_csv

ingest_from_csv(
    "market_data_multi.csv",
    "tickers.csv",
    "market_data.db",
    "schema.sql",
)
```

### 3. Write Parquet Dataset
```python
from src.parquet_storage import write_parquet_from_csv

write_parquet_from_csv(
    "market_data_multi.csv",
    "tickers.csv",
    "market_data/",
)
```

---

## Querying

### SQLite queries include:
- Ticker/date-range OHLCV extraction
- Average daily volume per ticker
- Top 3 tickers by return
- First/last trade per day per ticker

### Parquet queries include:
- Ticker/date-range extraction
- 5-day rolling volatility
- 5-minute rolling average (AAPL example)

All results are documented in **`query_tasks.md`**.

---

## Benchmarking
Run all required tasks and compare speed:
```bash
python3 benchmark_queries.py
```
This prints:
- SQLite and Parquet query results
- Timing comparison
- File size comparison

---

## Running Tests
Tests validate ingestion, schema, and query correctness.

```bash
pytest -q
```
Expected output:
```
5 passed in X.XXs
```

---

## Analysis
A detailed comparison of storage formats (query performance, file size, analytical workflow integration) is in:

- **`comparison.md`**

---

## Summary
This assignment demonstrates:
- Differences between relational and columnar storage
- Practical SQL analytics versus pandas/PyArrow analytics
- How storage format impacts query performance
- A clean pipeline for ingestion, storage, querying, and evaluation

The project is fully reproducible using the provided scripts and tests.