## Project Overview

Given historical OHLCV (Open, High, Low, Close, Volume) data for multiple equities, the goal is to:

1. Engineer predictive features from raw market data
2. Train supervised learning models to predict next‑day price direction
3. Convert model outputs into trading signals
4. Backtest simple trading strategies based on these signals
5. Compare predictive and financial performance across models

The focus is on clarity, correctness, and reproducibility rather than production‑level trading realism.

---

## Repository Structure

```
hw12/
│
├── feature_engineering.py    # Feature and label generation
├── train_model.py            # Model training and evaluation
├── signal_generator.py       # Model score → trading signal logic
├── backtest.py               # Trading strategy simulation
├── run_all.py                # End‑to‑end pipeline runner
│
├── market_data_ml.csv        # Historical OHLCV data
├── tickers-1.csv             # Subset of tickers to include
├── features_config.json      # Feature engineering configuration
├── model_params.json         # Model definitions and hyperparameters
│
├── comparison.md             # Model and strategy comparison write‑up
├── README.md                 # This file
│
├── equity_curves_portfolio.png
├── confusion_log_reg.png
├── confusion_rf.png
├── feature_importance_rf.png
│
└── summary.json              # Optional run summary (generated)
```

---

## Setup and Requirements

### Python Version
- Python 3.9+ recommended

### Required Packages

Install dependencies using pip:

```bash
pip install numpy pandas scikit-learn matplotlib
```

---

## Running the Full Pipeline

The entire workflow is executed with a single command:

```bash
python run_all.py \
  --market-data market_data_ml.csv \
  --tickers tickers-1.csv
```

Optional arguments:

- `--features-config features_config.json`
- `--model-params model_params.json`
- `--signal-model log_reg | rf`
- `--summary-out summary.json`

Example:

```bash
python run_all.py \
  --market-data market_data_ml.csv \
  --tickers tickers-1.csv \
  --summary-out summary.json
```

---

## Pipeline Stages

### 1. Feature Engineering (`feature_engineering.py`)
- Computes daily returns and log‑returns
- Generates lagged return features
- Adds technical indicators (SMA, RSI, MACD)
- Constructs classification labels:
  - 1 if next‑day return > 0
  - 0 otherwise

### 2. Model Training (`train_model.py`)
- Trains multiple supervised learning models:
  - Logistic Regression
  - Random Forest
- Evaluates predictive performance using:
  - Accuracy, precision, recall, F1 score
  - Confusion matrix
  - Cross‑validation (mean and standard deviation)

### 3. Signal Generation (`signal_generator.py`)
- Converts model predictions into discrete trading signals:
  - +1: long
  - 0: flat
  - −1: short (optional)
- Uses fixed probability thresholds for classification models

### 4. Backtesting (`backtest.py`)
- Simulates trading strategies using generated signals
- Equal‑weight portfolio across multiple tickers
- Computes:
  - Cumulative and annualized returns
  - Volatility and Sharpe ratio
  - Maximum drawdown
  - Comparison to buy‑and‑hold

### 5. Comparison and Visualization
Running `run_all.py` automatically generates:
- Portfolio equity curve comparisons
- Confusion matrix visualizations
- Feature importance plot for the random forest model

Results and discussion are summarized in `comparison.md`.

---

## Notes and Limitations

- No transaction costs or market impact are modeled
- Fixed position sizing
- Short‑horizon prediction (next‑day direction)
- Results should be interpreted as illustrative rather than realistic

---

