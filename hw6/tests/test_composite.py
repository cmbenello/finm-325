import os
import pytest
from src.patterns.composite import (
    Portfolio, PortfolioGroup, Position,
    load_portfolio_from_json, pretty_print
)

def test_composite_demo_from_configs():
    """
    Demonstrates recursive aggregation from configs/portfolio_structure.json.
    Run with: pytest -s tests/test_composite.py::test_composite_demo_from_configs
    """
    path = "configs/portfolio_structure.json"
    if not os.path.exists(path):
        pytest.skip("configs/portfolio_structure.json not found; demo skipped")

    portfolio = load_portfolio_from_json(path)

    print("\n=== Composite Pattern Demonstration ===")
    print(pretty_print(portfolio))

    # Minimal sanity checks to keep test green
    assert isinstance(portfolio, Portfolio)
    assert isinstance(portfolio.root, PortfolioGroup)
    assert len(portfolio.positions()) >= 1
    assert portfolio.value() >= 0.0


def test_manual_recursive_aggregation():
    """
    Pure unit test: builds a small tree in code to verify aggregation correctness.
    """
    main = PortfolioGroup("Main")
    main.add(Position("AAPL", 10, 190.0))      # 1900

    tech = PortfolioGroup("Tech")
    tech.add(Position("MSFT", 5, 420.0))       # 2100
    tech.add(Position("NVDA", 3, 900.0))       # 2700
    main.add(tech)

    rates = PortfolioGroup("Rates")
    rates.add(Position("T10", 100, 0.95))      # 95
    main.add(rates)

    port = Portfolio(root=main, owner="Bob", metadata={"currency": "USD"})

    assert abs(port.value() - (1900 + 2100 + 2700 + 95)) < 1e-9
    syms = {p["symbol"] for p in port.positions()}
    assert syms == {"AAPL", "MSFT", "NVDA", "T10"}