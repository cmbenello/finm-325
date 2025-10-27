from src.patterns.factory import InstrumentFactory
from src.instruments import Stock, Bond, ETF

def test_factory_types():
    s = InstrumentFactory.create_instrument({"type":"stock","symbol":"AAPL"})
    b = InstrumentFactory.create_instrument({"type":"bond","symbol":"T10","maturity":"2035-11-15"})
    e = InstrumentFactory.create_instrument({"type":"etf", "symbol":"SPY"})
    assert isinstance(s, Stock) and isinstance(b, Bond) and isinstance(e, ETF)