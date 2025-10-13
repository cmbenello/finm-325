import csv
from datetime import datetime
from src.models import MarketDataPoint
from typing import List
from dataclasses import dataclass, FrozenInstanceError


REQUIRED_COLUMNS = ("timestamp", "symbol", "price")

class CSVFormatError(Exception):
    pass

def _validate_header(header):
    if header is None:
        raise CSVFormatError("CSV missing header row")
    normalized = [h.strip().lower() for h in header]
    missing = [c for c in REQUIRED_COLUMNS if c not in normalized]
    if missing:
        raise CSVFormatError(f"Missing required columns: {', '.join(missing)}")
    return {name: normalized.index(name) for name in REQUIRED_COLUMNS}


def load_data(file_path: str):
    """Return raw rows [timestamp_str, symbol_str, price_str] after header validation."""
    data = []
    with open(file_path, 'r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader, None)
        idx = _validate_header(header)

        for row in reader:
            # Skip empty/blank lines
            if not row or all((c.strip() == '' for c in row)):
                continue

            # Ensure row has enough columns before indexing
            max_i = max(idx.values())
            if len(row) <= max_i:
                raise CSVFormatError("Row has insufficient columns")

            try:
                data.append([
                    row[idx['timestamp']],
                    row[idx['symbol']],
                    row[idx['price']],
                ])
            except IndexError:
                raise CSVFormatError("Row has insufficient columns")
    return data


def _parse_timestamp(ts: str) -> datetime:
    ts = ts.strip()
    # ISO 8601 with optional trailing Z
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        pass
    # Simple fallbacks
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    raise CSVFormatError(f"Invalid timestamp format: {ts}")

def create_market_data_points(data):
    mdp = []
    for row in data:
        timestamp_str, symbol, price = row

        ts = _parse_timestamp(timestamp_str)
        sym = symbol.strip()

        # Convert then validate price
        try:
            price_val = float(price)
        except ValueError as e:
            raise CSVFormatError(f"Invalid price value: {price}") from e
        if price_val <= 0:
            raise CSVFormatError("Price must be positive")

        mdp.append(MarketDataPoint(timestamp=ts, symbol=sym, price=price_val))

    # Engine expects time-ordered ticks
    mdp.sort(key=lambda x: x.timestamp)
    return mdp


if __name__ == "__main__":
    file_path = 'data/market_data.csv'
    data = load_data(file_path)
    market_data_points = create_market_data_points(data)

    print(market_data_points[:5])

