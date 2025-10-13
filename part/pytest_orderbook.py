import pytest

class Order:
    def __init__(self,price,side):
        self.price = price
        self.side = side


class OrderBook:
    def __init__(self):
        self.bids = []
        self.asks = []

    def add_order(self, order):
        if order.side == 'bid':
            self.bids.append(order)
            self.bids=sorted(self.bids, key=lambda order: order.price)
        else:
            self.asks.append(order)
            self.asks = sorted(self.asks, key=lambda order: order.price, reverse=True)

    def display_orders(self):
        print('Bids:')
        for order in self.bids:
            print(order.price,order.side)
        print('Asks:')
        for order in self.asks:
            print(order.price,order.side)

is_bids_sorted = lambda ob: all(
    (ob.bids if hasattr(ob, "bids") else ob)[i].price <=
    (ob.bids if hasattr(ob, "bids") else ob)[i + 1].price
    for i in range(len(ob.bids if hasattr(ob, "bids") else ob) - 1)
)

class TestOrderBook():

    def test_add_sorted(self):
        ob1 = OrderBook()
        ob1.add_order(Order(100,'ask'))
        assert(is_bids_sorted(ob1))
        assert(len(ob1.asks) == 1)
        ob1.add_order(Order(120,'ask'))
        assert(is_bids_sorted(ob1))
        assert(len(ob1.asks) == 2)
        ob1.add_order(Order(40, 'ask'))
        assert(is_bids_sorted(ob1))
        assert(len(ob1.asks) == 3)


    def test_bids_sorted(self):
        ob2 = OrderBook()
        ob2.add_order(Order(100,'bid'))
        assert(is_bids_sorted(ob2))
        assert(len(ob2.bids) == 1)
        ob2.add_order(Order(120,'bid'))
        assert(is_bids_sorted(ob2))
        assert(len(ob2.bids) == 2)
        ob2.add_order(Order(40, 'bid'))
        assert(is_bids_sorted(ob2))
        assert(len(ob2.bids) == 3)

    def test_bid_asks_sorted(self):
        ob3 = OrderBook()
        ob3.add_order(Order(100,'bid'))
        ob3.add_order(Order(100,'ask'))
        assert(is_bids_sorted(ob3))
        ob3.add_order(Order(120,'bid'))
        ob3.add_order(Order(120,'ask'))
        assert(is_bids_sorted(ob3))
        ob3.add_order(Order(40, 'bid'))
        ob3.add_order(Order(40, 'ask'))
        assert(is_bids_sorted(ob3))


if __name__ == "__main__":
    pytest.main()
