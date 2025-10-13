from __future__ import annotations

from pathlib import Path
from typing import List
import pandas as pd
import matplotlib.pyplot as plt


def results_to_dataframe(results) -> pd.DataFrame:
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


def save_results_csv(df: pd.DataFrame, outdir: Path | str = "reports") -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "benchmarks.csv"
    df.to_csv(path, index=False)
    return path


def plot_scaling(df: pd.DataFrame, outdir: Path | str = "reports") -> tuple[Path, Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

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


def generate_complexity_report(
    df: pd.DataFrame,
    strategies,
    runtime_plot: Path,
    memory_plot: Path,
    outdir: Path | str = "reports",
    filename: str = "complexity_report.md",
) -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / filename

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
    path.write_text(content)
    return path



def _complexity_table(strategies) -> str:
    lines = ["| Strategy | Complexity |", "|---|---|"]
    for s in strategies:
        lines.append(f"| {s.name} | {s.complexity} |")
    return "\n".join(lines)


def _metrics_table(df: pd.DataFrame, value_cols: list[str]) -> str:
    cols = ["strategy", "N"] + value_cols
    sub = df[cols].copy().sort_values(["strategy", "N"])
    header = "|" + "|".join(cols) + "|"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    lines = [header, sep]
    for _, row in sub.iterrows():
        lines.append("|" + "|".join(str(row[c]) for c in cols) + "|")
    return "\n".join(lines)


def _compute_narrative(df: pd.DataFrame) -> str:
    if df.empty:
        return "No results to compare."
    largest = int(df["N"].max())
    atN = df[df["N"] == largest]

    def get(name, col):
        s = atN[atN["strategy"] == name]
        return None if s.empty else float(s.iloc[0][col])

    naive_rt = get("NaiveMovingAverageStrategy", "runtime_best_sec")
    opt_rt = get("NaiveMovingAverageStrategyOptimized", "runtime_best_sec")
    win_rt = get("WindowedMovingAverageStrategy", "runtime_best_sec")

    naive_mem = get("NaiveMovingAverageStrategy", "memory_peak_MiB")
    opt_mem = get("NaiveMovingAverageStrategyOptimized", "memory_peak_MiB")
    win_mem = get("WindowedMovingAverageStrategy", "memory_peak_MiB")

    lines = [f"Comparison at N = {largest}"]
    if naive_rt and opt_rt:
        lines.append(f"- Optimized vs Naive runtime: x{naive_rt/opt_rt:.2f} faster (best).")
    if naive_rt and win_rt:
        lines.append(f"- Windowed vs Naive runtime: x{naive_rt/win_rt:.2f} faster (best).")
    if naive_mem and opt_mem and naive_mem > 0:
        lines.append(f"- Optimized memory vs Naive: {(100*(naive_mem-opt_mem)/naive_mem):.1f}% lower (peak).")
    if naive_mem and win_mem and naive_mem > 0:
        lines.append(f"- Windowed memory vs Naive: {(100*(naive_mem-win_mem)/naive_mem):.1f}% lower (peak).")
    lines.append("- Scaling: optimized/windowed ~O(1) per tick; naive grows with long_window.")
    return "\n".join(lines)