# tests/test_decorator.py
import math
from src.analytics import MetricsSubject, VolatilityDecorator, BetaDecorator, DrawdownDecorator

def test_volatility_decorator_basic():
    subj = MetricsSubject("AAPL")
    d = VolatilityDecorator(subj, window=3)
    prices = [100, 102, 101, 103]

    for i in range(1, len(prices)):
        d.observe_price(prices[i], prices[i-1])

    m = d.get_metrics()
    assert "volatility" in m
    assert m["volatility"] is None or m["volatility"] >= 0.0

def test_beta_decorator_basic():
    subj = MetricsSubject("AAPL")
    d = BetaDecorator(subj, window=4)
    px = [100, 102, 101, 103]
    mkt = [200, 202, 203, 204]

    for i in range(1, len(px)):
        d.observe_market_pair(px[i], px[i-1], mkt[i], mkt[i-1])

    m = d.get_metrics()
    assert "beta" in m
    # Beta should be numeric or None (insufficient data)
    assert m["beta"] is None or isinstance(m["beta"], float)

def test_drawdown_decorator_basic():
    subj = MetricsSubject("AAPL")
    d = DrawdownDecorator(subj)
    prices = [100, 120, 90, 95, 130, 110]

    for i in range(1, len(prices)):
        d.observe_price(prices[i], prices[i-1])

    m = d.get_metrics()
    assert "max_drawdown" in m
    assert m["max_drawdown"] <= 0.0  # should be non-positive

def test_stacked_decorators():
    subj = MetricsSubject("AAPL")
    decorated = DrawdownDecorator(BetaDecorator(VolatilityDecorator(subj)))

    px = [100, 102, 101, 103, 104]
    mkt = [200, 203, 202, 204, 205]

    for i in range(1, len(px)):
        decorated.ingest_tick(
            price=px[i],
            prev_price=px[i-1],
            mkt_price=mkt[i],
            mkt_prev_price=mkt[i-1],
        )

    m = decorated.get_metrics()
    assert all(k in m for k in ("volatility", "beta", "max_drawdown"))