"""Regression metrics used across the project.

Three metrics, each answering a different question:

- :func:`rmse_log` — the Kaggle leaderboard metric and the training
  objective. Penalises proportional error symmetrically across price
  bands. The headline number.
- :func:`mae_dollars` — average absolute error in dollars. The metric
  a non-technical user understands directly.
- :func:`r2_dollars` — variance explained on the raw target. Sanity
  check against pathological behaviour.

All three operate on raw dollars (not log dollars). The pipeline
inverse-transforms before predict, so the API and the evaluator see
the same numbers.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def _coerce(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        arr = arr.ravel()
    return arr


def rmse_log(y_true: Any, y_pred: Any) -> float:
    """Root mean squared error on ``log1p(y)``.

    Both inputs are in raw dollars; we apply ``log1p`` here so callers
    cannot accidentally pass log-space predictions and get a misleading
    "great score".

    Args:
        y_true: Actual ``SalePrice`` in dollars (>= 0).
        y_pred: Predicted ``SalePrice`` in dollars (>= 0). Negative
            predictions are clipped to ``0`` before applying ``log1p``;
            a regressor that goes negative is suspicious but should not
            crash the metric.

    Returns:
        The non-negative RMSE in log-dollar units.
    """
    yt = _coerce(y_true)
    yp = np.maximum(_coerce(y_pred), 0.0)
    return float(np.sqrt(mean_squared_error(np.log1p(yt), np.log1p(yp))))


def mae_dollars(y_true: Any, y_pred: Any) -> float:
    """Mean absolute error in dollars."""
    return float(mean_absolute_error(_coerce(y_true), _coerce(y_pred)))


def r2_dollars(y_true: Any, y_pred: Any) -> float:
    """Coefficient of determination on raw dollars."""
    return float(r2_score(_coerce(y_true), _coerce(y_pred)))


def median_ape(y_true: Any, y_pred: Any) -> float:
    """Median absolute percentage error (robust to outliers).

    Reported alongside :func:`mae_dollars` because it is the easiest
    statistic to translate into a sentence: "half the predictions are
    within X% of the true price."
    """
    yt = _coerce(y_true)
    yp = _coerce(y_pred)
    nonzero = yt != 0
    if not nonzero.any():
        return float("nan")
    return float(np.median(np.abs((yp[nonzero] - yt[nonzero]) / yt[nonzero])))
