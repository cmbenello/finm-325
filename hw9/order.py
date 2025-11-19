from enum import Enum, auto

class OrderState(Enum):
    NEW = auto()
    ACKED = auto()
    FILLED = auto()
    CANCELED = auto()
    REJECTED = auto()

class Order:
    def __init__(self, symbol, qty, side):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.state = OrderState.NEW

    def transition(self, new_state):
        allowed = {
            OrderState.NEW: {OrderState.ACKED, OrderState.REJECTED},
            OrderState.ACKED: {OrderState.FILLED, OrderState.CANCELED},
        }

        if self.state in allowed and new_state in allowed[self.state]:
            self.state = new_state
            print(f"Order {self.symbol} is now {self.state.name}")
        else:
            print(f"Invalid transition from {self.state} to {new_state}")