from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import copy

from src.models import Portfolio, Order, Signal, Action

class Command(ABC):
    @abstractmethod
    def execute(self) -> None: 
        ㅊ
    @abstractmethod
    def undo(self) -> None:
        ㅊ

@dataclass
class ExecuteOrderCommand(Command):
    """
    Execute a single Order against a Portfolio.
    - On execute(): applies the fill and snapshots pre-state for precise undo.
    - On undo(): *restores* the exact pre-state (cash + positions) without
      simulating a reverse trade (memento-style), so avg_price and flips are correct.
    """
    portfolio: Portfolio
    order: Order

    # internal state for undo
    _pre_cash: Optional[float] = None
    _pre_positions: Optional[dict] = None
    _executed: bool = False

    def execute(self) -> None:
        if self._executed:
            return
        # snapshot pre-state
        self._pre_cash = self.portfolio.cash
        # deep copy the nested dict (symbol -> {quantity, avg_price})
        self._pre_positions = copy.deepcopy(self.portfolio.positions)
        # perform fill
        self.portfolio.apply_fill(self.order)
        self._executed = True

    def undo(self) -> None:
        if not self._executed:
            return
        # restore pre-state exactly
        self.portfolio.cash = float(self._pre_cash) if self._pre_cash is not None else self.portfolio.cash
        if self._pre_positions is not None:
            self.portfolio.positions = copy.deepcopy(self._pre_positions)
        self._executed = False


@dataclass
class UndoOrderCommand(Command):
    """
    Command that *reverses* an ExecuteOrderCommand.
    - execute(): calls .undo() on the wrapped execute-command
    - undo(): calls .execute() on the wrapped execute-command (redo original)
    """
    wrapped: ExecuteOrderCommand

    def execute(self) -> None:
        self.wrapped.undo()

    def undo(self) -> None:
        self.wrapped.execute()

class CommandInvoker:
    """
    Manages a history of commands with undo/redo.
    submit(cmd): executes and pushes to undo stack; clears redo stack.
    undo(n): undo last n commands, pushing them to redo stack.
    redo(n): redo last n commands from redo stack back to undo stack.
    """
    def __init__(self) -> None:
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    def submit(self, cmd: Command) -> None:
        cmd.execute()
        self._undo_stack.append(cmd)
        self._redo_stack.clear()

    def undo(self, n: int = 1) -> None:
        for _ in range(min(n, len(self._undo_stack))):
            cmd = self._undo_stack.pop()
            cmd.undo()
            self._redo_stack.append(cmd)

    def redo(self, n: int = 1) -> None:
        for _ in range(min(n, len(self._redo_stack))):
            cmd = self._redo_stack.pop()
            cmd.execute()
            self._undo_stack.append(cmd)

def order_from_signal(sig: Signal) -> Order:
    """
    Convert your Signal NamedTuple into an executable Order.
    Ensures BUY/SELL only (HOLD returns a zero-qty BUY).
    """
    action = sig.action
    if action == Action.HOLD:
        return Order(symbol=sig.symbol, quantity=0, price=sig.price, action=Action.BUY)

    qty = sig.qty if sig.qty > 0 else -sig.qty  # ensure positive quantity
    return Order(symbol=sig.symbol, quantity=qty, price=sig.price, action=action)