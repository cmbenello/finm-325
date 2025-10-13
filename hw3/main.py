# main.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from src.profiler import (
    load_market_data,
    default_strategy_configs,
    profile_multiple,
)
from src.reporting import (
    results_to_dataframe,
    save_results_csv,
    plot_scaling,
    generate_complexity_report,
)

def main(
    data_path: str = "data/assignment3_market_data.csv",
    sizes: Iterable[int] = (1_000, 10_000, 100_000),
    repeat: int = 3,
    profile_dir: str | Path = "artifacts/profiles",
    report_dir: str | Path = "reports",
) -> None:
    ticks = load_market_data(data_path)
    if not ticks:
        raise RuntimeError(f"No rows found in {data_path}")

    strategies = default_strategy_configs()
    results = profile_multiple(
        data=ticks,
        strategies=strategies,
        sizes=sizes,
        repeat=repeat,
        profile_dir=profile_dir,
    )

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

if __name__ == "__main__":
    main()