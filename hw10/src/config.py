from pathlib import Path

# ---------- Asset configuration ----------
ASSET_TYPE = "equity"          # "equity" or "crypto"
TICKER = "AAPL"

# yfinance intraday settings:
DATA_PERIOD = "5y"             # last 7 days
DATA_INTERVAL = "1d"           # 1-minute bars

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_DATA_PATH = RAW_DATA_DIR / "aapl_1m_7d_raw.csv"
PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / "aapl_1m_7d_clean.csv"

# ---------- Feature configuration ----------
RETURN_COLUMN = "return"
LOG_RETURN_COLUMN = "log_return"
SHORT_MA_WINDOW = 20          # in bars (20 minutes)
LONG_MA_WINDOW = 60           # in bars (60 minutes)

SHORT_MA_COL = f"ma_{SHORT_MA_WINDOW}"
LONG_MA_COL = f"ma_{LONG_MA_WINDOW}"
VOL_COL = "rolling_vol"