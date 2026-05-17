"""Tests for ``hou53_ml.io.schema``."""

import pytest
from hou53_ml.constants import NUMERIC_BUT_CATEGORICAL
from hou53_ml.io.schema import (
    NOMINAL_FEATURES,
    NUMERIC_FEATURES,
    ORDINAL_QUALITY_FEATURES,
    Schema,
)


class TestSchemaConstruction:
    def test_default_yields_79_modeling_features(self) -> None:
        schema = Schema.default()
        assert len(schema.all_features) == 79

    def test_default_includes_target_and_id_in_expected_columns(self) -> None:
        schema = Schema.default()
        expected = schema.expected_columns
        assert expected[0] == "Id"
        assert expected[-1] == "SalePrice"
        assert len(expected) == 81

    def test_categorical_features_union(self) -> None:
        schema = Schema.default()
        cats = set(schema.categorical_features)
        assert cats == set(schema.ordinal_quality + schema.ordinal_other + schema.nominal)

    def test_no_overlap_between_groups(self) -> None:
        schema = Schema.default()
        groups = [
            set(schema.numeric),
            set(schema.temporal),
            set(schema.ordinal_quality),
            set(schema.ordinal_other),
            set(schema.nominal),
        ]
        for i, group in enumerate(groups):
            for j, other in enumerate(groups):
                if i == j:
                    continue
                assert group.isdisjoint(other), f"groups {i} and {j} share {group & other}"


class TestSchemaCovers:
    def test_passes_when_disk_matches_schema(self) -> None:
        schema = Schema.default()
        # The expected_columns view IS the canonical column list, so this
        # must pass trivially.
        schema.assert_covers(list(schema.expected_columns))

    def test_raises_when_columns_missing_on_disk(self) -> None:
        schema = Schema.default()
        truncated = list(schema.expected_columns)[:-2]  # drop last 2
        with pytest.raises(ValueError, match="in schema but not on disk"):
            schema.assert_covers(truncated)

    def test_raises_when_unknown_columns_on_disk(self) -> None:
        schema = Schema.default()
        extended = [*schema.expected_columns, "MysteryColumn"]
        with pytest.raises(ValueError, match="on disk but not in schema"):
            schema.assert_covers(extended)


class TestSchemaInvariants:
    def test_numeric_but_categorical_lives_in_nominal_group(self) -> None:
        # MSSubClass / MoSold / YrSold are numeric on disk but the schema
        # routes them through the nominal branch (because the encoder
        # treats them as categories, not magnitudes).
        for col in NUMERIC_BUT_CATEGORICAL:
            assert col in NOMINAL_FEATURES, f"{col} should be in NOMINAL_FEATURES, not numeric"
            assert col not in NUMERIC_FEATURES, (
                f"{col} must not be in NUMERIC_FEATURES (it would be treated as a magnitude)"
            )

    def test_quality_columns_use_documented_scale(self) -> None:
        # Every column in the Ex/Gd/TA/Fa/Po scale is listed in the
        # ORDINAL_QUALITY_FEATURES tuple — the encoder will iterate over
        # exactly this tuple in Phase 2.
        expected = {
            "ExterQual",
            "ExterCond",
            "BsmtQual",
            "BsmtCond",
            "HeatingQC",
            "KitchenQual",
            "FireplaceQu",
            "GarageQual",
            "GarageCond",
            "PoolQC",
        }
        assert set(ORDINAL_QUALITY_FEATURES) == expected
