# Performance & Reliability Report

## Setup

All components (Gateway, OrderBook, Strategy, OrderManager, shared memory initializer) were run on a single local machine using Python 3.12/3.13. The system used three symbols (`AAPL`, `MSFT`, `GOOG`) stored as `float64` in shared memory.

Shared memory size (payload):
- 3 symbols × 8 bytes = **24 bytes** for the price array

This excludes OS and Python bookkeeping overhead, but shows the core shared data is very small.

---

## Throughput

### Price / tick throughput (Gateway → OrderBook)

OrderBook prints tick throughput every 100 processed ticks. Sample output:

```text
[Metrics] orderbook tick throughput: 1000 ticks, 28.78 ticks/sec
...
[Metrics] orderbook tick throughput: 5500 ticks, 28.70 ticks/sec
```

Observed tick throughput is stable around **28–29 ticks/sec** over several thousand ticks. Each tick here is a `(symbol, price)` pair consumed and written into shared memory.

### Order throughput (Strategy → OrderManager)

OrderManager prints order metrics every 20 received orders. Sample output:

```text
[Metrics] orders received: 20, rate: 0.60 orders/sec
[Metrics] orders received: 40, rate: 0.66 orders/sec
[Metrics] orders received: 60, rate: 0.65 orders/sec
[Metrics] orders received: 80, rate: 0.60 orders/sec
[Metrics] orders received: 100, rate: 0.60 orders/sec
[Metrics] orders received: 120, rate: 0.63 orders/sec
```

Observed order throughput is roughly **0.6–0.65 orders/sec**. This is lower than tick rate by design, since Strategy only trades when:
- short moving average and long moving average agree on direction **and**
- news sentiment is consistently bullish or bearish.

---

## Latency (tick → trade decision)

Strategy tracks the time between seeing the latest price and deciding to send an order. It prints an average every 20 trades. Sample outputs:

```text
[Metrics] avg decision latency: 0.000569s over 20 trades
[Metrics] avg decision latency: 0.000331s over 40 trades
[Metrics] avg decision latency: 0.000252s over 60 trades
[Metrics] avg decision latency: 0.000209s over 80 trades
[Metrics] avg decision latency: 0.000197s over 100 trades
[Metrics] avg decision latency: 0.000185s over 120 trades
```

So the average latency from “latest price read” to “order decision and send” is on the order of **0.2–0.6 ms**, trending towards ~**0.2 ms** as more samples are collected.

This is an approximate decision latency measured inside the Strategy process; it does not include network latency between Gateway and OrderBook, or OS scheduling delays, but on a single local machine these are negligible for this assignment.

---

## Reliability and Failure Behavior

### Dropped price/news feed (Gateway)

When `gateway.py` is interrupted with `Ctrl+C`, both price and news sockets close. The logs show:

```text
[Gateway/Price] client ('127.0.0.1', 57110) disconnected
[Gateway/News] client ('127.0.0.1', 57111) disconnected
```

OrderBook and Strategy are written to catch `ConnectionError` / `ConnectionRefusedError` and retry every second. In practice, when Gateway is restarted, clients reconnect and resume normal operation without crashing the processes.

### Dropped OrderManager

When OrderManager is killed while Strategy is running, Strategy catches send errors (`ConnectionError`, `BrokenPipeError`, etc.), closes its socket, sleeps briefly, and attempts to reconnect:

- Orders temporarily fail to send while OrderManager is down.
- Strategy does not crash; it resumes sending orders once OrderManager restarts.

### Shared memory cleanup

The `shm_init.py` process creates the shared memory segment and keeps it alive. On abrupt termination (`Ctrl+C`) the Python `resource_tracker` may warn about leaked `SharedMemory` objects:

```text
resource_tracker: There appear to be 1 leaked shared_memory objects to clean up at shutdown
```

When `shm_init.py` is allowed to exit through its normal shutdown path (calling `close()` and `unlink()`), the shared memory segment is cleaned up correctly and these warnings disappear.

---

## Summary

- **Shared memory payload:** 24 bytes for 3 `float64` prices.
- **Tick throughput:** ~**28–29 ticks/sec** through OrderBook.
- **Order throughput:** ~**0.6–0.65 orders/sec** through OrderManager.
- **Decision latency:** ~**0.2–0.6 ms** from price read to order send in Strategy.
- **Reliability:** Components handle dropped connections by retrying; when Gateway or OrderManager are restarted, the system reconnects and resumes streaming/pricing/trading without a full restart of all processes.

These measurements show that the simplified trading stack can process continuous market data, generate strategy decisions, and execute orders with low latency and stable throughput on a single machine, while remaining robust to transient connection failures.
