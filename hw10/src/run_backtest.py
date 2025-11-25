# src/run_backtest.py

from .backtester import Backtester
from .performance import PerformanceAnalyzer


def main():
    bt = Backtester()
    result = bt.run()

    print("=== Backtest Summary ===")
    for k, v in result.final_metrics.items():
        print(f"{k:20s}: {v}")

    print("\nLast 5 points of equity curve:")
    print(result.equity_curve.tail())

    print("\nNumber of trades:", len(result.trades))
    if not result.trades.empty:
        print("Sample trades:")
        print(result.trades.head())

    # ---- New: plot curves vs random + buy-and-hold ----
    PerformanceAnalyzer.plot_equity_vs_random_and_bh(
        strategy_equity=result.equity_curve,
        close_prices=result.close_prices,
        n_random=200,   # adjust if you want more/less random paths
    )


if __name__ == "__main__":
    main()