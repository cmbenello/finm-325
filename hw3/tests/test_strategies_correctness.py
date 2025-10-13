import pytest
from .helpers import make_synthetic_ticks
from src.strategies import (
    NaiveMovingAverageStrategy,
    WindowedMovingAverageStrategy,
    NaiveMovingAverageStrategyOptimized,
)

def collect_actions(strategy, ticks):
    # Drive the strategy directly and collect .action from its Signal
    actions = []
    for t in ticks:
        sig = strategy.generate_signals(t)
        actions.append(sig.action)
    return actions

@pytest.mark.parametrize("s,L", [(5, 20), (10, 30)])
def test_signal_consistency_after_warmup(s, L):
    ticks = make_synthetic_ticks(300)

    naive_actions = collect_actions(NaiveMovingAverageStrategy(s, L), ticks)
    win_actions = collect_actions(WindowedMovingAverageStrategy(s, L), ticks)
    opt_actions = collect_actions(NaiveMovingAverageStrategyOptimized(s, L), ticks)

    # Warm-up: both "current" and "previous" MAs need to exist.
    # Naive requires len(prices) >= L+1; windowed also needs prev sums.
    start = L + 1

    assert win_actions[start:] == naive_actions[start:]
    assert opt_actions[start:] == naive_actions[start:]