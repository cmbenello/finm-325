# FINM 325 — HW8: Interprocess Communication Trading System

This project implements a simple multi-process trading system using interprocess communication (IPC) with TCP sockets and shared memory.

---

## Components

| Process           | Role                                              |
|-------------------|---------------------------------------------------|
| `gateway.py`      | Streams simulated price and sentiment data over TCP. |
| `orderbook.py`    | Receives prices and updates them in shared memory.   |
| `strategy.py`     | Reads prices and news, generates buy/sell signals, and sends orders. |
| `order_manager.py`| Receives and logs orders from strategies.            |
| `shared_memory_utils.py` | Defines the shared memory interface for price updates. |
| `main.py`         | Launches all processes for end-to-end orchestration. |

---

## Running the System

Run each component in a separate terminal:

```bash
python3 shm_init.py               # Create shared memory region
python3 gateway.py                # Start data feed servers
python3 orderbook.py prices      # Connect to gateway, update shared memory
python3 order_manager.py          # Receive and log trade orders
python3 strategy.py prices        # Generate trading signals and send orders
```

Alternatively, run all processes concurrently with:

```bash
python3 main.py
```

---

## Metrics

The system reports live performance metrics:

- OrderBook: tick throughput (ticks per second)
- Strategy: average decision latency (ms per trade decision)
- OrderManager: orders received (orders per second)
- Shared memory size in bytes (printed by `main.py`)

---

## Tests

Unit tests are located in the `tests/` directory and use `pytest`.

Run tests with:

```bash
pytest -q
```

All tests should pass to confirm correct IPC, serialization, and signal generation.

---

## Demonstration

To demonstrate the system:

- Open four terminals: Gateway, OrderBook, Strategy, and OrderManager.
- Start each process in order and observe metrics updating.
- Explain how processes communicate and handle disconnects.

---

## Performance Summary

- Tick throughput: approximately 28–29 ticks per second
- Order throughput: approximately 0.6–0.65 orders per second
- Decision latency: approximately 0.2–0.6 ms
- Shared memory payload: 24 bytes (3 float64 prices)
- Reliable reconnection on dropped connections

---

## Notes

- Communication uses TCP sockets with message delimiters (`b'*'`).
- Shared memory uses `multiprocessing.shared_memory` for zero-copy updates.
- Strategy decisions are based on moving-average crossovers and sentiment alignment.
