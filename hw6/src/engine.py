from __future__ import annotations
from typing import Iterable, List, Optional
from datetime import datetime

from src.models import (
    Portfolio, PortfolioLog, PortfolioSnapshot, MarketDataPoint,
    Signal, Action
)
from src.patterns.command import CommandInvoker, ExecuteOrderCommand, order_from_signal
from src.reporting import SignalPublisher


class ExecutionEngine:
    def __init__(self, strategy, portfolio: Portfolio, publisher: Optional[SignalPublisher] = None) -> None:
        self.strategy = strategy
        self.portfolio = portfolio
        self.publisher = publisher
        self.invoker = CommandInvoker()
        self.exception_log: List[Exception] = []
        self._last_px: dict[str, float] = {}  # <-- price book

    def run(self, market_feed: Iterable[MarketDataPoint], portfolio_log: Optional[PortfolioLog] = None) -> PortfolioLog:
        log = portfolio_log if portfolio_log is not None else []
        for tick in market_feed:
            try:
                # update price book first
                self._last_px[tick.symbol] = float(tick.price)

                signals = self.strategy.generate_signals(tick)

                if self.publisher is not None:
                    for sig in signals:
                        self.publisher.notify(sig)

                for sig in signals:
                    if sig.action == Action.HOLD or sig.qty == 0:
                        continue
                    cmd = ExecuteOrderCommand(self.portfolio, order_from_signal(sig))
                    self.invoker.submit(cmd)

                log.append(self._snapshot(tick))  # snapshots now use price map

            except Exception as ex:
                self.exception_log.append(ex)
                log.append(self._snapshot(tick))
        return log

    def undo_last(self, n: int = 1) -> None:
        self.invoker.undo(n)

    def redo_last(self, n: int = 1) -> None:
        self.invoker.redo(n)

    def _snapshot(self, tick: MarketDataPoint) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            timestamp=tick.timestamp,
            price=tick.price,
            portfolio_value=self.portfolio.total_equity_map(self._last_px),  # <-- use map
            position=self.portfolio.positions
        )