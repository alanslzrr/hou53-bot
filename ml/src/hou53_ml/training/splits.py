"""Train/test split + outlier filtering for the training set.

Kept tiny on purpose. The contract:

- Documented non-market outliers are removed before the split
  (``GrLivArea > 4000`` and ``SalePrice < 300_000``).
- Stratified 80/20 split by quintiles of ``SalePrice`` so each split carries
  the same cleaned price distribution.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from hou53_ml.constants import GRLIVAREA_OUTLIER_THRESHOLD, LOW_PRICE_OUTLIER_THRESHOLD


@dataclass(frozen=True, slots=True)
class Split:
    """Container with train/test slices and bookkeeping."""

    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    n_outliers_removed: int


def documented_outlier_mask(
    frame: pd.DataFrame,
    *,
    target: str = "SalePrice",
) -> pd.Series:
    """Rows flagged by De Cock as large, low-price non-market sales."""
    return (frame["GrLivArea"] > GRLIVAREA_OUTLIER_THRESHOLD) & (
        frame[target] < LOW_PRICE_OUTLIER_THRESHOLD
    )


def stratify_target(target: pd.Series, *, n_bins: int = 5) -> pd.Series:
    """Quintile-bin a continuous target for stratification.

    ``pd.qcut`` may collapse quintiles when duplicates dominate;
    ``duplicates="drop"`` makes it fall back to fewer bins instead of
    raising.
    """
    return pd.qcut(target, q=n_bins, labels=False, duplicates="drop")


def make_split(
    frame: pd.DataFrame,
    *,
    target: str = "SalePrice",
    test_size: float = 0.2,
    random_state: int = 42,
    drop_partial_outliers: bool = True,
) -> Split:
    """Split into train/test and optionally drop documented outliers.

    Args:
        frame: Raw dataset (post-loader).
        target: Name of the target column.
        test_size: Test-set fraction.
        random_state: Seed for the split.
        drop_partial_outliers: Backwards-compatible name for the documented
            outlier cleanup. When ``True`` (default), drop rows where
            ``GrLivArea > GRLIVAREA_OUTLIER_THRESHOLD`` and
            ``SalePrice < LOW_PRICE_OUTLIER_THRESHOLD`` before the split.
            See ``docs/eda/report.md`` § 8.

    Returns:
        A :class:`Split`.
    """
    working = frame.copy()

    n_outliers = 0
    if drop_partial_outliers:
        documented_outliers = documented_outlier_mask(working, target=target)
        n_outliers = int(documented_outliers.sum())
        if n_outliers:
            working = working.loc[~documented_outliers].reset_index(drop=True)

    y = working[target]
    X = working.drop(columns=[target])

    strata = stratify_target(y)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=strata,
    )

    # Reset indices for cleaner indexing in CV folds downstream.
    X_train = X_train.reset_index(drop=True)
    y_train = y_train.reset_index(drop=True)
    X_test = X_test.reset_index(drop=True)
    y_test = y_test.reset_index(drop=True)
    # Mypy-friendly cast: arrays are reshaped back to Series below.
    _ = np  # keep numpy import (used implicitly via pandas)

    return Split(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        n_outliers_removed=n_outliers,
    )
