

# Design Report  
**Assignment 6: Design Patterns in Financial Software Architecture**

## Overview

This project implements a modular, extensible financial analytics and trading simulation system using a suite of classic **object-oriented design patterns**.  
The goal was to demonstrate how creational, structural, and behavioral patterns improve code modularity, maintainability, and clarity in realistic finance contexts such as market data ingestion, portfolio analytics, and trading execution.

The system components are organized as follows:

| Module | Responsibility |
|:-------|:----------------|
| `src/models.py` | Core financial entities (MarketDataPoint, Order, Portfolio, Signal). |
| `src/patterns/` | Implementations of the Factory, Singleton, Builder, Strategy, Observer, Command, Decorator, and Composite patterns. |
| `src/analytics.py` | Instrument analytics using Decorator composition. |
| `src/data_loader.py` | Adapter pattern for integrating heterogeneous data sources. |
| `src/engine.py` | Strategy execution engine with undo/redo via the Command pattern. |
| `src/reporting.py` | Observer-driven logging and alerting. |
| `main.py` | Orchestrates configuration, ingestion, strategy execution, and reporting. |

All tests (`pytest`) pass successfully.

---

## 1. Creational Patterns

### **Factory Pattern**
- **Problem:** Instruments (Stock, Bond, ETF) needed to be instantiated dynamically from CSV rows.  
- **Solution:** `InstrumentFactory.create_instrument(data: dict)` looks up the correct subclass in a `_map` and instantiates it with relevant attributes.  
- **Benefit:** Centralized control over object creation — avoids large `if/elif` blocks.  
- **Example:**  
  ```python
  row = {"type": "Stock", "symbol": "AAPL", "sector": "Tech"}
  stock = InstrumentFactory.create_instrument(row)
  ```

### **Singleton Pattern**
- **Problem:** Configuration and parameters (from `config.json`) must be globally consistent across modules.  
- **Solution:** `Config` implemented via `__new__` ensures only one instance exists.  
- **Benefit:** Simplifies dependency injection — all components reference the same config without passing it explicitly.  
- **Tradeoff:** Reduces flexibility in testing; mitigated by allowing config reset in tests.

### **Builder Pattern**
- **Problem:** Need to construct complex, nested portfolios (positions + subportfolios) from structured JSON.  
- **Solution:** `PortfolioBuilder` implements fluent methods (`add_position`, `set_owner`, `add_subportfolio`, `build`).  
- **Benefit:** Separates portfolio construction logic from its representation; supports hierarchical composition and validation.  
- **Tradeoff:** Requires explicit `build()` calls, adding minor ceremony.

---

## 2. Structural Patterns

### **Decorator Pattern**
- **Problem:** Extend instrument analytics (volatility, beta, drawdown) without modifying the base class.  
- **Solution:** Created composable analytics decorators:  
  - `VolatilityDecorator` (rolling std of returns)  
  - `BetaDecorator` (covariance vs. market)  
  - `DrawdownDecorator` (peak-to-trough decline tracking)  
- **Usage:**  
  ```python
  decorated = DrawdownDecorator(BetaDecorator(VolatilityDecorator(stock)))
  metrics = decorated.get_metrics()
  ```
- **Benefit:** Enables analytics stacking and on-demand enrichment without altering base logic.

### **Adapter Pattern**
- **Problem:** External market data formats (Yahoo JSON, Bloomberg XML) differ.  
- **Solution:**  
  - `YahooFinanceAdapter` parses JSON  
  - `BloombergXMLAdapter` parses XML  
  Both expose a unified `.get_data(symbol) -> MarketDataPoint` interface.  
- **Benefit:** Standardized ingestion layer; strategy/engine code remains format-agnostic.

### **Composite Pattern**
- **Problem:** Model portfolios with nested sub-portfolios and positions.  
- **Solution:**  
  - `PortfolioComponent` defines `.get_value()` and `.get_positions()`  
  - `Position` (leaf) and `PortfolioGroup` (composite node) implement recursion.  
- **Benefit:** Treats single positions and multi-level portfolios uniformly.  
- **Demonstration:** Aggregated recursively from `configs/portfolio_structure.json`.

---

## 3. Behavioral Patterns

### **Strategy Pattern**
- **Problem:** Allow interchangeable trading logics (Mean Reversion, Breakout).  
- **Solution:** Abstract `Strategy.generate_signals(tick)` interface.  
  - `MeanReversionStrategy`: trades deviations from moving average.  
  - `BreakoutStrategy`: trades new highs/lows relative to lookback window.  
- **Benefit:** Strategies are pluggable and configurable from JSON.  
- **Tradeoff:** Stateful window maintenance requires careful reset between runs.

### **Observer Pattern**
- **Problem:** Notify modules when signals are generated without coupling.  
- **Solution:**  
  - `SignalPublisher.attach(observer)` / `.notify(signal)`  
  - Observers:  
    - `LoggerObserver`: appends to a log.  
    - `AlertObserver`: emits alerts for large trades.  
- **Benefit:** Decouples analytics, logging, and alerting from trading logic.

### **Command Pattern**
- **Problem:** Encapsulate order execution and support undo/redo.  
- **Solution:**  
  - `ExecuteOrderCommand` applies a trade and snapshots pre-state.  
  - `UndoOrderCommand` reverses a previous trade.  
  - `CommandInvoker` manages undo/redo stacks.  
- **Benefit:** Reversible trade lifecycle; ideal for simulation and backtesting.  
- **Demonstration:**  
  ```python
  inv.submit(ExecuteOrderCommand(portfolio, order))
  inv.undo(); inv.redo()
  ```

---

## 4. Integration and Engine

### **Execution Engine**
- Coordinates:
  - Market feed (adapters)
  - Strategy (signal generation)
  - CommandInvoker (execution + undo/redo)
  - SignalPublisher (observer notifications)
- Maintains a rolling price book to compute **mark-to-market per symbol**.
- Produces a `PortfolioLog` of snapshots after each tick.

### **Main Application**
- Initializes:
  - `Portfolio(cash=100_000)`
  - Strategy (selected via env var `STRAT`)
  - Observers (Logger, Alert)
  - `ExecutionEngine`
- Runs feed through the engine, prints run summary and P&L by symbol.

---

## 5. Tradeoffs and Design Insights

| Aspect | Benefit | Tradeoff / Mitigation |
|:--------|:---------|:----------------------|
| **Pattern layering** | Modular, testable components | Slightly verbose for small demos |
| **Command pattern** | Enables clean undo/redo | Memory overhead from deep copies |
| **Observer model** | Decoupled logging/alerts | Event order management complexity |
| **Decorators** | Extensible analytics | Stacking order affects metrics composition |
| **Singleton config** | Global access | Harder to mock; mitigated via reset |
| **Builder + Composite** | Clean hierarchical modeling | More indirection vs. simple dicts |

---

## 6. Results and Testing

- **All pytest suites pass**: factory, builder, decorator, singleton, composite, and command.
- **End-to-end demo** (`main.py`) produces realistic equity and alert behavior:
  ```
  Final equity: 100,573.25
  Positions: {'SPY': +70, 'AAPL': -40, 'MSFT': -90}
  Alerts: 68
  ```
- **Undo/redo** verified via command tests.
- **Adapters** correctly ingest `configs/external_data_yahoo.json` and `configs/external_data_bloomberg.xml`.

---


tl;dr if you want to test something j run the tests