"""
Model training utilities for the ML trading assignment.

This module is responsible for:
  * Loading engineered features and labels
  * Selecting feature columns (using features_config.json)
  * Building scikit-learn models from model_params.json
  * Training, evaluating, and cross-validating models

The main entry point for other modules is `train_models_from_market_data`,
while the CLI in the __main__ block can be used to run experiments
from the command line.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from feature_engineering import (
    FeatureConfig as FEFeatureConfig,
    TaskType,
    generate_features_and_labels,
)


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TrainingConfig:
  """
  Configuration for model training.

  Parameters
  ----------
  feature_columns : Optional[List[str]]
      Explicit list of feature column names to use. If None, the training
      code will infer feature columns as all numeric columns except:
      date, ticker, and target.
  test_size : float
      Fraction of the data to reserve for the test set.
  random_state : int
      Random seed for reproducible train/test split and certain models.
  task : TaskType
      "classification" or "regression". Should match feature_engineering.
  cv_folds : int
      Number of cross-validation folds.
  scaler : Literal["standard", "none"]
      Whether to apply StandardScaler before the model.
  """

  feature_columns: Optional[List[str]] = None
  test_size: float = 0.2
  random_state: int = 42
  task: TaskType = "classification"
  cv_folds: int = 5
  scaler: Literal["standard", "none"] = "standard"


# ---------------------------------------------------------------------------
# Config loading helpers
# ---------------------------------------------------------------------------


def load_feature_and_training_config(
    features_config_path: str | Path,
) -> Tuple[FEFeatureConfig, TrainingConfig]:
  """
  Load feature-engineering and training configuration from a single JSON file.

  The JSON is expected to contain keys, some of which match the fields of
  `feature_engineering.FeatureConfig` (e.g. "prediction_horizon",
  "task", "sma_windows", etc.), and some additional training keys such as:

    * "feature_columns": optional list of feature names
    * "test_size": float
    * "random_state": int
    * "cv_folds": int
    * "scaler": "standard" or "none"

  Any keys that match FeatureConfig fields are used to instantiate
  FEFeatureConfig; the remaining relevant keys are used for TrainingConfig.
  """
  features_config_path = Path(features_config_path)
  with features_config_path.open("r") as f:
    cfg = json.load(f)

  if not isinstance(cfg, dict):
    raise ValueError("features_config.json must contain a JSON object.")

  # Determine which keys belong to FeatureConfig
  fe_fields = set(FEFeatureConfig.__annotations__.keys())

  fe_kwargs = {k: v for k, v in cfg.items() if k in fe_fields}

  # Instantiate FeatureConfig with any provided overrides
  fe_config = FEFeatureConfig(**fe_kwargs)

  # Training-related keys; fall back to defaults for missing ones
  training_cfg = TrainingConfig(
    feature_columns=cfg.get("feature_columns"),
    test_size=cfg.get("test_size", 0.2),
    random_state=cfg.get("random_state", 42),
    task=cfg.get("task", fe_config.task),
    cv_folds=cfg.get("cv_folds", 5),
    scaler=cfg.get("scaler", "standard"),
  )

  return fe_config, training_cfg


# ---------------------------------------------------------------------------
# Model building
# ---------------------------------------------------------------------------


def build_models_from_params(
    model_params_path: str | Path,
    task: TaskType,
) -> Dict[str, Pipeline]:
  """
  Build one or more scikit-learn models defined in model_params.json.

  Expected JSON structure (flexible, but approximately):

  {
    "models": {
      "log_reg": {
        "type": "logistic_regression",
        "C": 1.0,
        "max_iter": 1000
      },
      "rf": {
        "type": "random_forest",
        "n_estimators": 200,
        "max_depth": 5
      }
    }
  }

  The "type" key determines the underlying estimator. Supporting:
    * "logistic_regression"  -> LogisticRegression (classification)
    * "random_forest"        -> RandomForestClassifier / RandomForestRegressor
    * "linear_regression"    -> LinearRegression (regression)

  For robustness, if the file is missing or malformed, we fall back to a
  small set of sensible default models.
  """
  model_params_path = Path(model_params_path)

  if not model_params_path.exists():
    # Fallback: simple defaults
    return _default_models(task)

  try:
    with model_params_path.open("r") as f:
      data = json.load(f)
  except Exception:
    # If parsing fails, also fall back to defaults
    return _default_models(task)

  if not isinstance(data, dict) or "models" not in data:
    return _default_models(task)

  models: Dict[str, Pipeline] = {}
  for name, spec in data["models"].items():
    if not isinstance(spec, dict):
      continue
    model_type = spec.get("type", "")
    # Remove "type" so remaining keys can be passed to the estimator
    est_kwargs = {k: v for k, v in spec.items() if k != "type"}

    if task == "classification":
      if model_type == "logistic_regression":
        est = LogisticRegression(**est_kwargs)
      elif model_type == "random_forest":
        est = RandomForestClassifier(**est_kwargs)
      else:
        # Unknown model type, skip
        continue
    else:  # regression
      if model_type == "linear_regression":
        est = LinearRegression(**est_kwargs)
      elif model_type == "random_forest":
        est = RandomForestRegressor(**est_kwargs)
      else:
        # Unknown model type, skip
        continue

    # Wrap with optional scaler; actual scaler choice is applied later
    models[name] = est  # type: ignore[assignment]

  if not models:
    # If nothing usable was specified, use defaults
    return _default_models(task)

  return models


def _default_models(task: TaskType) -> Dict[str, Pipeline]:
  """
  Fallback models used if model_params.json is not present or invalid.
  """
  if task == "classification":
    return {
      "log_reg": LogisticRegression(max_iter=1000),
      "rf": RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
      ),
    }
  else:
    return {
      "lin_reg": LinearRegression(),
      "rf": RandomForestRegressor(
        n_estimators=200,
        max_depth=None,
        random_state=42,
      ),
    }


# ---------------------------------------------------------------------------
# Feature selection
# ---------------------------------------------------------------------------


def select_feature_columns(
    df: pd.DataFrame,
    explicit_features: Optional[List[str]] = None,
) -> List[str]:
  """
  Determine which columns to use as features X.

  If `explicit_features` is provided, it is returned as-is after checking
  that all requested columns exist.

  Otherwise, the default behaviour is:
    * Drop non-numeric columns
    * Drop "date", "ticker", and "target"
  """
  if explicit_features is not None:
    missing = [c for c in explicit_features if c not in df.columns]
    if missing:
      raise ValueError(f"Requested feature columns not found in DataFrame: {missing}")
    return explicit_features

  # Auto-select numeric feature columns
  non_feature_cols = {"date", "ticker", "target"}
  numeric_cols = df.select_dtypes(include=[np.number]).columns
  feature_cols = [c for c in numeric_cols if c not in non_feature_cols]
  if not feature_cols:
    raise ValueError("No feature columns found. Check your engineered dataset.")
  return feature_cols


# ---------------------------------------------------------------------------
# Training and evaluation
# ---------------------------------------------------------------------------


def train_and_evaluate_models(
    df: pd.DataFrame,
    training_config: TrainingConfig,
    model_params_path: str | Path,
) -> Dict[str, Dict[str, object]]:
  """
  Train and evaluate models on an engineered feature DataFrame.

  Parameters
  ----------
  df : pd.DataFrame
      Must contain a "target" column and any number of feature columns.
  training_config : TrainingConfig
      Training configuration (feature selection, CV, etc.).
  model_params_path : str or Path
      Path to model_params.json.

  Returns
  -------
  Dict[str, Dict[str, object]]
      Mapping from model name to a dictionary containing:
        * "pipeline": the fitted scikit-learn Pipeline
        * "metrics":  dict of test metrics
        * "cv_scores": list or array of cross-validation scores
  """
  task = training_config.task

  if "target" not in df.columns:
    raise ValueError("Engineered DataFrame must contain a 'target' column.")

  feature_cols = select_feature_columns(df, training_config.feature_columns)
  X = df[feature_cols].to_numpy()
  y = df["target"].to_numpy()

  # Train/test split
  stratify = y if task == "classification" else None
  X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=training_config.test_size,
    random_state=training_config.random_state,
    stratify=stratify,
  )

  # Build base estimators from JSON
  base_models = build_models_from_params(model_params_path, task)

  results: Dict[str, Dict[str, object]] = {}

  # Choose CV splitter
  if task == "classification":
    cv = StratifiedKFold(
      n_splits=training_config.cv_folds,
      shuffle=True,
      random_state=training_config.random_state,
    )
    cv_scoring = "accuracy"
  else:
    cv = KFold(
      n_splits=training_config.cv_folds,
      shuffle=True,
      random_state=training_config.random_state,
    )
    cv_scoring = "neg_mean_squared_error"

  for name, base_estimator in base_models.items():
    # Assemble pipeline with optional scaler
    steps = []
    if training_config.scaler == "standard":
      steps.append(("scaler", StandardScaler()))
    steps.append(("model", base_estimator))
    pipeline = Pipeline(steps)

    # Fit model
    pipeline.fit(X_train, y_train)

    # Predictions on test set
    y_pred = pipeline.predict(X_test)

    if task == "classification":
      metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
      }
    else:
      mse = mean_squared_error(y_test, y_pred)
      metrics = {
        "mse": float(mse),
        "rmse": float(np.sqrt(mse)),
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "r2": float(r2_score(y_test, y_pred)),
      }

    # Cross-validation scores on the full dataset (X, y)
    cv_scores = cross_val_score(
      pipeline,
      X,
      y,
      cv=cv,
      scoring=cv_scoring,
    )

    results[name] = {
      "pipeline": pipeline,
      "metrics": metrics,
      "cv_scores": cv_scores,
    }

  return results


# ---------------------------------------------------------------------------
# High-level helper for use by other modules / scripts
# ---------------------------------------------------------------------------


def train_models_from_market_data(
    market_data_path: str | Path,
    features_config_path: str | Path,
    model_params_path: str | Path,
    tickers_path: Optional[str | Path] = None,
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, object]]]:
  """
  High-level convenience function:
    * Run feature engineering
    * Train and evaluate models

  Parameters
  ----------
  market_data_path : str or Path
      Path to market_data_ml.csv.
  features_config_path : str or Path
      Path to features_config.json.
  model_params_path : str or Path
      Path to model_params.json.
  tickers_path : str or Path, optional
      Path to a CSV with tickers to include.

  Returns
  -------
  (df_features, results)
    df_features : pd.DataFrame
        Engineered features and target.
    results : dict
        Output of `train_and_evaluate_models`.
  """
  fe_config, training_config = load_feature_and_training_config(features_config_path)

  df_features = generate_features_and_labels(
    market_data_path=str(market_data_path),
    tickers_path=str(tickers_path) if tickers_path is not None else None,
    config=fe_config,
  )

  results = train_and_evaluate_models(
    df_features,
    training_config=training_config,
    model_params_path=model_params_path,
  )
  return df_features, results


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(description="Train ML models on market data.")
  parser.add_argument(
    "--market-data",
    type=str,
    required=True,
    help="Path to market_data_ml.csv",
  )
  parser.add_argument(
    "--features-config",
    type=str,
    default="features_config.json",
    help="Path to features_config.json (default: features_config.json)",
  )
  parser.add_argument(
    "--model-params",
    type=str,
    default="model_params.json",
    help="Path to model_params.json (default: model_params.json)",
  )
  parser.add_argument(
    "--tickers",
    type=str,
    default=None,
    help="Optional path to tickers.csv (subset of tickers to keep).",
  )
  parser.add_argument(
    "--metrics-out",
    type=str,
    default=None,
    help="Optional path to save model metrics as JSON.",
  )

  args = parser.parse_args()

  df_features, results = train_models_from_market_data(
    market_data_path=args.market_data,
    features_config_path=args.features_config,
    model_params_path=args.model_params,
    tickers_path=args.tickers,
  )

  # Pretty-print metrics to the console
  print("Engineered dataset shape:", df_features.shape)
  print()
  for name, info in results.items():
    print(f"Model: {name}")
    print("  Test metrics:")
    for k, v in info["metrics"].items():
      print(f"    {k}: {v}")
    cv_scores = info["cv_scores"]
    print("  CV scores:", cv_scores)
    print("  CV mean:", float(np.mean(cv_scores)))
    print("  CV std: ", float(np.std(cv_scores)))
    print()

  # Optionally dump metrics to JSON (without the fitted pipelines)
  if args.metrics_out is not None:
    serialisable = {}
    for name, info in results.items():
      serialisable[name] = {
        "metrics": info["metrics"],
        "cv_scores": list(map(float, info["cv_scores"])),
      }
    with open(args.metrics_out, "w") as f:
      json.dump(serialisable, f, indent=2)
    print(f"Saved metrics to {args.metrics_out}")
