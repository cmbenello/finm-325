class Broker:
    def __init__(self, cash: float = 1_000_000):
        if cash < 0:
            raise ValueError("Initial cash must be non-negative.")
        self.cash = float(cash)
        self.position = 0 

    def market_order(self, side: str, qty: int, price: float):
        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Invalid order side: {side}. Must be 'BUY' or 'SELL'.")
        if qty <= 0:
            raise ValueError("Quantity must be positive.")
        if price <= 0:
            raise ValueError("Price must be positive.")

        cost = qty * price

        # Execute trade
        if side == "BUY":
            if cost > self.cash: 
                raise ValueError("Insufficient cash to execute BUY order.")
            self.cash -= cost
            self.position += qty

        elif side == "SELL":
            if qty > self.position:
                raise ValueError("Insufficient shares to execute SELL order.")
            self.cash += cost
            self.position -= qty