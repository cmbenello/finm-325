from src.PriceLoader import PriceLoader
from src.strategies.BenchmarkStrategy import Benchmark_Strategy


data_dir = "data/"
cash = 1_000_000

loader = PriceLoader("2005-01-01", "2025-01-01", data_dir)
tickers = loader.fetch_sp500_tickers()
print(len(tickers), tickers[:10])
# loader.batch_download(tickers=tickers)

bench_equities = Benchmark_Strategy(data_dir, cash).benchmark(0.05)
print(bench_equities.head())


