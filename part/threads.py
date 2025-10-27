import threading
from time import time
result = 0

# mutex = threading.Lock()
def dot_product(a, b):
    global result
    for i in range(len(a)):
        result += a[i] + b[i]

vector1 = [1] * 10_000_000 + [2] * 10_000_000
vector2 = [3] * 10_000_000 + [4] * 10_000_000
split_index = len(vector1) // 2

t1 = threading.Thread(target = dot_product, args = (vector1[:split_index], vector2[split_index:]))
t2 = threading.Thread(target = dot_product, args = (vector1[:split_index], vector2[split_index:]))
start_time = time()
t1.start() 
t2.start()

t1.join()
t2.join()
end_time = time()

print("time taken = :", end_time - start_time)
