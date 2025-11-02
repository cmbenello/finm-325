from __future__ import annotations
import json
import matplotlib
matplotlib.use("Agg")
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import psutil
from data_loader import load_market_data_pandas, load_market_data_polars
from metrics import pandas_rolling_metrics, polars_rolling_metrics
from parallel import pandas_threaded, pandas_multiproc, polars_threaded, polars_multiproc


def _ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _rss_mb() -> float:
    return psutil.Process().memory_info().rss / (1024**2)


def _cpu_time_s() -> float:
    t = psutil.Process().cpu_times()
    return float(t.user + t.system)


def _plot_symbol(ax, df_pd: pd.DataFrame, symbol: str):
    s = df_pd[df_pd["symbol"] == symbol].sort_values("timestamp")
    ax.plot(s["timestamp"], s["price"], label="price")
    if "ma20" in s:
        ax.plot(s["timestamp"], s["ma20"], label="ma20")
    ax.set_title(symbol)
    ax.legend(loc="best")


def _plot_sharpe(ax, df_pd: pd.DataFrame, symbol: str):
    s = df_pd[df_pd["symbol"] == symbol].sort_values("timestamp")
    if "sharpe20" in s:
        ax.plot(s["timestamp"], s["sharpe20"], label="sharpe20")
        ax.legend(loc="best")
        ax.set_title(f"{symbol} sharpe20")


def make_symbol_plots(df_pd_metrics: pd.DataFrame, symbol: str, outdir: str | Path) -> dict:
    outdir = _ensure_dir(outdir)
    f1 = outdir / f"{symbol}_price_ma20.png"
    f2 = outdir / f"{symbol}_sharpe20.png"
    fig, ax = plt.subplots(figsize=(10, 4))
    _plot_symbol(ax, df_pd_metrics, symbol)
    fig.tight_layout()
    fig.savefig(f1)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 3))
    _plot_sharpe(ax, df_pd_metrics, symbol)
    fig.tight_layout()
    fig.savefig(f2)
    plt.close(fig)
    return {"price_ma20": str(f1), "sharpe20": str(f2)}


def run_report(data_path: str = "data/market_data-1.csv", symbol: str = "AAPL", outdir: str | Path = "reports") -> dict:
    outdir = _ensure_dir(outdir)

    pd_res = load_market_data_pandas(data_path)
    pl_res = load_market_data_polars(data_path)

    rss0 = _rss_mb(); cpu0 = _cpu_time_s()
    pd_metrics, t_pd = pandas_rolling_metrics(pd_res.df)
    roll_pd_rss = _rss_mb() - rss0; roll_pd_cpu = _cpu_time_s() - cpu0

    rss0 = _rss_mb(); cpu0 = _cpu_time_s()
    pl_metrics, t_pl = polars_rolling_metrics(pl_res.df)
    roll_pl_rss = _rss_mb() - rss0; roll_pl_cpu = _cpu_time_s() - cpu0

    rss0 = _rss_mb(); cpu0 = _cpu_time_s()
    pd_thr_df, t_pd_thr, r_pd_thr = pandas_threaded(pd_res.df)
    par_pd_thr_cpu = _cpu_time_s() - cpu0

    rss0 = _rss_mb(); cpu0 = _cpu_time_s()
    pd_mp_df, t_pd_mp, r_pd_mp = pandas_multiproc(pd_res.df)
    par_pd_mp_cpu = _cpu_time_s() - cpu0

    rss0 = _rss_mb(); cpu0 = _cpu_time_s()
    pl_thr_df, t_pl_thr, r_pl_thr = polars_threaded(pl_res.df)
    par_pl_thr_cpu = _cpu_time_s() - cpu0

    rss0 = _rss_mb(); cpu0 = _cpu_time_s()
    pl_mp_df, t_pl_mp, r_pl_mp = polars_multiproc(pl_res.df)
    par_pl_mp_cpu = _cpu_time_s() - cpu0

    plot_df = pd_metrics.reset_index() if isinstance(pd_metrics.index, pd.DatetimeIndex) else pd_metrics
    charts = make_symbol_plots(plot_df, symbol, outdir)

    rows = [
        {"category": "ingest", "lib": "pandas", "time_s": pd_res.wall_time_s, "rss_delta_mb": pd_res.rss_delta_mb, "cpu_time_s": None, "notes": "load"},
        {"category": "ingest", "lib": "polars", "time_s": pl_res.wall_time_s, "rss_delta_mb": pl_res.rss_delta_mb, "cpu_time_s": None, "notes": "load"},
        {"category": "rolling", "lib": "pandas", "time_s": t_pd, "rss_delta_mb": roll_pd_rss, "cpu_time_s": roll_pd_cpu, "notes": "ma/std/sharpe"},
        {"category": "rolling", "lib": "polars", "time_s": t_pl, "rss_delta_mb": roll_pl_rss, "cpu_time_s": roll_pl_cpu, "notes": "ma/std/sharpe"},
        {"category": "parallel", "lib": "pandas-threaded", "time_s": t_pd_thr, "rss_delta_mb": r_pd_thr, "cpu_time_s": par_pd_thr_cpu, "notes": "per symbol"},
        {"category": "parallel", "lib": "pandas-multiproc", "time_s": t_pd_mp, "rss_delta_mb": r_pd_mp, "cpu_time_s": par_pd_mp_cpu, "notes": "per symbol"},
        {"category": "parallel", "lib": "polars-threaded", "time_s": t_pl_thr, "rss_delta_mb": r_pl_thr, "cpu_time_s": par_pl_thr_cpu, "notes": "per symbol"},
        {"category": "parallel", "lib": "polars-multiproc", "time_s": t_pl_mp, "rss_delta_mb": r_pl_mp, "cpu_time_s": par_pl_mp_cpu, "notes": "per symbol"},
    ]

    perf_df = pd.DataFrame(rows)
    perf_csv = Path(outdir) / "performance_summary.csv"
    perf_df.to_csv(perf_csv, index=False)

    fig, ax = plt.subplots(figsize=(10, 4))
    sub = perf_df[perf_df["category"].isin(["ingest","rolling"])]
    ax.bar(sub["lib"], sub["time_s"])
    ax.set_title("Ingestion and Rolling Times (s)")
    fig.tight_layout()
    t_png = Path(outdir) / "times_basic.png"
    fig.savefig(t_png)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    sub = perf_df[perf_df["category"]=="parallel"]
    ax.bar(sub["lib"], sub["time_s"])
    ax.set_title("Parallel Execution Times (s)")
    fig.tight_layout()
    p_png = Path(outdir) / "times_parallel.png"
    fig.savefig(p_png)
    plt.close(fig)

    out = {
        "symbol": symbol,
        "charts": charts,
        "performance_csv": str(perf_csv),
        "times_basic_png": str(t_png),
        "times_parallel_png": str(p_png),
        "summary_table": rows,
    }
    with open(Path(outdir) / "report.json", "w") as f:
        json.dump(out, f, indent=2)
    return out


if __name__ == "__main__":
    r = run_report()
    print(json.dumps({
        "charts": r["charts"],
        "performance_csv": r["performance_csv"],
        "times_basic_png": r["times_basic_png"],
        "times_parallel_png": r["times_parallel_png"],
    }, indent=2))
