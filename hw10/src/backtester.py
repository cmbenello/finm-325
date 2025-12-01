# src/backtester.py

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

from .config import PROCESSED_DATA_PATH
from .market_data_gateway import MarketDataGateway
from .strategy import MovingAverageCrossoverStrategy
from .order_book import OrderBook
from .order_manager import OrderManager, OrderManagerConfig
from .order_gateway import OrderGateway
from .matching_engine import MatchingEngine
from .orders import (
    Order,
    Side,
    OrderType,
    OrderStatus,
    ExecutionReport,
)


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    positions: pd.Series
    cash: pd.Series
    trades: pd.DataFrame
    raw_signals: pd.DataFrame
    close_prices: pd.Series        
    final_metrics: Dict[str, Any]


@dataclass
class Backtester:
    """
    Runs a discrete-time backtest:

      1. Load cleaned bar data via MarketDataGateway.
      2. Use strategy to compute desired position at each timestamp.
      3. Whenever desired_position != current_position, generate an order
         for the difference and route it through:
             OrderManager → MatchingEngine → OrderGateway.
      4. Mark-to-market portfolio at each bar to get an equity curve.
    """

    strategy: MovingAverageCrossoverStrategy = field(
        default_factory=MovingAverageCrossoverStrategy
    )
    data_path: Path | None = None
    om_config: OrderManagerConfig = field(default_factory=OrderManagerConfig)
    order_log_path: Path = field(default_factory=lambda: Path("logs") / "orders_backtest.csv")

    def run(self) -> BacktestResult:
        # ---- Set up components ----
        md_gateway = MarketDataGateway(data_path=self.data_path or PROCESSED_DATA_PATH)
        df = md_gateway.get_dataframe()  # full DataFrame of bars
        if df.empty:
            raise ValueError("No market data available for backtest.")

        first_price = float(df["Close"].iloc[0])

        # Size positions so that a +1/-1 signal corresponds to being fully
        # invested (or fully short) with the initial capital.
        target_shares = self.om_config.initial_capital / first_price

        # Loosen position limits automatically if the configured limits are too small
        # for a fully invested position in this dataset.
        local_config = replace(self.om_config)
        if local_config.max_long_position < target_shares:
            adjusted_limit = target_shares * 1.2
            local_config = replace(
                local_config,
                max_long_position=adjusted_limit,
                max_short_position=-adjusted_limit,
            )

        order_book = OrderBook()
        om = OrderManager(config=local_config)
        matching_engine = MatchingEngine(order_book=order_book)

        self.order_log_path.parent.mkdir(parents=True, exist_ok=True)
        order_gateway = OrderGateway(self.order_log_path)

        # ---- Strategy signals (desired positions) ----
        signals_df = self.strategy.generate_signals(df)

        # We track time series of cash, position, equity, and actual position
        cash_series: List[float] = []
        pos_series: List[float] = []
        equity_series: List[float] = []
        timestamps: List[pd.Timestamp] = []

        # For recording filled trades (each execution report with filled_qty > 0)
        trades_records: List[Dict[str, Any]] = []

        current_position = 0.0
        order_id_counter = 1

        # Iterate over "live" bars
        for ts, row in md_gateway:
            price = float(row["Close"])

            # Desired position from strategy at this timestamp
            raw_position = float(signals_df.loc[ts, self.strategy.position_col])
            desired_position = raw_position * target_shares

            delta = desired_position - current_position

            # If position needs to change, generate order
            if abs(delta) > 1e-8:
                side = Side.BUY if delta > 0 else Side.SELL
                quantity = abs(delta)

                order = Order(
                    order_id=order_id_counter,
                    side=side,
                    quantity=quantity,
                    price=price,               # limit price at current bar price
                    timestamp=ts,
                    order_type=OrderType.LIMIT
                )

                # Validate order
                ok, reason = om.validate_order(order)
                if not ok:
                    order.status = OrderStatus.REJECTED
                    er = ExecutionReport(
                        order_id=order.order_id,
                        status=order.status,
                        filled_quantity=0.0,
                        remaining_quantity=order.quantity,
                        avg_price=None,
                        timestamp=ts,
                        note=reason,
                    )
                    order_gateway.log("REJECT", order, er)

                else:
                    # Accept and send to matching engine
                    om.record_accepted_order(order)
                    er = matching_engine.process_order(order, mid_price=price)

                    # Apply execution to portfolio
                    if er.filled_quantity > 0 and er.avg_price is not None:
                        om.apply_execution(order, er.filled_quantity, er.avg_price)
                        current_position = om.position  # sync

                        # Record trade
                        trades_records.append(
                            {
                                "timestamp": er.timestamp,
                                "side": order.side.name,
                                "filled_quantity": er.filled_quantity,
                                "avg_price": er.avg_price,
                                "note": er.note,
                            }
                        )

                    # Log lifecycle
                    order_gateway.log("NEW", order, er)

                order_id_counter += 1

            # Mark-to-market equity at this bar
            mtm_equity = om.cash + om.position * price
            timestamps.append(ts)
            cash_series.append(om.cash)
            pos_series.append(om.position)
            equity_series.append(mtm_equity)

        # Build output structures
        idx = pd.DatetimeIndex(timestamps, name="Datetime")
        cash_s = pd.Series(cash_series, index=idx, name="cash")
        pos_s = pd.Series(pos_series, index=idx, name="position")
        equity_s = pd.Series(equity_series, index=idx, name="equity")

        trades_df = pd.DataFrame(trades_records)
        trades_df.sort_values("timestamp", inplace=True)

        from .performance import PerformanceAnalyzer

        close_prices = df["Close"].copy()

        metrics = PerformanceAnalyzer.compute_metrics(equity_s, pos_s, close_prices)

        return BacktestResult(
            equity_curve=equity_s,
            positions=pos_s,
            cash=cash_s,
            trades=trades_df,
            raw_signals=signals_df,
            close_prices=close_prices,
            final_metrics=metrics,
        )
