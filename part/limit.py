#Know the ordering

class Limit:
    _instance = None

    def __new__(cls): 
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.book = []
        return cls._instance
    
class OrderBook:
    def create(self, ordertype = "limit"):
        if ordertype == "limit":
            return Limit()
    
a = OrderBook()

b = OrderBook() 

limit_a = a.create("limit")

limit_b = b.create()    

print(limit_a is limit_b)
