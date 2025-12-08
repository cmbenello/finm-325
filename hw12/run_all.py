"""
End-to-end driver script for the ML trading assignment.

This script:
  1. Loads configs + raw OHLCV data
  2. Runs feature engineering
  3. Trains models (using model_params.json)
  4. Generates trading signals from model predictions
  5. Backtests the strategy using those signals
  6. Optionally saves intermediate CSVs and summary JSON

Typical usage from the repo root:

    python run_all.py \
      --market-data market_data_ml.csv \
      --tickers tickers-1.csv \
      --features-config features_config.json \
      --model-params model_params.json \
      --signal-model rf

All arguments have sensible defaults so you can also just run:

    python run_all.py --market-data market_data_ml.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Local modules
from feature_engineering import generate_features_and_labels
from train_model import (
    load_feature_and_training_config,
    train_and_evaluate_models,
)
from signal_generator import (
    SignalConfig,
    attach_signals_for_all_models,
)
from backtest import (
    BacktestConfig,
    backtest_multi_ticker_equal_weight,
    backtest_single_ticker,
)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    market_data_path: str | Path,
    features_config_path: str | Path,
    model_params_path: str | Path,
    tickers_path: Optional[str | Path] = None,
    buy_threshold: float = 0.55,
    sell_threshold: float = 0.45,
    allow_short: bool = False,
    initial_capital: float = 100_000.0,
    signal_model: Optional[str] = None,
    out_features: Optional[str | Path] = None,
    out_signals: Optional[str | Path] = None,
    summary_out: Optional[str | Path] = None,
) -> None:
  """
  Run the full ML → signals → backtest pipeline.

  Parameters
  ----------
  market_data_path : str or Path
      Path to market_data_ml.csv (or similar OHLCV file).
  features_config_path : str or Path
      Path to features_config.json.
  model_params_path : str or Path
      Path to model_params.json.
  tickers_path : str or Path, optional
      Optional path to a CSV listing tickers to include.
  buy_threshold, sell_threshold, allow_short :
      Parameters forwarded to SignalConfig.
  initial_capital : float
      Starting portfolio value for the backtest.
  signal_model : str, optional
      Name of the model whose signals will be used for backtesting.
      If None, the first trained model is used.
  out_features : str or Path, optional
      If provided, save engineered features + target as CSV.
  out_signals : str or Path, optional
      If provided, save DataFrame with signals as CSV.
  summary_out : str or Path, optional
      If provided, save backtest + model metrics summary as JSON.
  """
  market_data_path = Path(market_data_path)
  features_config_path = Path(features_config_path)
  model_params_path = Path(model_params_path)
  tickers_path = Path(tickers_path) if tickers_path is not None else None

  # 1) Load configs (feature + training)
  fe_config, training_config = load_feature_and_training_config(features_config_path)

  print("=== Step 1: Feature engineering ===")
  df_features = generate_features_and_labels(
    market_data_path=str(market_data_path),
    tickers_path=str(tickers_path) if tickers_path is not None else None,
    config=fe_config,
  )
  print(f"Engineered features shape: {df_features.shape}")

  if out_features is not None:
    out_features = Path(out_features)
    df_features.to_csv(out_features, index=False)
    print(f"Saved engineered features to {out_features}")

  # 2) Train models
  print("\n=== Step 2: Model training & evaluation ===")
  results = train_and_evaluate_models(
    df_features,
    training_config=training_config,
    model_params_path=model_params_path,
  )
  for name, info in results.items():
    print(f"Model: {name}")
    print("  Test metrics:")
    for k, v in info["metrics"].items():
      print(f"    {k}: {v}")
    cv_scores = info["cv_scores"]
    print("  CV mean:", float(np.mean(cv_scores)))
    print("  CV std: ", float(np.std(cv_scores)))
    print()

  # 3) Signal generation
  print("=== Step 3: Signal generation ===")
  sig_cfg = SignalConfig(
    buy_threshold=buy_threshold,
    sell_threshold=sell_threshold,
    allow_short=allow_short,
  )
  df_with_signals = attach_signals_for_all_models(
    df_features=df_features,
    training_config=training_config,
    trained_models=results,
    signal_config=sig_cfg,
  )
  print("Signal columns added:")
  signal_cols = [c for c in df_with_signals.columns if c.endswith("_signal")]
  print("  ", signal_cols)

  if out_signals is not None:
    out_signals = Path(out_signals)
    df_with_signals.to_csv(out_signals, index=False)
    print(f"Saved DataFrame with signals to {out_signals}")

  # Decide which model's signals to backtest
  if signal_model is None:
    # Use the first model in results
    if not results:
      raise RuntimeError("No trained models available for backtesting.")
    signal_model = next(iter(results.keys()))
    print(f"No --signal-model specified; defaulting to '{signal_model}'.")

  signal_col = f"{signal_model}_signal"
  if signal_col not in df_with_signals.columns:
    raise ValueError(
      f"Signal column '{signal_col}' not found. "
      f"Available signal columns: {signal_cols}"
    )

  # 4) Backtest each model separately
  print("\n=== Step 4: Backtest for each model ===")

  if "date" in df_with_signals.columns:
    df_with_signals["date"] = pd.to_datetime(df_with_signals["date"])

  backtest_results: dict[str, dict[str, object]] = {}

  for model_name in results.keys():
    sig_col = f"{model_name}_signal"
    if sig_col not in df_with_signals.columns:
      print(f"Skipping backtest for {model_name}: no signal column '{sig_col}'.")
      continue

    print(f"\n--- Backtest using signals from '{model_name}' ---")
    bt_cfg = BacktestConfig(
      initial_capital=initial_capital,
      price_col="close",
      signal_col=sig_col,
    )

    if "ticker" in df_with_signals.columns:
      portfolio_res, per_ticker_res = backtest_multi_ticker_equal_weight(
        df_with_signals,
        config=bt_cfg,
      )
      print("Portfolio (equal-weight) summary:")
      for k, v in portfolio_res.summary.items():
        print(f"  {k}: {v}")
      print("\nPer-ticker summaries:")
      for tkr, res in per_ticker_res.items():
        print(f"  TICKER {tkr}:")
        for k, v in res.summary.items():
          print(f"    {k}: {v}")
        print()

      backtest_results[model_name] = {
        "portfolio": portfolio_res,
        "per_ticker": per_ticker_res,
      }
    else:
      # Single-ticker case
      res = backtest_single_ticker(df_with_signals, config=bt_cfg)
      print("Single-ticker backtest summary:")
      for k, v in res.summary.items():
        print(f"  {k}: {v}")

      backtest_results[model_name] = {
        "single": res,
      }

  # 5) Visualisations / comparison plots
  print("\n=== Step 5: Generating comparison plots ===")

  figure_paths: list[str] = []

  # 5a. Portfolio equity curves (multi-ticker only)
  multi_models = {
    m: v for m, v in backtest_results.items() if "portfolio" in v
  }
  if multi_models:
    equity_df_list = []
    for m, res_dict in multi_models.items():
      port_res = res_dict["portfolio"]
      port_df = port_res.df
      if "date" in port_df.columns:
        s = port_df.set_index("date")["portfolio_equity"].rename(m)
        equity_df_list.append(s)

    if equity_df_list:
      equity_df = pd.concat(equity_df_list, axis=1).sort_index()
      plt.figure()
      equity_df.plot()
      plt.xlabel("Date")
      plt.ylabel("Portfolio equity")
      plt.title("Portfolio equity curves by model")
      plt.tight_layout()
      eq_path = "equity_curves_portfolio.png"
      plt.savefig(eq_path)
      plt.close()
      figure_paths.append(eq_path)
      print(f"Saved portfolio equity curve comparison to {eq_path}")

  # 5b. Confusion matrices for classification models
  for model_name, info in results.items():
    metrics = info.get("metrics", {})
    cm = metrics.get("confusion_matrix")
    if cm is None:
      continue
    cm_arr = np.asarray(cm)
    if cm_arr.shape != (2, 2):
      continue

    plt.figure()
    plt.imshow(cm_arr, interpolation="nearest")
    plt.title(f"Confusion matrix: {model_name}")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    # Annotate counts in each cell
    for i in range(2):
      for j in range(2):
        plt.text(
          j,
          i,
          str(cm_arr[i, j]),
          ha="center",
          va="center",
        )
    plt.colorbar()
    plt.tight_layout()
    cm_path = f"confusion_{model_name}.png"
    plt.savefig(cm_path)
    plt.close()
    figure_paths.append(cm_path)
    print(f"Saved confusion matrix for {model_name} to {cm_path}")

  # 5c. Feature importance for a tree-based model (e.g., random forest)
  if "rf" in results:
    rf_pipeline = results["rf"].get("pipeline")
    if rf_pipeline is not None and hasattr(rf_pipeline, "named_steps"):
      rf_est = rf_pipeline.named_steps.get("model")
    else:
      rf_est = None

    if rf_est is not None and hasattr(rf_est, "feature_importances_"):
      importances = np.asarray(rf_est.feature_importances_)
      feature_names = training_config.feature_columns
      if feature_names is None:
        # Fallback: infer feature columns the same way as during training
        from train_model import select_feature_columns

        feature_names = select_feature_columns(df_features, explicit_features=None)

      feature_names = list(feature_names)
      # Align lengths defensively
      n = min(len(importances), len(feature_names))
      plt.figure()
      indices = np.argsort(importances[:n])[::-1]
      ordered_importances = importances[indices]
      ordered_names = [feature_names[i] for i in indices]

      plt.bar(range(n), ordered_importances)
      plt.xticks(range(n), ordered_names, rotation=90)
      plt.ylabel("Importance")
      plt.title("RandomForest feature importances")
      plt.tight_layout()
      fi_path = "feature_importance_rf.png"
      plt.savefig(fi_path)
      plt.close()
      figure_paths.append(fi_path)
      print(f"Saved RF feature importance plot to {fi_path}")

  if figure_paths:
    print("\nGenerated figures:")
    for p in figure_paths:
      print(f"  {p}")
  else:
    print("No figures were generated (e.g., no portfolio results or confusion matrices).")

  # 6) Optional: write summary JSON
  summary_payload = {
    "training_config": {
      "task": training_config.task,
      "test_size": training_config.test_size,
      "cv_folds": training_config.cv_folds,
    },
    "signal_config": {
      "buy_threshold": buy_threshold,
      "sell_threshold": sell_threshold,
      "allow_short": allow_short,
    },
    "backtest_config": {
      "initial_capital": initial_capital,
      "price_col": "close",
    },
    "model_metrics": {
      name: {
        "metrics": info["metrics"],
        "cv_scores": list(map(float, info["cv_scores"])),
      }
      for name, info in results.items()
    },
    "backtests": {
      model_name: {
        "portfolio_summary": (
          res_dict["portfolio"].summary if "portfolio" in res_dict else None
        ),
        "single_summary": (
          res_dict["single"].summary if "single" in res_dict else None
        ),
      }
      for model_name, res_dict in backtest_results.items()
    },
    "figures": figure_paths,
  }

  if summary_out is not None:
    summary_out = Path(summary_out)
    with summary_out.open("w") as f:
      json.dump(summary_payload, f, indent=2)
    print(f"\nSaved summary JSON to {summary_out}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Run full ML → signals → backtest pipeline."
  )
  parser.add_argument(
    "--market-data",
    type=str,
    required=True,
    help="Path to market_data_ml.csv.",
  )
  parser.add_argument(
    "--tickers",
    type=str,
    default=None,
    help="Optional path to tickers-*.csv to subset tickers.",
  )
  parser.add_argument(
    "--features-config",
    type=str,
    default="features_config.json",
    help="Path to features_config.json (default: features_config.json).",
  )
  parser.add_argument(
    "--model-params",
    type=str,
    default="model_params.json",
    help="Path to model_params.json (default: model_params.json).",
  )
  parser.add_argument(
    "--buy-threshold",
    type=float,
    default=0.55,
    help="Buy threshold for scores (default: 0.55).",
  )
  parser.add_argument(
    "--sell-threshold",
    type=float,
    default=0.45,
    help="Sell/short threshold for scores (default: 0.45).",
  )
  parser.add_argument(
    "--allow-short",
    action="store_true",
    help="If set, enable short signals (-1).",
  )
  parser.add_argument(
    "--initial-capital",
    type=float,
    default=100_000.0,
    help="Initial capital for backtest (default: 100000).",
  )
  parser.add_argument(
    "--signal-model",
    type=str,
    default=None,
    help="Name of the model whose signals to backtest "
    "(must match a key in model_params.json; default: first model).",
  )
  parser.add_argument(
    "--out-features",
    type=str,
    default=None,
    help="Optional path to save engineered features as CSV.",
  )
  parser.add_argument(
    "--out-signals",
    type=str,
    default=None,
    help="Optional path to save DataFrame with signals as CSV.",
  )
  parser.add_argument(
    "--summary-out",
    type=str,
    default=None,
    help="Optional path to save training + backtest summary as JSON.",
  )

  args = parser.parse_args()

  run_pipeline(
    market_data_path=args.market_data,
    features_config_path=args.features_config,
    model_params_path=args.model_params,
    tickers_path=args.tickers,
    buy_threshold=args.buy_threshold,
    sell_threshold=args.sell_threshold,
    allow_short=args.allow_short,
    initial_capital=args.initial_capital,
    signal_model=args.signal_model,
    out_features=args.out_features,
    out_signals=args.out_signals,
    summary_out=args.summary_out,
  )


if __name__ == "__main__":
  main()
