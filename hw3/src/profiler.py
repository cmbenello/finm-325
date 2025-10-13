from __future__ import annotations

import cProfile, io, time, timeit, tracemalloc, pstats
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Iterable, List, Sequence

from src.data_loader import create_market_data_points, load_data
from src.engine import ExecutionEngine
from src.models import MarketDataPoint, Portfolio, PortfolioLog
from src.strategies import (
    NaiveMovingAverageStrategy,
    Strategy,
    WindowedMovingAverageStrategy,
    NaiveMovingAverageStrategyOptimized,
)

try:
    from memory_profiler import memory_usage  # type: ignore
except ImportError:
    memory_usage = None

StrategyFactory = Callable[[], Strategy]

@dataclass(frozen=True)
class StrategyConfig:
    name: str
    factory: StrategyFactory
    complexity: str

@dataclass
class ProfileResult:
    strategy_name: str
    num_ticks: int
    runtime_samples: List[float]
    runtime_best: float
    runtime_avg: float
    memory_peak_mb: float
    cprofile_path: Path | None
    cprofile_top_stats: str
    def as_dict(self) -> dict:
        d = asdict(self)
        d["cprofile_path"] = str(self.cprofile_path) if self.cprofile_path else None
        return d

def _slugify(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")

def _run_engine(factory: StrategyFactory, ticks: Sequence[MarketDataPoint]) -> PortfolioLog:
    engine = ExecutionEngine(strat=factory(), portfolio=Portfolio())
    log: PortfolioLog = []
    engine.run_strategy(list(ticks) if not isinstance(ticks, list) else ticks, log)
    return log

def _measure_with_timeit(factory: StrategyFactory, ticks: Sequence[MarketDataPoint], repeat: int) -> List[float]:
    timer = timeit.Timer(lambda: _run_engine(factory, ticks))
    return list(timer.repeat(repeat=repeat, number=1))

def _profile_with_cprofile(strategy_label: str, factory: StrategyFactory, ticks: Sequence[MarketDataPoint], output_dir: Path) -> tuple[Path | None, str]:
    profile = cProfile.Profile()
    profile.enable()
    _run_engine(factory, ticks)
    profile.disable()

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{_slugify(strategy_label)}_{len(ticks)}.prof"
    profile.dump_stats(str(filename))

    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(15)
    return filename, stream.getvalue()

def _measure_memory_usage(factory: StrategyFactory, ticks: Sequence[MarketDataPoint]) -> float:
    if memory_usage is not None:
        samples = memory_usage((_run_engine, (factory, ticks)), include_children=True)
        return float(max(samples) if samples else 0.0)
    tracemalloc.start()
    _run_engine(factory, ticks)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / (1024**2)

def profile_strategy(config: StrategyConfig, ticks: Sequence[MarketDataPoint], repeat: int = 3, profile_dir: Path | str = "artifacts/profiles") -> ProfileResult:
    if not ticks:
        raise ValueError("No market data supplied for profiling")

    runtime_samples = _measure_with_timeit(config.factory, ticks, repeat)
    runtime_best = min(runtime_samples)
    runtime_avg = sum(runtime_samples) / len(runtime_samples)
    memory_peak_mb = _measure_memory_usage(config.factory, ticks)

    profile_dir = Path(profile_dir)
    cprofile_path, cprofile_top = _profile_with_cprofile(config.name, config.factory, ticks, profile_dir / "cprofile")

    return ProfileResult(
        strategy_name=config.name,
        num_ticks=len(ticks),
        runtime_samples=runtime_samples,
        runtime_best=runtime_best,
        runtime_avg=runtime_avg,
        memory_peak_mb=memory_peak_mb,
        cprofile_path=cprofile_path,
        cprofile_top_stats=cprofile_top,
    )

def profile_multiple(data: Sequence[MarketDataPoint], strategies: Iterable[StrategyConfig], sizes: Iterable[int], repeat: int = 3, profile_dir: Path | str = "artifacts/profiles") -> List[ProfileResult]:
    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    available = len(data)
    results: List[ProfileResult] = []
    for size in sizes:
        if size > available:
            continue
        subset = list(data[:size])
        for cfg in strategies:
            t0 = time.perf_counter()
            res = profile_strategy(cfg, subset, repeat=repeat, profile_dir=profile_dir)
            wall = time.perf_counter() - t0
            print(f"[profiling] strategy={cfg.name} ticks={size} time_best={res.runtime_best:.4f}s memory_peak={res.memory_peak_mb:.2f}MiB (wall {wall:.2f}s)")
            results.append(res)
    return results

def load_market_data(path: str | Path) -> List[MarketDataPoint]:
    rows = load_data(str(path))
    return create_market_data_points(rows)

def default_strategy_configs() -> List[StrategyConfig]:
    return [
        StrategyConfig(
            name="NaiveMovingAverageStrategy",
            factory=lambda: NaiveMovingAverageStrategy(short_window=20, long_window=50),
            complexity="time=O(L) per tick, space=O(n)",
        ),
        StrategyConfig(
            name="NaiveMovingAverageStrategyOptimized",
            factory=lambda: NaiveMovingAverageStrategyOptimized(short_window=20, long_window=50),
            complexity="time=O(1) per tick, space=O(L)",
        ),
        StrategyConfig(
            name="WindowedMovingAverageStrategy",
            factory=lambda: WindowedMovingAverageStrategy(short_window=20, long_window=50),
            complexity="time=O(1) per tick, space=O(L)",
        ),
    ]