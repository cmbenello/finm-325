import pandas as pd 
from pathlib import Path

class Benchmark_Strategy():
    def __init__(self, root_dir: str, cash: float):
        self.cash = cash
        self.root_dir = root_dir

    def _initial_orders(self, pro: float) -> pd.DataFrame:
        root = Path(self.root_dir)
        files = sorted(root.glob("*.parquet"))
        # collect first valid price/volume for each ticker
        rows = []
        for f in files:
            t = f.stem
            df = pd.read_parquet(f)
            vol_col = "Volume" if "Volume" in df.columns else None
            px_col  = "Adj Close" if "Adj Close" in df.columns else ("Close" if "Close" in df.columns else None)
            if not vol_col or not px_col: 
                continue
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.sort_values("Date")
            else:
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
            fv = df[[vol_col, px_col]].dropna().iloc[0]  # first valid row
            vol0, px0 = float(fv[vol_col]), float(fv[px_col])
            if vol0 > 0 and px0 > 0:
                rows.append((t, vol0, px0))

        if not rows:
            return pd.DataFrame([{}])

        N = len(rows)
        dollars_per_name = self.cash / N

        shares = {}
        cash_left = self.cash
        for t, vol0, px0 in rows:
            q_part = int(pro * vol0)
            q_cash_bucket = int(dollars_per_name // px0)
            q = max(0, min(q_part, q_cash_bucket))
            shares[t] = q
            cash_left -= q * px0

        self._bench_cash_left = max(0.0, cash_left)
        return pd.DataFrame([shares])


    def _value_over_time(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        root = Path(self.root_dir)
        files = {f.stem: f for f in root.glob("*.parquet")}

        shares = orders_df.iloc[0].dropna().astype("int64")
        tickers = [t for t in shares.index if t in files and shares[t] > 0]
        if not tickers:
            return pd.DataFrame(columns=["total"])

        series = {}
        for t in tickers:
            df = pd.read_parquet(files[t])

            price_col = "Adj Close" if "Adj Close" in df.columns else ("Close" if "Close" in df.columns else None)
            if price_col is None:
                continue

            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.sort_values("Date").set_index("Date")
            else:
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()

            s = df[price_col].astype("float64")
            s.name = t
            series[t] = s

        if not series:
            return pd.DataFrame(columns=["total"])

        prices_wide = pd.concat(series, axis=1).sort_index().fillna(0.0)
        values_wide = prices_wide.mul(shares, axis=1)

        # add constant leftover cash to the daily total
        cash_left = getattr(self, "_bench_cash_left", 0.0)
        values_wide["total"] = values_wide.sum(axis=1) + float(cash_left)

        return values_wide

    def benchmark(self, pro: float) -> pd.DataFrame:
        orders = self._initial_orders(pro)
        equity = self._value_over_time(orders)
        return equity


