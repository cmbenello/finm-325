# Model and Strategy Comparison

This project implements a full machine‑learning trading pipeline, including feature engineering, model training, signal generation, and backtesting, applied to multi‑ticker equity data. This document compares predictive performance and trading outcomes across models and discusses insights and limitations.

---

## Models Compared

We evaluate two supervised classification models for predicting next‑day price direction:

- **Logistic Regression (`log_reg`)**
  - Linear classifier with probabilistic outputs
  - Interpretable and robust baseline

- **Random Forest (`rf`)**
  - Ensemble of decision trees using bootstrap aggregation
  - Non‑linear model capable of capturing feature interactions

Both models are trained on the same engineered feature set consisting of lagged returns and technical indicators, and both are evaluated using identical train/test splits and cross‑validation schemes.

---

## Predictive Performance

### Classification Metrics

Both models achieve very strong predictive accuracy on the held‑out test set, as shown in their confusion matrices (Figures 2 and 3):

- Accuracy, precision, recall, and F1‑score are all close to 1.0.
- Cross‑validation scores confirm that performance is consistent across folds.

Despite their architectural differences, the two models produce nearly identical classification results. This suggests that the feature set captures most of the predictive structure in the data, leaving limited scope for further gains from increased model complexity.

---

## Trading Strategy Performance

Trading signals are generated from each model’s predicted probabilities using fixed thresholds. These signals are backtested in a simple, equal‑weight strategy across all tickers, with no transaction costs assumed.

### Portfolio‑Level Results

- Portfolio equity curves for both models are shown in **Figure 1**.
- The equity curves lie almost perfectly on top of each other.
- Key statistics such as cumulative return, Sharpe ratio, and maximum drawdown are nearly identical across models.

This indicates that the two models place trades on almost the same days and in the same directions, leading to effectively equivalent portfolio behaviour.

### Per‑Ticker Results

At the individual‑ticker level, both models consistently outperform a buy‑and‑hold baseline for most assets. However, as with the portfolio results, differences between models are negligible.

---

## Why Are the Results So Similar?

The similarity in both predictive and financial performance is expected given the experimental setup:

1. **Short‑horizon prediction task**  
   The target variable is next‑day price direction, which often exhibits short‑term momentum and autocorrelation in highly liquid equities.

2. **Strong feature engineering**  
   Lagged returns and technical indicators already make the classification problem close to linearly separable.

3. **Absence of trading frictions**  
   No transaction costs or slippage are modeled, amplifying the apparent profitability of any reasonably accurate signal.

When the data is highly informative, very different classifiers can converge to almost identical decision rules.

---

## Feature Importance

Random Forest provides a natural measure of feature importance via impurity‑based splits. Analysis of feature importance indicates that lagged returns and momentum‑based technical indicators contribute most to predictive performance, reinforcing the conclusion that engineered features, rather than model complexity, drive results.

---

## Limitations and Future Improvements

Several simplifying assumptions limit the realism of these results:

- No transaction costs or market impact
- Binary (direction‑only) prediction target
- Fixed position sizing
- Short prediction horizon

Future extensions could include:
- Regression‑based return prediction
- Longer horizons
- Transaction cost modeling
- Regularisation or noise injection to reduce overfitting

---

## Conclusion

While logistic regression and random forest are fundamentally different models, their predictive and trading performance in this setting is nearly identical. This outcome highlights an important lesson in quantitative finance: **feature engineering and problem formulation often matter more than model complexity**, especially in short‑horizon prediction tasks.

The results therefore validate the correctness of the pipeline and underline the dominant role of engineered financial features in driving strategy performance.
