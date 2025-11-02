

from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
import polars as pl

@dataclass
class PosResult:
  symbol: str
  value: float
  volatility: float
  drawdown: float
  latest_price: float

def _to_pandas(df_any: Any) -> pd.DataFrame:
  if isinstance(df_any, pd.DataFrame):
    return df_any
  if isinstance(df_any, pl.DataFrame):
    return df_any.to_pandas()
  raise TypeError("price data must be pandas or polars DataFrame")

def _position_metrics(df: pd.DataFrame, symbol: str, quantity: float, window: int, min_periods: int) -> PosResult:
  s = df[df["symbol"] == symbol].sort_values("timestamp")
  if s.empty:
    return PosResult(symbol, 0.0, float("nan"), float("nan"), float("nan"))
  price = s["price"].astype(float)
  latest = float(price.iloc[-1])
  ret = price.pct_change()
  vol = float(ret.rolling(window, min_periods=min_periods).std(ddof=0).iloc[-1])
  peak = price.cummax()
  dd_series = (price / peak - 1.0)
  mdd = float(dd_series.min())
  return PosResult(symbol, quantity * latest, vol, mdd, latest)

def _position_worker(args: Tuple[pd.DataFrame, str, float, int, int]) -> PosResult:
  df, sym, qty, window, minp = args
  return _position_metrics(df, sym, qty, window, minp)

def compute_positions_parallel(price_df_any: Any, positions: List[Dict[str, Any]], window: int = 20, min_periods: int = 20, max_workers: Optional[int] = None) -> List[PosResult]:
  df = _to_pandas(price_df_any)
  tasks = []
  for pos in positions:
    sym = pos["symbol"]
    qty = float(pos.get("quantity", 0.0))
    tasks.append((df, sym, qty, window, min_periods))
  out: List[PosResult] = []
  with ProcessPoolExecutor(max_workers=max_workers) as ex:
    futs = [ex.submit(_position_worker, t) for t in tasks]
    for f in as_completed(futs):
      out.append(f.result())
  return out

def compute_positions_sequential(price_df_any: Any, positions: List[Dict[str, Any]], window: int = 20, min_periods: int = 20) -> List[PosResult]:
  df = _to_pandas(price_df_any)
  out = []
  for pos in positions:
    out.append(_position_metrics(df, pos["symbol"], float(pos.get("quantity", 0.0)), window, min_periods))
  return out

def _to_dict_pos(p: PosResult) -> Dict[str, Any]:
  return {"symbol": p.symbol, "value": round(p.value, 2), "volatility": _round_or_nan(p.volatility, 6), "drawdown": _round_or_nan(p.drawdown, 6)}

def _round_or_nan(x: float, nd: int) -> Optional[float]:
  if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
    return None
  return round(float(x), nd)

def _aggregate(vols_vals: List[Tuple[float, float]]) -> float:
  num = 0.0
  den = 0.0
  for v, val in vols_vals:
    if v is None or (isinstance(v, float) and math.isnan(v)):
      continue
    w = max(val, 0.0)
    num += w * v
    den += w
  return num / den if den > 0 else float("nan")

def _merge_children(children: List[Dict[str, Any]]) -> Tuple[float, float, float]:
  total = sum(c.get("total_value", 0.0) for c in children)
  vols_vals = []
  dds = []
  for c in children:
    vols_vals.append((c.get("aggregate_volatility", float("nan")), c.get("total_value", 0.0)))
    dds.append(c.get("max_drawdown", 0.0))
  agg_vol = _aggregate(vols_vals)
  worst_dd = min(dds) if dds else float("nan")
  return total, agg_vol, worst_dd

def build_portfolio(price_df_any: Any, portfolio: Dict[str, Any], window: int = 20, min_periods: int = 20, parallel: bool = True, max_workers: Optional[int] = None) -> Dict[str, Any]:
  df = _to_pandas(price_df_any)
  name = portfolio.get("name", "Portfolio")
  positions = portfolio.get("positions", [])
  subs = portfolio.get("sub_portfolios", [])

  if parallel and positions:
    pos_results = compute_positions_parallel(df, positions, window, min_periods, max_workers)
  else:
    pos_results = compute_positions_sequential(df, positions, window, min_periods)

  pos_dicts = [_to_dict_pos(p) for p in pos_results]
  pos_total = sum(p.value for p in pos_results)
  pos_vol = _aggregate([(p.volatility, p.value) for p in pos_results]) if pos_results else float("nan")
  pos_dd = min((p.drawdown for p in pos_results), default=float("nan"))

  sub_dicts = []
  for sp in subs:
    sub_dicts.append(build_portfolio(df, sp, window, min_periods, parallel, max_workers))

  subs_total, subs_vol, subs_dd = _merge_children(sub_dicts)

  total_value = pos_total + subs_total
  # combine vols by value weights
  vol_list = []
  if not math.isnan(pos_vol):
    vol_list.append((pos_vol, pos_total))
  if not math.isnan(subs_vol):
    vol_list.append((subs_vol, subs_total))
  aggregate_volatility = _aggregate(vol_list)
  # worst drawdown among positions and subs
  dd_candidates = [x for x in [pos_dd, subs_dd] if not (isinstance(x, float) and math.isnan(x))]
  max_drawdown = min(dd_candidates) if dd_candidates else float("nan")

  out = {
    "name": name,
    "total_value": round(total_value, 2),
    "aggregate_volatility": _round_or_nan(aggregate_volatility, 6),
    "max_drawdown": _round_or_nan(max_drawdown, 6),
    "positions": pos_dicts,
  }
  if sub_dicts:
    out["sub_portfolios"] = sub_dicts
  return out