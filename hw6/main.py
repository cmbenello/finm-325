# main.py
from __future__ import annotations
from typing import List, Mapping
from pathlib import Path
import csv
import os
from datetime import datetime, timezone

from src.models import Portfolio, MarketDataPoint
from src.engine import ExecutionEngine
from src.data_loader import YahooFinanceAdapter, BloombergXMLAdapter
from src.patterns.strategy import MeanReversionStrategy, BreakoutStrategy
from src.reporting import SignalPublisher, LoggerObserver, AlertObserver


# ---------- feed loaders ----------

def _parse_iso_z(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)

def load_market_csv(path: str) -> List[MarketDataPoint]:
    """Reads data/market_data.csv if present: timestamp,symbol,price (case-insensitive)."""
    p = Path(path)
    if not p.exists():
        return []
    ticks: List[MarketDataPoint] = []
    with p.open(newline="") as f:
        reader = csv.DictReader(f)
        fields = {k.lower(): k for k in (reader.fieldnames or [])}
        ts_key = fields.get("timestamp") or fields.get("time") or "timestamp"
        sym_key = fields.get("symbol") or "symbol"
        px_key = fields.get("price") or fields.get("close") or fields.get("last") or "price"
        for row in reader:
            sym = row.get(sym_key)
            if not sym:
                continue
            ts = _parse_iso_z(row[ts_key]) if row.get(ts_key) else datetime.now(timezone.utc)
            px = float(row[px_key])
            ticks.append(MarketDataPoint(ts, sym, px))
    ticks.sort(key=lambda t: t.timestamp)
    return ticks

def load_market_feed() -> List[MarketDataPoint]:
    """Prefer CSV; else adapters; fall back to tiny synthetic sequence if needed."""
    feed = load_market_csv("data/market_data.csv")
    if not feed:
        y = YahooFinanceAdapter("configs/external_data_yahoo.json")
        b = BloombergXMLAdapter("configs/external_data_bloomberg.xml")
        feed.extend(list(y.get_data("AAPL")))
        feed.extend(list(b.get_data("MSFT")))
        feed.sort(key=lambda t: t.timestamp)

    # If still thin, generate a tiny micro-path per seen symbol (demo-only).
    if len(feed) < 6:
        synth: List[MarketDataPoint] = []
        for base in (feed or [MarketDataPoint(datetime.now(timezone.utc), "AAPL", 100.0)]):
            ts0 = base.timestamp.replace(microsecond=0)
            seq = [base.price, base.price*1.01, base.price*0.99, base.price*1.03, base.price*0.97, base.price*1.02]
            for i, px in enumerate(seq):
                synth.append(MarketDataPoint(ts0, base.symbol, float(px)))
        feed = synth

    return feed

def limit_per_symbol(feed: List[MarketDataPoint], n: int = 500) -> List[MarketDataPoint]:
    """Keep only first n ticks per symbol to avoid huge runs."""
    seen: dict[str, int] = {}
    out: List[MarketDataPoint] = []
    for t in feed:
        c = seen.get(t.symbol, 0)
        if c < n:
            out.append(t)
            seen[t.symbol] = c + 1
    return out


# ---------- wiring helpers ----------

def build_strategy(which: str = "mean_reversion"):
    """
    Choose strategy. Calmer defaults for demo (few trades; clearer P&L).
    Set STRAT=breakout in env to switch.
    """
    which = (os.environ.get("STRAT") or which).lower()
    if which == "mean_reversion":
        return MeanReversionStrategy(window=40, z_entry=2.0, qty=5, min_window=20)
    if which == "breakout":
        return BreakoutStrategy(lookback=60, qty=5, buffer=0.25)
    raise ValueError(f"unknown strategy {which!r}")

def build_observers() -> SignalPublisher:
    pub = SignalPublisher()
    logger = LoggerObserver()
    alerts = AlertObserver(threshold_notional=2_000.0, threshold_qty=50)
    pub.attach(logger)
    pub.attach(alerts)
    return pub


# ---------- main ----------

def main():
    # 1) Portfolio
    portfolio = Portfolio(cash=100_000.0)

    # 2) Strategy (swap with env STRAT=breakout for other one)
    strategy = build_strategy("mean_reversion")

    # 3) Observers
    publisher = build_observers()

    # 4) Engine
    engine = ExecutionEngine(strategy=strategy, portfolio=portfolio, publisher=publisher)

    # 5) Feed (trim to keep the demo readable)
    feed = load_market_feed()
    feed = limit_per_symbol(feed, n=500)

    # 6) Run
    portfolio_log = engine.run(feed)

    # 7) Summary
    print("\n=== Run Summary ===")
    if portfolio_log:
        last = portfolio_log[-1]
        print(f"Final equity: {last.portfolio_value:,.2f}")
    print("Final positions:", portfolio.positions)
    print("Remaining cash :", f"{portfolio.cash:,.2f}")
    print("Exceptions     :", len(engine.exception_log))

    # 8) Observer outputs
    for ob in publisher.observers:
        cls = ob.__class__.__name__
        if hasattr(ob, "logs"):
            print(f"{cls}: {len(ob.logs)} signals logged")
        if hasattr(ob, "alerts"):
            print(f"{cls}: {len(ob.alerts)} alerts")

    # 9) Mark-to-market breakdown (uses engine's last-price map)
    if hasattr(engine, "_last_px"):
        print("\nMark-to-market by symbol:")
        eq_from_positions = 0.0
        for sym, pos in portfolio.positions.items():
            last_px = engine._last_px.get(sym)
            if last_px is None:
                continue
            mv = pos["quantity"] * last_px
            eq_from_positions += mv
            print(f"  {sym}: last={last_px:.2f}, qty={pos['quantity']}, MV={mv:,.2f}")
        print(f"Cash: {portfolio.cash:,.2f}")
        print(f"Σ MV: {eq_from_positions:,.2f}")

    # 10) Interchangeability quick check (optional): run breakout on the same feed
    print("\n=== Interchangeability Demo: Breakout Strategy ===")
    alt_strategy = build_strategy("breakout")
    alt_engine = ExecutionEngine(strategy=alt_strategy, portfolio=Portfolio(cash=100_000.0), publisher=publisher)
    alt_log = alt_engine.run(feed)
    if alt_log:
        print(f"Breakout final equity: {alt_log[-1].portfolio_value:,.2f}")


if __name__ == "__main__":
    main()