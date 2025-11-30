from pathlib import Path
from src.sqlite_storage import ingest_from_csv
from src.parquet_storage import write_parquet_from_csv

market_csv = Path("market_data_multi.csv")
tickers_csv = Path("tickers.csv")
schema_sql = Path("schema.sql")

ingest_from_csv(market_csv, tickers_csv, "market_data.db", schema_sql)
write_parquet_from_csv(market_csv, tickers_csv, "market_data")