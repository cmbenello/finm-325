from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json

class PortfolioComponent:
    def get_value(self) -> float: raise NotImplementedError
    def get_positions(self) -> List[dict]: raise NotImplementedError

@dataclass(frozen=True)
class Position(PortfolioComponent):
    symbol: str
    quantity: float
    price: float
    def get_value(self) -> float:
        return float(self.quantity) * float(self.price)
    def get_positions(self) -> List[dict]:
        return [{"symbol": self.symbol, "quantity": float(self.quantity), "price": float(self.price)}]

class PortfolioGroup(PortfolioComponent):
    def __init__(self, name: str):
        self.name = name
        self._children: List[PortfolioComponent] = []
    def add(self, comp: PortfolioComponent) -> None:
        self._children.append(comp)
    def get_value(self) -> float:
        return sum(c.get_value() for c in self._children)
    def get_positions(self) -> List[dict]:
        out: List[dict] = []
        for c in self._children:
            out.extend(c.get_positions())
        return out

@dataclass(frozen=True)
class Portfolio:
    root: PortfolioGroup
    owner: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    def value(self) -> float:
        return self.root.get_value()
    def positions(self) -> List[dict]:
        return self.root.get_positions()

class PortfolioBuilder:
    """
    Fluent builder for complex portfolios with nested positions and metadata.

    Required fluent API:
      - add_position(symbol, quantity, price)
      - set_owner(name)
      - add_subportfolio(name, builder)   # accepts a child builder
      - build() -> Portfolio
    """

    def __init__(self, name: str):
        self._root = PortfolioGroup(name)
        self._owner: Optional[str] = None
        self._metadata: Dict[str, Any] = {}
        self._built = False

    # ---- fluent methods (spec) ----
    def add_position(self, symbol: str, quantity: float, price: float) -> "PortfolioBuilder":
        self._ensure_not_built()
        self._root.add(Position(symbol, quantity, price))
        return self

    def set_owner(self, name: str) -> "PortfolioBuilder":
        self._ensure_not_built()
        self._owner = name
        return self

    def add_subportfolio(self, name: str, builder: "PortfolioBuilder") -> "PortfolioBuilder":
        """
        Add an already-configured subportfolio built by another PortfolioBuilder.
        """
        self._ensure_not_built()
        if not isinstance(builder, PortfolioBuilder):
            raise TypeError("builder must be a PortfolioBuilder")
        # finalize the child if not built yet
        child_port = builder.build() if not builder._built else builder._final_port
        # attach the child's root group under this root
        self._root.add(child_port.root)
        return self

    def build(self) -> Portfolio:
        self._ensure_not_built()
        self._final_port = Portfolio(self._root, self._owner, dict(self._metadata) or None)
        self._built = True
        return self._final_port

    def set_metadata(self, **kv) -> "PortfolioBuilder":
        self._ensure_not_built()
        self._metadata.update(kv)
        return self

    def _ensure_not_built(self):
        if self._built:
            raise RuntimeError("This PortfolioBuilder has already built a Portfolio.")

    @staticmethod
    def from_json(path: str) -> Portfolio:
        """
        Expected schema in portfolio_structure.json:

        {
          "owner": "Alice",
          "metadata": {"currency":"USD"},
          "root": {
            "name": "Main",
            "positions": [
              {"symbol":"AAPL","quantity":10,"price":190.0}
            ],
            "children": [
              {
                "name":"Tech",
                "positions":[{"symbol":"MSFT","quantity":5,"price":420.0}],
                "children":[]
              }
            ]
          }
        }
        """
        meta = json.loads(open(path, "r").read())

        def build_node(node: dict) -> PortfolioBuilder:
            pb = PortfolioBuilder(node["name"])
            for p in node.get("positions", []):
                pb.add_position(p["symbol"], float(p["quantity"]), float(p["price"]))
            for child in node.get("children", []):
                child_builder = build_node(child)
                pb.add_subportfolio(child["name"], child_builder)
            return pb

        root_node = meta["root"]
        root_builder = build_node(root_node)

        if "owner" in meta:
            root_builder.set_owner(meta["owner"])
        if "metadata" in meta:
            root_builder.set_metadata(**meta["metadata"])

        return root_builder.build()