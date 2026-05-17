"""Tests for ``hou53_ml.eda.summary``."""

import numpy as np
import pandas as pd
import pytest
from hou53_ml.eda.summary import (
    categorical_cardinality,
    correlation_with_target,
    missing_summary,
    numeric_skew,
    outlier_mask,
    target_summary,
)


@pytest.fixture
def small_frame() -> pd.DataFrame:
    """Tiny synthetic frame exercising every kind of column."""
    return pd.DataFrame(
        {
            "Id": [1, 2, 3, 4, 5],
            # PoolQC is in NA_AS_CATEGORY → "legit_na" kind, even though
            # in this fixture we already "filled" it the way the loader would.
            "PoolQC": ["NA", "NA", "NA", "Ex", "NA"],
            # LotFrontage has actual missings.
            "LotFrontage": [65.0, np.nan, 68.0, np.nan, 84.0],
            # MSZoning is complete.
            "MSZoning": ["RL", "RL", "RL", "RM", "RL"],
            # Skewed numeric.
            "GrLivArea": [1200, 1300, 1500, 1800, 6000],
            "SalePrice": [120_000, 150_000, 200_000, 350_000, 750_000],
        }
    )


class TestMissingSummary:
    def test_partitions_columns_by_kind(self, small_frame: pd.DataFrame) -> None:
        summary = missing_summary(small_frame)
        kinds = dict(zip(summary.per_column.column, summary.per_column.kind, strict=True))

        # PoolQC is in NA_AS_CATEGORY — even though it has no NaN here,
        # it is reported as "legit_na" so reviewers see it surfaced.
        assert kinds["PoolQC"] == "legit_na"
        assert kinds["LotFrontage"] == "actual"
        assert kinds["MSZoning"] == "complete"
        assert kinds["SalePrice"] == "complete"

    def test_total_missing_actual_excludes_legit_na(self, small_frame: pd.DataFrame) -> None:
        summary = missing_summary(small_frame)
        # Only LotFrontage has 2 actual missings.
        assert summary.total_missing_actual == 2

    def test_actual_pct_in_unit_interval(self, small_frame: pd.DataFrame) -> None:
        summary = missing_summary(small_frame)
        assert 0.0 <= summary.actual_pct <= 1.0


class TestTargetSummary:
    def test_basic_stats(self) -> None:
        target = pd.Series([100_000, 150_000, 200_000, 250_000, 300_000])
        summary = target_summary(target)
        assert summary.n == 5
        assert summary.median == 200_000
        assert summary.min == 100_000
        assert summary.max == 300_000

    def test_log_skew_smaller_than_raw_for_skewed_input(self) -> None:
        # Heavy right tail → log_skew should be substantially smaller in
        # absolute value than the raw skew (the whole point of the log
        # transform).
        target = pd.Series([100_000] * 90 + [1_000_000] * 10)
        summary = target_summary(target)
        assert abs(summary.log_skew) < abs(summary.skew)

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ValueError, match="empty series"):
            target_summary(pd.Series([], dtype=float))

    def test_negative_input_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            target_summary(pd.Series([-1.0, 0.0, 1.0]))


class TestNumericSkew:
    def test_recommends_log_for_heavy_tail(self, small_frame: pd.DataFrame) -> None:
        result = numeric_skew(small_frame, threshold=0.5)
        # GrLivArea has a very heavy tail (one row at 6000 vs others ~1500).
        assert "GrLivArea" in result.to_log_transform

    def test_to_log_transform_respects_threshold(self, small_frame: pd.DataFrame) -> None:
        loose = numeric_skew(small_frame, threshold=0.01)
        strict = numeric_skew(small_frame, threshold=10.0)
        assert len(loose.to_log_transform) >= len(strict.to_log_transform)

    def test_drops_zero_variance_columns(self) -> None:
        frame = pd.DataFrame({"flat": [1, 1, 1, 1], "varied": [1, 2, 3, 4]})
        result = numeric_skew(frame)
        assert "flat" not in result.per_column["column"].tolist()
        assert "varied" in result.per_column["column"].tolist()


class TestCategoricalCardinality:
    def test_reports_top_value_and_share(self, small_frame: pd.DataFrame) -> None:
        result = categorical_cardinality(small_frame, columns=["MSZoning", "PoolQC"])
        mszoning = result[result["column"] == "MSZoning"].iloc[0]
        assert mszoning["top_value"] == "RL"
        assert mszoning["top_pct"] == pytest.approx(0.8)


class TestCorrelationWithTarget:
    @pytest.fixture
    def dense_frame(self) -> pd.DataFrame:
        """Larger fixture so Pearson is well-defined (no n=3 edge cases)."""
        rng = np.random.default_rng(seed=0)
        n = 60
        size = np.linspace(800, 4500, n)
        # SalePrice is a monotonic function of size + a smaller-effect noise term.
        noise = rng.normal(0, 5_000, n)
        # A second feature with much weaker (but real) signal.
        rooms = rng.integers(3, 11, n)
        return pd.DataFrame(
            {
                "GrLivArea": size,
                "TotRmsAbvGrd": rooms,
                "SalePrice": 120 * size + 8_000 * rooms + noise,
            }
        )

    def test_orders_by_absolute_correlation(self, dense_frame: pd.DataFrame) -> None:
        ranked = correlation_with_target(dense_frame, target="SalePrice")
        # GrLivArea has the dominant linear effect — must rank first.
        assert ranked.index[0] == "GrLivArea"
        # Target itself never appears in the ranking.
        assert "SalePrice" not in ranked.index

    def test_top_k_truncates(self, dense_frame: pd.DataFrame) -> None:
        ranked = correlation_with_target(dense_frame, target="SalePrice", top_k=1)
        assert len(ranked) == 1

    def test_missing_target_raises(self, dense_frame: pd.DataFrame) -> None:
        with pytest.raises(KeyError):
            correlation_with_target(dense_frame, target="NotAColumn")


class TestOutlierMask:
    def test_threshold_mode_flags_above(self) -> None:
        series = pd.Series([1, 2, 3, 100])
        mask = outlier_mask(series, threshold=10)
        assert mask.tolist() == [False, False, False, True]

    def test_iqr_mode_flags_extreme_values(self) -> None:
        # Symmetric data with one obvious extreme.
        series = pd.Series([10, 11, 12, 13, 14, 15, 16, 1000])
        mask = outlier_mask(series, iqr_multiplier=1.5)
        assert mask.iloc[-1]

    def test_requires_some_rule(self) -> None:
        with pytest.raises(ValueError, match=r"threshold.*iqr"):
            outlier_mask(pd.Series([1, 2, 3]), iqr_multiplier=None)
