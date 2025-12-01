from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd

from .backtester import Backtester, BacktestResult
from .config import TICKER, load_portfolio, parse_tickers, processed_path_for_ticker
from .order_manager import OrderManagerConfig
from .strategy import (
    AggressiveMomentumStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    VWAPReversionStrategy,
)


def build_buy_and_hold_equity(close_prices: pd.Series, initial_equity: float) -> pd.Series:
    close_prices = close_prices.sort_index()
    shares = initial_equity / close_prices.iloc[0]
    return close_prices * shares


def run_strategies_for_ticker(
    ticker: str,
    om_config: OrderManagerConfig,
) -> Dict[str, BacktestResult]:
    data_path = processed_path_for_ticker(ticker)
    strategies = [
        MomentumStrategy(),
        AggressiveMomentumStrategy(),
        MeanReversionStrategy(),
        VWAPReversionStrategy(),
    ]

    results: Dict[str, BacktestResult] = {}
    for strat in strategies:
        log_path = Path("logs") / f"orders_{ticker.lower()}_{strat.name}.csv"
        bt = Backtester(
            strategy=strat,
            data_path=data_path,
            om_config=om_config,
            order_log_path=log_path,
        )
        results[strat.name] = bt.run()

    return results


def aggregate_portfolio_equity(
    per_ticker_results: Dict[str, Dict[str, BacktestResult]],
    initial_equity: float,
) -> Dict[str, pd.Series]:
    """
    Build equal-weight portfolio equity curves for each strategy across the
    provided tickers. Each ticker is normalized to 1 at start; we average and
    rescale to the portfolio initial equity.
    """
    aggregated: Dict[str, pd.Series] = {}

    # Collect all strategy names present
    strategy_names = set()
    for strat_map in per_ticker_results.values():
        strategy_names.update(strat_map.keys())

    for strat_name in strategy_names:
        norm_curves = []
        for strat_map in per_ticker_results.values():
            if strat_name not in strat_map:
                continue
            eq = strat_map[strat_name].equity_curve.sort_index()
            norm_curves.append(eq / eq.iloc[0])
        if not norm_curves:
            continue
        df = pd.concat(norm_curves, axis=1).ffill()
        aggregated[strat_name] = df.mean(axis=1) * initial_equity

    # Buy & hold aggregation across tickers
    bh_curves = []
    for strat_map in per_ticker_results.values():
        if not strat_map:
            continue
        any_result = next(iter(strat_map.values()))
        bh = build_buy_and_hold_equity(any_result.close_prices, initial_equity)
        bh_curves.append(bh / bh.iloc[0])
    if bh_curves:
        df = pd.concat(bh_curves, axis=1).ffill()
        aggregated["buy_and_hold"] = df.mean(axis=1) * initial_equity

    return aggregated


def plot_portfolio_equities(
    portfolio_equities: Dict[str, Dict[str, pd.Series]],
) -> None:
    """
    Plot one figure per portfolio, showing all strategy curves plus buy & hold.
    """
    if not portfolio_equities:
        return

    for portfolio_name, strat_curves in portfolio_equities.items():
        if not strat_curves:
            continue
        fig, ax = plt.subplots(figsize=(11, 5))
        for strat_name, curve in strat_curves.items():
            style = "--" if strat_name == "buy_and_hold" else "-"
            ax.plot(
                curve.index,
                curve,
                linestyle=style,
                linewidth=1.8 if strat_name != "buy_and_hold" else 1.2,
                alpha=0.85,
                label=strat_name,
            )
        ax.set_title(f"{portfolio_name} portfolio: strategies vs buy & hold")
        ax.set_ylabel("Equity")
        ax.set_xlabel("Time")
        ax.legend()
        plt.tight_layout()

    plt.show()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run strategies for one or more tickers/portfolios.",
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Tickers to backtest. If omitted, uses --portfolio/portfolio file/default.",
    )
    parser.add_argument(
        "--portfolio",
        action="append",
        help="Comma/space-separated list of tickers to use as the portfolio.",
    )
    parser.add_argument(
        "--portfolio-file",
        action="append",
        type=Path,
        help="Path to a markdown/text file containing tickers (bullets/commas are fine).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    om_config = OrderManagerConfig()

    def parse_portfolio_arg(raw: str | None) -> List[str]:
        if not raw:
            return []
        return parse_tickers(raw)

    portfolios: List[Tuple[str, List[str]]] = []
    if args.tickers:
        portfolios.append(("tickers", [t.upper() for t in args.tickers]))

    if args.portfolio:
        for i, raw in enumerate(args.portfolio, start=1):
            tickers = parse_portfolio_arg(raw)
            if tickers:
                portfolios.append((f"portfolio_{i}", tickers))

    if args.portfolio_file:
        for path in args.portfolio_file:
            tickers = load_portfolio(portfolio_file=path)
            if tickers:
                name = path.stem or "portfolio_file"
                portfolios.append((name, tickers))

    if not portfolios:
        tickers = load_portfolio()
        portfolios.append(("default", tickers))

    portfolio_equities: Dict[str, Dict[str, pd.Series]] = {}

    for portfolio_name, tickers in portfolios:
        print(f"\n=== Portfolio: {portfolio_name} | Tickers: {', '.join(tickers)} ===")
        per_ticker_results: Dict[str, Dict[str, BacktestResult]] = {}
        for ticker in tickers:
            print(f"\n--- Running strategies for {ticker} ---")
            strat_results = run_strategies_for_ticker(ticker, om_config)
            per_ticker_results[ticker] = strat_results

            for strat_name, res in strat_results.items():
                print(f"\n[{ticker}] {strat_name} metrics")
                for k, v in res.final_metrics.items():
                    print(f"{k:20s}: {v}")

        portfolio_equities[portfolio_name] = aggregate_portfolio_equity(
            per_ticker_results=per_ticker_results,
            initial_equity=om_config.initial_capital,
        )

    plot_portfolio_equities(portfolio_equities)


if __name__ == "__main__":
    main()
