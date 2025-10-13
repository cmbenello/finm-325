import math
import statistics
from typing import List
import matplotlib.pyplot as plt
from src.models import PortfolioSnapshot


class PerformanceAnalyzer:
    def __init__(self, risk_free_rate: float = 0.0366):
        #This is the current 1-year U.S. Treasury rate
        self.risk_free_rate = risk_free_rate
    
    
    def _calculate_total_return(self, initial_value: float, final_value: float) -> float:
        if initial_value <= 0:
            return 0.0
        return (final_value - initial_value) / initial_value


    def _calculate_returns(self, portfolio_values: List[PortfolioSnapshot]) -> List[float]:
        if len(portfolio_values) < 2:
            return []
        
        returns = []
        for i in range(1, len(portfolio_values)):
            prev_value = portfolio_values[i-1].portfolio_value
            curr_value = portfolio_values[i].portfolio_value
            
            if prev_value > 0:
                period_return = (curr_value - prev_value) / prev_value
                returns.append(period_return)
        
        return returns
    

    def _calculate_sharpe_ratio(self, returns: List[float], portfolio_values: List[PortfolioSnapshot]) -> float:
        if not returns or len(returns) < 2:
            return 0.0

        initial_value = portfolio_values[0].portfolio_value
        final_value = portfolio_values[-1].portfolio_value
        mean_return = self._calculate_total_return(initial_value=initial_value, final_value=final_value)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0

        if std_return == 0:
            return 0.0

        # Treat each period as a daily return, then annualize Sharpe ratio
        daily_risk_free_rate = self.risk_free_rate / 252
        daily_sharpe = (mean_return - daily_risk_free_rate) / std_return
        annualized_sharpe = daily_sharpe * math.sqrt(252)
        
        return annualized_sharpe

    
    
    def _calculate_maximum_drawdown(self, portfolio_values: List[PortfolioSnapshot]) -> float:
        if not portfolio_values:
            return 0.0
        
        values = [pv.portfolio_value for pv in portfolio_values]
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
        
        return max_dd
    

    def _plot_portfolio_value(self, portfolio_values: List[PortfolioSnapshot], 
                        strategy_name: str = "Strategy",
                        save_path: str = None) -> None:
    
        if not portfolio_values:
            print("No portfolio data to plot")
            return
    
        # Extract data
        timestamps = [pv.timestamp for pv in portfolio_values]
        values = [pv.portfolio_value for pv in portfolio_values]
    
        # Create the plot
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, values, 'b-', linewidth=2, label='Portfolio Value')
     
        # Customize the plot
        plt.title(strategy_name + " Portfolio Value Over Time", fontsize=14, fontweight='bold')
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Portfolio Value ($)', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
    
        # Format x-axis
        plt.xticks(rotation=45)
        plt.tight_layout()
    
        # Save if path provided
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
    

    def generate_performance_report(self, portfolio_values: List[PortfolioSnapshot], 
                                  strategy_name: str = "Strategy",
                                  output_path: str = './outputs/',
                                  chart_name: str = None,
                                  report_name: str = None) -> str:

        # Generate custom paths based on strategy name
        safe_strategy_name = strategy_name.lower().replace(' ', '_').replace('-', '_')
        if chart_name is None:
            chart_name = f"{output_path}{safe_strategy_name}_equity_chart.png"
        if report_name is None:
            report_name = f"{output_path}{safe_strategy_name}_performance_report.md"

        # Calculate all metrics
        initial_value = portfolio_values[0].portfolio_value
        final_value = portfolio_values[-1].portfolio_value
        total_return = self._calculate_total_return(initial_value, final_value)
        
        returns = self._calculate_returns(portfolio_values)
        sharpe_ratio = self._calculate_sharpe_ratio(returns, portfolio_values)
        max_drawdown = self._calculate_maximum_drawdown(portfolio_values)
        
        # Generate the chart
        self._plot_portfolio_value(portfolio_values, strategy_name, output_path + chart_name)
            
        # Generate the markdown content
        markdown_content = f"""# {strategy_name} - Performance Analysis Report

## Key Metrics

| Metric                | Value      |
|-----------------------|------------|
| Total Return          | {total_return:.2%}      |
| Sharpe Ratio          | {sharpe_ratio:.3f}      |
| Maximum Drawdown      | {max_drawdown:.2%}      |



---

## Equity Curve

Below is the equity curve for the strategy showing portfolio performance over time.

![Equity Curve]({chart_name})


## Narrative Interpretation of Results

The performance can be evaluated by examining the key metrics above. A total return of {total_return:.2%} indicates that the strategy {'was able to generate profits' if total_return > 0 else 'resulted in losses'} over the backtest period. The Sharpe ratio of {sharpe_ratio:.3f} measures the risk-adjusted return, with {'higher' if sharpe_ratio > 1 else 'lower'} values indicating {'better' if sharpe_ratio > 1 else 'poorer'} risk-reward tradeoffs. The maximum drawdown of {max_drawdown:.2%} highlights the largest observed loss from a peak to a trough, which is important for understanding potential downside risk.

In addition to these metrics, the strategy executed {len(portfolio_values)} data points over the backtest period. The equity curve above visually represents the growth of the portfolio over time, allowing for an assessment of the consistency and smoothness of returns.

Overall, interpreting these results involves balancing return and risk: a strategy with {'strong' if total_return > 0.1 else 'modest' if total_return > 0 else 'poor'} returns, a {'high' if sharpe_ratio > 1 else 'moderate' if sharpe_ratio > 0.5 else 'low'} Sharpe ratio, and {'manageable' if max_drawdown < 0.1 else 'significant'} drawdowns is generally considered {'robust' if sharpe_ratio > 0 else 'poor'}. However, it is also important to consider the market conditions during the backtest period when drawing conclusions about the strategy's effectiveness.
"""
        
        # Save the markdown file if output_path is provided
        if output_path:
            with open(output_path+report_name, 'w') as f:
                f.write(markdown_content)
            print(f"Performance report saved to: {output_path}")
        
        return markdown_content



