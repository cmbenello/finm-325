from src.reporting import SignalPublisher, LoggerObserver, AlertObserver
from src.models import Signal, Action

def test_observer_demo_dynamic_registration():
    pub = SignalPublisher()
    logger = LoggerObserver()
    alert = AlertObserver(threshold_notional=10_000.0, threshold_qty=200)

    # Attach only logger first
    pub.attach(logger)

    # 1) Small BUY -> should log, no alert
    pub.notify(Signal(Action.BUY, "AAPL", 10, 150.0))  # notional = 1500
    assert len(logger.logs) == 1
    assert len(alert.alerts) == 0  # not attached yet anyway

    # 2) Dynamically attach alert; send large SELL -> both should receive
    pub.attach(alert)
    pub.notify(Signal(Action.SELL, "MSFT", 300, 40.0))  # notional = 12,000
    assert len(logger.logs) == 2
    assert len(alert.alerts) == 1
    assert alert.alerts[0]["symbol"] == "MSFT"

    # 3) Detach logger; send another big -> only alert should record it
    pub.detach(logger)
    pub.notify({"action": "BUY", "symbol": "NVDA", "qty": 500, "price": 25.0})  # dict payload also accepted
    assert len(logger.logs) == 2  # unchanged
    assert len(alert.alerts) == 2
    assert alert.alerts[-1]["symbol"] == "NVDA"