# Query Tasks

## SQLite3

1. Retrieve all data for TSLA between 2025-11-17 and 2025-11-18.
2. Calculate average daily volume per ticker.
3. Identify top 3 tickers by return over the full period.
4. Find first and last trade price for each ticker per day.

## Parquet

1. Load all data for AAPL and compute 5-minute rolling average of close price.
2. Compute 5-day rolling volatility (std dev) of returns for each ticker.
3. Compare query time and file size with SQLite3 for Task 1.

---

## Results

### SQLite3 Task 1: TSLA between 2025-11-17 and 2025-11-18
```
            timestamp ticker    open    high     low   close  volume
0 2025-11-17 09:30:00   TSLA  268.31  268.51  267.95  268.07    1609
1 2025-11-17 09:31:00   TSLA  268.94  269.11  268.28  269.04    4809
2 2025-11-17 09:32:00   TSLA  267.70  267.94  267.69  267.92    1997
3 2025-11-17 09:33:00   TSLA  268.45  268.64  268.00  268.56    3461
4 2025-11-17 09:34:00   TSLA  269.01  269.57  268.21  269.23    4003
```

### SQLite3 Task 2: Average daily volume per ticker
```
  ticker  avg_daily_volume
0   AAPL         1082222.6
1   AMZN         1076588.8
2   GOOG         1071402.8
3   MSFT         1050441.4
4   TSLA         1085973.0
```

### SQLite3 Task 3: Top 3 tickers by return (full period)
```
  ticker    return
0   MSFT  0.326282
1   AAPL  0.235787
2   GOOG  0.106648
```

### SQLite3 Task 4: First and last trade per ticker per day
```
  ticker       date  first_price  last_price
0   AAPL 2025-11-17       270.88      287.68
1   AAPL 2025-11-18       287.48      289.52
2   AAPL 2025-11-19       288.80      295.87
3   AAPL 2025-11-20       296.99      319.43
4   AAPL 2025-11-21       319.63      334.57
```

### Parquet Task 1: AAPL 5-minute rolling average of close price
```
            timestamp    open    high     low   close  volume ticker  rolling_5min_close
0 2025-11-17 09:30:00  271.45  272.07  270.77  270.88    1416   AAPL          270.880000
1 2025-11-17 09:31:00  269.12  269.38  269.00  269.24    3812   AAPL          270.060000
2 2025-11-17 09:32:00  270.36  271.24  270.22  270.86    3046   AAPL          270.326667
3 2025-11-17 09:33:00  269.47  269.61  268.77  269.28    2090   AAPL          270.065000
4 2025-11-17 09:34:00  269.17  269.79  269.02  269.32    2035   AAPL          269.916000
```

### Parquet Task 2: 5-day rolling volatility per ticker
```
            timestamp ticker   close    return  rolling_vol_5d
0 2025-11-17 09:30:00   AAPL  270.88       NaN             NaN
1 2025-11-17 09:31:00   AAPL  269.24 -0.006054             NaN
2 2025-11-17 09:32:00   AAPL  270.86  0.006017             NaN
3 2025-11-17 09:33:00   AAPL  269.28 -0.005833             NaN
4 2025-11-17 09:34:00   AAPL  269.32  0.000149             NaN
```

### Parquet Task 3: Query time and file size comparison
```
SQLite AAPL rolling 5min avg time: 0.004146 s
Parquet AAPL rolling 5min avg time: 0.004617 s
SQLite file size (bytes): 688128
Parquet file size (bytes): 339423
```