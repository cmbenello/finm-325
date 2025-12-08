"""
Basic tests for the ML trading pipeline.

These are not meant to be exhaustive, but they validate that the main
pieces of the assignment work together and produce sensible outputs:

- Feature generation and label creation
- Model training and evaluation
- Signal generation
- Backtest output shapes and key summary fields
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from feature_engineering import generate_features_and_labels
from train_model import (
    load_feature_and_training_config,
    train_and_evaluate_models,
)
from signal_generator import (
    SignalConfig,
    scores_to_signals,
    attach_signals_for_all_models,
)
from backtest import (
    BacktestConfig,
    backtest_multi_ticker_equal_weight,
    backtest_single_ticker,
)


ROOT = Path(__file__).parent
MARKET_DATA = ROOT / "market_data_ml.csv"
TICKERS = ROOT / "tickers-1.csv"
FEATURES_CONFIG = ROOT / "features_config.json"
MODEL_PARAMS = ROOT / "model_params.json"


def test_feature_engineering_basic():
    """Feature engineering runs and produces sane outputs."""
    fe_config, training_config = load_feature_and_training_config(FEATURES_CONFIG)

    df = generate_features_and_labels(
        market_data_path=str(MARKET_DATA),
        tickers_path=str(TICKERS),
        config=fe_config,
    )

    # Non-empty and contains expected key columns
    assert not df.empty
    assert "date" in df.columns
    assert "ticker" in df.columns
    assert "target" in df.columns

    # Targets should be binary for the classification setup
    unique_targets = set(df["target"].unique())
    assert unique_targets.issubset({0, 1})

    # At least one engineered feature beyond the raw OHLCV + label
    base_cols = {"date", "ticker", "open", "high", "low", "close", "volume", "target"}
    engineered_cols = [c for c in df.columns if c not in base_cols]
    assert len(engineered_cols) > 0

    # No NaNs in the columns used for features
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    assert df[numeric_cols].notna().all().all()


def test_model_training_and_metrics():
    """Models train successfully and return metrics and CV scores."""
    fe_config, training_config = load_feature_and_training_config(FEATURES_CONFIG)

    df = generate_features_and_labels(
        market_data_path=str(MARKET_DATA),
        tickers_path=str(TICKERS),
        config=fe_config,
    )

    results = train_and_evaluate_models(
        df,
        training_config=training_config,
        model_params_path=str(MODEL_PARAMS),
    )

    # We expect at least logistic regression and random forest
    assert "log_reg" in results
    assert "rf" in results

    for name, info in results.items():
        # Must contain a fitted pipeline
        assert "pipeline" in info
        pipeline = info["pipeline"]
        assert hasattr(pipeline, "predict")

        # Metrics should include accuracy (classification task)
        metrics = info.get("metrics", {})
        assert "accuracy" in metrics

        # CV scores should be a non-empty list
        cv_scores = info.get("cv_scores", [])
        assert isinstance(cv_scores, (list, np.ndarray))
        assert len(cv_scores) == training_config.cv_folds


def test_scores_to_signals_classification():
    """Unit test for scores_to_signals mapping (classification)."""
    scores = np.array([0.2, 0.48, 0.51, 0.8])
    cfg = SignalConfig(buy_threshold=0.55, sell_threshold=0.45, allow_short=True)

    # task is passed as a string through TrainingConfig in practice;
    # here we call directly.
    out = scores_to_signals(scores, task="classification", config=cfg)

    # High score → long, low score → short, middle band → flat
    assert set(out.tolist()).issubset({-1, 0, 1})
    assert out[0] == -1  # 0.2 <= sell_threshold
    assert out[-1] == 1  # 0.8 >= buy_threshold


def test_signal_generation_and_backtest():
    """
    End-to-end smoke test:

    - Train models
    - Attach signals for each model
    - Run a simple backtest
    """

    fe_config, training_config = load_feature_and_training_config(FEATURES_CONFIG)

    df = generate_features_and_labels(
        market_data_path=str(MARKET_DATA),
        tickers_path=str(TICKERS),
        config=fe_config,
    )

    results = train_and_evaluate_models(
        df,
        training_config=training_config,
        model_params_path=str(MODEL_PARAMS),
    )

    sig_cfg = SignalConfig(buy_threshold=0.55, sell_threshold=0.45, allow_short=False)
    df_with_signals = attach_signals_for_all_models(
        df_features=df,
        training_config=training_config,
        trained_models=results,
        signal_config=sig_cfg,
    )

    # Check that each model produced a signal column with values in {-1, 0, 1}
    for model_name in results.keys():
        sig_col = f"{model_name}_signal"
        assert sig_col in df_with_signals.columns
        sig_vals = df_with_signals[sig_col].values
        assert len(sig_vals) == len(df_with_signals)
        assert set(np.unique(sig_vals)).issubset({-1, 0, 1})

    # Now run a simple backtest using log_reg signals
    assert "log_reg_signal" in df_with_signals.columns

    if "date" in df_with_signals.columns:
        df_with_signals["date"] = pd.to_datetime(df_with_signals["date"])

    bt_cfg = BacktestConfig(
        initial_capital=100_000.0,
        price_col="close",
        signal_col="log_reg_signal",
    )

    if "ticker" in df_with_signals.columns:
        portfolio_res, per_ticker_res = backtest_multi_ticker_equal_weight(
            df_with_signals,
            config=bt_cfg,
        )

        # Portfolio summary should contain key statistics
        summary = portfolio_res.summary
        assert "cumulative_return" in summary
        assert "sharpe" in summary

        # DataFrame with equity curve should be non-empty
        assert not portfolio_res.df.empty
        assert "portfolio_equity" in portfolio_res.df.columns

        # There should be at least one ticker result
        assert len(per_ticker_res) > 0
    else:
        res = backtest_single_ticker(df_with_signals, config=bt_cfg)
        summary = res.summary
        assert "cumulative_return" in summary
        assert "sharpe" in summary
        assert not res.df.empty
        assert "equity" in res.df.columns
