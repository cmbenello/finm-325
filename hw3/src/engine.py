from src.models import (ExecutionError, OrderError, Portfolio, PortfolioLog, Position, MarketDataPoint,
                    Signal, Order, PortfolioSnapshot, Action)
from src.strategies import Strategy
from typing import List
from random import random

class ExecutionEngine:
    """Execution engine for taking incoming data points and running strategies on settlement stream
    """
    def __init__(self, strat: Strategy, portfolio: Portfolio) -> None:
        self.strat = strat
        self.portfolio: Portfolio = portfolio
        self.exception_log: List[Exception] = []
        # self.orderbook: deque[Order] = []
        # self.portfolio_snapshot: PortfolioSnapshot = None

    def simulate_failure(self) -> None:
        raise ExecutionError
 
    def log_exception(self, exception: Exception) -> None:
        self.exception_log.append(exception)
    
    def _execute_on_signal(self, signal: Signal) -> None:
        try:
            quantity = signal.qty if signal.qty > 0 else -signal.qty # correct for sign
            if signal.action == Action.HOLD:
                return

            new_order = Order(symbol=signal.symbol, quantity=quantity,
                              price=signal.price, action=signal.action, status="NEW")
            self.portfolio.apply_fill(new_order)
        except ExecutionError as exerr:
            self.log_exception(exerr)


    def run_with_failures(self, market_feed: List[MarketDataPoint], 
                          portfolio_log: PortfolioLog,
                          error_rate: float = 0.02):
        for tick in market_feed:
            failure = True if random() < error_rate else False
            try:
                if failure:
                    raise ExecutionError
                signal = self.strat.generate_signals(tick)
                self._execute_on_signal(signal)
                self.log_data(portfolio_values=portfolio_log, tick=tick)
            except ExecutionError as exerr:
                self.log_exception(exerr)
                self.log_data(portfolio_values=portfolio_log, tick=tick)


    def run_strategy(self, market_feed: List[MarketDataPoint], portfolio_log: PortfolioLog) -> None:
        for i, tick in enumerate(market_feed):
            try:
                signal = self.strat.generate_signals(tick)
                self._execute_on_signal(signal)
                self.log_data(portfolio_values=portfolio_log, tick=tick)
            except ExecutionError as exerr:
                self.log_exception(exerr)
                self.log_data(portfolio_values=portfolio_log, tick=tick)


    def log_data(self, portfolio_values: PortfolioLog, tick: MarketDataPoint) -> None:
        portfolio_values.append(
            PortfolioSnapshot(timestamp=tick.timestamp, price=tick.price,
                              portfolio_value=self.portfolio.total_equity(tick),
                              position=self.portfolio.positions)
        )

