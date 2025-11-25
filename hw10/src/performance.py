# src/performance.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


@dataclass
class PerformanceAnalyzer:
    """
    Provides methods to compute performance statistics and simple plots
    for an equity curve and position time series.
    """

    @staticmethod
    def compute_metrics(
        equity: pd.Series,
        position: pd.Series,
        close_prices: pd.Series,
    ) -> Dict[str, Any]:
        """
        Compute basic metrics:
          - Total P&L
          - Total return
          - Annualized Sharpe (approximate, using bar returns)
          - Max drawdown
          - Win ratio (fraction of bars where position * return > 0)
        """
        equity = equity.sort_index()
        position = position.sort_index()
        close_prices = close_prices.sort_index()

        initial_equity = equity.iloc[0]
        final_equity = equity.iloc[-1]
        total_pnl = final_equity - initial_equity
        total_return = final_equity / initial_equity - 1.0

        # Bar returns from equity
        bar_returns = equity.pct_change().dropna()

        # Approximate bars-per-year (1-min bars, ~390 min/day, 252 days/year)
        bars_per_year = 252 * 390
        if bar_returns.std(ddof=1) > 0:
            sharpe = (
                np.sqrt(bars_per_year)
                * bar_returns.mean()
                / bar_returns.std(ddof=1)
            )
        else:
            sharpe = np.nan

        # Max drawdown
        running_max = equity.cummax()
        drawdown = equity / running_max - 1.0
        max_drawdown = drawdown.min()

        # Bar-level win ratio: position * price_return
        price_returns = close_prices.pct_change().reindex(position.index).fillna(0.0)
        directional_pnl = position * price_returns

        wins = (directional_pnl > 0).sum()
        losses = (directional_pnl < 0).sum()
        win_ratio = wins / (wins + losses) if (wins + losses) > 0 else np.nan

        return {
            "initial_equity": float(initial_equity),
            "final_equity": float(final_equity),
            "total_pnl": float(total_pnl),
            "total_return": float(total_return),
            "sharpe_annualized": float(sharpe) if not np.isnan(sharpe) else np.nan,
            "max_drawdown": float(max_drawdown),
            "win_ratio": float(win_ratio) if not np.isnan(win_ratio) else np.nan,
        }

    # ---------- OLD SIMPLE PLOTS (still available if you want them) ----------

    @staticmethod
    def plot_equity_curve(equity: pd.Series) -> None:
        """
        Plot the equity curve over time.
        """
        plt.figure()
        equity.sort_index().plot()
        plt.title("Equity Curve")
        plt.xlabel("Time")
        plt.ylabel("Equity")
        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_position(position: pd.Series) -> None:
        """
        Plot position over time.
        """
        plt.figure()
        position.sort_index().plot()
        plt.title("Position Over Time")
        plt.xlabel("Time")
        plt.ylabel("Position")
        plt.tight_layout()
        plt.show()

    # ---------- NEW: RANDOM STRATEGIES + BUY-AND-HOLD BENCHMARK ----------

    @staticmethod
    def _generate_random_equity_paths(
        initial_equity: float,
        close_prices: pd.Series,
        n_paths: int = 200,
    ) -> (pd.DataFrame, pd.Series):
        """
        Generate n_paths random strategies.

        Each random strategy:
          - Holds a position in {-1, 0, +1}
          - Changes that position at *random intervals* with some per-bar
            probability (change_prob), independent of your strategy.
        """

        prices = close_prices.sort_index()
        times = prices.index

        # Price returns (bar-to-bar)
        rets = prices.pct_change().fillna(0.0).to_numpy()
        T = len(rets)

        # Random exposures: shape (T, n_paths)
        exposures = np.zeros((T, n_paths), dtype=float)

        # Probability of changing position on a given bar.
        # Use a relatively high probability so random strategies trade
        # frequently and independently of the main MA crossover strategy.
        change_prob = 0.2  # 20% chance per bar to pick a new position

        # Build piecewise-constant random exposure paths
        for j in range(n_paths):
            state = float(np.random.choice([-1, 0, 1]))  # random initial state
            for t in range(T):
                if np.random.rand() < change_prob:
                    # pick a new state in {-1, 0, +1}
                    state = float(np.random.choice([-1, 0, 1]))
                exposures[t, j] = state

        # Equity paths: shape (T, n_paths)
        eq = np.zeros((T, n_paths), dtype=float)
        eq[0, :] = initial_equity

        for t in range(1, T):
            # equity_t = equity_{t-1} * (1 + exposure_{t-1} * return_t)
            eq[t, :] = eq[t - 1, :] * (1.0 + exposures[t - 1, :] * rets[t])

        random_equity = pd.DataFrame(
            eq,
            index=times,
            columns=[f"path_{i}" for i in range(n_paths)],
        )

        # Buy and hold: invest all capital at first price
        first_price = prices.iloc[0]
        shares = initial_equity / first_price
        buy_and_hold = shares * prices
        buy_and_hold.name = "buy_and_hold"

        return random_equity, buy_and_hold
    @staticmethod
    def plot_equity_vs_random_and_bh(
        strategy_equity: pd.Series,
        close_prices: pd.Series,
        n_random: int = 200,
    ) -> None:
        """
        Plot:
          - Many faint random-strategy equity curves
          - 2σ and 3σ bands from their distribution
          - Buy-and-hold equity curve
          - Strategy equity curve (bold and clearly visible)
        """
        strategy_equity = strategy_equity.sort_index()
        close_prices = close_prices.sort_index()
        close_prices = close_prices.reindex(strategy_equity.index).ffill()

        initial_equity = float(strategy_equity.iloc[0])

        random_equity, buy_and_hold = PerformanceAnalyzer._generate_random_equity_paths(
            initial_equity=initial_equity,
            close_prices=close_prices,
            n_paths=n_random,
        )

        # Align everything to the same index
        idx = strategy_equity.index
        random_equity = random_equity.reindex(idx).ffill()
        buy_and_hold = buy_and_hold.reindex(idx).ffill()

        # Compute mean/std over random paths at each time
        rand_vals = random_equity.to_numpy()
        mean_rand = rand_vals.mean(axis=1)
        std_rand = rand_vals.std(axis=1, ddof=1)

        mean_rand_s = pd.Series(mean_rand, index=idx)
        band_2_up = mean_rand_s + 2 * std_rand
        band_2_dn = mean_rand_s - 2 * std_rand
        band_3_up = mean_rand_s + 3 * std_rand
        band_3_dn = mean_rand_s - 3 * std_rand

        # ---- Plot ----
        fig, ax = plt.subplots()

        # Faint random paths
        for col in random_equity.columns:
            ax.plot(
                idx,
                random_equity[col],
                color="gray",
                alpha=0.05,
                linewidth=0.5,
            )

        # 2σ and 3σ bands (slightly more visible but still not dominant)
        ax.plot(idx, band_2_up, linestyle="--", linewidth=1.0, alpha=0.6, label="+2σ random")
        ax.plot(idx, band_2_dn, linestyle="--", linewidth=1.0, alpha=0.6, label="-2σ random")
        ax.plot(idx, band_3_up, linestyle=":", linewidth=1.0, alpha=0.6, label="+3σ random")
        ax.plot(idx, band_3_dn, linestyle=":", linewidth=1.0, alpha=0.6, label="-3σ random")

        # Buy-and-hold
        ax.plot(
            idx,
            buy_and_hold,
            linewidth=2.0,
            label="Buy & Hold",
        )

        # Strategy equity (main thing, must stand out)
        ax.plot(
            idx,
            strategy_equity,
            linewidth=2.5,
            label="Strategy",
        )

        ax.set_title("Strategy vs Buy & Hold vs Random Strategies")
        ax.set_xlabel("Time")
        ax.set_ylabel("Equity")

        ax.legend()
        plt.tight_layout()
        plt.show()