class RiskEngine:
    def __init__(self, max_order_size=1000, max_position=2000):
        self.max_order_size = max_order_size
        self.max_position = max_position
        self.positions = {}

    def _signed_qty(self, order):
        side = str(order.side).upper()
        if side in {"1", "BUY"}:
            return order.qty
        elif side in {"2", "SELL"}:
            return -order.qty
        else:
            raise ValueError(f"unknown side: {order.side}")

    def check(self, order) -> bool:
        if order.qty <= 0:
            raise ValueError("order qty must be positive")
        if order.qty > self.max_order_size:
            msg = f"order size {order.qty} exceeds max {self.max_order_size}"
            raise ValueError(msg)

        sym = order.symbol
        current = self.positions.get(sym, 0)
        signed = self._signed_qty(order)
        new_pos = current + signed

        if abs(new_pos) > self.max_position:
            msg = (
                f"position limit exceeded for {sym}: "
                f"current {current}, new {new_pos}, limit {self.max_position}"
            )
            raise ValueError(msg)

        return True

    def update_position(self, order):
        sym = order.symbol
        signed = self._signed_qty(order)
        self.positions[sym] = self.positions.get(sym, 0) + signed
