"""Tests for ``hou53_ml.features.ordinal``."""

import numpy as np
import pandas as pd
import pytest
from hou53_ml.features.ordinal import (
    QUALITY_LEVELS,
    UNKNOWN_VALUE,
    make_ordered_ordinal_encoder,
    make_quality_ordinal_encoder,
)


def test_quality_levels_are_canonical() -> None:
    assert QUALITY_LEVELS == ("NA", "Po", "Fa", "TA", "Gd", "Ex")
    # -1 sits below NA (0); cannot collide with any encoded category.
    assert UNKNOWN_VALUE == -1


def test_encoder_maps_levels_in_increasing_order() -> None:
    enc = make_quality_ordinal_encoder(n_features=1)
    X = pd.DataFrame({"q": list(QUALITY_LEVELS)})
    enc.fit(X)
    out = enc.transform(X)
    np.testing.assert_array_equal(out.ravel().astype(int), np.arange(len(QUALITY_LEVELS)))


def test_unknown_value_maps_to_na_code() -> None:
    enc = make_quality_ordinal_encoder(n_features=1)
    fit_df = pd.DataFrame({"q": list(QUALITY_LEVELS)})
    enc.fit(fit_df)
    # Serving-time value the encoder never saw — must collapse to NA (0).
    transformed = enc.transform(pd.DataFrame({"q": ["MysteryGrade"]}))
    assert transformed.ravel()[0] == UNKNOWN_VALUE


def test_zero_features_rejected() -> None:
    with pytest.raises(ValueError, match="n_features must be positive"):
        make_quality_ordinal_encoder(n_features=0)


def test_ordered_ordinal_encoder_uses_column_specific_order() -> None:
    enc = make_ordered_ordinal_encoder(["BsmtExposure", "PavedDrive"])
    X = pd.DataFrame(
        {
            "BsmtExposure": ["NA", "No", "Mn", "Av", "Gd"],
            "PavedDrive": ["NA", "N", "P", "Y", "Y"],
        }
    )
    enc.fit(X)
    out = enc.transform(X).astype(int)
    np.testing.assert_array_equal(out[:, 0], [0, 1, 2, 3, 4])
    np.testing.assert_array_equal(out[:, 1], [0, 1, 2, 3, 3])


def test_ordered_ordinal_encoder_rejects_missing_order() -> None:
    with pytest.raises(ValueError, match="missing ordinal category"):
        make_ordered_ordinal_encoder(["NotAColumn"])
