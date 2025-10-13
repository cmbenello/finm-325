from src.data_loader import load_data, create_market_data_points
from src.models import Portfolio, PortfolioLog
from src.engine import ExecutionEngine
from src.strategies import NaiveMovingAverageStrategy, WindowedMovingAverageStrategy
from src.reporting import PerformanceAnalyzer

# Load generated data
data = create_market_data_points(load_data('data/assignment3_market_data.csv'))

print("created market data points")
# Initialize 2 portfolios
mean_rev_portfolio: PortfolioLog = []
NaiveMovingAverageStrategy_portfolio: PortfolioLog = []
failures_mean_rev_portfolio: PortfolioLog = []
failures_NaiveMovingAverageStrategy_portfolio: PortfolioLog = []

# Run 2 strategies for each tick
NaiveMovingAverageStrategy_engine = ExecutionEngine(strat=NaiveMovingAverageStrategy(
    short_window=20, long_window=50
), portfolio=Portfolio())

mean_rev_engine = ExecutionEngine(strat=WindowedMovingAverageStrategy(
    short_window=20, long_window=50),
    portfolio=Portfolio())
NaiveMovingAverageStrategy_engine.run_strategy(data, NaiveMovingAverageStrategy_portfolio)
print("finished with naive strategy")
mean_rev_engine.run_strategy(data, mean_rev_portfolio)
print("finished with windowed strategy")


# Call performance reporting on each model's portfolio history
# perf_analyzer = PerformanceAnalyzer()
# perf_analyzer.generate_performance_report(mean_rev_portfolio, strategy_name="Mean reversion",
#                                           chart_name="mean_rev_chart.png",
#                                           report_name="mean_rev_report.md")
# perf_analyzer.generate_performance_report(NaiveMovingAverageStrategy_portfolio, strategy_name="NaiveMovingAverageStrategy",
#                                           chart_name="NaiveMovingAverageStrategy_chart.png",
#                                           report_name="NaiveMovingAverageStrategy_report.md")
# perf_analyzer.generate_performance_report(failures_mean_rev_portfolio, strategy_name="Mean reversion with simulated failures",
#                                           chart_name="failures_mean_rev_chart.png",
#                                           report_name="failures_mean_rev_report.md")
# perf_analyzer.generate_performance_report(failures_NaiveMovingAverageStrategy_portfolio, strategy_name="NaiveMovingAverageStrategy with simulated failures",
#                                           chart_name="failures_NaiveMovingAverageStrategy_chart.png",
#                                           report_name="failures_NaiveMovingAverageStrategy_report.md")

# Save images in the `img` directory
