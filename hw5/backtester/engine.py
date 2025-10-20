import pandas as pd

class Backtester:
    def __init__(self, strategy, broker):
        self.strategy = strategy
        self.broker = broker

    def run(self, prices: pd.Series) -> float:
        # Normalize/validate prices
        prices = pd.Series(prices, copy=False).astype(float)
        if prices.empty:
            return float(self.broker.cash)

        sig = self.strategy.signals(prices)

        prev_sig = sig.shift(1).fillna(0)

        for t in range(len(prices)):
            s = int(prev_sig.iloc[t])
            p = float(prices.iloc[t])

            if s > 0:
                # if flat, buy 1
                if self.broker.position == 0:
                    self.broker.market_order("BUY", 1, p)
            else:
                # if long, sell 1
                if self.broker.position > 0:
                    self.broker.market_order("SELL", 1, p)

        # Final mark-to-market equity
        last_price = float(prices.iloc[-1])
        equity = float(self.broker.cash + self.broker.position * last_price)
        return equity