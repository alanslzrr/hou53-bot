"""Tests for ``hou53_ml.training.splits``."""

import pandas as pd
from hou53_ml.constants import GRLIVAREA_OUTLIER_THRESHOLD
from hou53_ml.training.splits import (
    documented_outlier_mask,
    make_split,
    stratify_target,
)


def _toy_frame(n_rows: int = 200) -> pd.DataFrame:
    """Synthetic frame big enough for stratified 5-quintile split."""
    return pd.DataFrame(
        {
            "GrLivArea": [1000 + 10 * i for i in range(n_rows)],
            "SaleCondition": ["Normal"] * n_rows,
            "SalePrice": [100_000 + 1_000 * i for i in range(n_rows)],
        }
    )


def test_stratify_target_returns_bins() -> None:
    target = pd.Series(range(100))
    bins = stratify_target(target, n_bins=5)
    assert bins.nunique() == 5


def test_make_split_preserves_total_rows_when_no_outliers() -> None:
    df = _toy_frame()
    split = make_split(df, test_size=0.2, random_state=0)
    assert len(split.X_train) + len(split.X_test) == len(df)
    assert split.n_outliers_removed == 0


def test_make_split_drops_documented_outliers_before_split() -> None:
    df = _toy_frame()
    # Inject 3 partial-sale outliers.
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                {
                    "GrLivArea": [
                        GRLIVAREA_OUTLIER_THRESHOLD + 100,
                        GRLIVAREA_OUTLIER_THRESHOLD + 200,
                        GRLIVAREA_OUTLIER_THRESHOLD + 300,
                    ],
                    "SaleCondition": ["Partial", "Partial", "Partial"],
                    "SalePrice": [150_000, 160_000, 170_000],
                }
            ),
        ],
        ignore_index=True,
    )
    split = make_split(df, test_size=0.2, random_state=0)
    assert split.n_outliers_removed == 3
    assert len(split.X_train) + len(split.X_test) == len(df) - 3
    # No documented outlier rows remain in either split.
    assert not (
        (split.X_train["GrLivArea"] > GRLIVAREA_OUTLIER_THRESHOLD) & (split.y_train < 300_000)
    ).any()
    assert not (
        (split.X_test["GrLivArea"] > GRLIVAREA_OUTLIER_THRESHOLD) & (split.y_test < 300_000)
    ).any()


def test_documented_outlier_mask_is_target_based() -> None:
    df = _toy_frame()
    rows = pd.DataFrame(
        {
            "GrLivArea": [
                GRLIVAREA_OUTLIER_THRESHOLD + 100,
                GRLIVAREA_OUTLIER_THRESHOLD + 100,
            ],
            "SaleCondition": ["Normal", "Partial"],
            "SalePrice": [150_000, 750_000],
        }
    )
    mask = documented_outlier_mask(pd.concat([df, rows], ignore_index=True))
    assert mask.tail(2).tolist() == [True, False]
