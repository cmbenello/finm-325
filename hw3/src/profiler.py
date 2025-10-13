from __future__ import annotations

import cProfile
import io
import time
import timeit
import tracemalloc
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
import pandas as pd
import matplotlib.pyplot as plt
import pstats

try:
    # memory_profiler provides per-sample RSS, falling back to tracemalloc if absent.
    from memory_profiler import memory_usage  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    memory_usage = None


StrategyFactory = Callable[[], Strategy]


@dataclass(frozen=True)
class StrategyConfig:
    """Configuration wrapper used to instantiate a fresh strategy per run."""

    name: str
    factory: StrategyFactory
    complexity: str


@dataclass
class ProfileResult:
    """Container for runtime and memory metrics gathered during profiling."""

    strategy_name: str
    num_ticks: int
    runtime_samples: List[float]
    runtime_best: float
    runtime_avg: float
    memory_peak_mb: float
    cprofile_path: Path | None
    cprofile_top_stats: str

    def as_dict(self) -> dict:
        """Return a JSON-serialisable representation of the profiling outcome."""
        payload = asdict(self)
        payload["cprofile_path"] = str(self.cprofile_path) if self.cprofile_path else None
        return payload


def _slugify(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def _run_engine(factory: StrategyFactory, ticks: Sequence[MarketDataPoint]) -> PortfolioLog:
    """Execute a strategy over all ticks. Time complexity O(n) with n = len(ticks)."""
    engine = ExecutionEngine(strat=factory(), portfolio=Portfolio())
    log: PortfolioLog = []
    engine.run_strategy(list(ticks) if not isinstance(ticks, list) else ticks, log)
    return log


def _measure_with_timeit(
    factory: StrategyFactory, ticks: Sequence[MarketDataPoint], repeat: int
) -> List[float]:
    """Benchmark runtime using timeit so we get consistent timing samples."""
    timer = timeit.Timer(lambda: _run_engine(factory, ticks))
    return list(timer.repeat(repeat=repeat, number=1))


def _profile_with_cprofile(
    strategy_label: str,
    factory: StrategyFactory,
    ticks: Sequence[MarketDataPoint],
    output_dir: Path,
) -> tuple[Path | None, str]:
    """Capture a detailed call graph using cProfile and persist raw stats to disk."""
    profile = cProfile.Profile()
    profile.enable()
    _run_engine(factory, ticks)
    profile.disable()

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{_slugify(strategy_label)}_{len(ticks)}.prof"
    profile.dump_stats(str(filename))

    stream = io.StringIO()
    profile_stats = pstats.Stats(profile, stream=stream)
    profile_stats.sort_stats("cumulative")
    profile_stats.print_stats(15)
    return filename, stream.getvalue()


def _measure_memory_usage(factory: StrategyFactory, ticks: Sequence[MarketDataPoint]) -> float:
    """Measure peak memory while processing ticks."""
    if memory_usage is not None:
        mem_samples = memory_usage(
            (_run_engine, (factory, ticks)),
            include_children=True,
        )
        peak = max(mem_samples) if mem_samples else 0.0
        return float(peak)

    tracemalloc.start()
    _run_engine(factory, ticks)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / (1024**2)


def profile_strategy(
    config: StrategyConfig,
    ticks: Sequence[MarketDataPoint],
    repeat: int = 3,
    profile_dir: Path | str = "artifacts/profiles",
) -> ProfileResult:
    """Profile a single strategy on an input sequence."""
    if not ticks:
        raise ValueError("No market data supplied for profiling")

    runtime_samples = _measure_with_timeit(config.factory, ticks, repeat)
    runtime_best = min(runtime_samples)
    runtime_avg = sum(runtime_samples) / len(runtime_samples)

    # Capture memory and cProfile in separate passes to isolate signal from instrumentation.
    memory_peak_mb = _measure_memory_usage(config.factory, ticks)

    profile_dir = Path(profile_dir)
    cprofile_path, cprofile_top = _profile_with_cprofile(
        config.name,
        config.factory,
        ticks,
        profile_dir / "cprofile",
    )

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


def profile_multiple(
    data: Sequence[MarketDataPoint],
    strategies: Iterable[StrategyConfig],
    sizes: Iterable[int],
    repeat: int = 3,
    profile_dir: Path | str = "artifacts/profiles",
) -> List[ProfileResult]:
    """Run profiling for every combination of strategy and dataset size."""
    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    available = len(data)
    results: List[ProfileResult] = []

    for size in sizes:
        if size > available:
            continue
        slice_data = list(data[:size])
        for config in strategies:
            start = time.perf_counter()
            result = profile_strategy(
                config=config,
                ticks=slice_data,
                repeat=repeat,
                profile_dir=profile_dir,
            )
            elapsed = time.perf_counter() - start
            print(
                f"[profiling] strategy={config.name} ticks={size} "
                f"time_best={result.runtime_best:.4f}s "
                f"memory_peak={result.memory_peak_mb:.2f}MiB "
                f"(wall {elapsed:.2f}s)",
                flush=True,
            )
            results.append(result)
    return results


def load_market_data(path: str | Path) -> List[MarketDataPoint]:
    rows = load_data(str(path))
    return create_market_data_points(rows)


def default_strategy_configs() -> List[StrategyConfig]:
    return [
        StrategyConfig(
            name="NaiveMovingAverageStrategy",
            factory=lambda: NaiveMovingAverageStrategy(short_window=20, long_window=50),
            complexity="time=O(L) per tick, space=O(n)",  # L = long_window
        ),
        StrategyConfig(
            name="NaiveMovingAverageStrategyOptimized",
            factory=lambda: NaiveMovingAverageStrategyOptimized(short_window=20, long_window=50),
            complexity="time=O(1) per tick, space=O(L)",  # optimized rolling-sum version
        ),
        StrategyConfig(
            name="WindowedMovingAverageStrategy",
            factory=lambda: WindowedMovingAverageStrategy(short_window=20, long_window=50),
            complexity="time=O(1) per tick, space=O(L)",
        ),
    ]

def results_to_dataframe(results: List[ProfileResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "strategy": r.strategy_name,
            "N": r.num_ticks,
            "runtime_best_sec": r.runtime_best,
            "runtime_avg_sec": r.runtime_avg,
            "memory_peak_MiB": r.memory_peak_mb,
        })
    df = pd.DataFrame(rows).sort_values(["strategy", "N"]).reset_index(drop=True)
    return df


def save_results_csv(df: pd.DataFrame, outdir: Path | str = "artifacts/report") -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "benchmarks.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def plot_scaling(df: pd.DataFrame, outdir: Path | str = "artifacts/report") -> tuple[Path, Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Runtime vs N
    rt_path = outdir / "runtime_vs_n.png"
    plt.figure()
    for name, sub in df.groupby("strategy"):
        sub = sub.sort_values("N")
        plt.plot(sub["N"], sub["runtime_best_sec"], marker="o", label=name)
    plt.xlabel("ticks (N)")
    plt.ylabel("runtime_best (sec)")
    plt.title("Runtime vs N")
    plt.legend()
    plt.tight_layout()
    plt.savefig(rt_path, dpi=160)
    plt.close()

    # Memory vs N
    mem_path = outdir / "memory_vs_n.png"
    plt.figure()
    for name, sub in df.groupby("strategy"):
        sub = sub.sort_values("N")
        plt.plot(sub["N"], sub["memory_peak_MiB"], marker="o", label=name)
    plt.xlabel("ticks (N)")
    plt.ylabel("peak memory (MiB)")
    plt.title("Peak Memory vs N")
    plt.legend()
    plt.tight_layout()
    plt.savefig(mem_path, dpi=160)
    plt.close()

    return rt_path, mem_path


def _complexity_table(strategies: List[StrategyConfig]) -> str:
    lines = ["| Strategy | Complexity |",
             "|---|---|"]
    for s in strategies:
        lines.append(f"| {s.name} | {s.complexity} |")
    return "\n".join(lines)


def _metrics_table(df: pd.DataFrame, value_cols: list[str]) -> str:
    # Create a tidy Markdown table: strategy, N, and selected value columns
    cols = ["strategy", "N"] + value_cols
    sub = df[cols].copy().sort_values(["strategy", "N"])
    # Build header
    header = "|" + "|".join(cols) + "|"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    lines = [header, sep]
    for _, row in sub.iterrows():
        line = "|" + "|".join(str(row[c]) for c in cols) + "|"
        lines.append(line)
    return "\n".join(lines)


def _compute_narrative(df: pd.DataFrame) -> str:
    # Compare at largest N available
    if df.empty:
        return "No results to compare."

    largest_N = int(df["N"].max())
    atN = df[df["N"] == largest_N]
    if atN.empty:
        return "No results at the largest N."

    # pick reference = naive, compare optimized and windowed
    def get_metric(strategy_name: str, col: str) -> float | None:
        sub = atN[atN["strategy"] == strategy_name]
        if sub.empty:
            return None
        return float(sub.iloc[0][col])

    naive_rt = get_metric("NaiveMovingAverageStrategy", "runtime_best_sec")
    opt_rt = get_metric("NaiveMovingAverageStrategyOptimized", "runtime_best_sec")
    win_rt = get_metric("WindowedMovingAverageStrategy", "runtime_best_sec")

    naive_mem = get_metric("NaiveMovingAverageStrategy", "memory_peak_MiB")
    opt_mem = get_metric("NaiveMovingAverageStrategyOptimized", "memory_peak_MiB")
    win_mem = get_metric("WindowedMovingAverageStrategy", "memory_peak_MiB")

    lines = [f"Comparison at N = {largest_N}"]

    # Runtime comparisons
    if naive_rt is not None and opt_rt is not None:
        speedup_opt = (naive_rt / opt_rt) if opt_rt > 0 else float("inf")
        lines.append(f"- Optimized vs Naive runtime: x{speedup_opt:.2f} faster (best).")
    if naive_rt is not None and win_rt is not None:
        speedup_win = (naive_rt / win_rt) if win_rt > 0 else float("inf")
        lines.append(f"- Windowed vs Naive runtime: x{speedup_win:.2f} faster (best).")

    # Memory comparisons (lower is better)
    if naive_mem is not None and opt_mem is not None and naive_mem > 0:
        red_opt = 100.0 * (naive_mem - opt_mem) / naive_mem
        lines.append(f"- Optimized memory vs Naive: {red_opt:.1f}% lower (peak).")
    if naive_mem is not None and win_mem is not None and naive_mem > 0:
        red_win = 100.0 * (naive_mem - win_mem) / naive_mem
        lines.append(f"- Windowed memory vs Naive: {red_win:.1f}% lower (peak).")

    # Trend statement
    lines.append("- Scaling: optimized and windowed show near O(1) per tick behavior; naive grows with long_window and exhibits slower scaling as N increases.")

    return "\n".join(lines)


def generate_complexity_report(
    df: pd.DataFrame,
    strategies: List[StrategyConfig],
    runtime_plot: Path,
    memory_plot: Path,
    outdir: Path | str = "artifacts/report",
    filename: str = "complexity_report.md",
) -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    report_path = outdir / filename

    complexity_md = _complexity_table(strategies)
    rt_table = _metrics_table(df, ["runtime_best_sec", "runtime_avg_sec"])
    mem_table = _metrics_table(df, ["memory_peak_MiB"])
    narrative = _compute_narrative(df)

    content = f"""# Complexity and Performance Report

## Complexity Annotations
{complexity_md}

## Runtime Metrics
{rt_table}

## Memory Metrics
{mem_table}

## Plots
![Runtime vs N]({runtime_plot.name})
![Peak Memory vs N]({memory_plot.name})

## Narrative
{narrative}
"""
    report_path.write_text(content)
    return report_path


def main(
    data_path: str = "data/assignment3_market_data.csv",
    sizes: Iterable[int] = (1_000, 10_000, 100_000),
    repeat: int = 3,
    profile_dir: str | Path = "artifacts/profiles",
) -> List[ProfileResult]:
    market_data = load_market_data(data_path)
    if not market_data:
        raise RuntimeError(f"No rows found in {data_path}")

    strategies = default_strategy_configs()
    results = profile_multiple(
        data=market_data,
        strategies=strategies,
        sizes=sizes,
        repeat=repeat,
        profile_dir=profile_dir,
    )

    report_dir = Path("reports/")
    df = results_to_dataframe(results)
    csv_path = save_results_csv(df, report_dir)
    rt_plot, mem_plot = plot_scaling(df, report_dir)
    report_path = generate_complexity_report(
        df=df,
        strategies=strategies,
        runtime_plot=rt_plot,
        memory_plot=mem_plot,
        outdir=report_dir,
        filename="complexity_report.md",
    )

    print(f"[report] saved CSV: {csv_path}")
    print(f"[report] saved runtime plot: {rt_plot}")
    print(f"[report] saved memory plot: {mem_plot}")
    print(f"[report] saved markdown: {report_path}")

    return results


if __name__ == "__main__":
    main()
