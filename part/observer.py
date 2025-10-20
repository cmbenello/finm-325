class TradingStrategy:
    def __init__(self):
        self.mru_oder = None
    
    def update(self, order):
        self.mru_oder = order

    def last_trade(self):
        if self.mru_oder:
            return(self.mru_oder)
        else:
            return("No orders yet")


class PositionManager:
    def __init__(self):
        self.book = []
        self.obvserverCollection = []

    def update_trade(self, order_type, price, quantity):
        self.book = [(order_type, price, quantity)]
        self.notifyObservers()

    def registerObserver(self, observer):
        self.obvserverCollection.append(observer)

    def notifyObservers(self):
        for observer in self.obvserverCollection:
            observer.update(self.book[-1])

    def unregisterObserver(self, observer):
        self.obvserverCollection.remove(observer)


pos_manager = PositionManager()
t1 = TradingStrategy()
t2 = TradingStrategy()
t3 = TradingStrategy()

print("t1's last trade: ", t1.last_trade())
print("t2's last trade: ", t2.last_trade())
print("t3's last trade: ", t3.last_trade())

pos_manager.registerObserver(t1)
pos_manager.registerObserver(t2)
pos_manager.registerObserver(t3)


pos_manager.update_trade("BUY", 67, 1)

print("t1's last trade: ", t1.last_trade())
print("t2's last trade: ", t2.last_trade())
print("t3's last trade: ", t3.last_trade())


import time 

def my_time(function):
    def wrapper(*args, **kwargs):
        print(*args, **kwargs)
        start_time = time.time() 
        result = function(*args, **kwargs)
        stop_time = time.time()
        print("execution time:", stop_time - start_time)
        return result
    return wrapper

@my_time
def say_hello_1(name):
    return "hello " + name

@my_time
def say_hello_2(name1, name2):
    return "hello " + name1 + " " + name2

print(say_hello_1("james"))
print(say_hello_2("james", "pain"))


class iterator_list:
    def __init__(self, l):
        self.pos = 0
        self.list_ref = l 

    def __iter__(self):
        return self
    
    def __next__(self):
        if self.pos >= len(self.list_ref):
            raise StopIteration
        tmp_value = self.list_ref[self.pos]
        self.pos += 1
        return tmp_value


a = [60, 50, 40]


for i in iterator_list(a):
    print(i)

