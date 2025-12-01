# src/run_alpaca_paper.py

from .alpaca_trader import AlpacaPortfolioTrader, PortfolioLegConfig
from .strategy import (
    AggressiveMomentumStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    VWAPReversionStrategy,
)


def main():
    """
    Portfolio: BTCUSD short, NVDA overweight long, MRNA short, TQQQ long.
    Net short tilt (55% short, 45% long) with extra weight on NVDA and a
    smaller BTC short sleeve.
    Allocations are sized off account equity (e.g., 0.40 = 40% of equity).
    """
    portfolio = [
        PortfolioLegConfig(
            symbol="BTC/USD",
            allocation=0.20,
            strategies=[
                AggressiveMomentumStrategy(short_window=5, long_window=20),
                VWAPReversionStrategy(lookback=30, z_entry=1.0),
            ],
            asset_type="crypto",
            feed="us",
            lookback_bars=720,
            short_only=True,
        ),
        PortfolioLegConfig(
            symbol="NVDA",
            allocation=0.35,
            strategies=[
                AggressiveMomentumStrategy(short_window=5, long_window=20),
                VWAPReversionStrategy(lookback=30, z_entry=1.0),
            ],
            asset_type="equity",
            feed="iex",
            lookback_bars=720,
            long_only=True,
        ),
        PortfolioLegConfig(
            symbol="MRNA",
            allocation=0.35,
            strategies=[
                MeanReversionStrategy(lookback=20, z_entry=1.0),
            ],
            asset_type="equity",
            feed="iex",
            lookback_bars=720,
            short_only=True,
        ),
        PortfolioLegConfig(
            symbol="TQQQ",
            allocation=0.10,
            strategies=[
                MomentumStrategy(),
                VWAPReversionStrategy(lookback=30, z_entry=1.1),
            ],
            asset_type="equity",
            feed="iex",
            lookback_bars=720,
            long_only=True,
        ),
    ]

    trader = AlpacaPortfolioTrader(
        legs=portfolio,
        timeframe="1Min",
        poll_interval_sec=60,
        min_trade_notional=25.0,
    )
    trader.run()


if __name__ == "__main__":
    main()
