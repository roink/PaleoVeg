import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from paleoveg_training import (
    assign_size_balanced_folds,
    outer_tile_ids,
    shao_goodness_scores,
)


def test_outer_tile_ids_handle_global_edges():
    result = outer_tile_ids(
        np.array([-180.0, -175.0, 179.999]), np.array([-90.0, -85.0, 89.999])
    )
    assert result.tolist() == ["outer_r00_c00", "outer_r01_c01", "outer_r35_c71"]


def test_size_balanced_folds_are_complete_and_deterministic():
    counts = pd.Series({f"tile_{i}": value for i, value in enumerate([100, 90, 80, 70, 60, 50])})
    first = assign_size_balanced_folds(counts, fold_count=3, seed=42)
    second = assign_size_balanced_folds(counts, fold_count=3, seed=42)
    assert first == second
    assert set(first) == set(counts.index)
    assert set(first.values()) == {0, 1, 2}


def test_shao_goodness_score_is_one_for_perfect_probabilities():
    labels = np.array([1, 2, 1, 2, 1, 2])
    probabilities = np.column_stack((labels == 1, labels == 2)).astype(float)
    result = shao_goodness_scores(
        labels, probabilities, classes=[1, 2], random_state=7
    )
    assert np.allclose(result["shao_goodness_score"], 1.0)
    assert np.allclose(result["d_model"], 0.0)


def test_shao_goodness_score_is_reproducible():
    labels = np.array([1, 2, 1, 2, 1, 2, 1, 2])
    probabilities = np.full((len(labels), 2), 0.5)
    first = shao_goodness_scores(labels, probabilities, classes=[1, 2], random_state=42)
    second = shao_goodness_scores(labels, probabilities, classes=[1, 2], random_state=42)
    pd.testing.assert_frame_equal(first, second)
