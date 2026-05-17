"""Tests for feature-aware preprocessing transformers."""

import numpy as np
import pandas as pd
import pytest
from hou53_ml.features import (
    NeighborhoodLotFrontageImputer,
    NeighborhoodTargetEncoder,
)


def test_lot_frontage_imputer_uses_neighborhood_median() -> None:
    df = pd.DataFrame(
        {
            "Neighborhood": ["A", "A", "B", "B"],
            "LotFrontage": [60.0, np.nan, 90.0, np.nan],
        }
    )
    out = NeighborhoodLotFrontageImputer().fit_transform(df)
    assert out["LotFrontage"].tolist() == [60.0, 60.0, 90.0, 90.0]


def test_lot_frontage_imputer_falls_back_to_global_median() -> None:
    train = pd.DataFrame(
        {
            "Neighborhood": ["A", "B"],
            "LotFrontage": [60.0, 100.0],
        }
    )
    test = pd.DataFrame(
        {
            "Neighborhood": ["C"],
            "LotFrontage": [np.nan],
        }
    )
    out = NeighborhoodLotFrontageImputer().fit(train).transform(test)
    assert out.loc[0, "LotFrontage"] == 80.0


def test_neighborhood_target_encoder_is_fit_dependent() -> None:
    df = pd.DataFrame({"Neighborhood": ["A", "A", "B"]})
    y = np.log1p([100_000.0, 120_000.0, 300_000.0])
    out = NeighborhoodTargetEncoder().fit_transform(df, y)

    assert out.loc[0, "NeighborhoodPriceLog"] == pytest.approx(np.median(y[:2]))
    assert out.loc[2, "NeighborhoodPriceLog"] == pytest.approx(y[2])


def test_neighborhood_target_encoder_requires_y() -> None:
    with pytest.raises(ValueError, match="requires y"):
        NeighborhoodTargetEncoder().fit(pd.DataFrame({"Neighborhood": ["A"]}))
