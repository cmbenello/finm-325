import re
from pathlib import Path
from typing import Iterable, List

# ---------- Asset configuration ----------
ASSET_TYPE = "crypto"          # "equity" or "crypto"
TICKER = "SOL-USD"

# yfinance intraday settings:
DATA_PERIOD = "7d"             # last 7 days
DATA_INTERVAL = "1m"           # 1-minute bars

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_DATA_PATH = RAW_DATA_DIR / f"{TICKER.lower()}_{DATA_INTERVAL}_{DATA_PERIOD}_raw.csv"
PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / f"{TICKER.lower()}_{DATA_INTERVAL}_{DATA_PERIOD}_clean.csv"
PORTFOLIO_FILE = DATA_DIR / "portfolio.md"

# ---------- Feature configuration ----------
RETURN_COLUMN = "return"
LOG_RETURN_COLUMN = "log_return"
SHORT_MA_WINDOW = 20          # in bars (20 minutes)
LONG_MA_WINDOW = 60           # in bars (60 minutes)

SHORT_MA_COL = f"ma_{SHORT_MA_WINDOW}"
LONG_MA_COL = f"ma_{LONG_MA_WINDOW}"
VOL_COL = "rolling_vol"
DEFAULT_PORTFOLIO: List[str] = [TICKER]


def processed_path_for_ticker(ticker: str) -> Path:
    """
    Best-effort helper to locate the processed CSV for a ticker.
    Looks for files like "<ticker>*clean*.csv" under PROCESSED_DATA_DIR and
    falls back to PROCESSED_DATA_PATH when matching the default ticker.
    """
    ticker_lower = ticker.lower()

    if ticker_lower == TICKER.lower() and PROCESSED_DATA_PATH.exists():
        return PROCESSED_DATA_PATH

    candidates = sorted(PROCESSED_DATA_DIR.glob(f"{ticker_lower}*clean*.csv"))
    if not candidates:
        candidates = sorted(PROCESSED_DATA_DIR.glob(f"{ticker_lower}*.csv"))

    if not candidates:
        raise FileNotFoundError(
            f"No processed data found for {ticker}. "
            f"Place a CSV under {PROCESSED_DATA_DIR} or adjust the naming pattern."
        )

    return candidates[0]


def parse_tickers(text: str) -> List[str]:
    """
    Extract ticker symbols from freeform text (commas, bullets, whitespace).
    Allows dashes for crypto pairs.
    """
    tickers = re.findall(r"[A-Za-z][A-Za-z0-9\\-]{0,9}", text)
    return [t.upper() for t in tickers]


def load_portfolio(
    portfolio: Iterable[str] | None = None,
    portfolio_file: Path | None = None,
) -> List[str]:
    """
    Resolve a portfolio of tickers from (in priority order):
      1) explicit iterable of tickers
      2) a markdown/text file with ticker symbols
      3) DEFAULT_PORTFOLIO
    """
    if portfolio:
        return [str(t).upper() for t in portfolio]

    path = portfolio_file or PORTFOLIO_FILE
    if path and path.exists():
        tickers = parse_tickers(path.read_text())
        if tickers:
            return tickers

    return [t.upper() for t in DEFAULT_PORTFOLIO]
