"""
Signal generation utilities for the ML trading assignment.

This module is responsible for:
  * Converting model outputs (probabilities or predicted returns)
    into discrete trading signals (-1, 0, +1).
  * Providing helpers that apply a trained scikit-learn pipeline
    to an engineered feature DataFrame and attach signal columns.

The core idea is:
  - classification models: use predicted probability of the "up" class
    to decide when to go long / short / flat.
  - regression models: use predicted future returns directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator

from feature_engineering import TaskType
from train_model import TrainingConfig, select_feature_columns


@dataclass
class SignalConfig:
  """
  Configuration for mapping model scores to trading signals.

  Parameters
  ----------
  buy_threshold : float
      Threshold above which we take a +1 (long) signal.

      * For classification: interpreted as probability P(up) > buy_threshold.
      * For regression: interpreted as predicted return > buy_threshold.

  sell_threshold : float
      Threshold below which we take a -1 (short) signal if `allow_short`
      is True.

      * For classification: interpreted as probability P(up) < sell_threshold.
      * For regression: interpreted as predicted return < -sell_threshold
        (i.e. symmetric band around zero).

  allow_short : bool
      If False, only +1 and 0 signals are produced; no -1 signals.

  neutral_as_zero : bool
      If True, scores in between the thresholds lead to 0 (flat) signals.
      If False, these are nudged to the nearest side (rarely desired).
  """

  buy_threshold: float = 0.55
  sell_threshold: float = 0.45
  allow_short: bool = False
  neutral_as_zero: bool = True


# ---------------------------------------------------------------------------
# Core score → signal mapping
# ---------------------------------------------------------------------------


def scores_to_signals(
    scores: np.ndarray,
    task: TaskType,
    config: SignalConfig,
) -> np.ndarray:
  """
  Map continuous model scores to discrete signals {-1, 0, +1}.

  Parameters
  ----------
  scores : np.ndarray
      1D array of model scores:
        * classification: probabilities of the positive ("up") class
        * regression: predicted future returns
  task : TaskType
      "classification" or "regression"
  config : SignalConfig
      Thresholds and short-selling behaviour.

  Returns
  -------
  np.ndarray
      1D array of integer signals in {-1, 0, +1}.
  """
  scores = np.asarray(scores).ravel()
  signals = np.zeros_like(scores, dtype=int)

  if task == "classification":
    # Probabilities should be in [0,1]
    buy_mask = scores >= config.buy_threshold
    signals[buy_mask] = 1

    if config.allow_short:
      sell_mask = scores <= config.sell_threshold
      signals[sell_mask] = -1

    if not config.neutral_as_zero:
      # Force ambiguous region to the closest side
      neutral_mask = ~(buy_mask | (signals == -1))
      signals[neutral_mask] = np.where(
        scores[neutral_mask] >= 0.5,
        1,
        -1 if config.allow_short else 0,
      )

  else:  # regression: scores are predicted returns
    buy_mask = scores >= config.buy_threshold
    signals[buy_mask] = 1

    if config.allow_short:
      sell_mask = scores <= -config.sell_threshold
      signals[sell_mask] = -1

    if not config.neutral_as_zero:
      neutral_mask = ~(buy_mask | (signals == -1))
      # Push towards sign of the prediction
      signals[neutral_mask] = np.where(
        scores[neutral_mask] >= 0,
        1,
        -1 if config.allow_short else 0,
      )

  return signals


# ---------------------------------------------------------------------------
# Model → scores
# ---------------------------------------------------------------------------


def model_scores(
    model: BaseEstimator,
    X: np.ndarray,
    task: TaskType,
) -> np.ndarray:
  """
  Obtain a 1D array of "scores" from a fitted scikit-learn estimator.

  For classification, the preferred score is the probability of the
  positive class (class label 1). If `predict_proba` is not available
  we fall back to `decision_function` or finally `predict`.

  For regression, this is simply `predict(X)`.
  """
  if task == "classification":
    # Try probability of class 1
    if hasattr(model, "predict_proba"):
      proba = model.predict_proba(X)
      if proba.ndim == 2 and proba.shape[1] >= 2:
        return proba[:, 1]
      # If it's 1D or oddly shaped, fall through to other methods

    # Try decision_function
    if hasattr(model, "decision_function"):
      scores = model.decision_function(X)
      scores = np.asarray(scores).ravel()
      # Map scores to (0,1) via logistic transform for easier thresholding
      return 1.0 / (1.0 + np.exp(-scores))

    # Fallback: use predicted labels (0/1)
    preds = model.predict(X)
    return np.asarray(preds).ravel()

  else:
    # Regression: just use predicted returns
    preds = model.predict(X)
    return np.asarray(preds).ravel()


# ---------------------------------------------------------------------------
# Apply a trained pipeline to a feature DataFrame
# ---------------------------------------------------------------------------


def _feature_matrix_for_pipeline(
    df_features: pd.DataFrame,
    training_config: TrainingConfig,
    estimator: BaseEstimator,
) -> np.ndarray:
  """
  Build an X matrix for a fitted pipeline/estimator such that the number of
  columns matches what the estimator was trained on.

  Preference order:
    1. If training_config.feature_columns is set, use those columns.
    2. Else, if estimator has `n_features_in_`, take that many numeric
       columns (in the same order as during training).
    3. Else, fall back to automatic feature selection.
  """
  # Case 1: explicit feature list from training time
  if training_config.feature_columns is not None:
    cols = training_config.feature_columns
    missing = [c for c in cols if c not in df_features.columns]
    if missing:
      raise ValueError(f"Feature columns missing at inference time: {missing}")
    return df_features[cols].to_numpy()

  # Case 2: introspect estimator's input dimension
  n_in = getattr(estimator, "n_features_in_", None)
  if n_in is not None:
    # Take only the first n_in numeric columns (same heuristic as training)
    numeric_cols = df_features.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) < int(n_in):
      raise ValueError(
        f"Estimator expects {n_in} numeric features, "
        f"but only found {len(numeric_cols)}."
      )
    cols = list(numeric_cols[: int(n_in)])
    return df_features[cols].to_numpy()

  # Case 3: fallback – auto-select features
  cols = select_feature_columns(df_features, explicit_features=None)
  return df_features[cols].to_numpy()


def attach_signals_for_model(
    df_features: pd.DataFrame,
    pipeline: BaseEstimator,
    training_config: TrainingConfig,
    signal_config: Optional[SignalConfig] = None,
    model_name: str = "model",
) -> pd.DataFrame:
  """
  Apply a fitted pipeline to an engineered feature DataFrame and
  attach columns with scores and signals.

  This function does *not* refit the model; it assumes `pipeline` has
  already been trained (e.g., via `train_model.train_and_evaluate_models`).

  Parameters
  ----------
  df_features : pd.DataFrame
      Engineered features including "target". The DataFrame is not modified
      in-place; a copy with extra columns is returned.
  pipeline : BaseEstimator
      Fitted scikit-learn pipeline (typically with scaler + model).
  training_config : TrainingConfig
      Configuration used for feature selection and task type.
  signal_config : SignalConfig, optional
      Threshold configuration. If None, uses default SignalConfig().
  model_name : str
      Base name used for new columns:
        * f"{model_name}_score"
        * f"{model_name}_signal"

  Returns
  -------
  pd.DataFrame
      Copy of df_features with added score and signal columns.
  """
  if signal_config is None:
    signal_config = SignalConfig()

  # Build feature matrix with the same dimensionality as during training
  X_all = _feature_matrix_for_pipeline(df_features, training_config, pipeline)

  # The pipeline itself exposes predict/predict_proba, so we can treat it
  # as the model directly.
  scores = model_scores(pipeline, X_all, task=training_config.task)
  signals = scores_to_signals(scores, task=training_config.task, config=signal_config)

  out = df_features.copy()
  out[f"{model_name}_score"] = scores
  out[f"{model_name}_signal"] = signals.astype(int)
  return out


def attach_signals_for_all_models(
    df_features: pd.DataFrame,
    training_config: TrainingConfig,
    trained_models: Dict[str, Dict[str, object]],
    signal_config: Optional[SignalConfig] = None,
) -> pd.DataFrame:
  """
  Convenience helper: attach score/signal columns for each trained model.

  Parameters
  ----------
  df_features : pd.DataFrame
      Engineered features (no score/signal columns yet).
  training_config : TrainingConfig
      Training configuration used for the models.
  trained_models : dict
      The `results` dict returned by `train_model.train_and_evaluate_models`
      or `train_model.train_models_from_market_data`, mapping model name
      to a dict containing a "pipeline" key.
  signal_config : SignalConfig, optional
      Thresholds to use for all models. If None, uses the default.

  Returns
  -------
  pd.DataFrame
      Copy of df_features with additional columns:
        * "<model_name>_score"
        * "<model_name>_signal"
      for each model.
  """
  if signal_config is None:
    signal_config = SignalConfig()

  base_df = df_features  # keep original features separate
  out = df_features.copy()

  for name, info in trained_models.items():
    pipeline = info.get("pipeline")
    if pipeline is None:
      continue

    tmp = attach_signals_for_model(
      df_features=base_df,
      pipeline=pipeline,  # type: ignore[arg-type]
      training_config=training_config,
      signal_config=signal_config,
      model_name=name,
    )
    # Only copy over the new columns to avoid feature drift
    out[f"{name}_score"] = tmp[f"{name}_score"]
    out[f"{name}_signal"] = tmp[f"{name}_signal"]

  return out
