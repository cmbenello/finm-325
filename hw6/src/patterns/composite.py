from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Iterable, Optional
from pathlib import Path
import json


class PortfolioComponent(ABC):
    @abstractmethod
    def get_value(self) -> float:
        """Aggregate market value for this node (recursively for composites)."""
        

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Flattened list of leaf position dicts under this node."""



@dataclass(frozen=True)
class Position(PortfolioComponent):
    symbol: str
    quantity: float
    price: float

    def get_value(self) -> float:
        return float(self.quantity) * float(self.price)

    def get_positions(self) -> List[Dict[str, Any]]:
        return [{"symbol": self.symbol,
                 "quantity": float(self.quantity),
                 "price": float(self.price)}]


# ---------- Composite node ----------

class PortfolioGroup(PortfolioComponent):
    def __init__(self, name: str):
        self.name = name
        self._children: List[PortfolioComponent] = []

    def add(self, comp: PortfolioComponent) -> None:
        self._children.append(comp)

    def extend(self, comps: Iterable[PortfolioComponent]) -> None:
        self._children.extend(comps)

    def get_value(self) -> float:
        return sum(c.get_value() for c in self._children)

    def get_positions(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for c in self._children:
            out.extend(c.get_positions())
        return out

    def __repr__(self) -> str:
        return f"PortfolioGroup(name={self.name!r}, children={len(self._children)})"


@dataclass(frozen=True)
class Portfolio:
    root: PortfolioGroup
    owner: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def value(self) -> float:
        return self.root.get_value()

    def positions(self) -> List[Dict[str, Any]]:
        return self.root.get_positions()


def load_portfolio_from_json(path: str | Path) -> Portfolio:
    """
    Loads a portfolio tree from JSON with this schema:

    {
      "name": "Main Portfolio",
      "owner": "sdonadio",
      "positions": [
        {"symbol": "AAPL", "quantity": 100, "price": 172.35},
        {"symbol": "MSFT", "quantity": 50, "price": 328.10}
      ],
      "sub_portfolios": [
        {
          "name": "Index Holdings",
          "positions": [
            {"symbol": "SPY", "quantity": 20, "price": 430.50}
          ]
        }
      ]
    }
    """
    meta = json.loads(Path(path).read_text())

    def build_group(node: Dict[str, Any]) -> PortfolioGroup:
        g = PortfolioGroup(node["name"])
        # Add this group's positions
        for p in node.get("positions", []):
            g.add(Position(p["symbol"], float(p["quantity"]), float(p["price"])))
        # Recurse through sub-portfolios
        for child in node.get("sub_portfolios", []):
            g.add(build_group(child))
        return g

    root_group = build_group(meta)
    return Portfolio(root=root_group, owner=meta.get("owner"))


def pretty_print(portfolio: Portfolio) -> str:
    lines: List[str] = []
    lines.append(f"Owner: {portfolio.owner}")
    lines.append(f"Total value: {portfolio.value():,.2f}")
    lines.append("Tree:")

    def rec(node: PortfolioComponent, depth: int = 0, name: Optional[str] = None):
        indent = "  " * depth
        if isinstance(node, Position):
            lines.append(f"{indent}- {node.symbol}: qty={node.quantity}, "
                         f"px={node.price}, value={node.get_value():,.2f}")
        elif isinstance(node, PortfolioGroup):
            nm = node.name if name is None else name
            lines.append(f"{indent}{nm} (group) value={node.get_value():,.2f}")
            for child in node._children:
                rec(child, depth + 1)
        else:
            lines.append(f"{indent}? Unknown node")

    rec(portfolio.root, 0, portfolio.root.name)
    return "\n".join(lines)