from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from statistics import quantiles
from typing import TypedDict, NamedTuple, Literal, Dict, Mapping
from enum import Enum

        
#Create order form signal and check status
# do unit tests wrap order creation is try/except
class OrderError(Exception): pass
class ExecutionError(Exception): pass

class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class MarketDataPoint:
    timestamp: datetime
    symbol: str
    price: float

@dataclass
class Order:
    # public, printed fields (no defaults before defaults)
    symbol: str
    quantity: int
    price: float
    action: Action
    status: Literal["NEW", "FILLED", "REJECTED"] = "NEW"

    # private backing fields (not in __init__, not printed)
    _quantity: int = field(init=False, repr=False)
    _price: float = field(init=False, repr=False)

    def __post_init__(self):
        if self.quantity < 0:
            raise OrderError(f"Order quantity is negative: quantity={self.quantity}")
        if self.price < 0:
            raise OrderError(f"Order price is negative: price={self.price}")
        if self.action not in (Action.BUY, Action.SELL):
            raise OrderError(f"Action not defined: self.action={self.action}")

    def _validate_action(self) -> None:
        if self.action not in (Action.BUY, Action.SELL, Action.HOLD):
            raise OrderError("invalid action")


    def validate(self) -> None:
        # Called by Portfolio.apply_fill; 
        if self.quantity <= 0:
            raise OrderError(f"Order quantity is non-positive: self.quantity={self.quantity}")
        if self.price <= 0:
            raise OrderError(f"Order price is non-positive: self.price={self.price}")
        self._validate_action()


class Portfolio:
    """
    Tracks cash and per-symbol positions.
    Positions are stored as:
       positions[symbol] = {"quantity": int (signed), "avg_price": float}
    Long  => quantity > 0
    Short => quantity < 0
    """
    def __init__(self, cash: float = 10_000.0):
        self.cash: float = cash
        self.positions: Position = {}

    def _ensure_pos(self, symbol: str) -> Dict[str, float]:
        if symbol not in self.positions:
            self.positions[symbol] = {"quantity": 0, "avg_price": 0.0}
        return self.positions[symbol]

    def apply_fill(self, order: Order) -> None:
        """
        Apply an already validated executable order at its price.
        BUY  → cash -= qty * px, quantity += qty
        SELL → cash += qty * px, quantity -= qty

        Avg price rules:
          - Adding in same direction: VWAP blend
          - Reducing exposure: keep avg_price unchanged
          - Flat-out (qty -> 0): avg_price = 0.0
          - Flip side: avg_price = fill price (fresh entry)
        """
        # order.validate() # moved validation to Order __post_init__
        pos = self._ensure_pos(order.symbol)

        qty = order.quantity
        px = order.price
        q0 = int(pos["quantity"])
        p0 = float(pos["avg_price"])

        # Cash update
        notional = qty * px
        if order.action == Action.BUY:
            self.cash -= notional
            delta = qty               # signed +qty
        else:  # SELL
            self.cash += notional
            delta = -qty              # signed -qty

        q1 = q0 + delta  # new signed quantity

        # Determine new avg price
        if q0 == 0:
            # Fresh entry (unless q1==0 which would be bizarre here)
            new_avg = px if q1 != 0 else 0.0
        elif (q0 > 0 and delta > 0) or (q0 < 0 and delta < 0):
            # Adding exposure in the same direction → blend VWAP
            new_avg = (abs(q0) * p0 + abs(delta) * px) / (abs(q0) + abs(delta))
        else:
            # Reducing or flipping
            if abs(delta) < abs(q0):
                # Partial close → keep avg unchanged
                new_avg = p0
            elif abs(delta) == abs(q0):
                # Flat-out → reset avg
                new_avg = 0.0
            else:
                # Flip side → new side starts at fill price
                new_avg = px

        # Commit state
        pos["quantity"] = q1
        pos["avg_price"] = new_avg
        order.status = "FILLED"

    def market_value(self, last_prices: MarketDataPoint) -> float:
        total = 0.0
        for _, pos in self.positions.items():
            px = last_prices.price
            if px is not None:
                total += pos["quantity"] * px
        return total
    
    def total_equity(self, last_prices: MarketDataPoint) -> float:
        return self.cash + self.market_value(last_prices)
    

    def market_value_map(self, price_map: Mapping[str, float]) -> float:
        """
        Mark the book using a per-symbol price map.
        Symbols missing from the map are ignored (conservative).
        """
        total = 0.0
        for sym, pos in self.positions.items():
            px = price_map.get(sym)
            if px is not None:
                total += pos["quantity"] * float(px)
        return total

    def total_equity_map(self, price_map: Mapping[str, float]) -> float:
        return self.cash + self.market_value_map(price_map)


class MetricsDict(TypedDict):
    quantity: int
    avg_price: float
    
class Position(TypedDict):
    symbol: MetricsDict

class Signal(NamedTuple):
    """Signal tuple for more explicit use of signal data
    """
    action: Action
    symbol: str
    qty: int
    price: float

@dataclass(frozen=True)
class PortfolioSnapshot:
    timestamp: datetime
    price: float
    portfolio_value: float
    position: Position

PortfolioLog = list[PortfolioSnapshot]

class AnalyticsSubject:
    """
    Provides a stable .get_metrics() and a .symbol attribute.
    """
    def __init__(self, symbol: str):
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("symbol must be a non-empty string")
        self.symbol = symbol

    def get_metrics(self) -> Dict[str, float]:
        return {"symbol": self.symbol}