# Mini Trading System

This project implements a small end-to-end trading system composed of four components:

1. FIX message parser  
2. Order lifecycle simulator  
3. Risk check engine  
4. Event logger  

The system processes FIX messages, converts them into structured orders, validates them through a risk engine, records all events, and updates positions.

---

## Project Structure

```
src/
    fix_parser.py
    order.py
    risk_engine.py
    logger.py
    main.py
tests.py
events.json
```

---

## Components

### 1. FIX Parser (`fix_parser.py`)
Parses raw FIX protocol strings into Python dictionaries.  
Validates required fields for New Order Single (MsgType 35=D), including symbol, side, quantity, and price for limit orders.

### 2. Order Lifecycle (`order.py`)
Defines allowed state transitions:
- NEW → ACKED or REJECTED  
- ACKED → FILLED or CANCELED  

Transitions print state changes and prevent invalid transitions.

### 3. Risk Engine (`risk_engine.py`)
Applies basic trading constraints:
- Maximum order size  
- Maximum net position per symbol  

Updates per-symbol positions after fills.

### 4. Logger (`logger.py`)
Singleton logger that records all events (orders created, fills, rejections).  
Logs are written to `events.json`.

---

## Running the System

Run:

```
python3 src/main.py
```

This processes example FIX messages and writes event logs into `events.json`.

Console output includes:
- Order state transitions  
- Logging statements for created, filled, or rejected orders  

---

## Tests

Unit tests for all components are included in `tests.py`.

Run tests with:

```
pytest tests.py -q
```

Tests cover:
- FIX parsing and validation
- Order state transitions
- Risk checks and position updates
- Logging and file output

---

## Output Files

### `events.json`
Contains structured log entries.  
Useful for debugging, replay, or analysis.

---

## Requirements

Python 3.8+  
No external dependencies.

---

## Notes

This project focuses on simple trading system concepts such as FIX parsing, order state machines, risk checks, and structured logging.  
It is not intended for production trading use.
