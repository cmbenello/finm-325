# Assignment 5: Testing and Continuous Integration in Financial Engineering

## Project Overview

This project implements a minimal daily-bar backtester for financial strategies, focusing on engineering discipline through unit testing, coverage measurement, and continuous integration (CI). The backtester includes components for price loading, strategy signal generation, order execution via a broker, and an engine to run the backtest. The primary goal is to develop reliable, testable code with high coverage rather than maximizing trading performance.

## Design Notes

- **PriceLoader:** Returns synthetic `pandas.Series` price data for a single symbol to ensure deterministic tests without network dependencies.
- **VolatilityBreakoutStrategy:** Generates daily signals based on a rolling standard deviation of returns. Buys when the current return exceeds the x-day volatility threshold.
- **Broker:** Processes market orders without slippage or fees, updates cash and position, and enforces constraints such as sufficient cash or shares.
- **Backtester Engine:** Runs an end-of-day loop that computes signals with a one-day lag, executes trades at close prices, and tracks portfolio equity over time.

Tests are designed to be fast (<60 seconds), deterministic, and isolated from external systems by using mocks and synthetic data. Coverage is enforced to be ≥90% to ensure thorough testing.

## Running Tests

To run the tests locally, use:

```bash
pip install -r requirements.txt
pytest -q
```

For coverage measurement and reporting:

```bash
coverage run -m pytest -q
coverage report -m --fail-under=90
coverage html  # optional, generates an HTML coverage report in htmlcov/
```

Tests cover strategy logic, broker behavior, engine execution, edge cases (empty data, NaNs, short series), and failure handling through mocks.

## Continuous Integration Workflow

The project uses GitHub Actions for CI with the following workflow configuration (`.github/workflows/ci.yml`):

```yaml
name: CI Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: coverage run -m pytest -q
      - run: coverage report --fail-under=90
```

This pipeline runs tests and enforces coverage thresholds on every push and pull request, ensuring code quality and preventing regressions.

## Coverage Summary

- Target coverage: ≥90% lines covered (branch coverage optional)
- Coverage failures cause CI to fail, maintaining high test quality
- Coverage badges can be added for visualization (optional)

By adhering to these standards, the project maintains a robust, maintainable codebase with reliable testing and continuous integration practices.
