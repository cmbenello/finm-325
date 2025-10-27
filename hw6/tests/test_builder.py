# tests/test_builder.py
import json
import math
import pytest
from src.patterns.builder import PortfolioBuilder, Portfolio

def almost_eq(a, b, eps=1e-9):
    return abs(a - b) < eps

# 1) Basic fluent build + value/positions/owner
def test_builder_basic_chain():
    pb = (PortfolioBuilder("Main")
          .set_owner("Alice")
          .add_position("AAPL", 10, 190.0)
          .add_position("SPY", 2, 500.0))
    port = pb.build()

    assert isinstance(port, Portfolio)
    assert port.owner == "Alice"
    assert almost_eq(port.value(), 10*190.0 + 2*500.0)

    syms = {p["symbol"] for p in port.positions()}
    assert syms == {"AAPL", "SPY"}

# 2) Nested subportfolio via add_subportfolio(name, builder)
def test_builder_with_subportfolio():
    tech = (PortfolioBuilder("Tech")
            .add_position("MSFT", 5, 420.0)
            .add_position("NVDA", 3, 900.0))

    root = (PortfolioBuilder("Main")
            .set_owner("Bob")
            .add_position("AAPL", 10, 190.0)
            .add_subportfolio("Tech", tech))

    port = root.build()
    assert port.owner == "Bob"
    expected = 10*190.0 + 5*420.0 + 3*900.0
    assert almost_eq(port.value(), expected)

    syms = {p["symbol"] for p in port.positions()}
    assert syms == {"AAPL", "MSFT", "NVDA"}

# 3) add_subportfolio requires a PortfolioBuilder
def test_add_subportfolio_typecheck():
    root = PortfolioBuilder("Main")
    with pytest.raises(TypeError):
        root.add_subportfolio("Bad", builder="not a builder")  # type: ignore

# 4) Builder is single-use; add/ build again should fail
def test_builder_single_use():
    pb = PortfolioBuilder("Main").add_position("AAPL", 1, 100.0)
    port = pb.build()
    assert isinstance(port, Portfolio)

    with pytest.raises(RuntimeError):
        pb.add_position("MSFT", 1, 1.0)

    with pytest.raises(RuntimeError):
        pb.build()

# 5) From JSON demo: structure, value, positions, owner
def test_from_json_build(tmp_path):
    data = {
        "owner": "Amit",
        "metadata": {"currency": "USD"},
        "root": {
            "name": "Main",
            "positions": [
                {"symbol": "AAPL", "quantity": 10, "price": 190.0}
            ],
            "children": [
                {
                    "name": "Tech",
                    "positions": [
                        {"symbol": "MSFT", "quantity": 5, "price": 420.0}
                    ],
                    "children": []
                },
                {
                    "name": "Rates",
                    "positions": [
                        {"symbol": "T10", "quantity": 100, "price": 0.95}
                    ],
                    "children": []
                }
            ]
        }
    }
    p = tmp_path / "portfolio_structure.json"
    p.write_text(json.dumps(data))

    port = PortfolioBuilder.from_json(str(p))
    assert isinstance(port, Portfolio)
    assert port.owner == "Amit"

    expected = 10*190.0 + 5*420.0 + 100*0.95
    assert almost_eq(port.value(), expected)

    syms = {pos["symbol"] for pos in port.positions()}
    assert syms == {"AAPL", "MSFT", "T10"}

# 6) Empty portfolio edge case
def test_empty_portfolio_value_zero():
    pb = PortfolioBuilder("Empty")
    port = pb.build()
    assert almost_eq(port.value(), 0.0)
    assert port.positions() == []