"""Tests for the assembled :func:`build_preprocessor`.

These do not exercise the production pipeline end-to-end (that is in
``test_training_smoke.py``). They check structural invariants of the
preprocessor — column coverage, dtype contracts, log1p semantics.
"""

import numpy as np
import pandas as pd
import pytest
from hou53_ml.features import DerivedFeatures, build_preprocessor
from hou53_ml.io import Schema


@pytest.fixture
def sample_frame() -> pd.DataFrame:
    """A 3-row, schema-complete frame for preprocessor tests.

    Numeric columns get sensible non-zero values; categoricals get
    ``"NA"`` (the legit-NA sentinel). The three columns that are
    numeric-but-categorical in our schema (``MSSubClass``, ``MoSold``,
    ``YrSold``) get real numeric-looking strings so the
    :class:`DerivedFeatures` transformer can compute ``HouseAge`` from
    them without producing all-NaN columns.
    """
    schema = Schema.default()
    cols = ["Id", *schema.all_features, "SalePrice"]
    numeric_but_string = {"MSSubClass": "60", "MoSold": "6", "YrSold": "2008"}
    rows = []
    for _ in range(3):
        row: dict[str, object] = {}
        for c in cols:
            if c in numeric_but_string:
                row[c] = numeric_but_string[c]
            elif c in {"OverallQual", "OverallCond"}:
                row[c] = 5
            elif c in schema.temporal:
                row[c] = 1990  # plausible year
            elif c in schema.numeric:
                row[c] = 1000.0
            elif c == "Id":
                row[c] = 1
            elif c == "SalePrice":
                row[c] = 200_000.0
            else:
                row[c] = "NA"
        rows.append(row)
    return pd.DataFrame(rows)


def test_preprocessor_fits_and_transforms(sample_frame: pd.DataFrame) -> None:
    schema = Schema.default()
    derived = DerivedFeatures().fit_transform(sample_frame.drop(columns=["SalePrice"]))
    preprocessor = build_preprocessor(schema=schema)

    transformed = preprocessor.fit_transform(derived)
    assert transformed.shape[0] == 3
    # Output must be a DataFrame thanks to set_output("pandas").
    assert isinstance(transformed, pd.DataFrame)


def test_preprocessor_drops_id_column(sample_frame: pd.DataFrame) -> None:
    schema = Schema.default()
    derived = DerivedFeatures().fit_transform(sample_frame.drop(columns=["SalePrice"]))
    preprocessor = build_preprocessor(schema=schema)
    transformed = preprocessor.fit_transform(derived)
    assert "Id" not in transformed.columns


def test_quality_ordinals_become_integers(sample_frame: pd.DataFrame) -> None:
    schema = Schema.default()
    # Vary KitchenQual across rows so the encoded values are non-trivial.
    df = sample_frame.copy()
    df.loc[0, "KitchenQual"] = "Po"
    df.loc[1, "KitchenQual"] = "TA"
    df.loc[2, "KitchenQual"] = "Ex"

    derived = DerivedFeatures().fit_transform(df.drop(columns=["SalePrice"]))
    transformed = build_preprocessor(schema=schema).fit_transform(derived)
    kq = transformed["KitchenQual"].to_numpy()
    # Po=1, TA=3, Ex=5 per QUALITY_ORDER
    assert kq[0] == 1
    assert kq[1] == 3
    assert kq[2] == 5


def test_log1p_applied_to_skewed_columns(sample_frame: pd.DataFrame) -> None:
    schema = Schema.default()
    df = sample_frame.copy()
    # Set GrLivArea to a known value so we can check log1p was applied.
    df.loc[:, "GrLivArea"] = [1000.0, 2000.0, 3000.0]
    derived = DerivedFeatures().fit_transform(df.drop(columns=["SalePrice"]))
    transformed = build_preprocessor(schema=schema).fit_transform(derived)
    np.testing.assert_allclose(
        transformed["GrLivArea"].to_numpy(),
        np.log1p([1000.0, 2000.0, 3000.0]),
        rtol=1e-6,
    )


def test_ordered_ordinals_are_not_one_hot(sample_frame: pd.DataFrame) -> None:
    schema = Schema.default()
    df = sample_frame.copy()
    df.loc[:, "BsmtExposure"] = ["NA", "No", "Gd"]
    derived = DerivedFeatures().fit_transform(df.drop(columns=["SalePrice"]))
    transformed = build_preprocessor(schema=schema).fit_transform(derived)

    assert "BsmtExposure" in transformed.columns
    assert "BsmtExposure_Gd" not in transformed.columns
    assert transformed["BsmtExposure"].tolist() == [0, 1, 4]
