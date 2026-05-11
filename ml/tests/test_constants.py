"""Tests for domain constants.

Small but load-bearing: if someone accidentally removes a legitimate-NA
column from the set, the whole feature pipeline silently starts imputing
"no pool" as "missing pool" — a very expensive bug. These tests make such
mistakes visible in CI.
"""

from __future__ import annotations

from hou53_ml.constants import (
    NA_AS_CATEGORY,
    NUMERIC_BUT_CATEGORICAL,
    QUALITY_ORDER,
    TARGET,
)


def test_target_is_sale_price() -> None:
    assert TARGET == "SalePrice"


def test_na_as_category_contains_known_fields() -> None:
    # Sentinels: fields that De Cock's description file explicitly maps to
    # "NA" as a category. If any are missing, we are about to throw away
    # information during imputation.
    must_include = {"PoolQC", "FireplaceQu", "Alley", "Fence"}
    assert must_include.issubset(NA_AS_CATEGORY)


def test_quality_order_is_strictly_increasing() -> None:
    values = list(QUALITY_ORDER.values())
    assert values == sorted(values), "quality scale must be strictly increasing"
    assert QUALITY_ORDER["NA"] == 0
    assert QUALITY_ORDER["Ex"] == max(values)


def test_numeric_but_categorical_covers_mssubclass() -> None:
    assert "MSSubClass" in NUMERIC_BUT_CATEGORICAL
