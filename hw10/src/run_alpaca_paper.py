# src/run_alpaca_paper.py

from .alpaca_trader import AlpacaPaperTrader


def main():
    trader = AlpacaPaperTrader(
        symbol="AAPL",
        timeframe="1Min",
        lookback_bars=500,
        target_position_size=10,
        poll_interval_sec=60,
    )
    trader.run()


if __name__ == "__main__":
    main()