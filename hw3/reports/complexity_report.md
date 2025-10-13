# Complexity and Performance Report

## Complexity Annotations
| Strategy | Complexity |
|---|---|
| NaiveMovingAverageStrategy | time=O(L) per tick, space=O(n) |
| NaiveMovingAverageStrategyOptimized | time=O(1) per tick, space=O(L) |
| WindowedMovingAverageStrategy | time=O(1) per tick, space=O(L) |

## Runtime Metrics
|strategy|N|runtime_best_sec|runtime_avg_sec|
|---|---|---|---|
|NaiveMovingAverageStrategy|1000|0.015028832945972681|0.015233235938164095|
|NaiveMovingAverageStrategy|10000|0.15872075001243502|0.16105044435244054|
|NaiveMovingAverageStrategy|100000|1.5789590829517692|1.5907279163366184|
|NaiveMovingAverageStrategyOptimized|1000|0.001710625016130507|0.0017381390013421576|
|NaiveMovingAverageStrategyOptimized|10000|0.017229291959665716|0.017579583334736526|
|NaiveMovingAverageStrategyOptimized|100000|0.1754650000948459|0.175594486334982|
|WindowedMovingAverageStrategy|1000|0.00164229201618582|0.0016596113564446568|
|WindowedMovingAverageStrategy|10000|0.017128792009316385|0.01715750029931466|
|WindowedMovingAverageStrategy|100000|0.1710524579975754|0.17134088867654404|

## Memory Metrics
|strategy|N|memory_peak_MiB|
|---|---|---|
|NaiveMovingAverageStrategy|1000|0.13959884643554688|
|NaiveMovingAverageStrategy|10000|1.3834953308105469|
|NaiveMovingAverageStrategy|100000|13.734935760498047|
|NaiveMovingAverageStrategyOptimized|1000|0.13094329833984375|
|NaiveMovingAverageStrategyOptimized|10000|1.3026580810546875|
|NaiveMovingAverageStrategyOptimized|100000|12.971302032470703|
|WindowedMovingAverageStrategy|1000|0.12979507446289062|
|WindowedMovingAverageStrategy|10000|1.3009300231933594|
|WindowedMovingAverageStrategy|100000|12.970516204833984|

## Plots
![Runtime vs N](runtime_vs_n.png)
![Peak Memory vs N](memory_vs_n.png)

## Narrative
Comparison at N = 100000
- Optimized vs Naive runtime: x9.00 faster (best).
- Windowed vs Naive runtime: x9.23 faster (best).
- Optimized memory vs Naive: 5.6% lower (peak).
- Windowed memory vs Naive: 5.6% lower (peak).
- Scaling: optimized and windowed show near O(1) per tick behavior; naive grows with long_window and exhibits slower scaling as N increases.
