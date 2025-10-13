
import pytest
import time
from .helpers import make_synthetic_ticks
from src.strategies import NaiveMovingAverageStrategyOptimized
from src.engine import ExecutionEngine
from src.models import Portfolio

try:
    from memory_profiler import memory_usage  # type: ignore
    HAS_MEMPROF = True
except Exception:
    HAS_MEMPROF = False

@pytest.mark.slow
def test_optimized_strategy_runtime_and_memory_under_thresholds():
    MAX_SEC = 1.0
    MAX_MIB = 100.0

    ticks = make_synthetic_ticks(100_000)

    eng = ExecutionEngine(strat=NaiveMovingAverageStrategyOptimized(20, 50), portfolio=Portfolio())
    t0 = time.perf_counter()
    log = []
    eng.run_strategy(ticks, log)
    dt = time.perf_counter() - t0

    assert dt <= MAX_SEC, f"runtime {dt:.3f}s exceeded {MAX_SEC}s"

    if HAS_MEMPROF:
        def _target():
            eng2 = ExecutionEngine(strat=NaiveMovingAverageStrategyOptimized(20, 50), portfolio=Portfolio())
            log2 = []
            eng2.run_strategy(ticks, log2)

        samples = memory_usage((_target,), include_children=True)
        peak = max(samples) - min(samples) if samples else 0.0
        assert peak < MAX_MIB, f"peak RSS delta {peak:.1f} MiB exceeded {MAX_MIB} MiB"
    else:
        pytest.skip("memory_profiler not installed; skipping memory threshold check")
