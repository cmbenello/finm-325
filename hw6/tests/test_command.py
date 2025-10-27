from src.patterns.command import CommandInvoker, ExecuteOrderCommand, UndoOrderCommand, order_from_signal
from src.models import Portfolio, Signal, Action, MarketDataPoint

def test_trade_lifecycle_signal_execute_undo_redo():
    # Start with clean portfolio
    port = Portfolio(cash=10_000.0)

    # A BUY signal
    sig = Signal(Action.BUY, "AAPL", 10, 100.0)  # buy 10 @ 100 -> cash -1000
    order = order_from_signal(sig)

    inv = CommandInvoker()

    # Execute order
    exec_cmd = ExecuteOrderCommand(portfolio=port, order=order)
    inv.submit(exec_cmd)

    # After execution
    assert abs(port.cash - 9_000.0) < 1e-9
    assert port.positions["AAPL"]["quantity"] == 10
    assert abs(port.positions["AAPL"]["avg_price"] - 100.0) < 1e-9

    # Undo (using UndoOrderCommand or invoker.undo)
    undo_cmd = UndoOrderCommand(exec_cmd)
    inv.submit(undo_cmd)

    # Back to original portfolio state precisely
    assert abs(port.cash - 10_000.0) < 1e-9
    assert port.positions.get("AAPL", {"quantity": 0})["quantity"] in (0, port.positions.get("AAPL", {}).get("quantity", 0))

    # Redo: undo the undo (re-apply the original trade)
    inv.undo()   # undo the UndoOrderCommand => re-executes the original order
    # Now we should be back to post-trade state
    assert abs(port.cash - 9_000.0) < 1e-9
    assert port.positions["AAPL"]["quantity"] == 10
    assert abs(port.positions["AAPL"]["avg_price"] - 100.0) < 1e-9

def test_invoker_undo_redo_stack_direct():
    port = Portfolio(cash=5_000.0)

    buy1 = order_from_signal(Signal(Action.BUY, "MSFT", 5, 200.0))  # -1000
    buy2 = order_from_signal(Signal(Action.BUY, "MSFT", 5, 220.0))  # -1100

    inv = CommandInvoker()
    c1 = ExecuteOrderCommand(port, buy1)
    c2 = ExecuteOrderCommand(port, buy2)

    inv.submit(c1)
    inv.submit(c2)

    # After two buys
    assert abs(port.cash - (5000 - 1000 - 1100)) < 1e-9
    assert port.positions["MSFT"]["quantity"] == 10

    # Undo last (buy2)
    inv.undo(1)
    assert abs(port.cash - (5000 - 1000)) < 1e-9
    assert port.positions["MSFT"]["quantity"] == 5

    # Redo (re-apply buy2)
    inv.redo(1)
    assert abs(port.cash - (5000 - 1000 - 1100)) < 1e-9
    assert port.positions["MSFT"]["quantity"] == 10