import pandas as pd

class Backtester:
    def __init__(self, strategy, broker):
        self.strategy = strategy
        self.broker = broker

    def run(self, prices: pd.Series) -> float:
        prices = pd.Series(prices, copy=False).astype(float)
        if prices.empty:
            return float(self.broker.cash)

        sig = self.strategy.signals(prices).fillna(0)

        # t-1 signal drives a trade at t
        for t in range(1, len(prices)):
            prev = int(sig.iloc[t - 1])
            px = float(prices.iloc[t])

            if prev == 1 and self.broker.position == 0:
                self.broker.market_order("BUY", 1, px)
            elif prev == -1 and self.broker.position > 0:
                self.broker.market_order("SELL", 1, px)
            # prev == 0 -> no action

        last = float(prices.iloc[-1])
        return float(self.broker.cash + self.broker.position * last)