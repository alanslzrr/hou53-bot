"""Tests for ``hou53_ml.features.derived.DerivedFeatures``."""

import numpy as np
import pandas as pd
import pytest
from hou53_ml.features.derived import OUTPUT_NAMES, DerivedFeatures


@pytest.fixture
def raw_rows() -> pd.DataFrame:
    """Minimal frame with every column DerivedFeatures reads from."""
    return pd.DataFrame(
        {
            "YrSold": [2008, 2009, 2010, 2008],
            "YearBuilt": [2003, 1990, 2007, 1872],
            "YearRemodAdd": [2003, 1995, 2007, 2005],
            # NaN garage on the second row → HasGarage=0, GarageAge=0
            "GarageYrBlt": [2003.0, np.nan, 2007.0, 1872.0],
            "1stFlrSF": [856, 1262, 920, 961],
            "2ndFlrSF": [854, 0, 866, 756],
            "TotalBsmtSF": [856, 1262, 920, 756],
            "FullBath": [2, 2, 2, 1],
            "HalfBath": [1, 0, 1, 0],
            "BsmtFullBath": [1, 0, 1, 1],
            "BsmtHalfBath": [0, 1, 0, 0],
            "OpenPorchSF": [61, 0, 42, 35],
            "EnclosedPorch": [0, 0, 0, 272],
            "3SsnPorch": [0, 0, 0, 0],
            "ScreenPorch": [0, 0, 0, 0],
            "PoolArea": [0, 0, 0, 0],
            "GarageArea": [548, 0, 608, 642],
            "Fireplaces": [0, 1, 1, 1],
            "OverallQual": [7, 6, 7, 7],
            "GrLivArea": [1710, 1262, 1786, 1717],
            # Extra column that must pass through untouched.
            "MSZoning": ["RL", "RL", "RM", "RL"],
        }
    )


class TestDerivedTransform:
    def test_adds_expected_columns(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        for name in OUTPUT_NAMES:
            assert name in out.columns, f"{name} missing"

    def test_house_age_is_yrsold_minus_yearbuilt(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        expected = raw_rows["YrSold"] - raw_rows["YearBuilt"]
        np.testing.assert_array_equal(out["HouseAge"].to_numpy(), expected.to_numpy().astype(float))

    def test_total_sf_is_sum_of_three_areas(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        expected = raw_rows["1stFlrSF"] + raw_rows["2ndFlrSF"] + raw_rows["TotalBsmtSF"]
        np.testing.assert_array_equal(out["TotalSF"].to_numpy(), expected.to_numpy().astype(float))

    def test_has_garage_flag_matches_garageyrblt(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        # Second row is the only NaN garage in the fixture.
        assert out["HasGarage"].tolist() == [1, 0, 1, 1]

    def test_adds_bathroom_and_quality_area_features(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        assert out.loc[0, "TotalBathrooms"] == 3.5
        assert out.loc[0, "QualArea"] == 7 * 1710
        assert out.loc[0, "QualTotalSF"] == 7 * (856 + 854 + 856)

    def test_presence_flags(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        assert out["Has2ndFloor"].tolist() == [1, 0, 1, 1]
        assert out["HasBsmt"].tolist() == [1, 1, 1, 1]
        assert out["HasFireplace"].tolist() == [0, 1, 1, 1]

    def test_no_garage_yields_zero_garage_age(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        assert out.loc[1, "GarageAge"] == 0.0

    def test_clamp_keeps_ages_non_negative(self) -> None:
        # Edge: GarageYrBlt > YrSold (data-entry error).
        df = pd.DataFrame(
            {
                "YrSold": [2007],
                "YearBuilt": [2010],  # built AFTER sold → -3 years
                "YearRemodAdd": [2010],
                "GarageYrBlt": [2010.0],
                "1stFlrSF": [1000],
                "2ndFlrSF": [0],
                "TotalBsmtSF": [0],
                "FullBath": [1],
                "HalfBath": [0],
                "BsmtFullBath": [0],
                "BsmtHalfBath": [0],
                "OpenPorchSF": [0],
                "EnclosedPorch": [0],
                "3SsnPorch": [0],
                "ScreenPorch": [0],
                "PoolArea": [0],
                "GarageArea": [0],
                "Fireplaces": [0],
                "OverallQual": [5],
                "GrLivArea": [1000],
            }
        )
        out = DerivedFeatures(clamp_negative_ages=True).fit_transform(df)
        assert out.loc[0, "HouseAge"] == 0.0
        assert out.loc[0, "RemodAge"] == 0.0
        assert out.loc[0, "GarageAge"] == 0.0

    def test_clamp_off_surfaces_raw_negative(self) -> None:
        df = pd.DataFrame(
            {
                "YrSold": [2007],
                "YearBuilt": [2010],
                "YearRemodAdd": [2010],
                "GarageYrBlt": [2010.0],
                "1stFlrSF": [1000],
                "2ndFlrSF": [0],
                "TotalBsmtSF": [0],
                "FullBath": [1],
                "HalfBath": [0],
                "BsmtFullBath": [0],
                "BsmtHalfBath": [0],
                "OpenPorchSF": [0],
                "EnclosedPorch": [0],
                "3SsnPorch": [0],
                "ScreenPorch": [0],
                "PoolArea": [0],
                "GarageArea": [0],
                "Fireplaces": [0],
                "OverallQual": [5],
                "GrLivArea": [1000],
            }
        )
        out = DerivedFeatures(clamp_negative_ages=False).fit_transform(df)
        assert out.loc[0, "HouseAge"] == -3.0

    def test_passes_through_unchanged_columns(self, raw_rows: pd.DataFrame) -> None:
        out = DerivedFeatures().fit_transform(raw_rows)
        # MSZoning must not be touched.
        assert out["MSZoning"].tolist() == raw_rows["MSZoning"].tolist()

    def test_get_feature_names_out_extends_input(self, raw_rows: pd.DataFrame) -> None:
        transformer = DerivedFeatures().fit(raw_rows)
        names = transformer.get_feature_names_out().tolist()
        for col in raw_rows.columns:
            assert col in names
        for name in OUTPUT_NAMES:
            assert name in names


class TestValidation:
    def test_rejects_missing_required_column(self) -> None:
        df = pd.DataFrame({"YrSold": [2008], "YearBuilt": [2000]})
        with pytest.raises(ValueError, match="missing required column"):
            DerivedFeatures().fit(df)

    def test_rejects_non_dataframe(self) -> None:
        with pytest.raises(TypeError, match="expects a DataFrame"):
            DerivedFeatures().fit(np.zeros((3, 3)))
