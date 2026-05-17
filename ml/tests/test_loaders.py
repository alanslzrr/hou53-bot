"""Tests for ``hou53_ml.io.loaders``.

The loader is the single most load-bearing piece of code in the package:
every other module trusts the contract it enforces. These tests exercise
the contract end-to-end against the real CSV (when present) and against
synthetic fixtures (always).
"""

from pathlib import Path

import pandas as pd
import pytest
from hou53_ml.constants import NA_AS_CATEGORY
from hou53_ml.io.loaders import (
    EXPECTED_RAW_SHAPE,
    AmesHousingLoader,
    LoadResult,
)

# A trimmed CSV that mirrors the curated Ames format: ``?`` for actual
# missings and bare ``NA`` strings absent (because the curated file uses
# ``?`` everywhere, and we re-fill legit-NA columns ourselves). Five rows
# is enough to exercise the NA convention without slowing tests down.
_SYNTHETIC_HEADER = "Id,LotFrontage,PoolQC,MSSubClass,MSZoning,SalePrice"
_SYNTHETIC_ROWS = [
    "1,65,?,60,RL,208500",
    "2,?,?,20,RL,181500",
    "3,68,?,60,RL,223500",
    "4,60,Ex,70,RL,755000",
    "5,84,?,60,RL,140000",
]


@pytest.fixture
def synthetic_csv(tmp_path: Path) -> Path:
    csv = tmp_path / "house_prices.csv"
    csv.write_text("\n".join([_SYNTHETIC_HEADER, *_SYNTHETIC_ROWS]) + "\n")
    return csv


class TestSyntheticLoader:
    """Loader exercised against a tiny in-memory CSV under tmp_path."""

    def test_returns_load_result_with_expected_metadata(self, synthetic_csv: Path) -> None:
        loader = AmesHousingLoader(synthetic_csv, validate_shape=False)
        result = loader.load()

        assert isinstance(result, LoadResult)
        assert result.source == synthetic_csv.resolve()
        assert result.rows == 5
        assert "SalePrice" in result.columns
        assert result.frame.shape == (5, 6)

    def test_question_marks_become_nan(self, synthetic_csv: Path) -> None:
        result = AmesHousingLoader(synthetic_csv, validate_shape=False).load()
        # LotFrontage row 2 is `?` in the fixture
        assert pd.isna(result.frame.loc[1, "LotFrontage"])

    def test_legit_na_columns_get_string_na(self, synthetic_csv: Path) -> None:
        # PoolQC=`?` for rows 0,1,2,4 means "no pool" → must be filled
        # with "NA" so the encoder treats it as a category, not a missing.
        result = AmesHousingLoader(synthetic_csv, validate_shape=False).load()
        assert (result.frame["PoolQC"] == "NA").sum() == 4
        assert result.frame.loc[3, "PoolQC"] == "Ex"
        assert result.frame["PoolQC"].isna().sum() == 0

    def test_numeric_categoricals_coerced_to_string(self, synthetic_csv: Path) -> None:
        # MSSubClass is int on disk but a category by meaning.
        result = AmesHousingLoader(synthetic_csv, validate_shape=False).load()
        assert pd.api.types.is_string_dtype(result.frame["MSSubClass"])
        # Values preserved (just dtype-converted).
        assert result.frame.loc[0, "MSSubClass"] == "60"

    def test_missing_target_raises(self, tmp_path: Path) -> None:
        csv = tmp_path / "no_target.csv"
        csv.write_text("Id,LotFrontage\n1,65\n")
        loader = AmesHousingLoader(csv, validate_shape=False)
        with pytest.raises(ValueError, match="Target column 'SalePrice' missing"):
            loader.load()

    def test_missing_file_raises_filenotfound(self, tmp_path: Path) -> None:
        loader = AmesHousingLoader(tmp_path / "absent.csv")
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_shape_validation_off_by_default_fixture(self, synthetic_csv: Path) -> None:
        # Default validate_shape=True against a 5-row fixture must complain.
        loader = AmesHousingLoader(synthetic_csv)  # validate_shape=True
        with pytest.raises(ValueError, match="Unexpected shape"):
            loader.load()


@pytest.mark.integration
class TestRealAmesCsv:
    """Smoke tests against the real ``data/raw/house_prices.csv`` if present.

    These run only when the file is available locally. We use
    ``pytest.mark.integration`` so they are
    visible and de-selectable.
    """

    @pytest.fixture
    def real_csv(self) -> Path:
        # Walk up to the repo root since tests can be invoked from anywhere.
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "data" / "raw" / "house_prices.csv"
            if candidate.exists():
                return candidate
        pytest.skip("data/raw/house_prices.csv not available locally")

    def test_real_file_matches_expected_shape(self, real_csv: Path) -> None:
        result = AmesHousingLoader(real_csv).load()
        assert result.frame.shape == EXPECTED_RAW_SHAPE

    def test_every_legit_na_column_has_string_na(self, real_csv: Path) -> None:
        result = AmesHousingLoader(real_csv).load()
        for col in NA_AS_CATEGORY.intersection(result.frame.columns):
            assert result.frame[col].isna().sum() == 0, (
                f"{col} should have no NaN after the loader applies the legit-NA convention"
            )

    def test_actual_missing_columns_still_have_nan(self, real_csv: Path) -> None:
        # LotFrontage is a real missing — the loader must NOT touch it.
        result = AmesHousingLoader(real_csv).load()
        assert result.frame["LotFrontage"].isna().sum() > 0
