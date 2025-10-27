from __future__ import annotations
from typing import Iterator, Any, Dict
from pathlib import Path
from datetime import datetime, timezone
import json
import xml.etree.ElementTree as ET

from src.models import MarketDataPoint


def _parse_iso_z(s: str) -> datetime:
    """
    Parse ISO8601 strings that may end with 'Z' into timezone-aware datetimes.
    Example: '2025-10-01T09:30:00Z'
    """
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


class YahooFinanceAdapter:
    """
    Expected JSON record schema (per your example):

    {
      "ticker": "AAPL",
      "last_price": 172.35,
      "timestamp": "2025-10-01T09:30:00Z"
    }

    The file may contain either a single object (as above) OR a list of such objects.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        with self.path.open("r") as f:
            self._raw = json.load(f)

    def _iter_records(self) -> Iterator[Dict[str, Any]]:
        if isinstance(self._raw, dict):
            yield self._raw
        elif isinstance(self._raw, list):
            for rec in self._raw:
                if isinstance(rec, dict):
                    yield rec

    def get_data(self, symbol: str) -> Iterator[MarketDataPoint]:
        for rec in self._iter_records():
            if rec.get("ticker") != symbol:
                continue
            ts = _parse_iso_z(rec["timestamp"])
            px = float(rec["last_price"])
            yield MarketDataPoint(timestamp=ts, symbol=symbol, price=px)


class BloombergXMLAdapter:
    """
    Expected XML schema (per your example):

    <instrument>
      <symbol>MSFT</symbol>
      <price>328.10</price>
      <timestamp>2025-10-01T09:30:00Z</timestamp>
    </instrument>

    The file may contain one <instrument> or many (wrapped in a root).
    We'll iterate over every <instrument> node that has the requested symbol.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._root = ET.parse(self.path).getroot()

    def get_data(self, symbol: str) -> Iterator[MarketDataPoint]:
        # Allow either the root being <instrument> or containing multiple <instrument> children
        instruments = (
            [self._root] if self._root.tag == "instrument"
            else list(self._root.findall(".//instrument"))
        )

        for inst in instruments:
            sym_node = inst.find("symbol")
            price_node = inst.find("price")
            ts_node = inst.find("timestamp")
            if sym_node is None or price_node is None or ts_node is None:
                continue
            if (sym := sym_node.text) != symbol:
                continue
            ts = _parse_iso_z(ts_node.text or "")
            px = float(price_node.text)
            yield MarketDataPoint(timestamp=ts, symbol=sym, price=px)