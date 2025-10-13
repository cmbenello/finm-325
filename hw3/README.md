# FINM 325 — Assignment 3  
### Runtime & Space Complexity in Financial Signal Processing

This project benchmarks multiple trading strategies with different runtime and space complexities.  
You will analyze their computational efficiency, measure performance on increasing input sizes,  
and visualize scaling behavior.

---

## Setup

```bash
# clone and enter project
git clone https://github.com/cmbenello/finm-325.git
cd finm-325/hw3

# create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# if you don’t have a requirements.txt yet
pip install pipreqs
pipreqs . --force
```

---

## Run the Program

The main entry point is `main.py`, which orchestrates data loading, strategy execution, profiling, and reporting.

```bash
python main.py
```

### What Happens When You Run It

1. **Loads Data**  
   - Reads `data/assignment3_market_data.csv`  
   - Converts rows into immutable `MarketDataPoint` objects with `timestamp`, `symbol`, and `price`.

2. **Executes All Strategies**  
   - `NaiveMovingAverageStrategy`: recomputes averages from scratch each tick (O(n) time).  
   - `NaiveMovingAverageStrategyOptimized`: uses a rolling-sum optimization (O(1) time).  
   - `WindowedMovingAverageStrategy`: maintains a fixed-size buffer (O(1) time, O(k) space).

3. **Profiles Runtime and Memory**  
   - Measures execution time using `timeit` and `cProfile`.  
   - Measures peak memory usage using `memory_profiler` or `tracemalloc`.

4. **Generates Reports**  
   Saves performance metrics and complexity analysis under `reports/`:
   ```text
   reports/
     ├── benchmarks.csv
     ├── runtime_vs_n.png
     ├── memory_vs_n.png
     └── complexity_report.md
   ```
   The Markdown report includes runtime/memory tables, complexity annotations, and a narrative comparing scaling behavior.

### Example Output

```text
[profiling] strategy=NaiveMovingAverageStrategy size=100000 time_best=3.52s memory_peak=255.7MiB
[profiling] strategy=NaiveMovingAverageStrategyOptimized size=100000 time_best=0.31s memory_peak=62.3MiB
[report] saved CSV: reports/benchmarks.csv
[report] saved markdown: reports/complexity_report.md
```

---

## Run Tests

The `tests/` directory includes correctness, performance, and profiling validation.

```bash
pytest -q
```

This will:
- Confirm all strategies produce consistent signals after warm-up.
- Check that the optimized strategy runs under 1 second and uses <100 MB memory for 100k data points.
- Validate that profiling output files exist and contain expected hotspots.

To include long-running performance tests:

```bash
pytest -q -m "slow or not slow"
```

If all goes well, you should see:

```text
....                                                                                                                                        [100%]
4 passed in 5.2s
```