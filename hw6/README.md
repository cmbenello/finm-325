## Overview

This project applies object-oriented design patterns to build a simplified financial trading and analytics system.  
It includes market data ingestion, portfolio modeling, analytics, order execution, and strategy management.  
Patterns used include Factory, Builder, Singleton, Decorator, Strategy, Observer, Command, and Composite.

All components are tested and run together in `main.py`.

---

## Setup Instructions

### 1. Clone and Enter Project
```bash
git clone git@github.com:cmbenello/finm-325.git
cd hw6
```

### 2. Create and Activate Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
> Only `pytest` and standard libraries are needed.

### 4. Run All Tests
```bash
pytest -q
```
Tests under `/tests` check each design pattern.

### 5. Run Main Demo
```bash
python3 main.py
```

Expected output:
```
=== Run Summary ===
Final equity: 100,573.25
Final positions: {'SPY': 70, 'AAPL': -40, 'MSFT': -90}
LoggerObserver: 194 signals logged
AlertObserver: 68 alerts
```

---

## Module Descriptions

| Module | Purpose | Key Patterns |
|:--------|:---------|:-------------|
| `src/models.py` | Core financial entities: `MarketDataPoint`, `Order`, `Portfolio`, `Signal`. | Basic models |
| `src/patterns/factory.py` | Create instruments (`Stock`, `Bond`, `ETF`) from CSV. | Factory |
| `src/patterns/singleton.py` | Load and manage global config (single instance). | Singleton |
| `src/patterns/builder.py` | Build nested portfolios with fluent interface. | Builder |
| `src/patterns/decorator.py` | Add analytics (volatility, beta, drawdown) to instruments. | Decorator |
| `src/patterns/adapter.py` | Normalize Yahoo JSON and Bloomberg XML market data. | Adapter |
| `src/patterns/composite.py` | Model portfolios as recursive position trees. | Composite |
| `src/patterns/strategy.py` | Define trading algorithms (mean-reversion, breakout). | Strategy |
| `src/patterns/observer.py` | Notify observers on signal generation (logger, alerts). | Observer |
| `src/patterns/command.py` | Encapsulate trade execution with undo/redo. | Command |
| `src/analytics.py` | Implements volatility, beta, drawdown metrics. | Decorator utilities |
| `src/data_loader.py` | Adapter pattern for market data reading. | Adapter |
| `src/engine.py` | Executes strategies and manages state. | Strategy + Command |
| `src/reporting.py` | Logging, alerting, and report generation. | Observer |
| `main.py` | Runs ingestion, strategy execution, and output. | Integration |

---

## Testing

Each pattern is tested with pytest suites under `/tests`:

| Test File | Validates |
|:-----------|:-----------|
| `test_factory.py` | Factory creation from CSV |
| `test_singleton.py` | Singleton uniqueness |
| `test_builder.py` | PortfolioBuilder chaining and nesting |
| `test_decorator.py` | Metric stacking correctness |
| `test_adapter.py` | Yahoo/Bloomberg adapter consistency |
| `test_composite.py` | Recursive portfolio aggregation |
| `test_command.py` | Undo/redo functionality |
| `test_strategy.py` | Signal generation logic |

---

## Documentation

See [`design_resport.md`](./design_resport.md) for:
- Pattern rationale
- Architectural tradeoffs
- Integration overview
- Demo results

---

## Key Takeaways

This project shows that:
- Design patterns fit well with financial engineering problems.
- Modular pattern layers allow clean, testable trading workflows.
- Combining Strategy, Command, and Observer patterns supports flexible simulations.

---

ㅊ 다녀감