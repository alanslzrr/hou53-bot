"""Tests for ``hou53_ml.evaluation.metrics``."""

import math

import numpy as np
from hou53_ml.evaluation.metrics import (
    mae_dollars,
    median_ape,
    r2_dollars,
    rmse_log,
)


def test_rmse_log_zero_when_perfect() -> None:
    y = np.array([100_000.0, 200_000.0, 300_000.0])
    assert rmse_log(y, y) == 0.0


def test_rmse_log_handles_negative_predictions() -> None:
    # Negative predictions should not crash log1p — they get clipped to 0.
    y_true = np.array([100_000.0])
    y_pred = np.array([-50.0])
    # Manually: clipped to 0 → log1p(0)=0; log1p(100000)≈11.51 → RMSE ≈ 11.51
    value = rmse_log(y_true, y_pred)
    assert math.isfinite(value)
    assert value > 0


def test_mae_in_dollars_matches_manual() -> None:
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([110.0, 190.0, 290.0])
    assert mae_dollars(y_true, y_pred) == 10.0


def test_r2_one_when_perfect() -> None:
    y = np.array([100.0, 200.0, 300.0])
    assert r2_dollars(y, y) == 1.0


def test_median_ape_returns_relative_error() -> None:
    y_true = np.array([100.0, 100.0, 100.0])
    y_pred = np.array([110.0, 90.0, 100.0])
    # Errors: 10%, 10%, 0% → median = 10%.
    assert math.isclose(median_ape(y_true, y_pred), 0.10, rel_tol=1e-9)
