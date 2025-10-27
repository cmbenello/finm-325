from datetime import datetime, timezone, timedelta

from src.patterns.strategy import (
    MeanReversionStrategy, BreakoutStrategy, FirstSignalAdapter
)
from src.models import MarketDataPoint, Action

def _ticks(symbol: str, prices):
    t0 = datetime(2025, 10, 1, 9, 30, tzinfo=timezone.utc)
    for i, px in enumerate(prices):
        yield MarketDataPoint(timestamp=t0 + timedelta(minutes=i), symbol=symbol, price=float(px))

def test_interchangeability_and_signals():
    # Two different strategies, same interface
    mr = MeanReversionStrategy(window=5, z_entry=0.5, qty=3)  # tight to force signals in short test
    bo = BreakoutStrategy(lookback=4, qty=2, buffer=0.0)

    # Engine compatibility (your engine expects single Signal)
    mr_engine = FirstSignalAdapter(mr)
    bo_engine = FirstSignalAdapter(bo)

    # Construct a price path that mean reversion will sell (pop above mean) then buy (drop)
    prices = [100, 100, 101, 99, 100, 103, 98, 101]
    mr_emitted = []
    for tick in _ticks("AAPL", prices):
        sig = mr_engine.generate_signals(tick)
        mr_emitted.append(sig.action)

    # Construct a price path with a breakout above the rolling max
    prices2 = [100, 101, 102, 103, 104, 105]  # clear upward breakout after lookback
    bo_emitted = []
    for tick in _ticks("MSFT", prices2):
        sig = bo_engine.generate_signals(tick)
        bo_emitted.append(sig.action)

    # Assertions: at least one non-HOLD action for each, proving generation works
    assert any(a in (Action.BUY, Action.SELL) for a in mr_emitted)
    assert any(a in (Action.BUY, Action.SELL) for a in bo_emitted)