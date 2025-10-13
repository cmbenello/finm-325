
import pytest
from pathlib import Path
from .helpers import make_synthetic_ticks
from src.strategies import NaiveMovingAverageStrategy, NaiveMovingAverageStrategyOptimized, WindowedMovingAverageStrategy
from src.profiler import StrategyConfig, profile_strategy

def test_cprofile_outputs_and_hotspots(tmp_path: Path):
    ticks = make_synthetic_ticks(5000)

    cfg = StrategyConfig(
        name="NaiveMovingAverageStrategy",
        factory=lambda: NaiveMovingAverageStrategy(20, 50),
        complexity="time=O(L) per tick, space=O(n)",
    )

    res = profile_strategy(cfg, ticks, repeat=1, profile_dir=tmp_path)
    assert res.cprofile_path is not None and res.cprofile_path.exists()

    text = res.cprofile_top_stats
    assert isinstance(text, str) and len(text) > 0
    assert any(s in text for s in ["NaiveMovingAverageStrategy", "mean", "generate_signals"])
