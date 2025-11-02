from __future__ import annotations
import argparse
import json
from reporting import run_report

def main():
    p = argparse.ArgumentParser(description="Run the parallel analytics report")
    p.add_argument("--data", default="data/market_data-1.csv")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--outdir", default="reports")
    p.add_argument("--profile", action="store_true", default=False)
    args = p.parse_args()

    if args.profile:
        from memory_profiler import memory_usage
        mem_usage, res = memory_usage((run_report, (), {"data_path": args.data, "symbol": args.symbol, "outdir": args.outdir}), retval=True)
        print("Report written:")
        print(json.dumps({
            "charts": res["charts"],
            "performance_csv": res["performance_csv"],
            "times_basic_png": res["times_basic_png"],
            "times_parallel_png": res["times_parallel_png"],
        }, indent=2))
        print(f"Peak memory usage: {max(mem_usage)} MiB")
    else:
        res = run_report(data_path=args.data, symbol=args.symbol, outdir=args.outdir)
        print("Report written:")
        print(json.dumps({
            "charts": res["charts"],
            "performance_csv": res["performance_csv"],
            "times_basic_png": res["times_basic_png"],
            "times_parallel_png": res["times_parallel_png"],
        }, indent=2))

if __name__ == "__main__":
    main()